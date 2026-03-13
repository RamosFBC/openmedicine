# src/open_medicine/graphrag/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class GraphRAGSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GRAPHRAG_")

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "openmedicine"

    anthropic_api_key: str = ""
    voyage_api_key: str = ""
    embedding_model: str = "voyage-3-lite"
    embedding_dimensions: int = 1024

    api_keys: str = ""  # comma-separated
    rate_limit: int = 100
    port: int = 8000

    @property
    def valid_api_keys(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


def get_settings() -> GraphRAGSettings:
    return GraphRAGSettings()
