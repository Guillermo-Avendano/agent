import os

from rocketcontent.content_adm_services_api import ContentAdmServicesApi

try:

    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
    config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml')
    content_adm_obj = ContentAdmServicesApi(config_file)

except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}")