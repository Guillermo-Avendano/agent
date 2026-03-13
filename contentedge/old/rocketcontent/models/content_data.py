from dataclasses import dataclass
from typing import List, Optional, Any
import json
from dataclasses import asdict

@dataclass
class MetadataItem:
    dataType: str
    displayName: str
    keyName: str
    keyValue: str
    keyType: str
    keyOrdinal: int

@dataclass
class ContentClassData:
    name: str
    description: str
    objectId: str
    objectTypeId: str
    baseTypeId: str
    parentId: str
    path: str
    pageCount: Optional[int]
    parentRef: Optional[Any]
    items: Optional[Any]
    metadata: List[MetadataItem]

@dataclass
class ContentClassDataWrapper:
    data: ContentClassData

    @classmethod
    def from_json(cls, json_string: str) -> 'ContentClassDataWrapper':
        """Create instance from JSON string"""
        data_dict = json.loads(json_string)
        
        # Convert metadata list to MetadataItem objects
        if "data" in data_dict and "metadata" in data_dict["data"]:
            metadata_list = [
                MetadataItem(**item) 
                for item in data_dict["data"]["metadata"]
            ]
            data_dict["data"]["metadata"] = metadata_list

        # Create ContentData instance
        content_data = ContentClassData(**data_dict["data"])
        return cls(data=content_data)

    @classmethod
    def from_dict(cls, data_dict: dict) -> 'ContentClassDataWrapper':
        """Create instance from dictionary"""
        if "data" in data_dict and "metadata" in data_dict["data"]:
            metadata_list = [
                MetadataItem(**item) 
                for item in data_dict["data"]["metadata"]
            ]
            data_dict["data"]["metadata"] = metadata_list

        content_data = ContentClassData(**data_dict["data"])
        return cls(data=content_data)

    def to_json(self) -> str:
        """Convert instance to JSON string"""
        return json.dumps(asdict(self))

    def to_dict(self) -> dict:
        """Convert instance to dictionary"""
        return asdict(self)