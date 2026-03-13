import os

from rocketcontent.content_services_api import ContentServicesApi

# Use the classes...
"""
conf/rocketcontent.yaml
-----------
    repository:
        log_level: DEBUG     # Valid log Levels: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
        repo_id: 
        repo_name: Mobius
        repo_pass: admin
        repo_user: admin
        repo-server_user: ADMIN
        repo-server_pass: ''
        repo_url: https://rocketcontent.com:8444        
"""

try:
    # ContentServicesApi class requires a configuration file
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
    
    # Connect to the repository
    # CONTENT_CONFIG is an environment variable that can be set to override the default configuration file path
    # If not set, it defaults to 'conf/rocketcontent.yaml'
    config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.11567.yaml')
    content_obj = ContentServicesApi(config_file)

    print(f"Using configuration file: {config_file}")
    print(f"Repository ID: {content_obj.config.repo_id}")
    print(f"Repository Name: {content_obj.config.repo_name}")
    print(f"Repository URL: {content_obj.config.repo_url}")    
    print(f"Repository User: {content_obj.config.repo_user}")
    print(f"Repository Server User: {content_obj.config.repo_server_user}")

  


except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}")