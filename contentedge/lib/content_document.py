import json
import requests
import urllib3
import warnings
from copy import deepcopy

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

    def retrieve_document(self, object_id: str) -> str:
        """Get a viewer URL for a document using the Hostviewer endpoint.

        Uses the endpoint: POST /mobius/rest/hostviewer
        (createHostViewerURLPost) which returns a URL to view the document
        in the browser instead of downloading it.

        Args:
            object_id: The encrypted objectId returned by a search.

        Returns:
            The viewer URL string for the document.
        """
        url = f"{self.base_url}/mobius/rest/hostviewer"

        headers = deepcopy(self.headers)
        headers["Content-Type"] = "application/json"

        payload = {
            "objectId": object_id,
            "repositoryId": self.repo_id,
        }

        self.logger.info("--------------------------------")
        self.logger.info("Method : retrieve_document (hostviewer)")
        self.logger.debug(f"URL : {url}")

        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=60)

        if response.status_code != 200:
            self.logger.error(f"Hostviewer failed: HTTP {response.status_code} — {response.text[:300]}")
            raise ValueError(f"Failed to get viewer URL: HTTP {response.status_code}")

        data = response.json()
        viewer_url = data.get("url") or data.get("viewerUrl") or data.get("hostViewerUrl", "")

        if not viewer_url:
            self.logger.error(f"No viewer URL in response: {json.dumps(data)[:300]}")
            raise ValueError("Hostviewer response did not contain a viewer URL")

        self.logger.info(f"Viewer URL obtained: {viewer_url[:200]}")
        return viewer_url

    def delete_document(self, document_id: str) -> int:
        """Delete a document from the Content Repository by its document ID."""
        delete_url = f"{self.repo_url}/repositories/{self.repo_id}/documents?documentid={document_id}"
        self.logger.info("--------------------------------")
        self.logger.info("Method : delete_document")
        self.logger.debug(f"URL : {delete_url}")

        response = requests.delete(delete_url, headers=self.headers, verify=False)
        self.logger.debug(response.text)
        return response.status_code
