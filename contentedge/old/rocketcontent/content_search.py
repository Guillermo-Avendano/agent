import json
from rocketcontent.content_config import ContentConfig
import json
import requests
import urllib3
import warnings
from copy import deepcopy

# Disable https warnings if the http certificate is not valid
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

class IndexSearch:
    def __init__(self, conjunction="AND"):
        """
        Initializes the IndexSearch with an optional conjunction parameter.
        
        :param conjunction: The conjunction to use between constraints ("AND" or "OR"). Default is "AND".
        """
        valid_conjunctions = ["AND", "OR"]
        if conjunction not in valid_conjunctions:
            raise ValueError(f"Invalid conjunction '{conjunction}'. Valid conjunctions are: {', '.join(valid_conjunctions)}")
        
        self.conjunction = conjunction
        self.constraints = []
        self.repo_id = ""
        self.distinct = False
        self.exit_on_error = True
        self.returned_indexes = []
        self.repositories = [{"id": self.repo_id}]
        self.default_index_name = None  # To be set by first constraint if needed

    def add_constraint(self, index_name, operator="EQ", index_value=None):
        """
        Adds a constraint to the search.
        Args:
            index_name (str): The name of the index for the constraint.
            operator (str): The operator for the constraint. Default is "EQ".
            index_value: The value for the constraint.
        Returns:
            self: For chaining.
        """
        valid_operators = ["BT", "NB", "LK", "LT", "LE", "GT", "GE", "EQ", "NE", "NU", "NN"]
        if operator not in valid_operators:
            raise ValueError(f"Invalid operator '{operator}'. Valid operators are: {', '.join(valid_operators)}")
        if not self.default_index_name:
            self.default_index_name = index_name
            self.returned_indexes = [{"name": index_name, "sort": None}]
        constraint = {
            "name": index_name,
            "operator": operator,
            "values": [{"value": index_value}],
            "subexpression": None,
        }
        self.constraints.append(constraint)
        return self

    def set_conjunction(self, conjunction):
        """
        Sets the conjunction operator for combining constraints.
        
        :param conjunction: The conjunction to use ("AND" or "OR").
        """
        valid_conjunctions = ["AND", "OR"]
        if conjunction not in valid_conjunctions:
            raise ValueError(f"Invalid conjunction '{conjunction}'. Valid conjunctions are: {', '.join(valid_conjunctions)}")
        self.conjunction = conjunction
        return self

    def build(self):
        """
        Builds the search structure dictionary.
        """
        if not self.constraints:
            raise ValueError("At least one constraint must be added before building the search.")
        
        return {
            "indexSearch": {
                "name": f"Find {self.constraints[0]['values'][0]['value']} on Index {self.default_index_name}",
                "distinct": self.distinct,
                "conjunction": self.conjunction,
                "exitOnError": self.exit_on_error,
                "constraints": self.constraints,
                "returnedIndexes": self.returned_indexes,
                "repositories": self.repositories,
            }
        }

    def to_json(self, indent=4):
        """
        Converts the search structure to a formatted JSON string.
        """
        return json.dumps(self.build(), indent=indent)

    def to_dict(self):
        """
        Returns a dictionary representation of the search structure.
        """
        return self.build()


class ContentSearch:

    def __init__(self, content_config):

        if isinstance(content_config, ContentConfig):
            self.repo_url = content_config.repo_url
            self.repo_id = content_config.repo_id
            self.logger = content_config.logger
            self.headers = deepcopy(content_config.headers)
        else:
            raise TypeError("ContentConfig class object expected")

    # Execute a search using the SimpleSearch object
    def search_index(self, index_search: IndexSearch) -> list:
        """
        Executes a search using an IndexSearch object.
        Args:
            index_search (IndexSearch): IndexSearch object with search parameters.
        Returns:
            list: List of objectIds resulting from the search.
        """
        # Actualiza el repo_id y repositories en el objeto IndexSearch
        index_search.repo_id = self.repo_id
        index_search.repositories = [{"id": self.repo_id}]

        search_url = self.repo_url + "/searches?returnresults=true&limit=200"

        # Headers
        self.headers['Content-Type'] = 'application/vnd.asg-mobius-search.v1+json'
        self.headers['Accept'] = 'application/vnd.asg-mobius-search.v1+json'

        self.logger.info("--------------------------------")
        self.logger.info("Method : search_index")
        self.logger.debug(f"URL : {search_url}")
        self.logger.debug(f"Headers : {json.dumps(self.headers)}")
        self.logger.debug(f"Payload : {index_search.to_json()}")

        response = requests.post(search_url, json=index_search.to_dict(), headers=self.headers, verify=False)

        try:
            json_data = response.json()
        except json.JSONDecodeError:
            self.logger.error("JSON Decode Error. Returning empty list.")
            return []

        if isinstance(json_data, str):
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError:
                self.logger.error("JSON Decode Error. Returning empty list.")
                return []
        elif isinstance(json_data, dict):
            data = json_data
        else:
            self.logger.warning("Returning empty list.")
            return []

        object_ids = []
        if "results" in data and isinstance(data["results"], list):
            for result in data["results"]:
                if "objectId" in result:
                    object_ids.append(result["objectId"])

        self.logger.info(f"Search Results : {len(object_ids)}")    
        
        return object_ids



def main():

    # Validates if the SimpleSearch class is serializable.

    try:
        search = IndexSearch()
        search.add_constraint("fieldName", "fieldValue", "EQ")
        json_string = search.to_json(indent=4)
        print("IndexSearch is serializable:")
        print(json_string)

        deserialized_search = json.loads(json_string)
        print("\nDeserialized JSON:")
        print(deserialized_search)

    except TypeError as e:
        print(f"SimpleSearch is not serializable: {e}")
    except json.JSONDecodeError as e:
        print(f"Error while deserializing: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
