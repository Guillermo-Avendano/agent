import os
from rocketcontent.content_adm_services_api import ContentAdmServicesApi

try:
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
    config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml')
    content_adm_obj = ContentAdmServicesApi(config_file)
    
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'output'))
    
    #-------------------------------------------------------------------
    # Export Content Classes Definitions
    # This code exports content classes definitions filtered by a specific ID.
    # It checks if the output directory exists and raises an error if it does not.
    # The exported content classes are saved to a JSON file in the specified output directory.
    status_code = content_adm_obj.export_content_classes("A", output_path)
    print(f"Status code : {status_code}")


    #-------------------------------------------------------------------    
    # Export Index Groups Definitions
    # This code exports index groups definitions filtered by a specific ID.
    # It checks if the output directory exists and raises an error if it does not.
    # The exported index groups are saved to a JSON file in the specified output directory.
    status_code = content_adm_obj.export_index_groups("A", output_path)
    print(f"Status code : {status_code}")

except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}")