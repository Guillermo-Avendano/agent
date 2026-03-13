import urllib3
import warnings

from .content_config import ContentConfig
from .content_search import ContentSearch, IndexSearch
from .content_smart_chat import ContentSmartChat
from .content_archive_metadata import ContentArchiveMetadata
from .content_archive_policy import ContentArchivePolicy 
from .content_class_navigator import ContentClassNavigator
 
from .content_document import ContentDocument

# Disable https warnings if the http certificate is not valid
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

class ContentServicesApi:
    """
    ContentServicesApi is the main class for interacting with the Mobius REST Content Repository.

    Attributes:
        config: A ContentConfig object with connection, logging, and other information.
    """
    def __init__(self, yaml_file):
        """
        Initializes the ContentServicesApi class from a YAML file.
        Args:
            yaml_file: [Mandatory] Path to the YAML configuration file.
        """
        self.config = ContentConfig(yaml_file)
 
    def search_index(self, index_search: IndexSearch) -> list:
        """
        Executes a search using an IndexSearch object.
        Args:
            index_search (IndexSearch): IndexSearch object with search parameters.
        Returns:
            list: List of objectIds resulting from the search.
        """
        search_obj = ContentSearch(self.config)
        return search_obj.search_index(index_search)
    
    def smart_chat(self, user_query, document_ids=None, conversation=""):
        """
        Interrogate Content Repository with Smart Chat.
        Args:
            user_query    : [Mandatory] The query to send to the Smart Chat API.
            document_ids: [Optional] An array of document IDs to limit the query scope.
            conversation: [Optional] A conversation ID to maintain context.           
        Returns:
            SmartChatResponse object.
        """
        smart_obj = ContentSmartChat(self.config)
        return smart_obj.smart_chat(user_query, document_ids, conversation)
 
    def archive_metadata(self, document_collection):
        """
        Archives a document using metadata.
        Args:
            document_collection: [Mandatory] ArchiveDocumentCollection object containing a list of documents with metadata.
        Returns:
            API response.
        """
        archive_obj = ContentArchiveMetadata(self.config)
        return archive_obj.archive_metadata(document_collection)

    def archive_policy(self, file_path, policy_name):
        """
        Archives a document using an archiving policy.
        Args:
            file_path: [Mandatory] Path to the file to archive.
            policy_name: [Mandatory] Name of an existing archiving policy in rocketcontent.
        Returns:
            API response.
        """
        archive_obj = ContentArchivePolicy(self.config)
        return archive_obj.archive_policy(file_path, policy_name)

    def archive_policy_from_str(self, str_content, policy_name):
        """
        Archives a document using an archiving policy from a string.
        Args:
            str_content: [Mandatory] String to archive.
            policy_name: [Mandatory] Name of an existing archiving policy in rocketcontent.
        Returns:
            API response.
        """
        archive_obj = ContentArchivePolicy(self.config)
        return archive_obj.archive_policy_from_str(str_content, policy_name)
    

    
    def delete_document(self, document_id):
        """
        Delete a document in the Content Repository by ID.
        Args:
            document_id: [Mandatory] Document ID.
        Returns:
            API response (status code).
        """
        doc_obj = ContentDocument(self.config)
        return doc_obj.delete_document(document_id)

    #------------------------------------
    # Authentication Methods
    #------------------------------------
    
    def set_basic_auth(self, username=None, password=None):
        """
        Configure Basic Authentication for all API calls.
        Args:
            username (str, optional): Username. If None, uses config defaults.
            password (str, optional): Password. If None, uses config defaults.
        """
        self.config.headers = self.config.authenticate_basic(username, password)
        return self
    
    def set_bearer_auth(self, token):
        """
        Configure Bearer Token Authentication for all API calls.
        Args:
            token (str): Bearer token.
        """
        self.config.headers = self.config.authenticate_bearer(token)
        return self
    
    def set_api_key_auth(self, api_key, header_name='X-API-Key'):
        """
        Configure API Key Authentication for all API calls.
        Args:
            api_key (str): API key.
            header_name (str): Header name for the API key.
        """
        self.config.headers = self.config.authenticate_api_key(api_key, header_name)
        return self
    
    def set_oauth2_auth(self, access_token, token_type='Bearer'):
        """
        Configure OAuth2 Authentication for all API calls.
        Args:
            access_token (str): OAuth2 access token.
            token_type (str): Token type.
        """
        self.config.headers = self.config.authenticate_oauth2(access_token, token_type)
        return self
    
    def set_custom_auth(self, custom_headers):
        """
        Configure Custom Headers Authentication for all API calls.
        Args:
            custom_headers (dict): Custom authentication headers.
        """
        self.config.headers = self.config.authenticate_custom_headers(custom_headers)
        return self
    
    def validate_current_auth(self):
        """
        Validate the current authentication configuration.
        Returns:
            bool: True if authentication is valid.
        """
        return self.config.validate_authentication(self.config.headers)
    
    def get_available_auth_methods(self):
        """
        Get available authentication methods.
        Returns:
            dict: Available authentication methods and descriptions.
        """
        return self.config.get_authentication_methods()
    
    #------------------------------------
    # Token Acquisition Methods
    #------------------------------------
    
    def get_and_set_oauth2_token(self, client_id, client_secret, token_url, scope=None):
        """
        Get OAuth2 token and automatically configure Bearer authentication.
        
        Args:
            client_id (str): OAuth2 client ID.
            client_secret (str): OAuth2 client secret.
            token_url (str): URL of the token endpoint.
            scope (str, optional): OAuth2 scope.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        token_data = self.config.get_oauth2_token(client_id, client_secret, token_url, scope)
        if token_data and 'access_token' in token_data:
            self.set_bearer_auth(token_data['access_token'])
            return True
        return False
    
    def get_and_set_jwt_token(self, username, password, jwt_url):
        """
        Get JWT token and automatically configure Bearer authentication.
        
        Args:
            username (str): Username for authentication.
            password (str): Password for authentication.
            jwt_url (str): URL of the JWT token endpoint.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        token = self.config.get_jwt_token(username, password, jwt_url)
        if token:
            self.set_bearer_auth(token)
            return True
        return False
    
    def get_and_set_api_key_from_env(self, env_var_name='API_KEY'):
        """
        Get API key from environment variable and configure authentication.
        
        Args:
            env_var_name (str): Name of the environment variable.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        api_key = self.config.get_api_key_from_env(env_var_name)
        if api_key:
            self.set_api_key_auth(api_key)
            return True
        return False
    
    def get_and_set_token_from_file(self, file_path):
        """
        Get token from file and configure Bearer authentication.
        
        Args:
            file_path (str): Path to the token file.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        token = self.config.get_token_from_file(file_path)
        if token:
            self.set_bearer_auth(token)
            return True
        return False
    
    def refresh_and_set_oauth2_token(self, refresh_token, client_id, client_secret, token_url):
        """
        Refresh OAuth2 token and automatically configure Bearer authentication.
        
        Args:
            refresh_token (str): The refresh token.
            client_id (str): OAuth2 client ID.
            client_secret (str): OAuth2 client secret.
            token_url (str): URL of the token endpoint.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        token_data = self.config.refresh_oauth2_token(refresh_token, client_id, client_secret, token_url)
        if token_data and 'access_token' in token_data:
            self.set_bearer_auth(token_data['access_token'])
            return True
        return False
