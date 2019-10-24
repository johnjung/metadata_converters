import json, sys
from jsonschema import validate

if __name__=="__main__":
    property_dict = {
        "tag_re": {
            "type": "string"
        },
        "subfield_re": {
            "type": "string"
        },
        "indicator1_re": {
            "type": "string"
        },
        "indicator2_re": {
            "type": "string"
        },
        "join_subfields": {
            "type": "boolean"
        },
        "join_tags": {
            "type": "boolean"
        },
        "return_first_result_only": {
            "type": "boolean"
        }
    }

    property_dict_extras = {
        "exclude": {
            "items": {
                "subfield_re": {
                    "type": "string"
                },
                "value_re": {
                    "type": "string"
                }
            },
            "type": "array"
        },
        "filter": {
            "items": {
                "subfield_re": {
                    "type": "string"
                },
                "value_re": {
                    "type": "string"
                }
            },
            "type": "array"
        }
    }

    validate(
        instance = json.loads(sys.stdin.read()),
        schema = {
            "type": "object",
            "properties": {
                "template": {
                    "additionalProperties": False,
                    "properties": property_dict,
                    "required": list(property_dict.keys()),
                    "type": "object",
                },
                "crosswalk": {
                    "patternProperties": {
                        "^.*$": {
                            "items": {
                                "additionalProperties": False,
                                "properties": { **property_dict, **property_dict_extras },
                                "type": "object"
                            },
                            "type": "array"
                        }
                    },
                    "type": "object"
                }
            }
        }
    )
