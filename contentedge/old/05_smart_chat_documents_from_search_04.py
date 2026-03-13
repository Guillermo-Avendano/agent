import os

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
    
    # Smart Chat uses the list of DocumentIDs returned by the search
    smart_chat_response = content_obj.smart_chat("Tell me about John Smith",search_results )
    
    print(smart_chat_response.answer)

except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}")