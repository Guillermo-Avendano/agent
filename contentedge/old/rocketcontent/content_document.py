import json
from .content_config import ContentConfig
import json
import requests
import urllib3
import warnings
from copy import deepcopy

# Disable https warnings if the http certificate is not valid
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

class ContentDocument:
    """
    ContentDocument provides methods to interact with documents in the Content Repository.
    """

    def __init__(self, content_config):
        """
        Initializes the ContentDocument class with the given configuration.
        Args:
            content_config (ContentConfig): Configuration object with repository connection and authentication details.
        Raises:
            TypeError: If content_config is not an instance of ContentConfig.
        """
        if isinstance(content_config, ContentConfig):
            self.repo_url = content_config.repo_url
            self.repo_id = content_config.repo_id
            self.logger = content_config.logger
            self.headers = deepcopy(content_config.headers)
        else:
            raise TypeError("ContentConfig class object expected")

    def delete_document(self, document_id): 
        """
        Deletes a document from the Content Repository by its document ID.
        Args:
            document_id (str): The ID of the document to delete.
        Returns:
            int: HTTP status code returned by the API.
        Raises:
            ValueError: If an error occurs during the request.
        """
        delete_url = self.repo_url + "/repositories/" + self.repo_id + "/documents?documentid=" + document_id
        self.logger.info("--------------------------------")
        self.logger.info("Method : delete_document")
        self.logger.debug(f"URL : {delete_url}")
        self.logger.debug(f"Headers : {json.dumps(self.headers)}")
        try:
           response = requests.delete(delete_url, headers=self.headers, verify=False)
           self.logger.debug(response.text)
           return response.status_code
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            raise ValueError(f"An error occurred: {e}")