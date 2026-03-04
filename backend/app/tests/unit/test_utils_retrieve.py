import numpy as np
from unittest.mock import MagicMock
from app.services.utils.retrieve import hierarchical_retriever


def test_hierarchical_retriever():

    # Mock embedding model
    mock_embedder = MagicMock()
    mock_embedder.encode.return_value = np.array([0.1, 0.2, 0.3])

    # Mock Qdrant client
    mock_client = MagicMock()

    hit1 = MagicMock()
    hit1.payload = {"parent_id": 1}
    hit1.score = 0.9

    hit2 = MagicMock()
    hit2.payload = {"parent_id": 2}
    hit2.score = 0.8

    # Duplicate parent to test deduplication
    hit3 = MagicMock()
    hit3.payload = {"parent_id": 1}
    hit3.score = 0.7

    mock_client.search.return_value = [hit1, hit2, hit3]

    # Mock SQLite cursor
    mock_cursor = MagicMock()

    mock_cursor.fetchone.side_effect = [
        ("Parent text 1", "Chap1", "Sec1", "Cat1", 5),
        ("Parent text 2", "Chap2", "Sec2", "Cat2", 8),
    ]

    result = hierarchical_retriever(
        client=mock_client,
        cursor=mock_cursor,
        query="AI definition",
        embedder=mock_embedder,
        retrieval_top_k=3,
    )

    assert result == [
        {
            "text": "Parent text 1",
            "categorie": "Cat1",
            "chapter": "Chap1",
            "section": "Sec1",
            "page": 5,
            "score": 0.9,
        },
        {
            "text": "Parent text 2",
            "categorie": "Cat2",
            "chapter": "Chap2",
            "section": "Sec2",
            "page": 8,
            "score": 0.8,
        },
    ]
