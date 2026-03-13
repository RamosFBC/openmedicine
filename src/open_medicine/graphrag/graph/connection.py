from __future__ import annotations
from typing import Any
import neo4j


class GraphConnection:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver = neo4j.GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> GraphConnection:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def execute_read(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict]:
        with self._driver.session() as session:
            result = session.run(query, parameters or {})
            return result.data()

    def execute_write(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict]:
        with self._driver.session() as session:
            result = session.run(query, parameters or {})
            return result.data()

    def execute_write_tx(self, queries: list[tuple[str, dict[str, Any]]]) -> None:
        with self._driver.session() as session:
            with session.begin_transaction() as tx:
                for query, params in queries:
                    tx.run(query, params)
                tx.commit()
