from schema import Schema, Optional

from configcrunch import YamlConfigDocument


class Service(YamlConfigDocument):

    @classmethod
    def header(cls) -> str:
        return "service"

    def schema(self) -> Schema:
        return Schema(
            {
                Optional('$ref'): str,  # reference to other Service documents
                Optional('roles'): [str],
                'image': str,
                Optional('command'): str,
                Optional('port'): int,
                Optional('logging'): {
                    Optional('stdout'): str,
                    Optional('stderr'): str,
                    Optional('paths'): [
                        {
                            'name': str,
                            # TODO better or
                            Optional('path'): str,
                            Optional('command'): str
                        }
                    ]
                },
                Optional('start_commands'): [str],
                Optional('environment'): [
                    {
                        'name': str,
                        'value': str
                    }
                ],
                Optional('config'): [
                    {
                        'from': str,
                        'to': str
                    }
                ],
                Optional('working_directory'): str,
                Optional('wait_for_start'): bool,
                Optional('additional_ports'): [
                    {
                        'name': str,
                        'container': int,
                        'host_start': int
                    }
                ],
                # db only
                Optional('driver'): {
                    'name': str,
                    'access': any  # defined by driver
                }
            }
        )
