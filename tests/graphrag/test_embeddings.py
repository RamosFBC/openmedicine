import pytest
from unittest.mock import patch, MagicMock
from open_medicine.graphrag.ingestion.embeddings import embed_texts, embed_query


class TestEmbedTexts:
    @patch("open_medicine.graphrag.ingestion.embeddings.httpx.post")
    def test_returns_list_of_vectors(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]},
            ]
        }
        mock_post.return_value = mock_response

        result = embed_texts(["text one", "text two"], api_key="test-key")
        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]

    @patch("open_medicine.graphrag.ingestion.embeddings.httpx.post")
    def test_calls_voyage_api(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": [{"embedding": [0.1]}]}
        mock_post.return_value = mock_response

        embed_texts(["text"], api_key="my-key", model="voyage-3-lite")
        call_kwargs = mock_post.call_args
        assert "api.voyageai.com" in call_kwargs[0][0]
        assert call_kwargs[1]["headers"]["Authorization"] == "Bearer my-key"
        assert call_kwargs[1]["json"]["model"] == "voyage-3-lite"

    @patch("open_medicine.graphrag.ingestion.embeddings.httpx.post")
    def test_batches_large_inputs(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": [{"embedding": [0.1]}] * 50}
        mock_post.return_value = mock_response

        texts = [f"text {i}" for i in range(150)]
        result = embed_texts(texts, api_key="key", batch_size=50)
        assert mock_post.call_count == 3
        assert len(result) == 150


class TestEmbedQuery:
    @patch("open_medicine.graphrag.ingestion.embeddings.embed_texts")
    def test_returns_single_vector(self, mock_embed):
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        result = embed_query("dosing apixaban", api_key="key")
        assert result == [0.1, 0.2, 0.3]
        mock_embed.assert_called_once_with(
            ["dosing apixaban"], api_key="key",
            model="voyage-3", input_type="query",
            max_retries=1, timeout=10.0,
        )
