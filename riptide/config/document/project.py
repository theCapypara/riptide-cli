from typing import List

from schema import Schema, Optional

from configcrunch import YamlConfigDocument, DocReference
from configcrunch import load_subdocument
from riptide.config.document.app import App


class Project(YamlConfigDocument):

    @classmethod
    def header(cls) -> str:
        return "project"

    def schema(self) -> Schema:
        return Schema(
            {
                Optional('$ref'): str,  # reference to other Project documents
                'name': str,
                'src': str,
                Optional('import'): {
                    Optional('db'): {
                        'source': str
                    },
                    Optional('folders'): {
                        str: {
                            'target': str,
                            'source': str
                        }
                    }
                },
                'app': DocReference(App)
            }
        )

    def resolve_and_merge_references(self, lookup_paths: List[str]):
        super().resolve_and_merge_references(lookup_paths)
        if "app" in self:
            self["app"] = load_subdocument(self["app"], self, App, lookup_paths)
        return self
