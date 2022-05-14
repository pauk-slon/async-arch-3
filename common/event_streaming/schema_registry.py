import json
from pathlib import Path
from typing import Dict, Tuple, Type

import jsonschema


class SchemaRegistry:
    def __init__(self):
        self._validators: Dict[Tuple[str, int], jsonschema.Validator] = dict()

    def load_schemas(self, directory: str):
        directory_path = Path(directory)
        for json_file in directory_path.glob('**/*.json'):
            if json_file.is_file():
                with json_file.open() as json_stream:
                    schema = json.load(json_stream)
                validator_class: Type[jsonschema.Validator] = jsonschema.validators.validator_for(schema)
                validator_class.check_schema(schema)
                event_name = json_file.parent.name
                event_version = int(json_file.name.split('.json')[0])
                self._validators[event_name, event_version] = validator_class(schema)

    def validate_event(self, name, version, data):
        self._validators[name, version].validate(data)
