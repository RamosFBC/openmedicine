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
            return session.execute_read(
                lambda tx: tx.run(query, parameters or {}).data()
            )

    def execute_write(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict]:
        with self._driver.session() as session:
            return session.execute_write(
                lambda tx: tx.run(query, parameters or {}).data()
            )

    def execute_write_tx(
        self, queries: list[tuple[str, dict[str, Any]]], batch_size: int = 200
    ) -> None:
        for i in range(0, len(queries), batch_size):
            batch = queries[i : i + batch_size]

            def _work(tx: Any, stmts: list = batch) -> None:
                for query, params in stmts:
                    tx.run(query, params)

            with self._driver.session() as session:
                session.execute_write(_work)
