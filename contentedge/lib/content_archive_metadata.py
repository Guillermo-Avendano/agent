import json
import requests
import base64
import urllib3
import warnings
import os
from copy import deepcopy

from .util import get_uppercase_extension
from .content_config import ContentConfig

# Disable https warnings if the http certificate is not valid
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

class ArchiveMetadata:
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value
    
    def to_dict(self):
        return {
            "name": self.name,
            "value": self.value
        }

class ArchiveDocument:
    def __init__(self, document_class_id: str, file: str):
        self.document_class_id = document_class_id
        self.file = file
        self.type = os.path.splitext(file)[1][1:].upper() if os.path.splitext(file)[1] else "UNKNOWN"
        self.metadata = []
        self.section_set = False  # Track if SECTION has been set

        if self.type == "PNG":
            self.mime_type = "image/png"
        elif self.type == "PDF":
            self.mime_type = "application/pdf"
        elif self.type == "JPG":
            self.mime_type = "image/jpeg"
        elif self.type == "TXT":
            self.mime_type = "text/plain"    
        elif self.type == "SYS":
            self.mime_type = "text/plain"    
        else:
            raise ValueError("Unsupported file extension. Supported types are: PNG, PDF, JPG, TXT, and SYS")   
        
    def set_section(self, section_value: str):
        """
        Set or update section value, truncated to 20 characters.
        """
        section_value = section_value[:20]
        for item in self.metadata:
            if item.name == "SECTION":
                item.value = section_value
                self.section_set = True
                return
        # If SECTION doesn't exist, add it
        self.metadata.append(ArchiveMetadata("SECTION", section_value))
        self.section_set = True
    
    def set_file(self, file: str):
        self.file = file
        self.type = os.path.splitext(file)[1][1:].upper() if os.path.splitext(file)[1] else "UNKNOWN"
    
    def add_metadata(self, name: str, value: str):
        """
        Adds a new name-value pair to the metadata, only if the name does not already exist.
        """
        if name == "SECTION":
            self.set_section(value)  # Use set_section for "SECTION"
        else:
            # Check if the name already exists in the metadata list
            if not any(item.name == name for item in self.metadata):
                self.metadata.append(ArchiveMetadata(name, value))
            else:
                raise ValueError(f"The index name '{name}' already exists in the metadata.")
    
    def to_dict(self):
        return {
            "documentClassId": self.document_class_id,
            "type": self.type,
            "metadata": [m.to_dict() for m in self.metadata]
        }

class ArchiveDocumentCollection:
    def __init__(self):
        self.objects = []
    
    def add_document(self, document: ArchiveDocument):
        self.objects.append(document)
    
    def to_dict(self):
        return {
            "objects": [doc.to_dict() for doc in self.objects]
        }
    
    def get_files(self):
        return [doc.file for doc in self.objects]

 
class ContentArchiveMetadata:

    def __init__(self, content_config):

        if isinstance(content_config, ContentConfig):
            self.repo_url = content_config.repo_url
            self.repo_id = content_config.repo_id
            self.logger = content_config.logger
            self.headers = deepcopy(content_config.headers)
        else:
            raise TypeError("ContentConfig class object expected")

    def archive_metadata(self, document_collection: ArchiveDocumentCollection):
        """
        Creates and sends a multipart/mixed HTTP POST request with metadata and a base64 encoded file using ArchiveDocumentCollection.
        """
        boundary_string = "boundaryString"

        try:           

            body_parts = []

            #--------------------------------------------------------------
            # BODY
            body_parts.append(f"--{boundary_string}")
            body_parts.append("Content-Type: application/vnd.asg-mobius-archive-write-metadata.v2+json")
            body_parts.append("")
            body_parts.append(json.dumps(document_collection.to_dict(), indent=2))              
            
            for archive_document in document_collection.objects:   

                if archive_document.mime_type != "text/plain":
                    # If the file is not a text file, read it in binary mode and convert it to base64
                    with open(archive_document.file, "rb") as image_file:
                       encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

                    body_parts.append(f"--{boundary_string}")
                    body_parts.append(f"Content-Type: {archive_document.mime_type}")
                    body_parts.append("Content-Transfer-Encoding: base64")
                    body_parts.append( "")
                    body_parts.append(encoded_image)
                 
                else:
                    with open(archive_document.file, 'r', encoding='utf-8') as txt_file:     
                        txt_file_contents = txt_file.read()

                    body_parts.append(f"--{boundary_string}")
                    body_parts.append("Content-Type: text/plain")
                    body_parts.append( "")
                    body_parts.append(txt_file_contents)
                                           
            #--------------------------------------------------------------
            # BODY
            body_parts.append(f"--{boundary_string}--")
            body = "\n".join(body_parts)

            # END BODY
            #--------------------------------------------------------------  
  
            archive_write_url= self.repo_url + "/repositories/" + self.repo_id + "/documents?returnids=true"

            self.headers['Content-Type'] = f'multipart/mixed; TYPE=metadata; boundary={boundary_string}'
            self.headers['Accept'] = 'application/vnd.asg-mobius-archive-write-status.v2+json'  

            self.logger.info("--------------------------------")
            self.logger.info("Method : archive_metadata")
            self.logger.debug(f"URL : {archive_write_url}")
            self.logger.debug(f"Headers : {json.dumps(self.headers)}")
            self.logger.debug(f"Body : \n{body}")
                
            # Send the request
            response = requests.post(archive_write_url, headers=self.headers, data=body, verify=False)
            
            self.logger.debug(response.text)

            return response.status_code
            #return ""
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
    

