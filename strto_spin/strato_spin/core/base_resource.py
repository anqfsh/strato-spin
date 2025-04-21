from abc import ABC, abstractmethod

class BaseResource(ABC):
    resource_type = None
    platform = None
    required_tags = ["Environment", "Owner"]

    def __init__(self, name, properties, tags, schema, client):
        self.name = name
        self.properties = properties
        self.tags = tags
        self.schema = schema
        self.client = client
        self.outputs = {}
        self.self_outputs = {}
        self.validate()

    def validate(self):
        required_fields = self.schema.get("required", [])
        for field in required_fields:
            if field not in self.properties:
                raise ValueError(f"Missing required field {field} for {self.name}")
        schema_tags = self.schema.get("tags", {}).get("required", [])
        required_tags = schema_tags or self.required_tags
        for tag in required_tags:
            if tag not in self.tags:
                raise ValueError(f"Missing required tag {tag} for {self.name}")

    @classmethod
    def get_schema(cls):
        raise NotImplementedError("Subclasses must implement get_schema")

    @abstractmethod
    def exists(self):
        pass

    @abstractmethod
    def create(self):
        pass

    @abstractmethod
    def update(self, existing_properties):
        pass

    @abstractmethod
    def get_outputs(self):
        pass

    def get_existing_properties(self):
        return {}
