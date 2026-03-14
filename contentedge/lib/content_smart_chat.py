import json
import requests
import urllib3
import warnings
from copy import deepcopy

from .content_config import ContentConfig

# Disable https warnings if the http certificate is not valid
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)


class ContentSmartChat:
    """Interact with the Content Repository Smart Chat (Conversations) API."""

    def __init__(self, content_config):
        if isinstance(content_config, ContentConfig):
            self.repo_url = content_config.repo_url
            self.repo_id = content_config.repo_id
            self.logger = content_config.logger
            self.headers = deepcopy(content_config.headers)
        else:
            raise TypeError("ContentConfig class object expected")

    def smart_chat(self, user_query: str, document_ids: list[str] | None = None, conversation: str = "") -> "SmartChatResponse":
        """Send a question to the Smart Chat API.

        Uses the endpoint: POST /mobius/rest/conversations

        Args:
            user_query: The question to ask.
            document_ids: Optional list of objectIds to restrict the query
                          to specific documents.  Pass an empty list or None
                          to query the entire repository.
            conversation: Conversation ID returned by a previous call, used
                          to maintain multi-turn context.  Empty string for a
                          new conversation.

        Returns:
            A SmartChatResponse with answer, conversation id and matching
            document objectIds.
        """
        smart_chat_url = self.repo_url + "/conversations"

        payload = {
            "userQuery": user_query,
            "documentIDs": document_ids if document_ids is not None else [],
            "context": {
                "conversation": conversation,
            },
            "repositories": [
                {"id": self.repo_id},
            ],
        }

        headers = deepcopy(self.headers)
        headers["Content-Type"] = "application/vnd.conversation-request.v1+json"
        headers["Accept"] = "application/vnd.conversation-response.v1+json"

        self.logger.info("--------------------------------")
        self.logger.info("Method : smart_chat")
        self.logger.debug(f"URL : {smart_chat_url}")
        self.logger.debug(f"Headers : {json.dumps(headers)}")
        self.logger.debug(f"Payload : {json.dumps(payload, indent=4)}")

        response = requests.post(
            smart_chat_url, json=payload, headers=headers, verify=False, timeout=120,
        )

        if response.status_code != 200:
            self.logger.error(f"Smart Chat failed: HTTP {response.status_code} — {response.text[:300]}")
            raise ValueError(f"Smart Chat request failed: HTTP {response.status_code}")

        response_json = response.json()
        return SmartChatResponse(response_json)


class SmartChatResponse:
    """Parsed response from the Smart Chat API."""

    def __init__(self, json_data):
        data = json.loads(json_data) if isinstance(json_data, str) else json_data
        self.answer: str = data.get("answer", "")
        self.conversation: str = data.get("context", {}).get("conversation", "")
        self.object_ids: list[str] = [
            doc.get("objectId") for doc in data.get("matchingDocuments", [])
        ]

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "conversation": self.conversation,
            "object_ids": self.object_ids,
        }

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)
