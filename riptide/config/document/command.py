from schema import Schema, Optional

from configcrunch import YamlConfigDocument


class Command(YamlConfigDocument):

    @classmethod
    def header(cls) -> str:
        return "command"

    def schema(self) -> Schema:
        return Schema(
            {
                Optional('$ref'): str,  # reference to other Service documents
                # TODO better OR
                Optional('image'): str,
                Optional('command'): str,

                Optional('aliases'): str
            }
        )
