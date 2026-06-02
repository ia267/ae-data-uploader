"""
Invenio-RDM client for uploading datasets.

This module handles all API interactions with Invenio-RDM.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import zipfile
import tempfile


DEFAULT_COMMUNITY = "ae-dept-data"


def parse_community_list(value: Optional[str]) -> List[str]:
    """Parse comma-separated community references into a de-duplicated list."""
    communities: List[str] = []
    seen = set()
    for item in (value or "").replace("\n", ",").split(","):
        community = item.strip()
        if not community or community in seen:
            continue
        communities.append(community)
        seen.add(community)
    return communities


import requests
from requests.exceptions import RequestException


class InvenioClient:
    """Client for interacting with Invenio-RDM API."""
    
    def __init__(
        self,
        base_url: str,
        access_token: str,
        custom_field_namespace: str = "domain",
        community: str = DEFAULT_COMMUNITY,
        allowed_communities: Optional[List[str]] = None,
    ):
        """
        Initialise the Invenio client.
        
        Args:
            base_url: Base URL of the Invenio-RDM instance (e.g., https://data.ae.ic.ac.uk)
            access_token: Personal access token for authentication
            custom_field_namespace: Namespace for custom fields in Invenio (default: "domain")
                                   Must match the configuration in your Invenio instance
            community: Default community ID/slug for draft submissions
            allowed_communities: Optional allowlist of community IDs/slugs
                that uploads may target
        """
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.custom_field_namespace = custom_field_namespace
        self.community = community.strip() if community else None
        self.allowed_communities = []
        for community_ref in allowed_communities or []:
            community_ref = community_ref.strip()
            if community_ref and community_ref not in self.allowed_communities:
                self.allowed_communities.append(community_ref)
        self._community_id_cache: Dict[str, str] = {}
        self._draft_cache: Dict[str, Dict[str, Any]] = {}
        self.session = requests.Session()
        self.session.verify = True
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'ae-uploader/1.0 (Imperial College London)'
        })
    
    def test_connection(self) -> bool:
        """
        Test connection to Invenio-RDM instance.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/api/records")
            return response.status_code in [200, 403]  # 403 means auth is working
        except RequestException:
            return False
    
    def create_draft(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a draft record in Invenio-RDM.
        
        Args:
            metadata: Metadata dictionary (must be valid against schema)
            
        Returns:
            Dictionary containing draft information including draft_id
            
        Raises:
            RequestException: If API request fails
        """
        # Transform metadata to Invenio format
        invenio_metadata = self._transform_to_invenio_format(metadata)

        url = f"{self.base_url}/api/records"
        
        response = self.session.post(url, json=invenio_metadata)
        response.raise_for_status()

        draft = response.json()
        self._draft_cache[draft["id"]] = draft
        return draft

    def _normalise_link(self, url: Optional[str]) -> Optional[str]:
        """Convert API links into absolute, non-templated URLs."""
        if not url:
            return None
        cleaned = url.split("{", 1)[0]
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            return cleaned
        if cleaned.startswith("/"):
            return f"{self.base_url}{cleaned}"
        return f"{self.base_url}/{cleaned}"

    def _draft_resource(self, draft_id: str, refresh: bool = False) -> Dict[str, Any]:
        """Return draft payload, preferring cache and falling back to API fetch."""
        if not refresh and draft_id in self._draft_cache:
            return self._draft_cache[draft_id]

        url = f"{self.base_url}/api/records/{draft_id}/draft"
        response = self.session.get(url)
        response.raise_for_status()
        draft = response.json()
        self._draft_cache[draft_id] = draft
        return draft

    @staticmethod
    def _link_value(candidate: Any) -> Optional[str]:
        """Return link URL from either a raw string or an object with href."""
        if isinstance(candidate, str):
            return candidate
        if isinstance(candidate, dict):
            href = candidate.get("href")
            if isinstance(href, str):
                return href
        return None

    @classmethod
    def _get_link(cls, payload: Dict[str, Any], *names: str) -> Optional[str]:
        """Extract the first matching link from payload links."""
        links = payload.get("links", {})
        if not isinstance(links, dict):
            return None

        for name in names:
            direct = cls._link_value(links.get(name))
            if direct:
                return direct

            current: Any = links
            for part in name.split("."):
                if not isinstance(current, dict) or part not in current:
                    current = None
                    break
                current = current[part]

            nested = cls._link_value(current)
            if nested:
                return nested
        return None

    def _resolve_community_id(self, community_ref: str) -> str:
        """Resolve a community UUID or slug to the canonical community UUID."""
        community_ref = community_ref.strip()
        if community_ref in self._community_id_cache:
            return self._community_id_cache[community_ref]

        detail_response = self.session.get(
            f"{self.base_url}/api/communities/{community_ref}"
        )
        if detail_response.status_code == 200:
            resolved_id = detail_response.json()["id"]
            self._community_id_cache[community_ref] = resolved_id
            self._community_id_cache[resolved_id] = resolved_id
            return resolved_id
        if detail_response.status_code != 404:
            detail_response.raise_for_status()

        search_response = self.session.get(
            f"{self.base_url}/api/communities",
            params={"q": f"slug:{community_ref}"},
        )
        search_response.raise_for_status()

        hits = search_response.json().get("hits", {}).get("hits", [])
        if len(hits) == 1:
            resolved_id = hits[0]["id"]
            self._community_id_cache[community_ref] = resolved_id
            self._community_id_cache[resolved_id] = resolved_id
            return resolved_id
        if not hits:
            raise ValueError(
                f"Community '{community_ref}' was not found by ID or slug"
            )
        raise ValueError(
            f"Community slug '{community_ref}' matched multiple communities"
        )

    def _ensure_allowed_community(self, target_community: str, resolved_target_id: str) -> None:
        """Ensure the selected community is within the configured allowlist."""
        if not self.allowed_communities:
            return

        resolved_allowed_ids = set()
        invalid_allowed = []
        for allowed_ref in self.allowed_communities:
            try:
                resolved_allowed_ids.add(self._resolve_community_id(allowed_ref))
            except ValueError:
                invalid_allowed.append(allowed_ref)

        if invalid_allowed:
            raise ValueError(
                "Configured allowed communities were not found: "
                + ", ".join(invalid_allowed)
            )

        if resolved_target_id not in resolved_allowed_ids:
            raise ValueError(
                f"Community '{target_community}' is not in the configured allowlist: "
                + ", ".join(self.allowed_communities)
            )

    def resolve_submission_community(self, community_id: Optional[str] = None) -> str:
        """Resolve and validate the community used for a submission."""
        target_community = (community_id or self.community or "").strip()
        if not target_community:
            raise ValueError("A community ID is required to submit for review")

        resolved_community_id = self._resolve_community_id(target_community)
        self._ensure_allowed_community(target_community, resolved_community_id)
        return resolved_community_id
    
    def upload_file(self, draft_id: str, file_path: str, filename: str = None) -> Dict[str, Any]:
        """
        Upload a file to an existing draft.
        
        Args:
            draft_id: ID of the draft record
            file_path: Path to the file to upload
            filename: Optional custom filename (defaults to basename of file_path)
            
        Returns:
            Dictionary containing file upload information
            
        Raises:
            FileNotFoundError: If file doesn't exist
            RequestException: If API request fails
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if filename is None:
            filename = file_path.name
        
        draft = self._draft_resource(draft_id)
        files_link = self._normalise_link(
            self._get_link(draft, "files")
        )
        if not files_link:
            files_link = f"{self.base_url}/api/records/{draft_id}/draft/files"
        
        # Initialise file
        init_response = self.session.post(
            files_link,
            json=[{"key": filename}]
        )
        init_response.raise_for_status()
        init_payload = init_response.json()

        entry = None
        entries = init_payload.get("entries", [])
        if isinstance(entries, list) and entries:
            # Prefer matching by key for multi-file initialisation responses.
            for candidate in entries:
                if isinstance(candidate, dict) and candidate.get("key") == filename:
                    entry = candidate
                    break
            if entry is None:
                entry = entries[0] if isinstance(entries[0], dict) else None
        elif isinstance(entries, dict):
            if filename in entries and isinstance(entries[filename], dict):
                entry = entries[filename]
            else:
                for candidate in entries.values():
                    if isinstance(candidate, dict):
                        entry = candidate
                        break

        upload_url = None
        commit_url = None
        if entry:
            entry_links = entry.get("links", {})
            upload_url = self._normalise_link(self._link_value(entry_links.get("content")))
            commit_url = self._normalise_link(self._link_value(entry_links.get("commit")))
        if not upload_url:
            upload_url = self._normalise_link(
                self._get_link(init_payload, "content", "actions.content")
            )
        if not commit_url:
            commit_url = self._normalise_link(
                self._get_link(init_payload, "commit", "actions.commit")
            )
        
        # Fallback upload URL for instances not exposing per-file action links.
        if not upload_url:
            upload_url = f"{files_link}/{filename}/content"
        
        with open(file_path, 'rb') as f:
            upload_response = self.session.put(
                upload_url,
                data=f,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=(30, None)  # 30s connect, unlimited read for large file streaming
            )
            upload_response.raise_for_status()

        # Commit may be optional on some deployments; call it only when the API
        # advertises an explicit commit action link.
        if commit_url:
            commit_response = self.session.post(commit_url)
            commit_response.raise_for_status()
            result = commit_response.json()
        else:
            result = upload_response.json() if upload_response.content else {
                "key": filename,
                "status": "uploaded",
            }

        self._draft_resource(draft_id, refresh=True)

        return result
    
    def upload_directory(self, draft_id: str, directory: str, create_zip: bool = True) -> List[Dict[str, Any]]:
        """
        Upload all files from a directory to a draft.
        
        Args:
            draft_id: ID of the draft record
            directory: Path to directory containing files
            create_zip: If True, creates a single zip file; if False, uploads files individually
            
        Returns:
            List of dictionaries containing upload information for each file
            
        Raises:
            FileNotFoundError: If directory doesn't exist
        
        Warning:
            When create_zip=True, a temporary zip file is created in the system temp directory.
            For large datasets (>5GB), this may require significant disk space.
            Consider using create_zip=False for very large datasets.
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        uploaded_files = []
        
        if create_zip:
            # Create a temporary zip file
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.zip', delete=False) as tmp:
                zip_path = tmp.name
            
            try:
                # Create zip archive, excluding metadata files
                excluded_files = {'metadata.json', '.uploadignore'}
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in dir_path.rglob('*'):
                        if file_path.is_file() and file_path.name not in excluded_files and not file_path.name.startswith('.'):
                            # Add file with relative path
                            arcname = file_path.relative_to(dir_path)
                            zipf.write(file_path, arcname)
                
                # Upload the zip file
                zip_filename = f"{dir_path.name}.zip"
                result = self.upload_file(draft_id, zip_path, zip_filename)
                uploaded_files.append(result)
            
            finally:
                # Clean up temporary file
                if os.path.exists(zip_path):
                    os.unlink(zip_path)
        
        else:
            # Upload files individually
            # Skip metadata.json and hidden files
            excluded_files = {'metadata.json', '.uploadignore'}
            for file_path in dir_path.rglob('*'):
                if file_path.is_file() and file_path.name not in excluded_files and not file_path.name.startswith('.'):
                    result = self.upload_file(draft_id, str(file_path))
                    uploaded_files.append(result)
        
        return uploaded_files
    
    def publish_draft(self, draft_id: str) -> Dict[str, Any]:
        """
        Publish a draft record to make it publicly accessible.
        
        Args:
            draft_id: ID of the draft record
            
        Returns:
            Dictionary containing published record information
            
        Raises:
            RequestException: If API request fails
        """
        draft = self._draft_resource(draft_id)
        url = self._normalise_link(
            self._get_link(draft, "publish", "actions.publish")
        )
        if not url:
            url = f"{self.base_url}/api/records/{draft_id}/draft/actions/publish"
        
        response = self.session.post(url)
        response.raise_for_status()

        self._draft_cache.pop(draft_id, None)
        
        return response.json()

    def submit_draft_for_review(
        self,
        draft_id: str,
        community_id: Optional[str] = None,
        review_comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submit a draft to a community review workflow.

        This performs the same 2-step workflow as the Invenio deposit UI:
        1) Create/update review draft state via ``PUT /draft/review``
        2) Submit for review via ``POST /draft/actions/submit-review``

        Args:
            draft_id: ID of the draft record
            community_id: Community ID or slug to submit to
                (defaults to configured client community)
            review_comment: Optional review comment text

        Returns:
            Dictionary containing review request information

        Raises:
            ValueError: If no community is configured/provided
            RequestException: If API request fails
        """
        resolved_community_id = self.resolve_submission_community(community_id)

        draft = self._draft_resource(draft_id)
        review_url = self._normalise_link(
            self._get_link(draft, "review", "actions.review")
        )
        if not review_url:
            review_url = f"{self.base_url}/api/records/{draft_id}/draft/review"

        review_payload = {
            "receiver": {"community": resolved_community_id},
            "type": "community-submission",
        }
        review_response = self.session.put(review_url, json=review_payload)
        review_response.raise_for_status()

        refreshed_draft = self._draft_resource(draft_id, refresh=True)
        submit_url = self._normalise_link(
            self._get_link(
                refreshed_draft,
                "submit_review",
                "submit-review",
                "actions.submit_review",
                "actions.submit-review",
            )
        )
        if not submit_url:
            submit_url = f"{self.base_url}/api/records/{draft_id}/draft/actions/submit-review"

        submit_payload: Dict[str, Any] = {"require_review": True}
        if review_comment:
            submit_payload["payload"] = {
                "content": review_comment,
                "format": "html",
            }

        submit_response = self.session.post(submit_url, json=submit_payload)
        submit_response.raise_for_status()

        self._draft_resource(draft_id, refresh=True)
        return review_response.json()
    
    def _transform_to_invenio_format(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform our fluid dynamics metadata format to Invenio-RDM format.
        
        Args:
            metadata: Metadata in our schema format
            
        Returns:
            Metadata in Invenio-RDM format
        
        Note:
            This method places domain-specific metadata in custom_fields under
            the configured namespace (default: 'domain'). Your Invenio-RDM instance 
            must have this custom field configured in invenio.cfg or via extensions. 
            If not configured, the API may reject the payload or silently drop the 
            custom fields.
            
            Consult your Invenio administrator to ensure the custom field namespace
            is properly registered in the custom fields configuration.
        """
        invenio_metadata = {
            "metadata": {
                "title": metadata["title"],
                "description": metadata["description"],
                "publication_date": metadata["publication_date"],
                "resource_type": metadata["resource_type"],
                "creators": metadata["creators"]
            }
        }
        
        # Add rights/license if present
        if "rights" in metadata:
            invenio_metadata["metadata"]["rights"] = metadata["rights"]

        # Add selected generic Invenio metadata fields if present
        for field_name in ("publisher", "version", "contributors", "related_identifiers"):
            if field_name in metadata:
                invenio_metadata["metadata"][field_name] = metadata[field_name]

        # Add funding if present
        if "funding" in metadata:
            invenio_metadata["metadata"]["funding"] = metadata["funding"]
        
        # Add domain-specific custom fields
        if "domain" in metadata:
            # Import conversion function
            try:
                from ae_uploader.schemas.domain import to_invenio_custom_fields
                # Convert to deployment-specific custom_fields payload format
                invenio_metadata["custom_fields"] = to_invenio_custom_fields(
                    metadata["domain"], 
                    namespace=self.custom_field_namespace
                )
            except ImportError:
                # Fallback: wrap in namespace (legacy behavior)
                invenio_metadata["custom_fields"] = {
                    self.custom_field_namespace: metadata["domain"]
                }
        
        # Enable files if observations contain file metadata
        if "domain" in metadata and "observations" in metadata["domain"]:
            for obs in metadata["domain"]["observations"]:
                if "files" in obs and obs["files"]:
                    invenio_metadata["files"] = {"enabled": True}
                    break
        
        return invenio_metadata
    
    def get_record(self, record_id: str) -> Dict[str, Any]:
        """
        Retrieve a published record.
        
        Args:
            record_id: ID of the record
            
        Returns:
            Dictionary containing record information
        """
        url = f"{self.base_url}/api/records/{record_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()


def create_client_from_env() -> InvenioClient:
    """
    Create an InvenioClient using environment variables.
    
    Expects:
        INVENIO_URL: Base URL of Invenio instance
        INVENIO_TOKEN: Access token
        CUSTOM_FIELD_NAMESPACE: Namespace for custom fields (optional, defaults to "domain")
        INVENIO_COMMUNITY: Default community ID or slug for submissions
            (optional, defaults to "ae-dept-data")
        INVENIO_COMMUNITIES: Optional comma-separated allowlist of approved
            community IDs/slugs for uploads
        
    Returns:
        Configured InvenioClient instance
        
    Raises:
        ValueError: If required environment variables are not set
    """
    url = os.environ.get('INVENIO_URL')
    token = os.environ.get('INVENIO_TOKEN')
    namespace = os.environ.get('CUSTOM_FIELD_NAMESPACE', 'domain')
    community = (os.environ.get('INVENIO_COMMUNITY') or '').strip()
    allowed_communities = parse_community_list(os.environ.get('INVENIO_COMMUNITIES'))
    if not allowed_communities and community:
        allowed_communities = [community]
    if not community:
        if allowed_communities:
            community = allowed_communities[0]
        else:
            community = DEFAULT_COMMUNITY
    
    if not url:
        raise ValueError("INVENIO_URL environment variable not set")
    if not token:
        raise ValueError("INVENIO_TOKEN environment variable not set")
    
    return InvenioClient(
        url,
        token,
        namespace,
        community,
        allowed_communities=allowed_communities,
    )
