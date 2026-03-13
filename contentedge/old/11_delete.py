import os

from rocketcontent.content_services_api import ContentServicesApi
from rocketcontent.content_search import IndexSearch

try:
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
    config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml')
    content_obj = ContentServicesApi(config_file)
    # Elimina las líneas que crean config y doc_obj

    # Crear búsqueda usando IndexSearch
    index_search = IndexSearch()
    index_search.add_constraint(index_name="DEPT", operator="EQ", index_value="0013")
    search_results = content_obj.search_index(index_search)

    #---------------------------------------------------
    print ("Delete DEPT=0013")
    if search_results:
        for object_id in search_results:
            print(f"Deleting: {object_id}")
            status = content_obj.delete_document(object_id)
            print(f"Status :{status}")

    #---------------------------------------------------
    print ("Delete DEPT=0014")
    index_search = IndexSearch()
    index_search.add_constraint(index_name="DEPT", operator="EQ", index_value="0014")
    search_results = content_obj.search_index(index_search) 

    if search_results:
        for object_id in search_results:
            print(f"Deleting: {object_id}")
            status = content_obj.delete_document(object_id)
            print(f"Status :{status}")
                  
    #---------------------------------------------------
    print ("Delete CUST_ID=1000")
    index_search = IndexSearch()
    index_search.add_constraint(index_name="CUST_ID", operator="EQ", index_value="1000")
    search_results = content_obj.search_index(index_search) 
    if search_results:
        for object_id in search_results:
            print(f"Deleting: {object_id}")
            status = content_obj.delete_document(object_id)
            print(f"Status :{status}")    
        
except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}")