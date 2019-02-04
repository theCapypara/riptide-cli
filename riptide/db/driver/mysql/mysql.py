import os

from schema import Schema

from riptide.config.document.command import Command
from riptide.db.driver.abstract import AbstractDbDriver, DbValidationError, DbImportExport
from riptide.db.environments import DbEnvironments
from riptide.engine.abstract import AbstractEngine

IMAGE_NAME = 'mysql'
DATA_PATH = '/var/lib/mysql'
ENV_PW = 'MYSQL_ROOT_PASSWORD'
ENV_DB = 'MYSQL_DATABASE'
PORT = 3306


class MySQLDbDriver(AbstractDbDriver):
    """Database driver for 'mysql' Docker images."""

    def ask_for_import_file(self):
        return "Enter the path to the SQL file."

    def validate_service(self) -> bool:
        """
        A mysql database driver may only be used with 'mysql' images.
        It's config must include password and database.
        """
        if self.service["image"].split(":")[0] != IMAGE_NAME:
            raise DbValidationError("%s service: A mysql database driver may only be used with 'mysql' images." % self.service["$name"])

        # validate schema
        return Schema({
            'password': str,
            'database': str
        }).validate(self.service['driver']['config'])

    def importt(self, engine: AbstractEngine, absolute_path_to_import_object):
        command = Command({
            'image': self.service["image"],
            'command':
                'mysql -h%s -uroot -p%s %s < /db_file'
                % (self.service["$name"], self.service['driver']['config']['password'],
                   self.service['driver']['config']['database']),
            'additional_volumes': [{
                'host': absolute_path_to_import_object,
                'container': '/db_file',
                'mode': 'ro'
            }]
        })
        command.validate()
        (exit_code, log) = engine.cmd_detached(self.service.get_project(), command)
        if exit_code != 0:
            raise DbImportExport('MySQL command failed: %s' % log.decode('utf-8'))

    def export(self, engine: AbstractEngine, absolute_path_to_export_target):
        name_of_file = os.path.basename(absolute_path_to_export_target)
        file_dir = os.path.abspath(os.path.join(absolute_path_to_export_target, '..'))
        command = Command({
            'image': self.service["image"],
            'command':
                'mysqldump -h%s -uroot -p%s %s > /db_folder/%s'
                % (self.service["$name"], self.service['driver']['config']['password'],
                   self.service['driver']['config']['database'], name_of_file),
            'additional_volumes': [{
                'host': file_dir,
                'container': '/db_folder',
                'mode': 'rw'
            }]
        })
        command.validate()
        (exit_code, log) = engine.cmd_detached(self.service.get_project(), command)
        if exit_code != 0:
            raise DbImportExport('MySQL command failed: %s' % log.decode('utf-8'))

    def collect_volumes(self):
        host_path = DbEnvironments.path_for_db_data(self.service)
        return {host_path: {'bind': DATA_PATH, 'mode': 'rw'}}

    def collect_additional_ports(self):
        return [{
            'title': 'MySQL Port',
            'container': PORT,
            'host_start': PORT
        }]

    def collect_environment(self):
        return {
            ENV_PW:  self.service['driver']['config']['password'],
            ENV_DB:  self.service['driver']['config']['database']
        }
