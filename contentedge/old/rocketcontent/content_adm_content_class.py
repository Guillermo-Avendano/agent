import json
from pathlib import Path
import requests
import urllib3
import warnings
from dataclasses import dataclass
from typing import Optional
from copy import deepcopy
from .content_config import ContentConfig
from urllib.parse import quote
import datetime
import os
from .content_adm_archive_policy import ContentAdmArchivePolicy
from .content_adm_index_group import ContentAdmIndexGroup, IndexGroup
import time

# Disable https warnings if the http certificate is not valid
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

class ContentAdmContentClass:
    """
    ContentAdmContentClass provides functionality to manage content class definitions for a repository administration system.
    Classes:
        ContentClass: A data class representing the configuration and properties of a content class, including options for compression, encryption, retention, indexing, and more.
    Methods:
        __init__(content_config):
            Initializes the ContentAdmContentClass with a ContentConfig object, setting up repository admin URL, logger, and headers.
        create_content_class(content_class_json):
            Creates a new content class by sending a POST request to the repository admin API using the provided JSON payload.
        TypeError: If the provided content_config is not an instance of ContentConfig.
        Exception: If an error occurs during the creation of the content class, it is logged and handled.
    """

    #--------------------------------------------------------------
    # Content Class definition
    class ContentClass:
        compress: bool = True
        encrypt: bool = False
        deleteExpiredAuto: bool = False
        type: int = 7
        description: str = ""
        details: str = "Note that %REPORTID% gets truncated to 8 characters.\nUse %REPORTID.10% to get the entire report ID.\nAlso, in general, avoid using relative paths."
        ocrProcessing: bool = True
        template: str = "/mnt/efs%PATHDELIM%%REPORTID%%PATHDELIM%%ARCHIVEDATE%%PATHDELIM%%ARCHIVETIME%%UNIQUE.2%.DAF"
        retentionType: str = "No retention"
        retentionBased: str = "Report version ID"
        enableMetadataIndexing: bool = True
        enableContentIndexing: bool = True
        redactionType: str = "No Redaction"
        securityTopic: str = ""
        characterType: str = "PC ANSI"
        daysForRetention: Optional[int] = None
        daysForRetentionWithInitialFixedPeriod: Optional[int] = None
        id: str
        name: str

        def __init__(self, id: str, name: str):
            self.id = id
            self.name = name
            self.compress = True
            self.encrypt = False
            self.deleteExpiredAuto = False
            self.type = 7
            self.description = ""
            self.details = "Note that %REPORTID% gets truncated to 8 characters.\nUse %REPORTID.10% to get the entire report ID.\nAlso, in general, avoid using relative paths."
            self.ocrProcessing = True
            self.template = "/mnt/efs%PATHDELIM%%REPORTID%%PATHDELIM%%ARCHIVEDATE%%PATHDELIM%%ARCHIVETIME%%UNIQUE.2%.DAF"
            self.retentionType = "No retention"
            self.retentionBased = "Report version ID"
            self.enableMetadataIndexing = True
            self.enableContentIndexing = True
            self.redactionType = "No Redaction"
            self.securityTopic = ""
            self.characterType = "PC ANSI"
            self.daysForRetention = None
            self.daysForRetentionWithInitialFixedPeriod = None

        @classmethod
        def from_json(cls, json_data: dict) -> 'ContentAdmContentClass.ContentClass':
            instance = cls(
                id=json_data.get('id', ''),
                name=json_data.get('name', '')
            )
            instance.compress = json_data.get('compress', True)
            instance.encrypt = json_data.get('encrypt', False)
            instance.deleteExpiredAuto = json_data.get('deleteExpiredAuto', False)
            instance.type = json_data.get('type', 7)
            instance.description = json_data.get('description', '')
            instance.details = json_data.get('details', "Note that %REPORTID% gets truncated to 8 characters.\nUse %REPORTID.10% to get the entire report ID.\nAlso, in general, avoid using relative paths.")
            instance.ocrProcessing = json_data.get('ocrProcessing', True)
            instance.template = json_data.get('template', "/mnt/efs%PATHDELIM%%REPORTID%%PATHDELIM%%ARCHIVEDATE%%PATHDELIM%%ARCHIVETIME%%UNIQUE.2%.DAF")
            instance.retentionType = json_data.get('retentionType', "No retention")
            instance.retentionBased = json_data.get('retentionBased', "Report version ID")
            instance.enableMetadataIndexing = json_data.get('enableMetadataIndexing', True)
            instance.enableContentIndexing = json_data.get('enableContentIndexing', True)
            instance.redactionType = json_data.get('redactionType', "No Redaction")
            instance.securityTopic = json_data.get('securityTopic', "")
            instance.characterType = json_data.get('characterType', "PC ANSI")
            instance.daysForRetention = json_data.get('daysForRetention', None)
            instance.daysForRetentionWithInitialFixedPeriod = json_data.get('daysForRetentionWithInitialFixedPeriod', None)
            return instance

        def setEncrypt(self, encrypt: bool) -> None:
            self.encrypt = encrypt

        def to_dict(self):
            return {
                "compress": self.compress,
                "encrypt": self.encrypt,
                "deleteExpiredAuto": self.deleteExpiredAuto,
                "type": self.type,
                "description": self.description,
                "details": self.details,
                "ocrProcessing": self.ocrProcessing,
                "template": self.template,
                "retentionType": self.retentionType,
                "retentionBased": self.retentionBased,
                "enableMetadataIndexing": self.enableMetadataIndexing,
                "enableContentIndexing": self.enableContentIndexing,
                "redactionType": self.redactionType,
                "securityTopic": self.securityTopic,
                "characterType": self.characterType,
                "daysForRetention": self.daysForRetention,
                "daysForRetentionWithInitialFixedPeriod": self.daysForRetentionWithInitialFixedPeriod,
                "id": self.id,
                "name": self.name
            }    
        
    def __init__(self, content_config):

        if isinstance(content_config, ContentConfig):
            self.repo_admin_url = content_config.repo_admin_url
            self.logger = content_config.logger
            self.headers = deepcopy(content_config.headers)
        else:
            raise TypeError("ContentConfig class object expected")

    #--------------------------------------------------------------
    # Extract content classes from JSON and save to file
    def extract_content_classes(self, json_data, output_dir) -> Optional[str]:
        """
        Extracts content classes objects from a JSON structure and saves them to a file
        with a timestamp in the filename.
        
        Args:
            json_data (dict): JSON object containing 'items' with content class data
            output_dir (str): Directory where the output file will be saved
            
        Returns:
            str: Path to the saved file
        """
        
        # Generate timestamp for filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"content_class_{timestamp}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        # Extract topic groups
        if not isinstance(json_data, dict) or 'items' not in json_data:
           raise ValueError("Invalid JSON data: 'items' key not found or JSON is not a dictionary")
        
        result = []
        for item in json_data['items']:
            content_class = {
                'id': item.get('id', ''),
                'name': item.get('name', ''),
                'details': item.get('details', ''),
                'policyName': item.get('policyName', ''),
                'topicId': item.get('topicId', ''),
                'compress': item.get('compress', False),
                'encrypt': item.get('encrypt', False),
                'template': item.get('template', ''),
                'retentionType': item.get('retentionType', ''),
                'daysForRetention': item.get('daysForRetention', 0),
                'daysForRetentionWithInitialFixedPeriod': item.get('daysForRetentionWithInitialFixedPeriod', 0),
                'intermediateRetentionDays': item.get('intermediateRetentionDays', 0),
                'numberOfRecentVersions': item.get('numberOfRecentVersions', 0),
                'retentionBased': item.get('retentionBased', ''),
                'deleteExpiredAuto': item.get('deleteExpiredAuto', False),
                'enableYearEndRounding': item.get('enableYearEndRounding', False),
                'allowArchiveProcessing': item.get('allowArchiveProcessing', False)
            }
            result.append(content_class)
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(result, file, indent=2)
        
        return output_path
    
    #--------------------------------------------------------------
    # Verify if Content Class definition exists
    # This method checks if a content class with the specified name exists by querying the admin reports API.
    # It returns True if the content class exists, otherwise returns False.
    # If an error occurs during the request or JSON parsing, it logs the error and returns False.
    def verify_content_class(self, cc_id) -> bool:
        """
        Verifies if a content class with the specified name exists by querying the admin reports API.
        Args:
            cc_id (str): The ID of the content class to verify.
        Returns:
            bool: True if an item with the given ID exists in the response, False otherwise.
        Raises:
            requests.HTTPError: If the HTTP request to the API fails.
            json.JSONDecodeError: If the response cannot be parsed as JSON.
        Logs:
            - Method name, request URL, and headers for debugging purposes.
        """
        try:
            local_headers = deepcopy(self.headers)
            local_headers['Accept'] = 'application/vnd.asg-mobius-admin-reports.v3+json,application/vnd.asg-mobius-admin-reports.v2+json,application/vnd.asg-mobius-admin-reports.v1+json'

            tm = str(int(time.time() * 1000))
            content_class_get_url = self.repo_admin_url + f"/reports?limit=5&&reportid={cc_id}&timestamp={tm}"

            self.logger.info("--------------------------------")
            self.logger.info("Method : verify_content_class")
            self.logger.debug(f"URL : {content_class_get_url}")
            self.logger.debug(f"Headers : {json.dumps(local_headers)}")
                         
            # Send the request
            response = requests.get(content_class_get_url, headers=local_headers, verify=False)
            
            # Check if the HTTP request was successful
            response.raise_for_status()
            
            # Parse JSON from response
            data = response.json()
          
            # Get items list, default to empty list if not found
            items = data.get("items", [])
            
            # Check each item for id == "AAA01"
            for item in items:
                if item.get("id") == cc_id:
                    return True
            return False
        
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error occurred: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return False       
        
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

        try:

            if self.verify_content_class(cc_id):
                self.logger.error(f"Content class with name '{cc_id}' already exists.")
                return 409

            # Create instance of ReportConfig with id and name
            content_class_definition = self.ContentClass(id=cc_id, name=cc_name)

            # Example: Set encrypt to True
            content_class_definition.setEncrypt(True)

            content_class_definition_url = self.repo_admin_url + "/reports?sourcereportidtoclone=AC001"
 
            self.headers['Content-Type'] = 'application/vnd.asg-mobius-admin-report.v1+json'
            self.headers['accept'] = 'application/vnd.asg-mobius-admin-report.v1+json'

            self.logger.info("--------------------------------")
            self.logger.info("Method : create_content_class")
            self.logger.debug(f"URL : {content_class_definition_url}")
            self.logger.debug(f"Headers : {json.dumps(self.headers)}")
            self.logger.debug(f"Payload : {json.dumps(content_class_definition.to_dict(), indent=2)}")  
                         
            # Send the request
            response = requests.post(content_class_definition_url, headers=self.headers, json=content_class_definition.to_dict(), verify=False)
            
            self.logger.info(f"Response Status Code: {response.status_code}")
            return response.status_code
         
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")


    #--------------------------------------------------------------    
    # Export Content Classes Definitions
    # This method exports the content classes definitions to a file.
    # It retrieves the content class by its id, extracts the topics, and saves them to a JSON file.
    # If an error occurs during the request or JSON parsing, it logs the error and returns False.
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
        try:
            # Check if output directory exists
            if not os.path.exists(output_dir):
                raise FileNotFoundError(f"Output directory '{output_dir}' does not exist")
                        
            local_headers = deepcopy(self.headers)
            local_headers['Accept'] = 'application/vnd.asg-mobius-admin-reports.v3+json,application/vnd.asg-mobius-admin-reports.v2+json,application/vnd.asg-mobius-admin-reports.v1+json'

            tm = str(int(time.time() * 1000))
            content_class_get_url = self.repo_admin_url + f"/reports?limit=200&&reportid={cc_id}*&timestamp={tm}"

            self.logger.info("--------------------------------")
            self.logger.info("Method : export_content_classes")
            self.logger.debug(f"URL : {content_class_get_url}")
            self.logger.debug(f"Headers : {json.dumps(local_headers)}")
                         
            # Send the request
            response = requests.get(content_class_get_url, headers=local_headers, verify=False)
            
            # Check if the HTTP request was successful
            response.raise_for_status()
            
            # Parse JSON from response
            data = response.json()
          
            saved_file = self.extract_content_classes(data, output_dir)
        
            self.logger.info(f"Data saved to: {saved_file}")

            return saved_file
    
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error occurred: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON: {e}")
            return None
        except FileNotFoundError as e:
            self.logger.error(f"Directory error: {e}")
            return None
        except ValueError as e:
            self.logger.error(f"Data error: {e}")
            return None
        
    #--------------------------------------------------------------
    # Import Content Class definition
    def import_content_class(self, cc_json): 
        """
        Imports a content class definition from a JSON object.
        This method creates an instance of ContentClass from the provided JSON,
        checks if a content class with the same ID already exists, and if not,
        sets encryption, prepares the request, and sends it to the repository admin URL
        to create the content class.
        Args:
            cc_json (dict): The JSON object representing the content class definition.
        Returns:
            int: The HTTP status code from the POST request, or 409 if the content class already exists.
        Logs:
            - Errors if the content class already exists or if any exception occurs.
            - Information and debug logs for request details and responses.
        """

        try:
            # Create instance of ContentClass from json
            content_class_definition = self.ContentClass.from_json(cc_json)

            cc_id = content_class_definition.id

            if self.verify_content_class(cc_id):
                self.logger.error(f"Content class with name '{cc_id}' already exists.")
                return 409


            # Example: Set encrypt to True
            content_class_definition.setEncrypt(True)

            content_class_definition_url = self.repo_admin_url + "/reports?sourcereportidtoclone=AC001"
 
            self.headers['Content-Type'] = 'application/vnd.asg-mobius-admin-report.v1+json'
            self.headers['accept'] = 'application/vnd.asg-mobius-admin-report.v1+json'

            self.logger.info("--------------------------------")
            self.logger.info("Method : create_content_class")
            self.logger.debug(f"URL : {content_class_definition_url}")
            self.logger.debug(f"Headers : {json.dumps(self.headers)}")
            self.logger.debug(f"Payload : {json.dumps(content_class_definition.to_dict(), indent=2)}")  
                         
            # Send the request
            response = requests.post(content_class_definition_url, headers=self.headers, json=content_class_definition.to_dict(), verify=False)
            
            self.logger.info(f"Response: {response.status_code} - Content Class '{cc_id}' imported successfully.")

            return response.status_code
         
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            return -1

    #--------------------------------------------------------------
    # Import Content Classes from file
    def import_content_classes(self, file_path: str) -> None:
        """
        Imports content classes from a JSON file.
        This method reads a JSON file specified by `file_path`, expecting the file to contain a JSON array.
        Each element of the array is passed to the `import_content_class` method for processing.
        Args:
            file_path (str): The path to the JSON file containing content class definitions.
        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file does not contain a JSON array.
        Logs:
            Errors related to file not found, invalid JSON format, or other exceptions are logged using the class logger.
        """

        if not Path(file_path).exists():
            raise FileNotFoundError(f"Error: File '{file_path}' does not exist")

        try:
            with open(file_path, 'r') as file:
                json_array = json.load(file)

                if not isinstance(json_array, list):
                    raise ValueError("Error: File does not contain a JSON array")
                    
                for index, content_class_json_obj in enumerate(json_array):
                    self.import_content_class(content_class_json_obj)

        except FileNotFoundError:
            self.logger.error(f"Error: File '{file_path}' not found")
        except json.JSONDecodeError:
            self.logger.error("Error: Invalid JSON format in file")
        except Exception as e:
            self.logger.error(f"Error: {str(e)}")                