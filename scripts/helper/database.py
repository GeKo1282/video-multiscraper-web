import sqlite3, os
from typing import List, Dict

class Database:
    def __init__(self, path: str) -> None:
        self.path: str = path

        self.tables: List[str] = self.get_tables()
        self.columns: Dict[str, List[str]] = {table: self.get_columns(table) for table in self.tables}

    def connect(self, makedirs: bool = True) -> sqlite3.Connection:
        if makedirs:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        
        return sqlite3.connect(self.path)
    
    def create_table(self, table_name: str, columns: list, if_not_exists: bool = True) -> None:
        with self.connect() as connection:
            connection.execute(f"CREATE TABLE {'IF NOT EXISTS' if if_not_exists else ''} {table_name} ({', '.join(columns)})")

        self.tables = self.get_tables()

    def get_tables(self) -> list:
        with self.connect() as connection:
            return [table[0] for table in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    
    def get_columns(self, table_name: str) -> list:
        with self.connect() as connection:
            return [column[1] for column in connection.execute(f"PRAGMA table_info({table_name})").fetchall()]
    
    def insert(self, table_name: str, columns: list, values: list) -> None:
        with self.connect() as connection:
            connection.execute(f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['?' for _ in range(len(values))])})", values)

    def select(self, table_name: str, columns: list, where: str = None, where_values: list = None) -> list:
        with self.connect() as connection:
            if where:
                return connection.execute(f"SELECT {', '.join(columns)} FROM {table_name} WHERE {where}", where_values).fetchall()
            
            return connection.execute(f"SELECT {', '.join(columns)} FROM {table_name}").fetchall()
    
    def update(self, table_name: str, columns: list, values: list, where: str = None, where_values: list = None) -> None:
        with self.connect() as connection:
            if where:
                connection.execute(f"UPDATE {table_name} SET {', '.join([f'{column} = ?' for column in columns])} WHERE {where}", values + where_values)
                return

            connection.execute(f"UPDATE {table_name} SET {', '.join([f'{column} = ?' for column in columns])}", values)
    
    def delete(self, table_name: str, where: str = None, where_values: list = None) -> None:
        with self.connect() as connection:
            if where:
                connection.execute(f"DELETE FROM {table_name} WHERE {where}", where_values)
                return

            connection.execute(f"DELETE FROM {table_name}")