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

import requests
from requests.exceptions import RequestException


class InvenioClient:
    """Client for interacting with Invenio-RDM API."""
    
    def __init__(self, base_url: str, access_token: str, custom_field_namespace: str = "domain"):
        """
        Initialize the Invenio client.
        
        Args:
            base_url: Base URL of the Invenio-RDM instance (e.g., https://data.ae.ic.ac.uk)
            access_token: Personal access token for authentication
            custom_field_namespace: Namespace for custom fields in Invenio (default: "domain")
                                   Must match the configuration in your Invenio instance
        """
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.custom_field_namespace = custom_field_namespace
        self.session = requests.Session()
        self.session.verify = True
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'ae-uploader/1.0 (Imperial College London)'
        })
        
        # Auto-detect if we need /api prefix (production with HAProxy) or not (local dev)
        self._api_prefix = self._detect_api_prefix()
    
    def _detect_api_prefix(self) -> str:
        """
        Auto-detect if the Invenio instance uses /api prefix or not.
        
        Production instances with HAProxy use /api, local dev instances don't.
        
        Returns:
            "/api" or "" depending on instance configuration
        """
        try:
            # Try with /api prefix first (production setup)
            response = self.session.get(f"{self.base_url}/api/records", timeout=5)
            if response.status_code in [200, 403, 401]:
                return "/api"
            
            # Try without /api prefix (local dev setup)
            response = self.session.get(f"{self.base_url}/records", timeout=5)
            if response.status_code in [200, 403, 401]:
                return ""
            
            # Default to /api if both fail
            return "/api"
        except RequestException:
            # Default to /api if detection fails
            return "/api"
    
    def test_connection(self) -> bool:
        """
        Test connection to Invenio-RDM instance.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}{self._api_prefix}/records")
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
        
        url = f"{self.base_url}{self._api_prefix}/records"
        
        response = self.session.post(url, json=invenio_metadata)
        response.raise_for_status()
        
        return response.json()
    
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
        
        # Start file upload
        url = f"{self.base_url}{self._api_prefix}/records/{draft_id}/draft/files"
        
        # Initialize file
        init_response = self.session.post(
            url,
            json=[{"key": filename}]
        )
        init_response.raise_for_status()
        
        # Upload file content
        upload_url = f"{url}/{filename}/content"
        
        with open(file_path, 'rb') as f:
            upload_response = self.session.put(
                upload_url,
                data=f,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=(30, None)  # 30s connect, unlimited read for large file streaming
            )
            upload_response.raise_for_status()
        
        # Commit file
        commit_response = self.session.post(f"{url}/{filename}/commit")
        commit_response.raise_for_status()
        
        return commit_response.json()
    
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
        url = f"{self.base_url}{self._api_prefix}/records/{draft_id}/draft/actions/publish"
        
        response = self.session.post(url)
        response.raise_for_status()
        
        return response.json()
    
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
        
        # Add funding if present
        if "funding" in metadata:
            invenio_metadata["metadata"]["funding"] = metadata["funding"]
        
        # Add domain-specific custom fields
        if "domain" in metadata:
            # Import conversion function
            try:
                from ae_uploader.schemas.domain import to_invenio_custom_fields
                # Convert nested domain structure to flattened Invenio format
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
        url = f"{self.base_url}{self._api_prefix}/records/{record_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()


def create_client_from_env() -> InvenioClient:
    """
    Create an InvenioClient using environment variables.
    
    Expects:
        INVENIO_URL: Base URL of Invenio instance
        INVENIO_TOKEN: Access token
        
    Returns:
        Configured InvenioClient instance
        
    Raises:
        ValueError: If required environment variables are not set
    """
    url = os.environ.get('INVENIO_URL')
    token = os.environ.get('INVENIO_TOKEN')
    
    if not url:
        raise ValueError("INVENIO_URL environment variable not set")
    if not token:
        raise ValueError("INVENIO_TOKEN environment variable not set")
    
    return InvenioClient(url, token)
