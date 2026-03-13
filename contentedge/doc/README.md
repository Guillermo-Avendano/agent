# Python Library for Content Repository

>**Disclaimer: This Python library is provided for demonstration purposes only to illustrate the use of the Content Repository API. It is explicitly stated that this library does not constitute an official Rocket Software product and lacks official support. Rocket Software assumes no responsibility for the use, performance, or any consequences arising from the use of this library. Users are advised to consult the official Rocket Software documentation for information and support regarding the Content Repository API.**

The `ContentServicesApi` Python library offers a primary class designed to facilitate interaction with the Content Repository REST Api. This class encompasses a wide range of operations, including:

- Configuration loading.
- Logging management for activity tracking.
- Repository ID handling.
- Search query execution.
- Smart chat functionality enablement.
- Document archiving and deletion.

## Table of Contents

- [Release Notes](#release-notes)

- [Installation](#installation)
    - [Configuration File](#configuration-file)
- [Class Initialization](#class-initialization)
- [Methods](#methods)
    - [Smart Chat](#smart-chat)
        - [Repository](#repository)
        - [Document List](#document-list)
        - [Conversation](#conversation)
    - [Search](#search)
    - [Document Archiving with Metadata](#document-archiving-with-metadata)
    - [Document Archiving with Policy](#document-archiving-with-policy)
    - [Delete](#delete)

<hr style="border: 1px solid grey; background-color: grey;">

`ContentAdmServicesApi` Python library offers a primary class designed to facilitate interaction with the Content Repository Administration REST Api. This class encompasses a wide range of operations, including:
Create Content Classes, Create Indexes, Import Archiving Policies.

- [Administration API](#administration-api)    


<hr style="border: 2px solid grey; background-color: grey;">

## Installation

`ContentServicesApi` and `ContentAdmServicesApi` classes requires **Python 3.9+**. To install the necessary dependencies and the Content Repository library, run the following commands:

```bash
## From cmd.exe
pip install rocketcontent
```

### Configuration file

* Create a YAML configuration file (e.g., `rocketcontent.yaml`) to store your Content Repository ID, credentials and settings. For the first connection, leave the `repo_id` field blank—it will be populated automatically.

    ```yaml
    # <python-content-services-api-dir>/conf/rocketcontent.yaml
    repository:
        log_level: DEBUG     # Valid log Levels: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NONE"
        repo_id: 
        repo_name: myRepo
        repo_server_user: ADMIN
        repo_server_pass: ''
        repo_pass: admin
        repo_user: $admin$
        repo_url: https://contentrepo.rocket.com        
    ```

    > **Note: Ensure the configuration file is placed in the appropriate directory (e.g., `<python-content-services-api-dir>/conf/`).**

## Class Initialization
[Table of Contents](#table-of-contents)

The `ContentServicesApi` class is the primary interface for interacting with the Content Repository REST Api. It is instantiated by providing a YAML configuration file that contains essential settings for Api communication. Once initialized, it exposes methods for performing various operations against the Content Repository REST Api.

The class uses the YAML configuration file to persistently store key attributes, such as the repository ID (`repo_id`), which are required for many Api methods. Upon initial data retrieval from Content Repository, an MD5 checksum file is generated alongside the configuration. If the YAML file is modified, a refresh mechanism triggers a re-fetch of the `repo_id` from Content Repository to ensure consistency.

> **Note:** Use `try:` and `except:` blocks for robust error handling.

* **Parameter**:
    - `yaml_config_file`: **[Mandatory]** Path to the YAML configuration file. 

* **Returns**:
    - A `ContentServicesApi` object. 

* **Example**:
    - The `01_repository.py` program illustrates the initialization process of this object and displays its key attributes.

    ```python
    import os
    from rocketcontent.content_services_api import ContentServicesApi
    
    try:
        cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
        # Connect to the repository
        # CONTENT_CONFIG is an environment variable that can be set to override the default configuration file path
        # If not set, it defaults to 'conf/rocketcontent.yaml'        
        config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml') 
        content_obj = ContentServicesApi(config_file)

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")    
    ```

<hr style="border: 2px solid grey; background-color: grey;">

## Methods

### Smart Chat 
[Table of Contents](#table-of-contents)

  The `smart_chat` method enables interaction with the Content Repository Smart Chat Api. It supports queries at the repository level or against a specific list of documents. To maintain context across multiple interactions, a `conversation` ID can be provided.


* **Prerequisites:**
    - [Class Initialization](#class-initialization)
    
* **Parameters:**
    - `question`: **[Mandatory]** The query to send to the Smart Chat Api.
    - `document_ids`: **[Optional]** An array of document IDs to limit the query scope.
    - `conversation`: **[Optional]** A conversation ID to maintain context across interactions.

* **Returns:**

    A `SmartChatResponse` object with the following attributes:

    - `answer`: The text with the answer generated by the Smart Chat Api.
    - `object_ids`: A list of documents that are relevant to the query.
    - `conversation`: The conversation state, allowing for subsequent interactions.

* Usage Modes:
    - [Repository](#repository)
    - [Document List](#document-list)
    - [Conversation](#conversation)

---

#### Repository
[Smart Chat](#smart-chat)

  Queries the entire Content Repository repository using the Smart Chat Api.

* **Example:**

   The `02_smart_chat_repo.py` script demonstrates a repository-level query:

    ```python
    import os
    from rocketcontent.content_services_api import ContentServicesApi
    
    try:
        cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
        # CONTENT_CONFIG is an environment variable that can be set to override the default configuration file path
        config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml')         
        content_obj = ContentServicesApi(config_file)

        # Smart Chat uses all the repository
        smart_chat_response = content_obj.smart_chat("Tell me about John Smith")    

        print(smart_chat_response.answer)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")    
    ```
* **Logging:**

    With `log_level="DEBUG"` in the configuration, all Smart Chat Api interactions are logged, including JSON payloads. Example log output:

    ```log
    2025-03-11 11:10:05,549 - INFO - Configuration file : c:\Rocket\content_services_api\dev\conf/rocketcontent.yaml
    2025-03-11 11:10:05,549 - INFO - Content Repository Configuration:
    2025-03-11 11:10:05,549 - INFO -   URL: https://contentrepo.rocket.com/mobius/rest
    2025-03-11 11:10:05,549 - INFO -   Repo Name: myRepo
    2025-03-11 11:10:05,549 - INFO -   Repo User: admin
    2025-03-11 11:10:05,549 - INFO -   Repo ID: 9CE264E6-DF17-4F63-A4C7-84E40CCAAC9C
    2025-03-11 11:10:05,549 - INFO - --------------------------------
    2025-03-11 11:10:05,549 - INFO - Smart Chat URL : https://contentrepo.rocket.com/mobius/rest/conversations
    2025-03-11 11:10:05,549 - DEBUG - Headers : {"Content-Type": "application/vnd.conversation-request.v1+json", "Accept": "application/vnd.conversation-response.v1+json", "Authorization-Repo-9CE264E6-DF17-4F63-A4C7-84E40CCAAC9C": "Basic YWRtaW46YWRtaW4="}
    2025-03-11 11:10:05,549 - DEBUG - Payload : {
        "userQuery": "Tell me about John Smith",
        "documentIDs": [],
        "context": {
            "conversation": ""
        },
        "repositories": [
            {
                "id": "9CE264E6-DF17-4F63-A4C7-84E40CCAAC9C"
            }
        ]
    }
    2025-03-11 11:10:05,549 - DEBUG - Starting new HTTPS connection (1): https://contentrepo.rocket.com
    2025-03-11 11:10:25,871 - DEBUG - https://contentrepo.rocket.com "POST /mobius/rest/conversations HTTP/1.1" 200 None
    ```
---
#### Document List
[Smart Chat](#smart-chat)

  Limits Smart Chat queries to a specific list of documents.

* **Prerequisites:**
    - [Repository](#repository)
    - [Search](#search)  
    - [Content Classes and Indexes](#content-classes-and-indexes)

* **Example:**

    The `05_smart_chat_documents_from_search_04.py` script searches for documents and uses the results in a Smart Chat query:

    ```python
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
    ```
---
#### Conversation
[Smart Chat](#smart-chat)

  Maintains context across multiple Smart Chat interactions using a `conversation` ID.

* **Prerequisites:**
    - [Document List](#document-list)

* **Example:**

    The `09_smart_chat_conversation.py`  script demonstrates two consecutive queries with context:

    ```python
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

        print("---------------------------------------")
        # Doing 1st question
        question = "Who is the loan applicant?"
        smart_chat_response = content_obj.smart_chat( question ,search_results )

        print(smart_chat_response.answer)

        print("---------------------------------------")
        # Following the conversation
        question = "Give me more details about him"
        smart_chat_response = content_obj.smart_chat( question ,search_results, smart_chat_response.conversation )

        print(smart_chat_response.answer)
        
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
    ```    

<hr style="border: 2px solid grey; background-color: grey;">

## Search
[Table of Contents](#table-of-contents)

The `search_index` method allows you to search for documents in the Content Repository using index constraints.

* **Prerequisites:**
    - [Class Initialization](#class-initialization)

* **Parameters:**
    - `index_search` (**IndexSearch**): The search builder object with one or more constraints.

* **Returns:**
    - A list of document IDs matching the search criteria.

* **Example:**
    - The `04_simple_search.py` script shows a search using the index `CUST_ID`.

    ```python
    import os
    from rocketcontent.content_services_api import ContentServicesApi
    from rocketcontent.content_search import IndexSearch

        try:

            cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
            config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml')
            content_obj = ContentServicesApi(config_file)

            index_search = IndexSearch()
            index_search.add_constraint("CUST_ID", "EQ", "1000")
            search_results = content_obj.search_index(index_search)

            print(search_results)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}")     
    ```

- Use `add_constraint(index_name, operator, index_value)` to add search conditions.
- Use `search_index` to execute the search and get a list of object IDs.

<hr style="border: 2px solid grey; background-color: grey;">

## Document Archiving with Metadata
[Table of Contents](#table-of-contents)

   The `archive_metadata` method archives a list of documents with associated metadata.

* **Prerequisites:**
    - [Class Initialization](#class-initialization)
    - [Content Classes and Indexes](#content-classes-and-indexes)

* **Parameters**:
    - `ArchiveDocumentCollection`:**[Mandatory]** Object containing a list of documents with metadata (indexes).

* **Returns** 
    - HTTP status code (e.g., `201` indicates success).

* **Example:**

    The `06_archive_binary.py` script archives a PNG file with metadata:    

    ```python
    import os
    from rocketcontent.content_services_api import ContentServicesApi
    from rocketcontent.content_archive_metadata import ArchiveDocumentCollection,  ArchiveDocument

     try:
        ################ Content Repository Connection
        cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
        # CONTENT_CONFIG is an environment variable that can be set to override the default configuration file path
        config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml')
        content_obj = ContentServicesApi(config_file)
    
        ################  Archive PNG
        # Create metadata for png
        pgn_collection = ArchiveDocumentCollection()

        myfile = os.path.join(os.path.dirname(__file__) + "/files/image.png") 
        png_metadata = ArchiveDocument("LISTFILE", myfile)
        png_metadata.set_section("PNGTEST")
        png_metadata.add("DEPT", "0013")

        pgn_collection.add_document(png_metadata)
        
        # Supported file extensions: TXT, PNG, PDF, and JPG
        status = content_obj.archive_metadata(pgn_collection)
        
        print(f"File PNG {myfile} archived successfully. Response Status: {status}") 
    
     except (FileNotFoundError, ValueError) as e:
         print(f"Error: {e}") 
    ```
    > **Supported Formats: TXT, PNG, PDF, JPG, SYS.**

## Document Archiving with Policy
[Table of Contents](#table-of-contents)

   The `archive_policy` method archives TXT or PDF files using predefined Content Repository archiving policies.
   > **Note: Only `.txt` and `.pdf` files are supported.**

* Prerequisites:
    - [Class Initialization](#class-initialization)
    - [Content Classes and Indexes](#content-classes-and-indexes)
    - [Document Archiving with Metadata](#document-archiving-with-metadata)

* **Parameters**:
    - `file`: **[Mandatory]** Path to the file to archive.
    - `policy_name`: **[Mandatory]** Name of an existing archiving policy in rocketcontent.

* **Returns** 
   - HTTP status code (e.g., `201` indicates success).

* **Example:**

   The `10_archive_using_policy.py` script archives a file using a policy:

    ```python
    import os
    from rocketcontent.content_services_api import ContentServicesApi

    try:
        cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
        # CONTENT_CONFIG is an environment variable that can be set to override the default configuration file path
        config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml')         
        content_obj = ContentServicesApi(config_file)

        my_txt_file = os.path.join(os.path.dirname(__file__), "files", "AC001.txt")
        status = content_obj.archive_policy(my_txt_file, policy_name="AC001_POLICY")
        print(f"File archived successfully. Response Status: {status}")

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")  
    ```    
  > **Note: Ensure the policy (`AC001_POLICY`), content class (`AC001`), and required indexes are defined in rocketcontent. Test archiving policies using Rocket Content Explorer Capture.**

## Delete
[Table of Contents](#table-of-contents)

  Delete document by ID.

* **Prerequisites:**
    - [Search](#search)  

* **Parameters**:
    - `document_id`: **[Mandatory]** Document ID.

* **Returns** 
   - HTTP status code 
        - `204` Indicates success.
        - `404` Not found.

* **Example:**

    The `11_delete.py` script demonstrates how to delete documents from search results. It provides an example of deleting documents based on a previous search.

    ```python
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

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")                 
    ```

# Release Notes
[Table of Contents](#table-of-contents)

### 2025-07-10
- Code improved and documented

### 2025-07-08
- Tested with version 12.5.0

### 2025-06-26
- Improved Authorization Headers
- New main class `ContentAdmServicesApi` adding administrative fucntions (example:`import_archiving_policy`) 


# Administration API

[Table of Contents](#table-of-contents)

The `ContentAdmServicesApi` class is the primary interface for interacting with the Content Repository Administration REST Api. It is instantiated by providing a YAML configuration file that contains essential settings for Api communication. Once initialized, it exposes methods for performing various operations against the Content Repository Administration REST Api.

* Methods:
    - [Import Archiving Policy](#import-archiving-policy)
    - [Create Content Class](#create-content-class)
    - [Create Index Group](#create-index-group)

## Import Archiving Policy

  Import a file with an Archiving Policy definition previously exported in a JSON file.

* **Example:**

    The `51_import_archiving_policy.py` script demonstrates how to import an archiving policy definition.

     ```python
     import os
     from rocketcontent.content_adm_services_api import ContentAdmServicesApi
     try:
        cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
        # CONTENT_CONFIG is an environment variable that can be set to override the default configuration file path
        config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml')
        content_adm_obj = ContentAdmServicesApi(config_file)
    
        ##################  TXT POLICY
        # Archiving Policy to be imported
        # The file must be in the same folder as this script or provide the full path
        # The file must be a valid JSON file with the archiving policy definition
        # The file must contain the Content Class and the indexes to be used in the policy
        # The file must be defined in the ArchivingPolicies folder
        archiving_policy_file = os.path.join(os.path.dirname(__file__) + "/ArchivingPolicies/AP_ES_CONSOLE.json") 

        status = content_adm_obj.import_archiving_policy(archiving_policy_file, archiving_policy_name="AP_ES_CONSOLE")
        
        print(f"File {archiving_policy_file} archived successfully as Archiving Policy. Response Status: {status}") 

     except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")    
     ```

## Create Content Class

- [Administration API](#administration-api)   

  Create Content Class using a unique id, and name.

* **Example:**

    The `52_create_content_class.py` script demonstrates how to create a content class.

    ```python
    import os
    from rocketcontent.content_adm_services_api import ContentAdmServicesApi

    try:
        cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
        # CONTENT_CONFIG is an environment variable that can be set to override the default configuration file path
        config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml')
        content_adm_obj = ContentAdmServicesApi(config_file)
        
        #-------------------------------------------------------------------
        # Create a content class
        # The create_content_class method is used to create a new content class.
        # It requires two parameters: cc_id (content class ID) and cc_name (content class name).        
        # create_content_class method it creates a content class with:
        #  cc_id="AAA03" and cc_name="Loan Content Class"
        status_code = content_adm_obj.create_content_class("AAA03", "Loan Content Class")
        print(f"Status code : {status_code}")

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
    ```

## Create Index Group    

>**NOTE: Is in development, It's not working.**

- [Administration API](#administration-api)   

  Create Index Group using a IndexGroup object.

* **Example:**

    The `53_create_index_group.py` script demonstrates how to create a index group.

    ```python
    import os
    from rocketcontent.content_adm_services_api import ContentAdmServicesApi
    from rocketcontent.content_adm_index_group import IndexGroup, Topic

    try:
        cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'conf'))
        # CONTENT_CONFIG is an environment variable that can be set to override the default configuration file path
        config_file = os.getenv("CONTENT_CONFIG", cfg_path + '/rocketcontent.yaml')
        content_adm_obj = ContentAdmServicesApi(config_file)

        # Create an IndexGroup instance with a specific ID and name.
        # Adds three Topic instances to the index group, 
        # each with unique IDs, names, details, data types, and maximum lengths.
        # Calls the API to create the index group and prints the resulting status code.
        index_group_manual = IndexGroup(id="API_Loan_inx", name="content_repoLoan Index Group")
        
        index_group_manual.addTopic(Topic(id="A_CUST_ID", 
                                          name="A_CUST_ID", 
                                          details="A_CUST_ID content_repotest",
                                          dataType="Character",
                                          maxLength="30"))
        index_group_manual.addTopic(Topic(id="A_LOAN_ID", 
                                          name="A_LOAN_ID", 
                                          details="A_LOAN_ID content_repotest",
                                          dataType="Character",
                                          maxLength="30"))
        index_group_manual.addTopic(Topic(id="A_REQ_DATE", 
                                          name="A_REQ_DATE", 
                                          details="A_REQ_DATE content_repotest",
                                          dataType="Character",
                                          maxLength="30"))

        status_code = content_adm_obj.create_index_group(index_group_manual)
        print(f"Status code : {status_code}")
        
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
    ```
