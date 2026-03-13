from typing import Optional
import urllib3
import warnings

from .content_config import ContentConfig
from .content_adm_archive_policy import ContentAdmArchivePolicy
from .content_adm_content_class import ContentAdmContentClass
from .content_adm_index_group import ContentAdmIndexGroup, IndexGroup

# Disable https warnings if the http certificate is not valid
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

class ContentAdmServicesApi:
    """
    ContentAdnServicesApi is the main class for interacting with Mobius ADMIN REST content_obj.

    Attributes:
        config: is a ContentConfig object with information about connection, and logging ,etc.
    """
    def __init__(self, yaml_file):
        """
        Initializes the ContentAdmServicesApi class from YAML file.
        
        Args:
            yaml_file: [Mandatory] Path to the YAML configuration 
        """
        self.config = ContentConfig(yaml_file)
 
    #--------------------------------------------------------------
    # Import Archiving Policy
    def import_archiving_policy(self, archiving_policy_path, archiving_policy_name):
        """
        Import an archiving policy by reading a JSON file and sending it via POST request.
        
        Args:
            archiving_policy_path (str): Path to the JSON file containing the archiving policy.
            archiving_policy_name (str): Name of the archiving policy.
        
        Returns:
            int: HTTP status code of the response, or None if an error occurs.
        """
        repo = ContentAdmArchivePolicy(self.config)

        return repo.import_archiving_policy(archiving_policy_path, archiving_policy_name)
    
    #--------------------------------------------------------------
    #--------------------------------------------------------------
    # Create Content Class definition
    def create_content_class(self, cc_id, cc_name): 
        """
        Creates a new content class by sending a POST request to the repository admin URL.
        Args:
            cc_id (str): The unique identifier for the content class.
            cc_name (str): The name of the content class.
        Returns:
            int: The HTTP status code returned by the POST request.
        Raises:
            Exception: Logs any exception that occurs during the process.
        Side Effects:
            - Logs method execution details, request headers, body, and response.
            - Sets encryption to True for the content class definition.
            - Modifies self.headers for content type and accept headers.
        """
        repo = ContentAdmContentClass(self.config)

        return repo.create_content_class(cc_id, cc_name)
    
    #--------------------------------------------------------------
    # Create Index Group Definition
    def create_index_group(self, index_group):
        """
        Creates a new index group by sending a POST request to the repository admin API.
        Args:
            index_group: IndexGroup object containing the index group definition.
        Returns:
            int: The HTTP status code returned by the API.
        Logs:
            - Method entry and exit points.
            - Request URL, headers, and body.
            - Response text.
            - Errors encountered during the process.
        Raises:
            Logs any exceptions that occur during the request.
        """
        if not isinstance(index_group, IndexGroup):
            raise TypeError("IndexGroup class object expected")

        repo = ContentAdmIndexGroup(self.config)
    
        return repo.create_index_group(index_group)
    
    #--------------------------------------------------------------    
    # Export Index Group Definitions
    def export_index_groups(self, ig_id, output_dir) -> Optional[str]:
        """
        Export to a file the index groups filtered by ig_id.
        Args:
            ig_id (str): The ID (or part) of the index group.
        Returns:
            filename: generated.
        Raises:
            requests.HTTPError: If the HTTP request to the API fails.
            json.JSONDecodeError: If the response cannot be parsed as JSON.
            FileNotFoundError: If the output directory does not exist
            ValueError: if the JSON data is invalid.
        Logs:
            - Method name, request URL, and headers for debugging purposes.
        """    
        repo = ContentAdmIndexGroup(self.config)
    
        return repo.export_index_groups(ig_id, output_dir)

    #--------------------------------------------------------------    
    # Export Content Classes Definitions
    def export_content_classes(self, cc_id, output_dir) -> Optional[str]:
        """
        Export content classes filtered by cc_id.
        Args:
            cc_id (str): The ID of the content class used as filter.
        Returns:
            filename: generated.
        Raises:
            requests.HTTPError: If the HTTP request to the API fails.
            json.JSONDecodeError: If the response cannot be parsed as JSON.
            FileNotFoundError: If the output directory does not exist
            ValueError: if the JSON data is invalid.            
        Logs:
            - Method name, request URL, and headers for debugging purposes.
        """
        repo = ContentAdmContentClass(self.config)
    
        return repo.export_content_classes(cc_id, output_dir)
    
    #--------------------------------------------------------------
    # Export Archiving Policies
    def export_archiving_policies(self, ap_filter, path: str ):
        """
        Exports archiving policies matching a given filter to the specified directory.
        This method retrieves a list of archiving policies from the repository admin URL
        that match the provided filter, then exports each policy's details as JSON files
        to the given output directory.
        Args:
            ap_filter (str): Filter string to match archiving policy names.
            path (str): Path to the output directory where policies will be saved.
        Raises:
            FileNotFoundError: If the specified output directory does not exist.
            requests.HTTPError: If an HTTP request to the repository fails.
            json.JSONDecodeError: If the response JSON cannot be parsed.
        Returns:
             None.
        """
        repo = ContentAdmArchivePolicy(self.config)

        repo.export_archiving_policies(ap_filter, path)

    #--------------------------------------------------------------
    # Import Index Groups from file
    def import_index_groups(self, file_path: str) -> None:
        """
        Imports index groups from a JSON file.
        Args:
            file_path (str): The path to the JSON file containing an array of index group objects.
        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file does not contain a JSON array.
        The method reads the specified JSON file, validates that it contains a list of index group objects,
        and imports each index group by calling `self.import_index_group`. Errors encountered during the process
        are logged using the class logger.
        """
        repo = ContentAdmIndexGroup(self.config)

        repo.import_index_groups(file_path)


    #--------------------------------------------------------------
    # Import Content Classes from file
    def import_content_classes(self, file_path: str) -> None:
        """
        Imports content classes from a JSON file.
        This method reads a JSON file specified by `file_path`, expecting the file to contain a JSON array.
        Each element of the array is passed to the `import_content_class` method for processing.
        Args:
            file_path (str): The path to the JSON file containing a list of content class definitions.
        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file does not contain a JSON array.
        Logs:
            Errors related to file not found, invalid JSON format, or other exceptions are logged using the class logger.
        """
        repo = ContentAdmContentClass(self.config)

        repo.import_content_classes(file_path)
