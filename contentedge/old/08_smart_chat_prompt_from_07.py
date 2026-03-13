import os
import datetime

from rocketcontent.content_services_api import ContentServicesApi
from rocketcontent.content_search import IndexSearch

try:
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
    config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml')
    content_obj = ContentServicesApi(config_file)

    # Crear búsqueda usando IndexSearch
    index_search = IndexSearch()
    index_search.add_constraint(index_name="CUST_ID", operator="EQ", index_value="1000")

    search_results = content_obj.search_index(index_search)

    question = "Who is the loan applicant? Give a summary of the documents presented, and what is your recomendation regarding the loan?"

    x = datetime.datetime.now()

    # Example Prompt by Mike Rajkowski mrajkowski@rocketsoftware.com
    prompt_example_input = '<input>With the financial documents for John Smith.  The company name is My Saving and Loan Company, and the loan officer is Guillermo Avendano</input>'
    prompt_example_date = '<date>' + x.strftime("%x") + '</date>'
    prompt_example_criteria = '<criteria>Documents need to have name and address information</criteria> '
    prompt_example_output = '<output>Create a letter to the applicant, using the name and address from the first document that contains it. The letter needs to be from the Company and loan officer described in the Input.</output>'
    prompt_example_question = 'Determine what documents meet the criteria, and alert me if the addresses do not match?'
    prompt_example = prompt_example_input + prompt_example_criteria + prompt_example_date + prompt_example_output + " " + prompt_example_question

    smart_chat_response = content_obj.smart_chat( prompt_example ,search_results )

    print(smart_chat_response.answer)

except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}")