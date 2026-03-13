import os

from rocketcontent.content_services_api import ContentServicesApi
from rocketcontent.content_archive_metadata import ArchiveDocumentCollection,  ArchiveDocument

try:
    ################ Mobius Connection
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
    config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml')
    content_obj = ContentServicesApi(config_file)

    ################  Archive PNG
    # Create metadata for png
    pgn_collection = ArchiveDocumentCollection()

    myfile = os.path.join(os.path.dirname(__file__) + "/files/image.png") 
    png_metadata = ArchiveDocument("LISTFILE", myfile)
    png_metadata.set_section("PNGTEST")
    png_metadata.add_metadata("DEPT", "0013")

    pgn_collection.add_document(png_metadata)
    
    # Supported file extensions: TXT, PNG, PDF, and JPG
    status = content_obj.archive_metadata(pgn_collection)
     
    print(f"File PNG {myfile} archived successfully. Response Status: {status}")  

    ###############  Archive PDF
    # Create metadata for PDF
    pdf_collection = ArchiveDocumentCollection()

    myfile = os.path.join(os.path.dirname(__file__) + "/files/smart-chat-brochure.pdf") 
    pdf_metadata = ArchiveDocument("LISTFILE", myfile)
    pdf_metadata.set_section("PDFTEST")
    pdf_metadata.add_metadata("DEPT", "0014")

    pdf_collection.add_document(pdf_metadata)

    # Supported file extensions: TXT, PNG, PDF, and JPG 
    status = content_obj.archive_metadata(pdf_collection)
     
    print(f"File PDF {myfile} archived successfully. Response Status: {status}")  


except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}")