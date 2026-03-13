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

class ContentSmartChat:

    def __init__(self, content_config):
        if isinstance(content_config, ContentConfig):
            self.repo_url = content_config.repo_url
            self.repo_id = content_config.repo_id
            self.logger = content_config.logger
            self.headers = deepcopy(content_config.headers)
        else:
            raise TypeError("ContentConfig class object expected")

    #--------------------------------------------------------------
    def smart_chat(self, user_query, document_ids=None, conversation=""):

        smart_chat_url = self.repo_url + "/conversations"

        smart_chat_object = SmartChatBuilder(user_query, document_ids, conversation, self.repo_id)
  
  # Headers
        self.headers['Content-Type'] = 'application/vnd.conversation-request.v1+json'
        self.headers['Accept'] = 'application/vnd.conversation-response.v1+json'

 
        self.logger.info("--------------------------------")
        self.logger.info("Method : smart_chat")
        self.logger.debug(f"URL : {smart_chat_url}")
        self.logger.debug(f"Headers : {json.dumps(self.headers)}")
        self.logger.debug(f"Payload : {smart_chat_object.to_json()}")

        # POST 
        response = requests.post(smart_chat_url, json=smart_chat_object.to_dict(), headers=self.headers, verify=False)

        # Convert string to dict
        response_json = json.loads(response.text)

        return SmartChatResponse(response_json)
    
class SmartChatBuilder:
    def __init__(self, user_query, document_ids=None, conversation="", repository_id="1C90AB8B-8A9F-4CE7-9124-F9FDDD186093"):
        self.user_query = user_query
        self.document_ids = document_ids if document_ids is not None else []
        self.conversation = conversation
        self.repository_id = repository_id

    def to_dict(self):
        return {
            "userQuery": self.user_query,
            "documentIDs": self.document_ids,
            "context": {
                "conversation": self.conversation
            },
            "repositories": [
                {
                    "id": self.repository_id
                }
            ]
        }

    def to_json(self, indent=4):
        return json.dumps(self.to_dict(), indent=indent)
    
class SmartChatResponse:
    def __init__(self, json_data):
        data = json.loads(json_data) if isinstance(json_data, str) else json_data
        self.answer = data.get("answer")
        self.conversation = data.get("context", {}).get("conversation")
        self.object_ids = [doc.get("objectId") for doc in data.get("matchingDocuments", [])]

    def to_dict(self):
        return {
            "answer": self.answer,
            "conversation": self.conversation,
            "object_ids": self.object_ids
        }

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)    