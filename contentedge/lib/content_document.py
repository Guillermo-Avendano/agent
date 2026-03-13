import json
import os
import requests
import urllib3
import warnings
from copy import deepcopy
from urllib.parse import quote

from .content_config import ContentConfig

# Disable https warnings if the http certificate is not valid
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)


class ContentDocument:
    """Retrieve and delete documents from the Content Repository."""

    def __init__(self, content_config):
        if isinstance(content_config, ContentConfig):
            self.repo_url = content_config.repo_url
            self.base_url = content_config.base_url
            self.repo_id = content_config.repo_id
            self.logger = content_config.logger
            self.headers = deepcopy(content_config.headers)
        else:
            raise TypeError("ContentConfig class object expected")

    def retrieve_document(self, object_id: str, output_dir: str, filename: str | None = None) -> str:
        """Download a document from the repository using its objectId.

        Uses the endpoint: GET /mobius/rest/contentstreams?id={objectId}

        Args:
            object_id: The encrypted objectId returned by a search.
            output_dir: Directory where the file will be saved.
            filename: Optional filename. If not provided, one is generated from
                      the Content-Disposition header or a default name.

        Returns:
            Absolute path of the saved file.
        """
        encoded_id = quote(object_id, safe='')
        url = f"{self.base_url}/mobius/rest/contentstreams?id={encoded_id}"

        headers = deepcopy(self.headers)

        self.logger.info("--------------------------------")
        self.logger.info("Method : retrieve_document")
        self.logger.debug(f"URL : {url[:200]}")

        response = requests.get(url, headers=headers, verify=False, timeout=60)

        if response.status_code != 200:
            self.logger.error(f"Retrieve failed: HTTP {response.status_code} — {response.text[:300]}")
            raise ValueError(f"Failed to retrieve document: HTTP {response.status_code}")

        # Determine filename
        if not filename:
            cd = response.headers.get("Content-Disposition", "")
            if "filename=" in cd:
                filename = cd.split("filename=")[-1].strip('" ')
            else:
                # Infer extension from Content-Type
                ct = response.headers.get("Content-Type", "application/octet-stream")
                ext_map = {
                    "application/pdf": ".pdf",
                    "text/plain": ".txt",
                    "image/png": ".png",
                    "image/jpeg": ".jpg",
                }
                ext = ext_map.get(ct, ".bin")
                filename = f"document{ext}"

        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)

        with open(output_path, "wb") as f:
            f.write(response.content)

        self.logger.info(f"Document saved: {output_path} ({len(response.content)} bytes)")
        return output_path

    def delete_document(self, document_id: str) -> int:
        """Delete a document from the Content Repository by its document ID."""
        delete_url = f"{self.repo_url}/repositories/{self.repo_id}/documents?documentid={document_id}"
        self.logger.info("--------------------------------")
        self.logger.info("Method : delete_document")
        self.logger.debug(f"URL : {delete_url}")

        response = requests.delete(delete_url, headers=self.headers, verify=False)
        self.logger.debug(response.text)
        return response.status_code
