import json
import requests
import base64
import urllib3
import warnings
from copy import deepcopy

from .util import get_uppercase_extension
from .content_config import ContentConfig

# Disable https warnings if the http certificate is not valid
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

class ContentArchivePolicy:

    def __init__(self, content_config):

        if isinstance(content_config, ContentConfig):
            self.repo_url = content_config.repo_url
            self.repo_id = content_config.repo_id
            self.logger = content_config.logger
            self.headers = deepcopy(content_config.headers)
        else:
            raise TypeError("ContentConfig class object expected")

    #--------------------------------------------------------------
    # Archive based on policy
    def archive_policy(self, file_path, policy_name):

        file_type = get_uppercase_extension(file_path)

        boundary_string = "boundaryString"
            
        metadata_json = {
                            "objects": [
                                {
                                    "policies": [f"{policy_name}"]
                                }
                            ]
                        }
        
        metadata_str =  json.dumps(metadata_json, indent=4)

        try:       
            if file_type in ["TXT", "SYS", "LOG"]:
                    
                with open(file_path, 'r', encoding='utf-8') as txt_file:     
                    txt_file_contents = txt_file.read()

                body_parts = [
                            f"--{boundary_string}",
                            "Content-Type: application/vnd.asg-mobius-archive-write-policy.v2+json",
                            "",
                            metadata_str,
                            f"--{boundary_string}",
                            "Content-Type: archive/file",
                            "",
                            txt_file_contents,
                            "",
                            f"--{boundary_string}--",
                        ]

                body = "\n".join(body_parts)

            elif file_type == "PDF":
                # If the file is not a text file, read it in binary mode and convert it to base64
                with open(file_path, "rb") as image_file:
                    encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

                body_parts = [
                            f"--{boundary_string}",
                            "Content-Type: application/vnd.asg-mobius-archive-write-policy.v2+json",
                            "",
                            metadata_str,
                            f"--{boundary_string}",
                            "Content-Type: application/pdf",
                            "Content-Transfer-Encoding: base64",
                            "",
                            encoded_image,
                            "",
                            f"--{boundary_string}--",
                        ]

                body = "\n".join(body_parts)

            else:
                self.logger.error(f"File extension not valid :'{file_path}'. Only PDF, and TXT allowed") 
                raise ValueError(f"File extension not valid :'{file_path}'. Only PDF, and TXT allowed")    
                                                    
        except FileNotFoundError:
                self.logger.error(f"File not found :'{file_path}'.")
                raise FileNotFoundError(f"File not found :'{file_path}'.")
        except Exception as e:
                self.logger.error(f"Reading file : {e}")
                raise ValueError(f"Reading file : {e}")

        archive_write_url= self.repo_url + "/repositories/" + self.repo_id + "/documents?returnids=true"

        self.headers['Content-Type'] = f'multipart/mixed; TYPE=policy; boundary={boundary_string}'
        self.headers['Accept'] = 'application/vnd.asg-mobius-archive-write-status.v2+json'

        self.logger.info("--------------------------------")
        self.logger.info("Method : archive_policy")
        self.logger.debug(f"URL : {archive_write_url}")
        self.logger.debug(f"Headers : {json.dumps(self.headers)}")
        self.logger.debug(f"Body : \n{body}")
            
        # Send the request
        response = requests.post(archive_write_url, headers=self.headers, data=body, verify=False)
        
        self.logger.debug(response.text)

        return response.status_code


    #####
    #--------------------------------------------------------------
    # Archive based on policy from string
    def archive_policy_from_str(self, str_content, policy_name):

        boundary_string = "boundaryString"
            
        metadata_json = {
                            "objects": [
                                {
                                    "policies": [f"{policy_name}"]
                                }
                            ]
                        }
        
        metadata_str =  json.dumps(metadata_json, indent=4)

        try:                          
            body_parts = [
                        f"--{boundary_string}",
                        "Content-Type: application/vnd.asg-mobius-archive-write-policy.v2+json",
                        "",
                        metadata_str,
                        f"--{boundary_string}",
                        "Content-Type: archive/file",
                        "",
                        str_content,
                        "",
                        f"--{boundary_string}--",
                    ]

            body = "\n".join(body_parts)

        except Exception as e:
                self.logger.error(f"Reading file : {e}")
                raise ValueError(f"Reading file : {e}")

        archive_write_url= self.repo_url + "/repositories/" + self.repo_id + "/documents?returnids=true"

        self.headers['Content-Type'] = f'multipart/mixed; TYPE=policy; boundary={boundary_string}'
        self.headers['Accept'] = 'application/vnd.asg-mobius-archive-write-status.v2+json'

        self.logger.info("--------------------------------")
        self.logger.info("Method : archive_policy_from_str")
        self.logger.debug(f"URL : {archive_write_url}")
        self.logger.debug(f"Headers : {json.dumps(self.headers)}")
        self.logger.debug(f"Body : \n{body}")
            
        # Send the request
        response = requests.post(archive_write_url, headers=self.headers, data=body, verify=False)
        
        self.logger.debug(response.text)

        return response.status_code
