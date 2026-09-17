"""
Command-line interface for ae-uploader.

This module provides the CLI commands for uploading research data to Invenio-RDM.
"""

import sys
import os
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files

import click
import requests

from .validate import validate_metadata_file, validate_with_hints, ValidationError, load_schema
from .client import (
    DEFAULT_COMMUNITY,
    DEFAULT_URL,
    InvenioClient,
    normalise_base_url,
    parse_community_list,
)
from .prompts import prompt_secret
from .config import (
    CredentialStorageResult,
    load_config,
    delete_token,
    load_token,
    save_config,
    save_token,
    user_config_path,
)
from .completion import (
    SUPPORTED_SHELLS,
    completion_script,
    detect_shell,
    echo_install_result,
    install_completion,
    is_completion_installed,
)


def _get_directory_size(directory: Path) -> int:
    """Calculate total size of directory in bytes."""
    total_size = 0
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            total_size += file_path.stat().st_size
    return total_size


def _format_bytes(size: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def _format_exception(exc: Exception) -> str:
    """Format request exceptions with API response details when available."""
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        response = exc.response
        try:
            data = response.json()
        except ValueError:
            text = response.text.strip()
            return f"{exc}: {text}" if text else str(exc)

        message = data.get("message")
        errors = data.get("errors", [])
        if errors:
            details = []
            for error in errors:
                field = error.get("field", "unknown")
                messages = ", ".join(error.get("messages", []))
                details.append(f"{field}: {messages}")
            detail_text = "; ".join(details)
            if message:
                return f"{message} ({detail_text})"
            return detail_text
        if message:
            return f"{exc}: {message}"
    return str(exc)


def _is_auth_http_error(exc: Exception) -> bool:
    """Return True for HTTP errors that usually mean missing/invalid permissions."""
    return (
        isinstance(exc, requests.exceptions.HTTPError)
        and exc.response is not None
        and exc.response.status_code in {401, 403}
    )


def _normalise_url_or_exit(url: str) -> str:
    """Normalise an Invenio base URL, exiting with a clear error if invalid."""
    try:
        return normalise_base_url(url)
    except ValueError as e:
        click.echo(f"[ERROR] Invalid Invenio URL: {e}", err=True)
        sys.exit(1)


def _echo_draft_auth_hints(url: str) -> None:
    click.echo("[HINT] Draft creation was refused by the server.", err=True)
    click.echo(
        "   Check that ae-upload has the token for this Invenio instance.",
        err=True,
    )
    click.echo(
        "   Run ae-upload configure or set INVENIO_TOKEN for this command.",
        err=True,
    )
    click.echo(
        f"   If needed, create a fresh token with deposit:write at {url}/account/settings/applications/tokens/new/",
        err=True,
    )


def _configured_communities_from_env(
    stored_config: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Read the optional community allowlist from env or user config."""
    communities = parse_community_list(os.environ.get("INVENIO_COMMUNITIES"))
    if communities:
        return communities

    if stored_config:
        communities = parse_community_list(
            ",".join(stored_config.get("allowed_communities") or [])
        )
        if communities:
            return communities

    community = (os.environ.get("INVENIO_COMMUNITY") or "").strip()
    if not community and stored_config:
        community = (stored_config.get("community") or "").strip()
    return [community] if community else []


def _default_community_from_env(
    allowed_communities: Optional[List[str]] = None,
    stored_config: Optional[Dict[str, Any]] = None,
) -> str:
    """Resolve the default target community from env or user config."""
    community = (os.environ.get("INVENIO_COMMUNITY") or "").strip()
    if community:
        return community
    if stored_config:
        community = (stored_config.get("community") or "").strip()
        if community:
            return community
    if allowed_communities:
        return allowed_communities[0]
    return DEFAULT_COMMUNITY


def _save_user_credentials(
    url: str,
    token: str,
    namespace: str,
    community: str,
    allowed_communities: Optional[List[str]],
    allow_token_file: bool = False,
) -> tuple[Path, CredentialStorageResult]:
    """Save non-secret config plus token using the safest available backend."""
    config_path = save_config(url, namespace, community, allowed_communities)
    token_storage = save_token(url, token, allow_file=allow_token_file)
    return config_path, token_storage


def _echo_token_storage(token_storage: CredentialStorageResult) -> None:
    """Explain where the token was saved, or why it was not."""
    if token_storage.method == "keyring":
        click.echo("[OK] Token saved to the system credential store")
    elif token_storage.method == "file":
        click.echo(f"[OK] Token saved to {token_storage.path}")
        if token_storage.warning:
            click.echo(f"[WARNING] {token_storage.warning}", err=True)
    else:
        click.echo(f"[INFO] {token_storage.warning}")
        click.echo("   You will be asked for the token each time you upload,")
        click.echo("   or you can set INVENIO_TOKEN for a single command.")
        click.echo(
            "   To save it in a file readable only by your account instead, run: "
            "ae-upload configure --token-file"
        )


from . import __version__


@click.group()
@click.version_option(version=__version__)
def cli():
    """
    AE Uploader - CLI tool for uploading research data to Invenio-RDM.
    
    This tool validates metadata against a JSON schema and uploads
    datasets with their metadata to an Invenio-RDM repository.
    
    Supports fluid mechanics and structural mechanics
    data from the Department of Aeronautics.
    """
    pass


@cli.command()
@click.argument('data_path', type=click.Path(exists=True))
@click.option('--token', '-t', help='Invenio access token', envvar='INVENIO_TOKEN')
@click.option('--url', '-u', help='Invenio base URL', envvar='INVENIO_URL')
@click.option('--namespace', '-n', help='Custom field namespace',
              envvar='CUSTOM_FIELD_NAMESPACE')
@click.option('--community', '-c', help='Community ID or slug for submission')
@click.option('--metadata', '-m', 
              type=click.Path(exists=True),
              help='Path to metadata.json (default: metadata.json inside DATA_PATH, or next to it for a single file)')
@click.option('--zip/--no-zip', 'zip_upload', default=False,
              help='Upload directories as a single zip archive instead of individual files')
@click.option('--draft-only', 'draft_only_requested', is_flag=True,
              help='Keep as editable draft after upload. This is the default.')
@click.option('--submit-review', is_flag=True,
              help='Advanced: submit the uploaded draft for community review after upload.')
@click.option('--save-credentials', is_flag=True,
              help='Save credentials to the user config store')
@click.option('--schema', '-s', type=click.Path(exists=True),
              help='Path to custom JSON schema file')
@click.option('--insecure', is_flag=True, help='Disable SSL verification (not recommended)')
@click.option('--auto-index', is_flag=True,
              help='Automatically generate and upload byte-offset index for selective downloads')
@click.option('--index-pattern', 
              help='Glob pattern for multi-file indexing (e.g., "*.h5") - used with --auto-index')

def upload(data_path: str, 
           token: Optional[str],
           url: Optional[str],
           namespace: Optional[str],
           community: Optional[str],
           metadata: Optional[str],
           zip_upload: bool,
           draft_only_requested: bool,
           submit_review: bool,
           save_credentials: bool,
           schema: Optional[str],
           insecure: bool,
           auto_index: bool,
           index_pattern: Optional[str]):
    """
    Upload a file or directory to Invenio-RDM.
    
    DATA_PATH can be either a single file or a directory containing multiple files.
    
    \b
    Examples:
      ae-upload upload ./data.h5 --metadata metadata.json
      ae-upload upload ./my_simulation_data --token YOUR_TOKEN --url https://invenio.example.org
      ae-upload upload ./my_simulation_data --zip

    The command looks for metadata.json, validates it, creates a draft record,
    uploads the selected file(s), and keeps the record as a draft by default.
    """
    # Routine credentials live in the user config directory and token store.
    stored_config = load_config()
    
    # Check for required credentials - CLI/env overrides user config.
    if not url:
        url = os.environ.get('INVENIO_URL') or stored_config.get("url")
    raw_url = url
    if url:
        url = _normalise_url_or_exit(url)
    if not namespace:
        namespace = (
            os.environ.get('CUSTOM_FIELD_NAMESPACE')
            or stored_config.get("namespace")
            or "domain"
        )
    if not token:
        token = os.environ.get('INVENIO_TOKEN')
    if not token and url:
        # Tokens saved before URL normalisation are keyed by the raw URL.
        token = load_token(url) or load_token(raw_url)

    allowed_communities = _configured_communities_from_env(stored_config)
    if community is None:
        community = _default_community_from_env(allowed_communities, stored_config)
    community = (community or '').strip()

    if allowed_communities and not community:
        click.echo("[ERROR] Refusing upload without an approved community.", err=True)
        click.echo(
            "   Configure INVENIO_COMMUNITY or choose one of the approved values "
            "with --community <community-id-or-slug>.",
            err=True,
        )
        click.echo(
            f"   Approved communities: {', '.join(allowed_communities)}",
            err=True,
        )
        sys.exit(1)

    if draft_only_requested and submit_review:
        click.echo("[ERROR] Choose either --draft-only or --submit-review, not both.", err=True)
        sys.exit(1)

    draft_only = not submit_review

    if submit_review and not community:
        click.echo("[ERROR] Cannot submit for review without a configured community.", err=True)
        click.echo("   Direct publish without review is disabled.", err=True)
        click.echo("   Configure INVENIO_COMMUNITY or use --community <community-id-or-slug>.", err=True)
        sys.exit(1)
    
    # Prompt for URL if not provided
    if not url:
        url = click.prompt('Invenio-RDM instance URL', 
                          type=str,
                          default=DEFAULT_URL)
        url = _normalise_url_or_exit(url)

    # Prompt for token if not provided (input is masked for security)
    if not token:
        click.echo("\nYou can get an access token from your Invenio profile:")
        click.echo(f"  {url}/account/settings/applications/tokens/new/")
        token = prompt_secret('\nInvenio access token')
    
    # Save credentials if requested
    if save_credentials and url and token:
        config_path, token_storage = _save_user_credentials(
            url, token, namespace, community, allowed_communities
        )
        click.echo(f"[OK] Configuration saved to {config_path}")
        _echo_token_storage(token_storage)
    
    # Determine if data_path is a file or directory
    path = Path(data_path)
    is_single_file = path.is_file()
    
    # Find metadata file
    if metadata:
        metadata_path = Path(metadata)
    else:
        # For single files, look in the same directory; for directories, look inside
        if is_single_file:
            metadata_path = path.parent / "metadata.json"
        else:
            metadata_path = path / "metadata.json"
    
    if not metadata_path.exists():
        location = path.parent if is_single_file else path
        click.echo(f"[ERROR] metadata.json not found in {location}", err=True)
        click.echo("   Use --metadata to specify a different location", err=True)
        sys.exit(1)
    
    click.echo(f"[INFO] Validating metadata from {metadata_path}...")
    
    # Load custom schema if provided
    custom_schema = None
    if schema:
        try:
            with open(schema, 'r') as f:
                custom_schema = json.load(f)
            click.echo(f"[INFO] Using custom schema from {schema}")
        except Exception as e:
            click.echo(f"[ERROR] Failed to load custom schema: {e}", err=True)
            sys.exit(1)

    # Validate metadata
    try:
        is_valid, errors, hints = validate_with_hints(
            json.loads(metadata_path.read_text()),
            schema=custom_schema
        )
        
        if not is_valid:
            click.echo("[FAILED] Validation failed:", err=True)
            for error in errors:
                click.echo(f"   - {error}", err=True)
            
            if hints:
                click.echo("\n[HINTS]", err=True)
                for hint in hints:
                    click.echo(f"   - {hint}", err=True)
            
            sys.exit(1)
        
        click.echo("[OK] Metadata is valid!")
        
    except json.JSONDecodeError as e:
        click.echo(f"[ERROR] Invalid JSON in metadata file: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"[ERROR] Validation error: {e}", err=True)
        sys.exit(1)
    
    # Load metadata for upload
    metadata_dict = json.loads(metadata_path.read_text())
    
    # Initialise Invenio client
    click.echo(f"\n[INFO] Connecting to {url}...")
    client = InvenioClient(
        url,
        token,
        namespace,
        community,
        allowed_communities=allowed_communities,
    )

    # Apply the insecure flag
    if insecure:
        client.session.verify = False
        click.echo("[WARNING] SSL verification is disabled. This is not recommended.", err=True)
    
    if not client.test_connection():
        click.echo(f"[ERROR] Cannot connect to Invenio instance at {url}", err=True)
        if client.last_connection_error:
            click.echo(f"   {client.last_connection_error}", err=True)
        click.echo("   Check your URL and token", err=True)
        sys.exit(1)
    
    click.echo("[OK] Connected!")

    if community:
        try:
            client.resolve_submission_community(community)
        except Exception as e:
            click.echo(
                f"[ERROR] Invalid target community: {_format_exception(e)}",
                err=True,
            )
            sys.exit(1)
    
    # Create draft
    click.echo("\n[INFO] Creating draft record...")
    try:
        draft = client.create_draft(metadata_dict)
        draft_id = draft['id']
        click.echo(f"[OK] Draft created with ID: {draft_id}")
    except Exception as e:
        click.echo(f"[ERROR] Error creating draft: {_format_exception(e)}", err=True)
        if _is_auth_http_error(e):
            _echo_draft_auth_hints(url)
        sys.exit(1)
    
    # Generate index if requested
    index_file = None
    if auto_index:
        click.echo("\n[INFO] Generating byte-offset index...")
        try:
            from .indexer import IndexGenerator, MultiFileIndexGenerator, save_index

            if is_single_file:
                # Generate index for single file
                index_file = path.parent / f"{path.stem}_index.json"
                index = IndexGenerator.generate(path)
                save_index(index, index_file)
                click.echo(f"[OK] Index generated: {index_file.name}")
                click.echo(f"  Index size: {_format_bytes(index_file.stat().st_size)}")
            else:
                # Generate master index for directory
                index_file = path / f"{path.name}_index.json"
                master_index = MultiFileIndexGenerator.generate_master_index(
                    path,
                    pattern=index_pattern,
                    strategy='master'
                )
                save_index(master_index, index_file)
                click.echo(f"[OK] Master index generated: {index_file.name}")
                click.echo(f"  Total files indexed: {master_index['total_files']}")
                click.echo(f"  Index size: {_format_bytes(index_file.stat().st_size)}")
        except ImportError as e:
            click.echo(f"[WARNING] Could not generate index: {e}", err=True)
            if 'h5py' in str(e):
                click.echo("[HINT] Install required library: pip install h5py", err=True)
            elif 'netCDF4' in str(e):
                click.echo("[HINT] Install required library: pip install netCDF4", err=True)
            elif 'numpy' in str(e).lower():
                click.echo("[HINT] Install required library: pip install numpy", err=True)
            click.echo("[WARNING] Continuing without index...", err=True)
            auto_index = False
        except Exception as e:
            click.echo(f"[WARNING] Index generation failed: {e}", err=True)
            click.echo("[WARNING] Continuing without index...", err=True)
            auto_index = False
    
    # Upload files
    if is_single_file:
        # Single file upload
        file_size = path.stat().st_size
        click.echo(f"\n[INFO] File size: {_format_bytes(file_size)}")
        click.echo(f"[INFO] Uploading file {path.name}...")
        try:
            uploaded = client.upload_file(draft_id, str(path))
            click.echo(f"[OK] Uploaded 1 file")
            
            # Upload index if generated
            if auto_index and index_file and index_file.exists():
                click.echo(f"[INFO] Uploading index file...")
                client.upload_file(draft_id, str(index_file))
                click.echo(f"[OK] Uploaded index file: {index_file.name}")
        except Exception as e:
            click.echo(f"[ERROR] Error uploading file: {e}", err=True)
            sys.exit(1)
    else:
        # Directory upload
        dir_size = _get_directory_size(path)
        uploadable_files = InvenioClient.uploadable_files(str(path))
        upload_mode = "single zip archive" if zip_upload else "individual files"
        click.echo(f"\n[INFO] Directory size: {_format_bytes(dir_size)}")
        click.echo(f"[INFO] Uploadable files: {len(uploadable_files)}")
        click.echo(f"[INFO] Upload mode: {upload_mode}")
        if not uploadable_files:
            click.echo(
                "[WARNING] No uploadable files found. metadata.json and hidden files are skipped.",
                err=True,
            )
        elif zip_upload:
            click.echo("[INFO] Creating zip archive before upload...")

        click.echo(f"\n[INFO] Uploading files from {path}...")
        try:
            def report_upload_progress(file_path: Path, index: int, total: int) -> None:
                relative_path = file_path.relative_to(path)
                file_size = _format_bytes(file_path.stat().st_size)
                upload_name = file_path.name
                if str(relative_path) == upload_name:
                    click.echo(f"   [{index}/{total}] Uploading {relative_path} ({file_size})")
                else:
                    click.echo(
                        f"   [{index}/{total}] Uploading {relative_path} as {upload_name} "
                        f"({file_size})"
                    )

            uploaded = client.upload_directory(
                draft_id, 
                str(path),
                create_zip=zip_upload,
                progress_callback=None if zip_upload else report_upload_progress,
            )
            uploaded_label = "archive" if zip_upload else "file(s)"
            click.echo(f"[OK] Uploaded {len(uploaded)} {uploaded_label}")
            
            # Upload index if generated and not already in directory
            if auto_index and index_file and index_file.exists():
                # Check if index was already uploaded as part of directory
                if not any(f.get('key', '').endswith('_index.json') for f in uploaded):
                    click.echo(f"[INFO] Uploading index file...")
                    client.upload_file(draft_id, str(index_file))
                    click.echo(f"[OK] Uploaded index file: {index_file.name}")
        except Exception as e:
            click.echo(f"[ERROR] Error uploading files: {e}", err=True)
            sys.exit(1)
    
    # Pre-select community on draft so users can continue in UI without
    # manually choosing the community later.
    if draft_only and community:
        click.echo("\n[INFO] Setting draft community...")
        try:
            if hasattr(client, "set_draft_submission_community"):
                client.set_draft_submission_community(
                    draft_id,
                    community_id=community,
                )
                click.echo(f"[OK] Draft linked to community: {community}")
        except Exception as e:
            click.echo(
                f"[WARNING] Could not pre-select draft community: {_format_exception(e)}",
                err=True,
            )
            click.echo(
                "          You can still choose the community manually in the UI.",
                err=True,
            )

    # Submit for review now, or keep as an editable draft with the community set.
    if draft_only:
        click.echo(f"\n[OK] Draft created successfully!")
        click.echo(f"   View at: {url}/uploads/{draft_id}")
        click.echo("   Review the draft in the UI, then submit it for community review when ready.")
        if auto_index:
            click.echo(f"   ✨ Byte-offset index included for selective downloads")
    else:
        click.echo("\n[INFO] Submitting draft for community review...")
        try:
            review_request = client.submit_draft_for_review(
                draft_id,
                community_id=community,
            )
            click.echo("[OK] Draft submitted for community review!")
            click.echo(f"   Community: {community}")
            click.echo(f"   Request ID: {review_request.get('id', 'N/A')}")
            click.echo(f"   View at: {url}/uploads/{draft_id}")
            if auto_index:
                click.echo(f"   ✨ Byte-offset index included for selective downloads")
        except Exception as e:
            click.echo(
                f"[ERROR] Error submitting for review: {_format_exception(e)}",
                err=True,
            )
            click.echo(f"   Draft saved at: {url}/uploads/{draft_id}", err=True)
            sys.exit(1)


@cli.command()
@click.argument('metadata_file', type=click.Path(exists=True))
@click.option('--verbose', '-v', is_flag=True, help='Show detailed validation errors')
@click.option('--schema', '-s', type=click.Path(exists=True),
              help='Path to custom JSON schema file')
def validate(metadata_file: str, verbose: bool, schema: Optional[str]):
    """
    Validate a metadata JSON file against the schema.
    
    Example:
        ae-upload validate metadata.json
        ae-upload validate metadata.json --schema my_schema.json
    """
    click.echo(f"[INFO] Validating {metadata_file}...")
    
    try:
        metadata_path = Path(metadata_file)
        metadata = json.loads(metadata_path.read_text())
        
        custom_schema = None
        if schema:
            with open(schema, 'r') as f:
                custom_schema = json.load(f)
            click.echo(f"[INFO] Using custom schema from {schema}")

        is_valid, errors, hints = validate_with_hints(metadata, schema=custom_schema)
        
        if is_valid:
            click.echo("[OK] Metadata is valid!")
            
            # Show summary
            if verbose:
                click.echo("\nSummary:")
                click.echo(f"  Title: {metadata.get('title', 'N/A')}")
                domain = metadata.get('domain', {})
                click.echo(f"  Discipline: {domain.get('discipline', 'N/A')}")
                click.echo(f"  Creators: {len(metadata.get('creators', []))}")
        else:
            click.echo("[FAILED] Validation failed:", err=True)
            click.echo()
            
            for error in errors:
                click.echo(f"  - {error}", err=True)
            
            if hints:
                click.echo("\n[HINTS]")
                for hint in hints:
                    click.echo(f"  - {hint}")
            
            sys.exit(1)
            
    except json.JSONDecodeError as e:
        click.echo(f"[ERROR] Invalid JSON in file: {e}", err=True)
        sys.exit(1)
    except FileNotFoundError:
        click.echo(f"[ERROR] File not found: {metadata_file}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('observation_type', type=click.Choice(['numerical', 'experimental'], case_sensitive=False))
@click.option('--output', '-o', type=click.Path(), default='metadata.json',
              help='Output file path (default: metadata.json)')
def generate(observation_type: str, output: str):
    """
    Generate a template metadata.json file for fluid dynamics data.
    
    Example:
        ae-upload generate numerical
        ae-upload generate experimental --output my_metadata.json
    """
    from datetime import date
    
    # Base template
    template = {
        "title": "My Fluid Dynamics Dataset",
        "description": "Detailed description of the dataset and methodology.",
        "creators": [
            {
                "person_or_org": {
                    "type": "personal",
                    "given_name": "FirstName",
                    "family_name": "LastName"
                },
                "affiliations": [
                    {
                        "name": "Your Institution"
                    }
                ]
            }
        ],
        "publication_date": date.today().isoformat(),
        "resource_type": {
            "id": "dataset"
        },
        "domain": {
            "discipline": "fluid_dynamics",
            "study": {
                "field": "jet",
                "subfield": ["combustion"],
                "regime": "turbulent",
                "model": "your_model_name",
                "keywords": ["fluid dynamics", "aerodynamics"]
            },
            "observations": [
                {
                    "observation_type": observation_type,
                    "facility": "Your Facility/Code Name",
                    "methods": ["LES" if observation_type == "numerical" else "PIV"],
                    "data_acquisition_settings": "time_resolved",
                    "operating_conditions": {
                        "Mach": 0.7,
                        "Reynolds": 1000000,
                        "Temperature": 300
                    },
                    "observed_quantities": ["velocity", "pressure", "temperature"],
                    "model_description": "Description of your setup",
                    "coordinate_system": "Cartesian: X=streamwise, Y=lateral, Z=vertical",
                    "files": [
                        {
                            "file_name": "data_*.vtk",
                            "file_type": "vtk",
                            "multiple_files_rule": "timestep number",
                            "variables": ["u", "v", "w", "p", "T"],
                            "variable_description": {
                                "u": "velocity in x-direction",
                                "v": "velocity in y-direction",
                                "w": "velocity in z-direction",
                                "p": "pressure",
                                "T": "temperature"
                            },
                            "variable_units": {
                                "u": "m/s",
                                "v": "m/s",
                                "w": "m/s",
                                "p": "Pa",
                                "T": "K"
                            },
                            "storage_format": "binary",
                            "description": "Description of file format and contents"
                        }
                    ]
                }
            ]
        }
    }
    
    # Write template
    output_path = Path(output)
    with open(output_path, 'w') as f:
        json.dump(template, f, indent=2)
    
    click.echo(f"[OK] Template created: {output_path}")
    click.echo(f"  Edit the file and fill in your dataset details")
    click.echo(f"  Then upload with: ae-upload upload ./your_data_directory --metadata {output_path}")


@cli.command()
@click.option('--output', '-o', type=click.Path(), default='schema.json',
              help='Output file path (default: schema.json)')
def schema(output: str):
    """
    Export the default JSON schema for modification.
    """
    schema_data = load_schema()
    with open(output, 'w') as f:
        json.dump(schema_data, f, indent=2)
        
    click.echo(f"[OK] Schema exported to: {output}")
    click.echo(f"  You can modify this file and use it with:")
    click.echo(f"  ae-upload upload ... --schema {output}")


@cli.command()
@click.argument('file_or_directory', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(),
              help='Output index file path (default: <filename>_index.json)')
@click.option('--file-type', '-t', 
              type=click.Choice(['hdf5', 'csv', 'netcdf', 'binary', 'auto'], case_sensitive=False),
              default='auto',
              help='File type (default: auto-detect from extension)')
@click.option('--pattern', '-p',
              help='Glob pattern for multi-file index (e.g., "*.h5", "sim_*.nc")')
@click.option('--strategy', '-s',
              type=click.Choice(['master', 'hierarchical'], case_sensitive=False),
              default='master',
              help='Multi-file index strategy (default: master)')
def generate_index(file_or_directory: str, 
                   output: Optional[str],
                   file_type: str,
                   pattern: Optional[str],
                   strategy: str):
    """
    Generate byte-offset index for selective downloading.
    
    Supports HDF5, CSV, NetCDF, and binary files. The index enables users to
    download specific portions of large files using HTTP Range requests.
    
    Examples:
        # Single HDF5 file
        ae-upload generate-index data.h5
        
        # Single CSV file with custom output
        ae-upload generate-index data.csv --output my_index.json
        
        # Multiple files (creates master index)
        ae-upload generate-index ./simulation_data --pattern "*.h5"
        
        # Hierarchical index for large datasets
        ae-upload generate-index ./data --strategy hierarchical
    """
    path = Path(file_or_directory)
    
    try:
        from .indexer import IndexGenerator, MultiFileIndexGenerator, save_index

        if path.is_file():
            # Single file index
            click.echo(f"[INFO] Generating index for {path.name}...")
            
            # Auto-detect or use specified type
            ftype = None if file_type == 'auto' else file_type
            
            index = IndexGenerator.generate(path, file_type=ftype)
            
            # Determine output path
            if output is None:
                output = path.parent / f"{path.stem}_index.json"
            else:
                output = Path(output)
            
            # Save index
            save_index(index, output)
            
            click.echo(f"[OK] Index created: {output}")
            click.echo(f"  File type: {index['file_type']}")
            click.echo(f"  Index size: {_format_bytes(output.stat().st_size)}")
            click.echo(f"  Data size: {_format_bytes(index['file_size'])}")
            
            if 'datasets' in index:
                click.echo(f"  Datasets: {len(index['datasets'])}")
            elif 'variables' in index:
                click.echo(f"  Variables: {len(index['variables'])}")
            elif 'chunks' in index:
                click.echo(f"  Chunks: {index.get('total_chunks', 'N/A')}")
            
        elif path.is_dir():
            # Multi-file index
            click.echo(f"[INFO] Generating {strategy} index for directory: {path.name}")
            
            if pattern:
                click.echo(f"[INFO] Pattern: {pattern}")
            
            master_index = MultiFileIndexGenerator.generate_master_index(
                path,
                pattern=pattern,
                strategy=strategy
            )
            
            # Determine output path
            if output is None:
                output = path / f"{path.name}_index.json"
            else:
                output = Path(output)
            
            # Save index
            save_index(master_index, output)
            
            click.echo(f"[OK] Index created: {output}")
            click.echo(f"  Strategy: {strategy}")
            click.echo(f"  Total files: {master_index['total_files']}")
            click.echo(f"  Index size: {_format_bytes(output.stat().st_size)}")
            click.echo(f"  Total data size: {_format_bytes(master_index['total_size'])}")
            
        else:
            click.echo(f"[ERROR] Path is neither file nor directory: {path}", err=True)
            sys.exit(1)
            
    except ImportError as e:
        click.echo(f"[ERROR] {e}", err=True)
        click.echo("\n[HINT] Install required library:", err=True)
        if 'h5py' in str(e):
            click.echo("  pip install h5py", err=True)
        elif 'netCDF4' in str(e):
            click.echo("  pip install netCDF4", err=True)
        elif 'numpy' in str(e).lower():
            click.echo("  pip install numpy", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"[ERROR] Failed to generate index: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--url', '-u', help='Invenio base URL (default: the configured URL)')
def logout(url: Optional[str]):
    """
    Remove the saved access token from this computer.

    Non-secret settings (URL, community) are kept. The token itself stays
    valid on the server until you delete it in the Invenio web interface.
    """
    raw_url = url or os.environ.get('INVENIO_URL') or load_config().get("url")
    if not raw_url:
        click.echo("[ERROR] No Invenio URL configured. Use --url to choose one.", err=True)
        sys.exit(1)
    url = _normalise_url_or_exit(raw_url)

    removed = delete_token(url, raw_url)
    if removed:
        for location in removed:
            click.echo(f"[OK] Removed saved token from {location}")
    else:
        click.echo(f"[INFO] No saved token found for {url}")

    if os.environ.get('INVENIO_TOKEN'):
        click.echo(
            "[WARNING] INVENIO_TOKEN is set in your environment; "
            "unset it to stop using that token.",
            err=True,
        )

    click.echo("\nThe token is still valid on the server. To revoke it:")
    click.echo(f"  1. Open {url}/account/settings/applications/")
    click.echo("  2. Delete the token under 'Personal access tokens'")


@cli.command()
def info():
    """
    Show information about the uploader and configuration.
    """
    click.echo(f"AE Uploader v{__version__}")
    click.echo("=" * 50)
    click.echo("\nConfiguration:")
    
    stored_config = load_config()
    raw_url = os.environ.get('INVENIO_URL') or stored_config.get("url")
    url = raw_url or "Not set"
    token = os.environ.get('INVENIO_TOKEN')
    if raw_url:
        try:
            url = normalise_base_url(raw_url)
        except ValueError as e:
            url = f"{raw_url} (invalid: {e})"
        if not token:
            token = load_token(url) or load_token(raw_url)
    namespace = (
        os.environ.get('CUSTOM_FIELD_NAMESPACE')
        or stored_config.get("namespace")
        or "domain"
    )
    allowed_communities = _configured_communities_from_env(stored_config)
    community = _default_community_from_env(allowed_communities, stored_config)

    click.echo(f"  INVENIO_URL: {url}")
    click.echo(
        f"  INVENIO_TOKEN: {'Set' if token else 'Not saved (asked for when uploading)'}"
    )
    click.echo(f"  Metadata namespace: {namespace}")
    click.echo(f"  INVENIO_COMMUNITY: {community}")
    click.echo(
        "  INVENIO_COMMUNITIES: "
        + (", ".join(allowed_communities) if allowed_communities else "Not set")
    )
    click.echo(f"  User config: {user_config_path()}")
    
    if raw_url:
        click.echo("\n[OK] Configuration looks good!")
    else:
        click.echo("\n[WARNING] Missing configuration. Run 'ae-upload configure' to set up credentials")
    
    click.echo("\nSupported disciplines:")
    click.echo("  - fluid_dynamics")
    click.echo("  - structures")
    
    click.echo("\nSupported fields (fluid_dynamics):")
    fluid_fields = ["jet", "boundary_layer", "wake", "combustion", "other"]
    for field in fluid_fields:
        click.echo(f"  - {field}")

    click.echo("\nSupported fields (structures):")
    structures_fields = ["aeroelasticity", "structural_dynamics", "composites", "fracture_fatigue", "other"]
    for field in structures_fields:
        click.echo(f"  - {field}")
    
    click.echo("\nObservation types:")
    click.echo("  - numerical")
    click.echo("  - experimental")


@cli.command()
@click.option('--insecure', is_flag=True, help='Disable SSL verification (not recommended)')
@click.option('--token-file', is_flag=True,
              help='If no system credential store is available, save the token '
                   'in a file readable only by your account instead of not saving it')
def configure(insecure: bool, token_file: bool):
    """
    Configure Invenio-RDM credentials interactively.
    
    This will prompt for your Invenio instance URL and access token,
    then save non-secret settings to the user config directory and the
    token to the system credential store. If no credential store is
    available, the token is not saved and upload asks for it each time
    (unless --token-file is given).
    
    \b
    Examples:
      ae-upload configure
      ae-upload configure --insecure
      ae-upload configure --token-file
    """
    click.echo("=" * 50)
    click.echo("Invenio-RDM Credentials Setup")
    click.echo("=" * 50)
    
    config_path = user_config_path()
    if config_path.exists():
        click.echo(f"\n[WARNING] ae-upload configuration already exists at {config_path}")
        if not click.confirm('Overwrite existing configuration?', default=False):
            click.echo("Configuration cancelled.")
            return
    
    # Prompt for URL
    click.echo("\nStep 1: Invenio-RDM Instance URL")
    click.echo("  Press Enter to use the default shown in brackets")
    while True:
        try:
            url = normalise_base_url(
                click.prompt('\nEnter URL', type=str, default=DEFAULT_URL)
            )
            break
        except ValueError as e:
            click.echo(f"[ERROR] {e}", err=True)
    click.echo(f"  Using {url}")

    # Prompt for token
    click.echo("\nStep 2: Access Token")
    click.echo("  You can create a token at:")
    click.echo(f"  {url}/account/settings/applications/tokens/new/")
    click.echo("\n  The token should have 'deposit:write' permissions")
    token = prompt_secret('\nEnter access token')
    
    # Prompt for advanced community settings only when needed.
    namespace = "domain"
    click.echo("\nStep 3: Upload Destination")
    click.echo(
        f"  Standard uploads use the default repository community "
        f"({DEFAULT_COMMUNITY})."
    )
    community = DEFAULT_COMMUNITY
    allowed_communities = [DEFAULT_COMMUNITY]
    if click.confirm(
        "\nConfigure advanced community options?", default=False
    ):
        click.echo("  Use this only if you need a non-default target or multiple approved communities")
        community = click.prompt(
            '\nEnter default community ID or slug',
            type=str,
            default=DEFAULT_COMMUNITY,
            show_default=True,
        )
        additional_communities = click.prompt(
            '\nEnter additional communities',
            type=str,
            default='',
            show_default=False,
        )
        allowed_communities = parse_community_list(
            ",".join([community, additional_communities])
        )

    # Test connection
    click.echo("\n[INFO] Testing connection...")
    try:
        client = InvenioClient(
            url,
            token,
            namespace,
            community,
            allowed_communities=allowed_communities,
        )

        if insecure:
            client.session.verify = False
            click.echo("[WARNING] SSL verification disabled for connection test")
        try:
            resp = client.session.get(f"{client.base_url}/api/records")
            if resp.status_code in [200, 403]:
                click.echo("[OK] Connection successful!")
            else:
                click.echo(f"[WARNING] Server returned status code: {resp.status_code}")
                click.echo("Check that your URL is correct (should be the base URL, not /api)")
        except Exception as e:
            click.echo(f"[WARNING] Connection failed: {e}")
            click.echo("Check your network connection and URL typo.")

    except Exception as e:
        click.echo(f"[WARNING] Connection test failed: {e}")
        if not click.confirm('\nSave credentials anyway?', default=True):
            click.echo("Configuration cancelled.")
            return
    
    # Save configuration and token
    config_path, token_storage = _save_user_credentials(
        url,
        token,
        namespace,
        community,
        allowed_communities,
        allow_token_file=token_file,
    )
    click.echo(f"\n[OK] Configuration saved to {config_path}")
    _echo_token_storage(token_storage)
    click.echo("\nFor each new dataset:")
    click.echo("  ae-upload export-form --output metadata_form.html")
    click.echo("  # open metadata_form.html in your browser, download metadata.json")
    click.echo("  # and save it inside ./my_data_directory")
    click.echo("  ae-upload upload ./my_data_directory")
    click.echo("\nFor scripts or temporary credentials, use environment variables:")
    click.echo("  INVENIO_TOKEN=... ae-upload upload ./data")
    _offer_completion_install()


def _offer_completion_install() -> None:
    """Offer to enable tab completion during interactive setup."""
    shell = detect_shell()
    if not shell or not sys.stdin.isatty() or is_completion_installed(shell):
        return
    click.echo("\nTab completion lets you press TAB to complete ae-upload commands and options.")
    if not click.confirm(f"Enable tab completion for {shell}?", default=True):
        click.echo("  You can enable it later with: ae-upload completion --install")
        return
    try:
        echo_install_result(install_completion(cli, shell))
    except OSError as e:
        click.echo(f"[WARNING] Could not enable tab completion: {e}", err=True)


@cli.command()
@click.argument('shell', required=False, type=click.Choice(SUPPORTED_SHELLS))
@click.option('--install', is_flag=True,
              help='Set up completion for your shell instead of printing the script')
def completion(shell: Optional[str], install: bool):
    """
    Enable TAB completion for ae-upload commands and options.

    SHELL is bash, zsh or fish (default: detected from $SHELL).

    \b
    Examples:
      ae-upload completion --install
      ae-upload completion zsh > ~/.ae-upload-completion.zsh
    """
    shell = shell or detect_shell()
    if not shell:
        click.echo(
            "[ERROR] Could not detect a supported shell. "
            f"Specify one of: {', '.join(SUPPORTED_SHELLS)}",
            err=True,
        )
        sys.exit(1)

    if not install:
        click.echo(completion_script(cli, shell), nl=False)
        return

    try:
        echo_install_result(install_completion(cli, shell))
    except OSError as e:
        click.echo(f"[ERROR] Could not enable tab completion: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--output', '-o', default='metadata_form.html',
              help='Output file path')
def export_form(output: str):
    """
    Export the web-based metadata form.
    
    Exports the HTML form for creating metadata.json files in a web browser.
    The form runs entirely client-side and generates downloadable metadata files.
    """
    output_path = Path(output)
    
    try:
        # Get the HTML file from package data
        form_file = files('ae_uploader').joinpath('web/metadata_form.html')
        form_html = form_file.read_text(encoding='utf-8')
        
        # Write to output file
        with open(output_path, 'w') as f:
            f.write(form_html)
        
        click.echo(f"[OK] Metadata form exported to: {output_path.absolute()}")
        click.echo(f"\nTo use the form:")
        click.echo(f"  firefox {output_path.name}")
        click.echo(f"  # or open in any web browser")
        click.echo(f"\nThe form runs entirely in the browser (no server needed).")
        
    except Exception as e:
        click.echo(f"[ERROR] Failed to export form: {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
