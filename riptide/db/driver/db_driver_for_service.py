"""Module to resolve database drivers for services"""
from typing import Union

from riptide.db.driver.abstract import AbstractDbDriver
from riptide.db.driver.mysql.mysql import MySQLDbDriver


def get(service: 'Service') -> Union[AbstractDbDriver, None]:
    """Returns the db driver instance for this service, if a driver is defined."""
    # todo currently hardcoded
    if service["driver"]["name"] == "mysql":
        return MySQLDbDriver(service)
    return None
