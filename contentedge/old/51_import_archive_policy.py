import os

from rocketcontent.content_adm_services_api import ContentAdmServicesApi

try:

    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
    config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.11567.yaml')
    content_adm_obj = ContentAdmServicesApi(config_file)
  
    ##################  TXT POLICY
    # Archiving Policy to be imported
    # The file must be in the same folder as this script or provide the full path
    # The file must be a valid JSON file with the archiving policy definition
    # The file must contain the Content Class and the indexes to be used in the policy
    # The file must be defined in the ArchivingPolicies folder
    archiving_policy_file = os.path.join(os.path.dirname(__file__) + "/ArchivingPolicies/AP_ES_CONSOLE.json") 

    status = content_adm_obj.import_archiving_policy(archiving_policy_file, archiving_policy_name="AP_ES_CONSOLE")
     
    print(f"File {archiving_policy_file} archived successfully as Archiving Policy. Response Status: {status}") 

except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}")