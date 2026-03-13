import json
import requests
import base64
import logging
import os
import urllib3
import warnings
import yaml
import os
from copy import deepcopy
from urllib.parse import quote

from rocketcontent.util import copy_file_with_timestamp, calculate_md5, verify_md5

# Disable https warnings if the http certificate is not valid
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

class ContentConfig:
    
    VALID_DEBUG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NONE"]
    
    # API Endpoints
    REPOSITORIES_ENDPOINT = "/repositories"
    MOBIUS_REST_ENDPOINT = "/mobius/rest"
    VDR_CONTENT_SOURCES_ENDPOINT = "/mobius/adminrest/vdrcontentsources"
    VDR_REPOSITORIES_ENDPOINT = "/mobius/adminrest/vdrrepositories"
    
    client_id: str  # Anotación de tipo para client_id

    def __init__(self, yaml_file):
        """
        Initializes the ContentConfig class by reading and validating a YAML file.
        
        Args:
            yaml_file (str): The path to the configuration YAML file.
        """

        # Verifies if the YAML configuration file exists
        if not os.path.exists(yaml_file):
             raise FileNotFoundError(f"YAML file '{yaml_file}' not found.")

        # Opens the file and load it into "config"
        try: 
            with open(yaml_file, 'r') as file:
                config = yaml.safe_load(file)
        except:
            raise ValueError(f"Not valid YAML configuration file '{yaml_file}'.")

        # Verifies the required attributes 
        required_attributes = ['repo_name', 'repo_pass', 'repo_user', 'repo_url']
            
        if config and 'repository' in config:
            content_data = config['repository']
            for attr in required_attributes:
                if attr in content_data:
                    value = content_data[attr]
                else:
                    raise ValueError(f"Attribute: '{attr}' not found.")
        else:
            raise ValueError("Key 'repository' not found in configuration file.")  
                
        #-------------------------------
        # Read values from Required Attributes
        content_config = config['repository']
        self.config_file = yaml_file

        self.base_url = content_config.get('repo_url')
        
        # IMPORTANT 'url' internal is different to 'url' in the configuration file
        self.repo_url = self.base_url + self.MOBIUS_REST_ENDPOINT
       
        self.repo_name = content_config.get('repo_name', 'Mobius') or ''
        self.repo_user = content_config.get('repo_user', 'admin') or ''
        self.repo_pass = content_config.get('repo_pass', 'admin') or ''

        if not self.repo_url.lower().startswith("https://"):
            self.repo_url = "https://" + self.repo_url
            self.base_url = "https://" + self.base_url

        #-------------------------------    
        # Read and set defualts for NON Required parameters 
        # Repository ID        
        self.repo_id = content_config.get('repo_id', '') or ''
        self.content_source_id = content_config.get('content_source_id', '') or ''
        self.repo_id_enc = content_config.get('repo_id_enc','') or ''

        # Used for Content Repository Admin Rest API
        self.repo_server_user = content_config.get('repo_server_user', 'ADMIN') or ''
        self.repo_server_pass = content_config.get('repo_server_pass', '') or ''

        self.class_navigator_cache_days_cc = int(content_config.get('class_navigator_cache_days_cc', 365))
        self.class_navigator_cache_days_reports = int(content_config.get('class_navigator_cache_days_reports', 30))
        self.class_navigator_cache_days_versions = int(content_config.get('class_navigator_cache_days_versions', 30))
        self.class_navigator_page_limit = int(content_config.get('class_navigator_page_limit', 200))        
        
        #--- Authorization HEADERS
        credentials = (self.repo_user + ":" + self.repo_pass).encode('utf-8') 
        self.encoded_credentials = base64.b64encode(credentials).decode('utf-8')

        repo_credentials = (self.repo_server_user + ":" + self.repo_server_pass).encode('utf-8')
        self.encoded_repo_credentials = base64.b64encode(repo_credentials).decode('utf-8')
         
        self.headers = {}
        self.headers['Authorization'] = f'Basic {self.encoded_credentials}'
        self.authorization_repo = "Authorization-Repo-" + self.repo_id   
        self.headers[self.authorization_repo] = f'Basic {self.encoded_repo_credentials}' 
        
        #--- END Authorization HEADERS

        # Opcional: client-id para headers especiales
        self.client_id = content_config.get('client_id', 'AKxwdvdB1DSLvL5jxz5-uXH1G1ElOwZ9kj1r9lPw1slDYoJ_LjPsoNsiUpQSINQoGzyfESp3OYnONLmLqqyElw5Fh3xpnveuLYkknAp7frKINUqwGmOAA3owMzDSOQQWxLFbFYnWAXDNkQKOptesoI8aym4wxuIOtcc2MKGJR76H9gBmAl6pmTWxCQBO_864yCcrRBeu-SCKi436BQ3aRySFHdmmsSI35XVLsEg29Wb3R_RG_eChj5kf-M1Zcs0_J2vI5rMpaZN8bB5Fpb-dTMpbhwf3CN5vUF-bAdKtbf3RXzDacM4K0ugfAfEjkCw36qlEB3Qu6nCyZj7MdFbUTMxyNwwvYAuRhNm47jq3-BVGYoXTJyeGSIMpmZtmYOF2tc_-JShHbnZ0WfbySASbPHZZduo9dm9orXgPVzyfGCsrGP5541EXHWy9buZ3XvbOuD7Pto8POtrIJRC1_gC3G16Z2reHGSHSbzYJHFykQFghSpHNwMS2AZBNn4CXZEl-fEmj92UJpq6EwKuR14UPtvwOtCXiHS-P_ofo1n0duF8gqNIoZ1LWdfxFzvMImuUHmbNdMqs91M9flIE_PFnU0Nw2eHCFlYNJKqedFiV2NNrX1mQEHJnTmwdGBWbb6R5_ibaKQy__6a6duuLoyNGy6M3U4lpViFyd0IPCoQTbxqUNouecm3i2JZM8E0WfPWa_SiXwsKSurNNSeNzfagQsS_D-JA5EJjSwaA9ZYw3sBnbZiWK_v1r9uciYGoS9OZbSA3IfZeyhpwcjtARXVBRCOBLfpT_rIJelY-sWPkHNJJvgtAXzV_qGTyl54WHhSmxP7vT9bExNY-h-oDlh2PebA4VFPdzZXDHbrT3UeAKwTGlJAqhtjl1yEpZhS_9fiS8US0_ljwHCF9vlyAC3Kd0TNdf01x52krkZVvImRYPzKK_bgqUUOGY47Zi4mgBbhj_WJxGDIFX3YhBn')

        # Log Level
        self.log_level = content_config.get('log_level', "INFO")
        if self.log_level not in self.VALID_DEBUG_LEVELS:
            self.log_level = "INFO"

        # Set Logging configuration (console only)
        self.logger = logging.getLogger(__name__)
        if self.log_level != "NONE":
            if self.log_level == "DEBUG":
                self.logger.setLevel(logging.DEBUG)
            elif self.log_level == "INFO":
                self.logger.setLevel(logging.INFO)
            elif self.log_level == "ERROR":
                self.logger.setLevel(logging.ERROR)
            elif self.log_level == "CRITICAL":
                self.logger.setLevel(logging.CRITICAL)
            else:
                self.logger.setLevel(logging.WARNING)

            # Solo agregar handler a consola si no hay handlers configurados globalmente
            root_logger = logging.getLogger()
            if not root_logger.handlers:
                # No hay configuración global, agregar handler a consola
                if not self.logger.handlers:
                    console_handler = logging.StreamHandler()
                    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
                    self.logger.addHandler(console_handler)
                self.logger.propagate = False  # Desactiva la propagación
            else:
                # Hay configuración global, propaga los logs
                self.logger.propagate = True
        else:
            # Disable logging completely
            self.logger.handlers = []
            self.logger.setLevel(logging.CRITICAL + 1)  # Higher than any valid level
        # End of Logging configuration                           
        #---------------

        # Verifies if the YAML configuration was changed
        config_is_the_same = self.verify_md5()

        if not config_is_the_same:
             
            self.repo_id = ''
            self.content_source_id = '' 
            self.repo_id_enc = ''
             
            # Refresh the repository ID, contentSourceId  and repo_id_ENC.
            self.get_repo_id()
             
            # Gets the current configuration in memory
            new_content_config = self.get_current_config()
             
            # Saves the updated configuration and calculates the MD5
            self.save_config(new_content_config) 

        self.logger.info("---------------------------#  NEW SESSION #--------------------------------")
        self.logger.info("                          Content Services API                             ")
        self.logger.info("---------------------------------------------------------------------------")
        self.logger.info (f"Configuration file : {yaml_file}")
        self.logger.info("Repository Configuration:")
        self.logger.info(f"  Repo URL         : {self.base_url}")
        self.logger.info(f"  Repo Name        : {self.repo_name}")     
        self.logger.info(f"  Repo User        : {self.repo_user}")
        self.logger.info(f"  Repo Server User : {self.repo_server_user}")
        self.logger.info(f"  Repo ID          : {self.repo_id}")
        self.logger.info(f"  Log Level        : {self.log_level}")
        
        if config_is_the_same:
            # Doing a ping to Content Repository
            self.get_repo_capabilities()

        self.repo_admin_url = self.base_url + self.repo_id_enc

    def _validate_url(self, url):
        """
        Validate URL format.
        
        Args:
            url (str): URL to validate
            
        Returns:
            bool: True if URL is valid, False otherwise
        """
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None

    #------------------------------------
    # Saves the updated configuration to a YAML file and generates an MD5 checksum file.
    # This method is called when the configuration file is changed or when the repository ID is updated.
    # It also updates the content_source_id and repo_id_enc if they are not present in the configuration.
    def save_config(self, config):
        """
        Saves the updated configuration in specified order to a YAML file and generates an MD5 checksum file.

        Args:
            config (dict): The configuration dictionary to save.
        """

        copy_file_with_timestamp(self.config_file)
        
        # Define el orden deseado de las claves
        key_order = [
            "log_level",
            "repo_url",
            "repo_name",
            "repo_user",
            "repo_pass",
            "repo_server_user",
            "repo_server_pass",
            "repo_id",
            "repo_id_enc",
            "content_source_id",
            "class_navigator_cache_days_cc",
            "class_navigator_cache_days_reports",
            "class_navigator_cache_days_versions",
            "class_navigator_page_limit"
        ]

        # Reordena el diccionario
        ordered_repo = {k: config["repository"][k] for k in key_order if k in config["repository"]}
        ordered_config = {"repository": ordered_repo}

        with open(self.config_file, "w") as f:
            yaml.dump(ordered_config, f, sort_keys=False)

        # Calculate and save MD5
        md5_checksum = calculate_md5(self.config_file)
        with open(self.config_file + ".md5", "w") as f:
            f.write(md5_checksum)

        self.md5_checksum = md5_checksum

    def verify_md5(self):
        """
        Verifies if the MD5 checksum of a YAML file matches the content of its corresponding .md5 file.

        Args:
            yaml_filepath (str): The path of the YAML file.

        Returns:
            bool: True if the checksum matches, False otherwise.
        """
        md5_filepath = self.config_file + ".md5"

        if not os.path.exists(md5_filepath):
            return False

        try:
            with open(md5_filepath, "r") as f:
                expected_md5 = f.read().strip()
        except FileNotFoundError:
            return False

        actual_md5 = calculate_md5(self.config_file)


        if actual_md5 == expected_md5:
            self.md5_checksum = actual_md5  
            return True
        else:
           return False
    # Return the current configuration in memory
    def get_current_config(self):
        content_config = {} 
        content_config["repository"] = content_config.get("repository", {}) # Creates 'repository' key if doesn't exist
        content_config["repository"]["repo_url"] = self.base_url  
        content_config["repository"]["repo_name"] = self.repo_name  
        content_config["repository"]["repo_server_user"] = self.repo_server_user  
        content_config["repository"]["repo_server_pass"] = self.repo_server_pass         
        content_config["repository"]["repo_user"] = self.repo_user  
        content_config["repository"]["repo_pass"] = self.repo_pass  
        content_config["repository"]["repo_id"] = self.repo_id  
        content_config["repository"]["log_level"] = self.log_level 
        content_config["repository"]["content_source_id"] = self.content_source_id   
        content_config["repository"]["repo_id_enc"] = self.repo_id_enc 

        content_config["repository"]["class_navigator_cache_days_cc"] = int(self.class_navigator_cache_days_cc)
        content_config["repository"]["class_navigator_cache_days_reports"] = int(self.class_navigator_cache_days_reports)
        content_config["repository"]["class_navigator_cache_days_versions"] = int(self.class_navigator_cache_days_versions)
        content_config["repository"]["class_navigator_page_limit"] = int(self.class_navigator_page_limit)

        return content_config
     
    # Updates Repository ID in the configuration file
    def get_repo_id(self):
        """Retrieves the repository ID, contentSourceId  and repo_id_ENC."""
 
        try:
            repositories_url= self.repo_url + self.REPOSITORIES_ENDPOINT

            headers = {}
            headers['Authorization'] = f'Basic {self.encoded_credentials}'

            self.logger.info("--------------------------------")
            self.logger.info("Method : get_repo_id")
            self.logger.debug(f"Headers : {json.dumps(headers)}")
            self.logger.debug (f"URL: {repositories_url}")               

            response = requests.get(repositories_url, headers=headers, verify=False)  # Make a GET request to the specified URL
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            data = response.json()  # Parse the JSON response

            if "items" in data and len(data["items"]) > 0:  # Check if "items" key exists and is not empty

                for repItems in data['items']:
                    if repItems['name'] == self.repo_name:
                        self.repo_id = repItems['repositoryId']  # Extract the repositoryId

                if not self.repo_id:
                    self.logger.error(f"Repository '{self.repo_name}' not found.")
                    raise ValueError(f"Repository '{self.repo_name}' not found.")
                    
                try:
                    self.headers = {}
                    self.headers['Authorization'] = f'Basic {self.encoded_credentials}'
                    self.authorization_repo = "Authorization-Repo-" + self.repo_id   
                    self.headers[self.authorization_repo] = f'Basic {self.encoded_repo_credentials}' 

                    self.get_vdr_content_sources()
                except:
                    self.logger.error(f"VDR Repository '{self.repo_name}' not found.")
                    raise ValueError(f"VRD Repository '{self.repo_name}' not found.")                                  
                  
                self.logger.debug (f"Repository ID: {self.repo_id}")       
                
            else:
                self.logger.error("'items' or 'items' not found in reponse.") # print a message if items is not found or empty
                raise ValueError("'items' or 'items' not found in reponse.")

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error doing the request: {e}") # Handle request exceptions
            raise requests.exceptions.RequestException(f"Error doing the request: {e}")
        except json.JSONDecodeError:
            self.logger.error("Invalid JSON.") # Handle JSON decoding errors
            raise ValueError("Invalid JSON.")
        except KeyError as e:
            self.logger.error(f"Key '{e}' doesn not found in JSON.") #Handle key errors
            raise ValueError(f"Key '{e}' doesn not found in JSON.")



    def get_vdr_content_sources(self):
        try:
            content_sources_url= self.base_url + self.VDR_CONTENT_SOURCES_ENDPOINT
    
            headers = deepcopy(self.headers)  # Copy the headers from the instance
            headers['Accept'] = 'application/vnd.asg-mobius-admin-vdrcontentsources.v2+json'

            self.logger.info("--------------------------------")
            self.logger.info("Method : get_vdr_content_sources")
            self.logger.debug(f"URL : {content_sources_url}")
            self.logger.debug(f"Headers : {json.dumps(headers)}")
               
            # Send the request
            response = requests.get(content_sources_url, headers=headers, verify=False)
            json_data = json.loads(response.text)
            
            self.logger.info(response.text)

            self.content_source_id = ""
            self.repo_id_enc = ""

            items = json_data["items"]
            links = items[0]["links"]
            self.content_source_id = links[0]["href"]
            self.content_source_id = self.content_source_id.replace("/mobius/adminrest/vdrcontentsources/", "")

            self.logger.info(f"contentSourceId={self.content_source_id}")

            self.logger.info("--------------------------------")
            self.logger.info("Method : get_vdr_content_sources")
            self.logger.debug(f"URL : {content_sources_url}")
            self.logger.debug(f"Headers : {json.dumps(headers)}")

            vdrrepositories_url= self.base_url + f"{self.VDR_REPOSITORIES_ENDPOINT}?contentsourceid={self.content_source_id}"
            
            headers2 = deepcopy(self.headers) 
            headers2['Accept'] = 'application/vnd.asg-mobius-admin-vdrrepositories.v1+json'
                        
            response = requests.get(vdrrepositories_url, headers=headers2, verify=False)
            
            data = json.loads(response.text)

            href_values = []

            if "items" in data:
                for item in data["items"]:
                    if "links" in item:
                        for link in item["links"]:
                            if "href" in link and "/mobius/adminrest/vdrrepositories/ENC(" in link["href"]:
                                # Extraer el valor dentro de ENC(...)
                                start_index = link["href"].find("ENC(") + 4
                                end_index = link["href"].find(")", start_index)
                                enc_value = link["href"][start_index:end_index]

                                # Escapar los caracteres especiales
                                escaped_enc_value = quote(enc_value)

                                # Reemplazar el valor original con el valor escapado
                                escaped_href = link["href"].replace(enc_value, escaped_enc_value)

                                href_values.append(escaped_href)            

            for href in href_values:
                # self.repo_id_enc = /mobius/adminrest/vdrrepositories/ENC(Y2E0OWEyYjMtMzU2Ni00MjE4LTk3MzItOWMwM2ExNDRmNGQwL1ZEUk5ldFNRTA)
                self.repo_id_enc = href.replace("/redactionpolicies","")

            self.logger.info(f"repo_id_enc={self.repo_id_enc}")
            
            if self.repo_id_enc == "" or self.content_source_id == "":
                self.logger.error("VDR repository information not found")
                raise ValueError ("VDR repository information not found")
                   
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            raise ValueError (f"An error occurred: {e}")
        

    # Verifies if Content Repository is active
    # it uses the repo_id and the credentials
    def get_repo_capabilities(self):
        """Retrieves the repository ID, contentSourceId  and repo_id_ENC."""
 
        try:
            capabilities_url= self.repo_url + "/repositories/" + self.repo_id + "/capabilities"
            
            headers = deepcopy(self.headers)  # Copy the headers from the instance

            headers['Accept'] = 'application/vnd.asg-mobius-repository-capability.v1+json'

            self.logger.info("--------------------------------")
            self.logger.info("Verifying if the repository is active")
            self.logger.debug (f"URL: {capabilities_url}")
  
            response = requests.get(capabilities_url, headers=headers, verify=False)  # Make a GET request to the specified URL

            response.raise_for_status()  # Lanza una excepción para códigos de error HTTP

        except requests.exceptions.ConnectTimeout as e:
            self.logger.error(f"Connection to Content Repository was not possible, verifies network connection or the server: {e}") # Handle request exceptions
            raise Exception(f"Connection to Content Repository was not possible, verifies network connection or the server: {e}")

        except requests.exceptions.RequestException as e:  # Captura otras excepciones de requests
            self.logger.error(f"Request: {e}") # Handle request exceptions
            raise Exception("Content Repository is not active, or credentials are not valid, or repository ID is not valid(delete repoID config, and try again)")    
            
        except Exception as e:
            self.logger.error(f"HTTP request: {e}") # Handle request exceptions
            raise Exception(f"HTTP request: {e}")    


 