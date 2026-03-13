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

    print ("Document list")

    if search_results:
        for object_id in search_results:
            print(object_id)

    print (f"Search results: {len(search_results)}")
    
except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}")