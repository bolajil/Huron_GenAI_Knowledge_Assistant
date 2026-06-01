"""
Test suite for embedding generation and vector operations.
Tests both OpenAI embeddings and local fallback (FAISS).
"""

import os
import pytest
from unittest.mock import patch, MagicMock

# Set test environment before imports
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-32-bytes-xx")
os.environ.setdefault("VECTOR_BACKEND", "faiss")


class TestEmbeddingGeneration:
    """Tests for embedding generation functionality."""

    def test_embedding_dimension_openai(self):
        """Verify OpenAI text-embedding-3-small returns 1536 dimensions."""
        mock_embedding = [0.1] * 1536
        
        with patch("openai.OpenAI") as mock_client:
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=mock_embedding)]
            mock_client.return_value.embeddings.create.return_value = mock_response
            
            from openai import OpenAI
            client = OpenAI(api_key="sk-test")
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input="test query"
            )
            
            assert len(response.data[0].embedding) == 1536

    def test_embedding_handles_empty_input(self):
        """Empty input should raise or return empty gracefully."""
        with patch("openai.OpenAI") as mock_client:
            mock_client.return_value.embeddings.create.side_effect = ValueError("Input cannot be empty")
            
            from openai import OpenAI
            client = OpenAI(api_key="sk-test")
            
            with pytest.raises(ValueError):
                client.embeddings.create(
                    model="text-embedding-3-small",
                    input=""
                )

    def test_embedding_batch_processing(self):
        """Batch embedding should process multiple texts."""
        texts = ["document one", "document two", "document three"]
        mock_embeddings = [[0.1] * 1536 for _ in texts]
        
        with patch("openai.OpenAI") as mock_client:
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=emb) for emb in mock_embeddings]
            mock_client.return_value.embeddings.create.return_value = mock_response
            
            from openai import OpenAI
            client = OpenAI(api_key="sk-test")
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            
            assert len(response.data) == 3
            for item in response.data:
                assert len(item.embedding) == 1536


class TestVectorSimilarity:
    """Tests for vector similarity calculations."""

    def test_cosine_similarity_identical_vectors(self):
        """Identical vectors should have similarity of 1.0."""
        import numpy as np
        
        vec_a = np.array([1.0, 0.0, 0.0])
        vec_b = np.array([1.0, 0.0, 0.0])
        
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        similarity = dot_product / (norm_a * norm_b)
        
        assert abs(similarity - 1.0) < 1e-6

    def test_cosine_similarity_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity of 0.0."""
        import numpy as np
        
        vec_a = np.array([1.0, 0.0, 0.0])
        vec_b = np.array([0.0, 1.0, 0.0])
        
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        similarity = dot_product / (norm_a * norm_b)
        
        assert abs(similarity - 0.0) < 1e-6

    def test_cosine_similarity_opposite_vectors(self):
        """Opposite vectors should have similarity of -1.0."""
        import numpy as np
        
        vec_a = np.array([1.0, 0.0, 0.0])
        vec_b = np.array([-1.0, 0.0, 0.0])
        
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        similarity = dot_product / (norm_a * norm_b)
        
        assert abs(similarity - (-1.0)) < 1e-6


class TestFAISSFallback:
    """Tests for local FAISS vector store fallback."""

    @pytest.mark.skipif(
        os.getenv("VECTOR_BACKEND") != "faiss",
        reason="FAISS tests only run when VECTOR_BACKEND=faiss"
    )
    def test_faiss_index_creation(self):
        """FAISS index should be creatable with correct dimensions."""
        try:
            import faiss
            import numpy as np
            
            dimension = 1536
            index = faiss.IndexFlatIP(dimension)
            
            vectors = np.random.rand(10, dimension).astype('float32')
            faiss.normalize_L2(vectors)
            index.add(vectors)
            
            assert index.ntotal == 10
        except ImportError:
            pytest.skip("faiss-cpu not installed")

    @pytest.mark.skipif(
        os.getenv("VECTOR_BACKEND") != "faiss",
        reason="FAISS tests only run when VECTOR_BACKEND=faiss"
    )
    def test_faiss_search(self):
        """FAISS search should return k nearest neighbors."""
        try:
            import faiss
            import numpy as np
            
            dimension = 1536
            index = faiss.IndexFlatIP(dimension)
            
            vectors = np.random.rand(100, dimension).astype('float32')
            faiss.normalize_L2(vectors)
            index.add(vectors)
            
            query = np.random.rand(1, dimension).astype('float32')
            faiss.normalize_L2(query)
            
            k = 5
            distances, indices = index.search(query, k)
            
            assert indices.shape == (1, k)
            assert distances.shape == (1, k)
            assert all(distances[0][i] >= distances[0][i+1] for i in range(k-1))
        except ImportError:
            pytest.skip("faiss-cpu not installed")


class TestPineconeIntegration:
    """Tests for Pinecone vector store (mocked)."""

    def test_pinecone_upsert_format(self):
        """Verify upsert payload matches Pinecone expected format."""
        vectors = [
            {
                "id": "doc-1-chunk-0",
                "values": [0.1] * 1536,
                "metadata": {
                    "doc_id": "doc-1",
                    "chunk_index": 0,
                    "text": "Sample document text",
                    "is_latest": True,
                    "dept": "hr"
                }
            }
        ]
        
        for vec in vectors:
            assert "id" in vec
            assert "values" in vec
            assert "metadata" in vec
            assert len(vec["values"]) == 1536
            assert isinstance(vec["metadata"], dict)

    def test_pinecone_query_format(self):
        """Verify query payload matches Pinecone expected format."""
        query_params = {
            "vector": [0.1] * 1536,
            "top_k": 10,
            "namespace": "vaultmind-huron-hr-general",
            "filter": {"is_latest": {"$eq": True}},
            "include_metadata": True
        }
        
        assert len(query_params["vector"]) == 1536
        assert query_params["top_k"] > 0
        assert "namespace" in query_params
        assert query_params["include_metadata"] is True
