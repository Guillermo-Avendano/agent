import os

from rocketcontent.content_services_api import ContentServicesApi

try:

    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
    config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.11567.yaml')
    content_obj = ContentServicesApi(config_file)
  
    ##################  TXT POLICY
    # file to be archived
    my_txt_file = os.path.join(os.path.dirname(__file__) + "/files/AC001.txt") 

    # Archive the file with policy
    # IMPORTANT: 
    #    - The archiving policy AC001_POLICY must be defined
    #    - The Content Class AC001 must be defined 
    #    - All the indexes in the policy must be defined before
    status = content_obj.archive_policy(my_txt_file, policy_name="AC001_POLICY")
     
    print(f"File {my_txt_file} archived successfully in AC001 Content Class. Response Status: {status}") 

    ##################  PDF POLICY
    #my_pdf_file = os.path.join(os.path.dirname(__file__) + "/files/smart-chat-brochure.pdf") 


    # NOT_WORKING
    # Archive the file with policy
    # IMPORTANT: 
    #    - The archiving policy PDF_POLICY must be defined
    #    - The Content Class LISTFILE must be defined 
    #    - All the indexes in the policy must be defined before
    #status = content_obj.archive_policy (my_pdf_file, policy_name="PDF_POLICY")
     
    #print(f"File {my_pdf_file} archived successfully in LISTFILE Content Class. Response Status: {status}") 

except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}")