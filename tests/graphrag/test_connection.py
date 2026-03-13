from unittest.mock import patch, MagicMock
from open_medicine.graphrag.graph.connection import GraphConnection


class TestGraphConnection:
    def test_creates_driver(self):
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            conn = GraphConnection(uri="bolt://localhost:7687", user="neo4j", password="test")
            mock_driver.assert_called_once_with("bolt://localhost:7687", auth=("neo4j", "test"))

    def test_close(self):
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            mock_instance = MagicMock()
            mock_driver.return_value = mock_instance
            conn = GraphConnection(uri="bolt://localhost:7687", user="neo4j", password="test")
            conn.close()
            mock_instance.close.assert_called_once()

    def test_context_manager(self):
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            mock_instance = MagicMock()
            mock_driver.return_value = mock_instance
            with GraphConnection(uri="bolt://localhost:7687", user="neo4j", password="test") as conn:
                assert conn is not None
            mock_instance.close.assert_called_once()

    def test_execute_read_uses_managed_transaction(self):
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            mock_instance = MagicMock()
            mock_session = MagicMock()
            mock_tx = MagicMock()
            mock_result = MagicMock()
            mock_result.data.return_value = [{"n": 1}]
            mock_tx.run.return_value = mock_result
            mock_session.execute_read.side_effect = lambda fn: fn(mock_tx)
            mock_instance.session.return_value.__enter__ = lambda s: mock_session
            mock_instance.session.return_value.__exit__ = MagicMock(return_value=False)
            mock_driver.return_value = mock_instance

            conn = GraphConnection(uri="bolt://localhost:7687", user="neo4j", password="test")
            results = conn.execute_read("MATCH (n) RETURN n LIMIT 1")
            assert results == [{"n": 1}]
            mock_session.execute_read.assert_called_once()

    def test_execute_write_uses_managed_transaction(self):
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            mock_instance = MagicMock()
            mock_session = MagicMock()
            mock_tx = MagicMock()
            mock_result = MagicMock()
            mock_result.data.return_value = []
            mock_tx.run.return_value = mock_result
            mock_session.execute_write.side_effect = lambda fn: fn(mock_tx)
            mock_instance.session.return_value.__enter__ = lambda s: mock_session
            mock_instance.session.return_value.__exit__ = MagicMock(return_value=False)
            mock_driver.return_value = mock_instance

            conn = GraphConnection(uri="bolt://localhost:7687", user="neo4j", password="test")
            conn.execute_write("CREATE (n:Test {id: 1})")
            mock_session.execute_write.assert_called_once()

    def test_execute_write_tx_runs_all_queries(self):
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            mock_instance = MagicMock()
            mock_session = MagicMock()
            mock_tx = MagicMock()
            mock_session.execute_write.side_effect = lambda fn: fn(mock_tx)
            mock_instance.session.return_value.__enter__ = lambda s: mock_session
            mock_instance.session.return_value.__exit__ = MagicMock(return_value=False)
            mock_driver.return_value = mock_instance

            conn = GraphConnection(uri="bolt://localhost:7687", user="neo4j", password="test")
            conn.execute_write_tx([
                ("CREATE (a:A {id: 1})", {}),
                ("CREATE (b:B {id: 2})", {}),
            ])
            assert mock_tx.run.call_count == 2
