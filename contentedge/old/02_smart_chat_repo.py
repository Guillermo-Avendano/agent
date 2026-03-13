import os

from rocketcontent.content_services_api import ContentServicesApi

try:
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))

    config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.11567.yaml')
    content_obj = ContentServicesApi(config_file)

    # Smart Chat uses all the repository
    smart_chat_response = content_obj.smart_chat("Dime si los siniestros cumplen con las condiciones de la poliza")

    print(smart_chat_response.answer)

except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}")