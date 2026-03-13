import json
import requests
import urllib3
import warnings
import logging
import time
import os
from copy import deepcopy
from rocketcontent.content_services_api import ContentServicesApi
from rocketcontent.content_config import ContentConfig
from rocketcontent.util import validate_id

# Disable https warnings if the http certificate is not valid
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

class ContentAdmArchivePolicy:

    def __init__(self, content_config):

        if isinstance(content_config, ContentConfig):
            self.repo_admin_url = content_config.repo_admin_url
            self.logger = content_config.logger
            self.headers = deepcopy(content_config.headers)
        else:
            raise TypeError("ContentConfig class object expected")

    #--------------------------------------------------------------
    # Verify if Archivig Policy definition exists
    # This method checks if a Archivig Policy with the specified id exists.
    # It returns True if the Archivig Policyexists, otherwise returns False.
    # If an error occurs during the request or JSON parsing, it logs the error and returns False.
    def verify_archiving_policy(self, ap_id) -> bool:
        """
        Verifies if a Archivig Policy the specified name exists.
        Args:
            ap_id (str): The ID of the Archivig Policy to verify.
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
            local_headers['Accept'] = 'application/vnd.asg-mobius-admin-archiving-policies.v1+json'

            tm = str(int(time.time() * 1000))
            archiving_policy_get_url = self.repo_admin_url + f"/archivingpolicies?limit=5&&name={ap_id}*&timestamp={tm}"

            self.logger.info("--------------------------------")
            self.logger.info("Method : verify_archiving_policy")
            self.logger.debug(f"URL : {archiving_policy_get_url}")
            self.logger.debug(f"Headers : {json.dumps(local_headers)}")
                         
            # Send the request
            response = requests.get(archiving_policy_get_url, headers=local_headers, verify=False)
            
            # Check if the HTTP request was successful
            response.raise_for_status()
            
            # Parse JSON from response
            data = response.json()
          
        
            # Get items list, default to empty list if not found
            items = data.get("items", [])
            
            # Check each item for matching name
            for item in items:
                if isinstance(item, dict) and item.get("name") == ap_id:
                    self.logger.info(f"Found matching archiving policy: {ap_id}")
                    return True
            
            self.logger.info(f"No matching archiving policy found for: {ap_id}")
            return False
        
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error occurred: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return False       
        

    #--------------------------------------------------------------
    # Import an archiving policy
    def import_archiving_policy(self, archiving_policy_path, archiving_policy_name):
        """
        Import an archiving policy by reading a JSON file and sending it via POST request.
        
        Args:
            archiving_policy_path (str): Path to the JSON file containing the archiving policy.
            archiving_policy_name (str): Name of the archiving policy.
        
        Returns:
            int: HTTP status code of the response, or None if an error occurs.
        """

            # Check if output directory exists
        if not validate_id(archiving_policy_name):
                raise ValueError(f"Not valid archiving policy name: '{archiving_policy_name}'.")
        
        if self.verify_archiving_policy(archiving_policy_name):
            self.logger.error(f"Archivig Policy with name '{archiving_policy_name}' already exists.")
            return 409

        import_archive_policy_url = self.repo_admin_url + "/archivingpolicies"

        self.headers ['Content-Type'] = 'application/vnd.asg-mobius-admin-archiving-policy.v1+json'

        # Read the archiving policy file
        try:
            with open(archiving_policy_path, 'r', encoding='utf-8') as file:
                body = file.read()

            json_data = json.loads(body)

             # Replace root-level 'name' if it matches old_value
            if isinstance(json_data, dict) and "name" in json_data:
                json_data["name"] = archiving_policy_name


        except FileNotFoundError:
            self.logger.error(f"Archiving policy file not found: {archiving_policy_path}")
            return None
        except UnicodeDecodeError:
            self.logger.error(f"Failed to decode file as UTF-8: {archiving_policy_path}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading archiving policy file: {e}")
            return None

        self.logger.info("--------------------------------")
        self.logger.info("Method: import_archive_policy")
        self.logger.debug(f"URL: {import_archive_policy_url}")
        self.logger.debug(f"Headers: {json.dumps(self.headers, indent=2)}")

        try:
            # Send the POST request
            response = requests.post(import_archive_policy_url, headers=self.headers, data=json.dumps(json_data, indent=2), verify=False)

            self.logger.info(f"Response: {response.status_code} - Archiving policy '{archiving_policy_name}' imported successfully.")

            return response.status_code
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error importing archiving policy: {e}")
            return None            

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

        try:
            # Check if output directory exists
            if not os.path.exists(path):
                raise FileNotFoundError(f"Output directory '{path}' does not exist")
                        
            local_headers = deepcopy(self.headers)
            local_headers['Accept'] = 'application/vnd.asg-mobius-admin-archiving-policies.v1+json'

            tm = str(int(time.time() * 1000))
            archiving_policy_get_url = self.repo_admin_url + f"/archivingpolicies?limit=200&&name={ap_filter}*&timestamp={tm}"

            self.logger.info("--------------------------------")
            self.logger.info("Method : export_archiving_policies")
            self.logger.debug(f"URL : {archiving_policy_get_url}")
            self.logger.debug(f"Headers : {json.dumps(local_headers)}")
                        
            # Send the request
            response = requests.get(archiving_policy_get_url, headers=local_headers, verify=False)
            
            # Check if the HTTP request was successful
            response.raise_for_status()
            
            # Parse JSON from response
            data = response.json()
        
            # Get items list, default to empty list if not found
            items = data.get("items", [])
            
            ap_headers = deepcopy(self.headers)
            ap_headers['Accept'] = 'application/vnd.asg-mobius-admin-archiving-policy.v1+json'

            for item in items:
                archiving_policy_name = item.get("name")
                archiving_policy_export_url = self.repo_admin_url + f"/archivingpolicies/{archiving_policy_name}?timestamp={tm}"
                self.logger.info("--------------------------------")
                self.logger.info(f"Exporting archiving policy: {archiving_policy_name}")
                self.logger.debug(f"URL : {archiving_policy_export_url}")
                self.logger.debug(f"Headers : {json.dumps(ap_headers)}")
                            
                # Send the request
                response = requests.get(archiving_policy_export_url, headers=ap_headers, verify=False)
                
                # Check if the HTTP request was successful
                response.raise_for_status()
                 # Parse JSON from response
                ap_data = response.json()

                self.save_archive_policy(ap_data, archiving_policy_name, path)
                            

        
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error occurred: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON: {e}")
            return []
        
    #--------------------------------------------------------------
    # Save Archive Policy to a file with UTF-8 encoding   
    def save_archive_policy(self, json_data: dict, archive_policy_name: str, path: str) -> bool:
        """
        Saves Archive Policy to a file with UTF-8 encoding.
        
        Args:
            json_data (dict): The input JSON data as a dictionary.
            archive_policy_name (str): The name of the file to save the JSON data.
            path (str): The directory path where the file will be saved.
        
        Returns:
            bool: True if the file was saved successfully, False if an error occurred.
        
        Logs:
            - Success message when the file is saved.
            - Error messages for JSON processing or file writing issues.
        """
        try:

            # Create a copy of the JSON data to avoid modifying the original
            modified_json = json_data.copy()
            
            # Remove the 'links' key if it exists
            modified_json.pop("links", None)

            converted_json = self.convert_json(modified_json)
            
            # Construct the full file path
            file_path = os.path.join(path, archive_policy_name + '.json')
            
            # Save the modified JSON to a file with UTF-8 encoding
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(converted_json, f, ensure_ascii=False, indent=2)
            
            # Log success
            self.logger.info(f"Archive policy {archive_policy_name} saved successfully at: {file_path}")

            return True
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Error processing JSON: {e}")
            return False
        except OSError as e:
            self.logger.error(f"Error writing to file: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False

    def convert_json(self, input_json):
        """
        Convert a JSON object to match the structure of the target JSON by removing specific keys
        and adding missing ones.
        
        Args:
            input_json (dict): The input JSON object to transform.
        
        Returns:
            dict: The transformed JSON object.
        """
        # Create a deep copy to avoid modifying the input
        output_json = json.loads(json.dumps(input_json))
        
        # Keys to remove from the top level
        keys_to_remove = [
            'decimalSeparator',
            'enableAggregation',
            'enableEnhancedFieldLevelJoining',
            'requireMatchForFieldExtraction',
            'sampleFile',
            'locationIndexScope'
        ]
        
        # Remove specified top-level keys if they exist
        for key in keys_to_remove:
            output_json.pop(key, None)
        
        # Remove specific keys from documentInfo if it exists
        if 'documentInfo' in output_json:
            document_info_keys_to_remove = ['documentID', 'useLastVersion', 'useAllSections']
            for key in document_info_keys_to_remove:
                output_json['documentInfo'].pop(key, None)
        
        # Add xmlParentInfoList if it doesn't exist
        if 'xmlParentInfoList' not in output_json:
            output_json['xmlParentInfoList'] = []
        
        return output_json

# Ejecutar la función
if __name__ == "__main__":

        # Configure logger
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
    logging.getLogger('requests').setLevel(logging.CRITICAL)

    logger = logging.getLogger('')
    logger.handlers = []
    logger.setLevel(getattr(logging, "DEBUG"))
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

    config_file = 'C:\\git\\content-python-library\\dev\conf\\rocketcontent.11759.yaml'  # Ensure this file exists

    config_file = 'C:\\git\\content-python-library\\apps\export_import\\conf\\target.yaml'
    content_obj = ContentServicesApi(config_file)


    content_adm_archive_policy = ContentAdmArchivePolicy(content_obj.config)

    status = content_adm_archive_policy.import_archiving_policy(
        archiving_policy_path='C:\\git\\content-python-library\\apps\\export_import\\output_ap\\AP_ES_CONSOLE_API.json.txt',
        archiving_policy_name='AP_ES_CONSOLE_API'
    )
    print(f"Import Archiving Policy Status: {status}")
    exit(0)
    # Export archiving policies
    export_path = 'C:\\git\\content-python-library\\dev\\output\\'
    ap_filter = ''            
    content_adm_archive_policy.export_archiving_policies(ap_filter, export_path)
    print(f"Exported archiving policies to: {export_path}")
