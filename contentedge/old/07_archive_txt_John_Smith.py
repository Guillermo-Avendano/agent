import os

from rocketcontent.content_services_api import ContentServicesApi
from rocketcontent.content_archive_metadata import ArchiveDocumentCollection,  ArchiveDocument

try:
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
    config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml')
    content_obj = ContentServicesApi(config_file)

    collection = ArchiveDocumentCollection()
  
    try:
        content_class_name = "AC001" 
        customer_id = "3000"
        loan_id = "H366100"
        request_date = "2025-07-05"

        directory = os.path.abspath(os.path.join(os.path.dirname(__file__), 'files'))

        filename = directory + "/John Smith - Financial Statements.txt"
        section = "Financial Statements"
        doc1 = ArchiveDocument(content_class_name, filename)
        doc1.set_section(section)
        doc1.add_metadata("CUST_ID", customer_id)
        doc1.add_metadata("LOAN_ID", loan_id)
        doc1.add_metadata("REQ_DATE", request_date)
    
        filename = directory + "/John Smith - Home improvement Estimates - Approve.txt"
        section = "Home improvement"
        doc2 = ArchiveDocument(content_class_name, filename)
        doc2.set_section(section)
        doc2.add_metadata("CUST_ID", customer_id)
        doc2.add_metadata("LOAN_ID", loan_id)
        doc2.add_metadata("REQ_DATE", request_date)

        filename = directory + "/John Smith - Legal Report - Divorce Decree - Approve.txt"
        section = "Legal Divorce Decree"
        doc3 = ArchiveDocument(content_class_name, filename)
        doc3.set_section(section)
        doc3.add_metadata("CUST_ID", customer_id)
        doc3.add_metadata("LOAN_ID", loan_id)
        doc3.add_metadata("REQ_DATE", request_date)

        filename = directory + "/John Smith - Loan Agreement.txt"
        section = "Loan Agreement"
        doc4 = ArchiveDocument(content_class_name, filename)
        doc4.set_section(section)
        doc4.add_metadata("CUST_ID", customer_id)
        doc4.add_metadata("LOAN_ID", loan_id)
        doc4.add_metadata("REQ_DATE", request_date)

        filename = directory + "/John Smith - Loan Application.txt"
        section = "Loan Application"
        doc5 = ArchiveDocument(content_class_name, filename)
        doc5.set_section(section)
        doc5.add_metadata("CUST_ID", customer_id)
        doc5.add_metadata("LOAN_ID", loan_id)
        doc5.add_metadata("REQ_DATE", request_date)

        filename = directory + "/John Smith - Reference Letter - Approve.txt"
        section = "Reference Letter"
        doc6 = ArchiveDocument(content_class_name, filename)
        doc6.set_section(section)
        doc6.add_metadata("CUST_ID", customer_id)
        doc6.add_metadata("LOAN_ID", loan_id)
        doc6.add_metadata("REQ_DATE", request_date)
 
        # Add documents to the collection
        collection.add_document(doc1)
        collection.add_document(doc2)
        collection.add_document(doc3)
        collection.add_document(doc4)
        collection.add_document(doc5)
        collection.add_document(doc6)

        status = content_obj.archive_metadata(collection)
        if status != 200:
           raise Exception(f"Failed to archive documents. Status code: {status}")  
        else:
           print("")
           print(f"Documents archived successfully. Response Status: {status}")

        for archived_document in collection.objects:   
           print(f"File '{archived_document.file}' archived successfully.") 

    except FileNotFoundError:
        print(f"Error: Directory not found '{directory}'.")
    except Exception as e:
        print(f"Error listing files in '{directory}': {e}")


except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}")