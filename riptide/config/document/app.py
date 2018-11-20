from schema import Optional, Schema
from typing import List

from configcrunch import YamlConfigDocument, DocReference
from configcrunch import load_subdocument
from riptide.config.document.command import Command
from riptide.config.document.service import Service


class App(YamlConfigDocument):

    @classmethod
    def header(cls) -> str:
        return "app"

    def schema(self) -> Schema:
        return Schema(
            {
                Optional('$ref'): str,  # reference to other App documents
                'name': str,
                Optional('installation_notice_text'): str,
                'services': {
                    str: DocReference(Service)
                },
                'commands': {
                    str: DocReference(Command)
                }
            }
        )

    def resolve_and_merge_references(self, lookup_paths: List[str]):
        super().resolve_and_merge_references(lookup_paths)
        if "services" in self:
            for key, servicedoc in self["services"].items():
                self["services"][key] = load_subdocument(servicedoc, self, Service, lookup_paths)

        if "commands" in self:
            for key, commanddoc in self["commands"].items():
                self["commands"][key] = load_subdocument(commanddoc, self, Command, lookup_paths)

        return self
