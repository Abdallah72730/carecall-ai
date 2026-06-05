"""Unit tests for services/embedding.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np


def _make_model(dim: int = 384):
    model = MagicMock()
    model.encode.side_effect = lambda texts, **kw: (
        np.random.rand(dim).astype("float32")
        if isinstance(texts, str)
        else np.random.rand(len(texts), dim).astype("float32")
    )
    return model


class TestGetEmbedding:
    def test_returns_list_of_floats(self, monkeypatch):
        from services import embedding as emb

        monkeypatch.setattr(emb, "get_model", lambda: _make_model())
        result = emb.get_embedding("what are your hours?")
        assert isinstance(result, list)
        assert len(result) == 384
        assert all(isinstance(x, float) for x in result)

    def test_empty_string_still_returns_vector(self, monkeypatch):
        from services import embedding as emb

        monkeypatch.setattr(emb, "get_model", lambda: _make_model())
        result = emb.get_embedding("")
        assert len(result) == 384


class TestBatchEncode:
    def test_empty_list_returns_empty(self, monkeypatch):
        from services import embedding as emb

        monkeypatch.setattr(emb, "get_model", lambda: _make_model())
        assert emb.batch_encode([]) == []

    def test_returns_one_vector_per_text(self, monkeypatch):
        from services import embedding as emb

        monkeypatch.setattr(emb, "get_model", lambda: _make_model())
        texts = ["hello", "world", "foo"]
        result = emb.batch_encode(texts)
        assert len(result) == 3
        for vec in result:
            assert isinstance(vec, list)
            assert len(vec) == 384

    def test_all_elements_are_floats(self, monkeypatch):
        from services import embedding as emb

        monkeypatch.setattr(emb, "get_model", lambda: _make_model())
        result = emb.batch_encode(["dental appointment", "office hours"])
        for vec in result:
            assert all(isinstance(x, float) for x in vec)


class TestGetModel:
    def test_loads_sentence_transformer(self):
        mock_model = MagicMock()
        with patch("services.embedding.SentenceTransformer", return_value=mock_model):
            from services.embedding import get_model

            get_model.cache_clear()
            model = get_model()
            assert model is mock_model
            get_model.cache_clear()
