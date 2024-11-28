import polars as pl
from typing import Dict, List, Set, Union, Any
import json
from collections import defaultdict

def infer_type(value: Any) -> str:
    """Infer the type of a value in a way that maps to Polars datatypes."""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, list):
        return "list"
    elif isinstance(value, dict):
        return "struct"
    else:
        return "unknown"

def analyze_json_array(json_array: List[Dict]) -> Dict:
    """Analyze an array of JSON objects to determine consistent types."""
    field_types: Dict[str, Set[str]] = defaultdict(set)
    nested_schemas: Dict[str, Dict] = {}
    list_element_types: Dict[str, Set[str]] = defaultdict(set)

    # Analyze each JSON object
    for item in json_array:
        analyze_object(item, field_types, nested_schemas, list_element_types)

    # Convert the analysis into a Polars-compatible schema
    schema = build_polars_schema(field_types, nested_schemas, list_element_types)
    return schema

def analyze_object(
    obj: Dict,
    field_types: Dict[str, Set[str]],
    nested_schemas: Dict[str, Dict],
    list_element_types: Dict[str, Set[str]],
    prefix: str = ""
) -> None:
    """Recursively analyze a JSON object to determine field types."""
    for key, value in obj.items():
        full_key = f"{prefix}.{key}" if prefix else key
        value_type = infer_type(value)
        field_types[full_key].add(value_type)

        if value_type == "struct":
            if full_key not in nested_schemas:
                nested_schemas[full_key] = defaultdict(set)
            analyze_object(value, field_types, nested_schemas, list_element_types, full_key)
        elif value_type == "list" and value:
            for item in value:
                item_type = infer_type(item)
                list_element_types[full_key].add(item_type)
                if item_type == "struct":
                    if f"{full_key}.[]" not in nested_schemas:
                        nested_schemas[f"{full_key}.[]"] = defaultdict(set)
                    analyze_object(item, field_types, nested_schemas, list_element_types, f"{full_key}.[]")

def build_polars_schema(
    field_types: Dict[str, Set[str]],
    nested_schemas: Dict[str, Dict],
    list_element_types: Dict[str, Set[str]]
) -> Dict:
    """Convert the analyzed types into a Polars-compatible schema structure."""
    schema = {}
    
    for field, types in field_types.items():
        if len(types) == 1:
            type_name = next(iter(types))
            if type_name == "struct":
                schema[field] = {
                    "type": "struct",
                    "fields": nested_schemas[field]
                }
            elif type_name == "list":
                element_types = list_element_types[field]
                if len(element_types) == 1:
                    element_type = next(iter(element_types))
                    if element_type == "struct":
                        schema[field] = {
                            "type": "list",
                            "elements": {
                                "type": "struct",
                                "fields": nested_schemas[f"{field}.[]"]
                            }
                        }
                    else:
                        schema[field] = {
                            "type": "list",
                            "elements": {"type": element_type}
                        }
                else:
                    schema[field] = {
                        "type": "list",
                        "elements": {"type": "mixed"}
                    }
            else:
                schema[field] = {"type": type_name}
        else:
            schema[field] = {"type": "mixed"}
            
    return schema

def generate_polars_schema(sample_data: List[str], sample_size: int = 10000) -> Dict:
    """
    Generate a Polars-compatible schema from a sample of JSON strings.
    
    Args:
        sample_data: List of JSON strings to analyze
        sample_size: Maximum number of samples to analyze
    
    Returns:
        Dict containing the inferred schema
    """
    json_objects = []
    
    # Parse JSON strings and collect objects
    for json_str in sample_data[:sample_size]:
        try:
            if isinstance(json_str, str):
                obj = json.loads(json_str)
            else:
                obj = json_str
            if isinstance(obj, list):
                json_objects.extend(obj)
            else:
                json_objects.append(obj)
        except json.JSONDecodeError:
            continue
            
    # Analyze the collected objects
    schema = analyze_json_array(json_objects)
    return schema

def convert_to_polars_type(schema_type):
    """
    Convert a schema type to a Polars type.
    """
    type_mapping = {
        "string": pl.Utf8,
        "integer": pl.Int64,
        "float": pl.Float64,
        "boolean": pl.Boolean,
        "null": pl.Null,
        "mixed": pl.Object
    }
    
    if schema_type["type"] == "list":
        element_type = convert_to_polars_type(schema_type.get("elements", {"type": "null"}))
        return pl.List(element_type)
    elif schema_type["type"] == "struct":
        return pl.Struct([
            pl.Field(k, convert_to_polars_type(v))
            for k, v in schema_type["fields"].items()
        ])
    else:
        return type_mapping.get(schema_type["type"], pl.Object)

def convert_schema_to_polars(schema: Dict) -> Dict:
    """
    Convert a json schema to a Polars schema.
    """

    polars_schema = {
        field: convert_to_polars_type(field_schema)
        for field, field_schema in schema.items()
    }
    return polars_schema

# Example usage:
def create_polars_schema_from_samples():
    # Example data
    sample_jsons = [
        '[{"name": "bor", "args": {"1": "la", "2": "grc", "3": "\u1f08\u03b2\u03b1\u03b4\u03b4\u03ce\u03bd"}, "expansion": "Ancient Greek \u1f08\u03b2\u03b1\u03b4\u03b4\u03ce\u03bd (Abadd\u1e53n)"}]'
    ]
    
    # Generate schema
    schema = generate_polars_schema(sample_jsons)
    
    # Convert schema to Polars types
    
    
    polars_schema = {
        field: convert_to_polars_type(field_schema)
        for field, field_schema in schema.items()
    }
    
    return polars_schema

if __name__ == '__main__':
    schema = create_polars_schema_from_samples()
    print(schema)