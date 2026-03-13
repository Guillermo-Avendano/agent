import os
from rocketcontent.content_adm_services_api import ContentAdmServicesApi

try:
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
    config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml')
    content_adm_obj = ContentAdmServicesApi(config_file)
    
    #-------------------------------------------------------------------
    # Create a content class
    # The create_content_class method is used to create a new content class.
    # It requires two parameters: cc_id (content class ID) and cc_name (content class name).        
    # create_content_class method it creates a content class with:
    #  cc_id="AAA03" and cc_name="Loan Content Class"
    status_code = content_adm_obj.create_content_class("AAA03", "Loan Content Class")
    print(f"Status code : {status_code}")

except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}")