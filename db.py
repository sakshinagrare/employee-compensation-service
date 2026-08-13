import os
import pyodbc

class ConfigError(Exception):
    pass

def get_connection():
    conn_str = os.environ.get("SQL_CONNECTION_STRING")
    if not conn_str:
        raise ConfigError(
            "SQL_CONNECTION_STRING is not set."
        )
    return pyodbc.connect(conn_str)