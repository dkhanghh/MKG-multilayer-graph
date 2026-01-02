"""
Embedding handling for Neo4j Retriever.
"""
import os

# Optional embedding support
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

# Optional Ollama for embeddings
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

# Optional Gemini for embeddings
try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


class EmbeddingHandler:
    """Handles embedding model initialization and generation."""
    
    def __init__(self):
        self.embedding_model = None
        self.embedding_type = None
        self.gemini_client = None
        
        # Check for embedding model configuration
        model_name = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
        embedding_provider = os.getenv("EMBEDDING_PROVIDER", "gemini")  # gemini, ollama, sentence-transformers

        # Try Gemini first (for embedding-001 and other Gemini models)
        if embedding_provider == "gemini" and HAS_GEMINI:
            try:
                # Configure Gemini API
                api_key = os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    raise ValueError("GOOGLE_API_KEY environment variable is required for Gemini embeddings")

                # Initialize Gemini client (using google-genai package)
                self.gemini_client = genai.Client(api_key=api_key)
                self.embedding_model = model_name
                self.embedding_type = "gemini"

                # Test embedding
                test_result = self.gemini_client.models.embed_content(
                    model=self.embedding_model,
                    contents=["test"],
                    config=types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT"
                    )
                )
                test_vec = test_result.embeddings[0].values
                print(f"[Neo4j Retriever] Using Gemini embedding model: {self.embedding_model}")
                print(f"[Neo4j Retriever] Embedding dimension: {len(test_vec)}")
            except Exception as e:
                print(f"Warning: Could not use Gemini embedding model: {e}")
                self.embedding_model = None
                self.gemini_client = None

        # Try Ollama (for nomic-embed-text and other Ollama models)
        if self.embedding_model is None and embedding_provider == "ollama" and HAS_OLLAMA:
            try:
                # For Ollama models, just store the model name
                # The actual model name without @quantization suffix
                self.embedding_model = model_name.split('@')[0] if '@' in model_name else model_name
                self.embedding_type = "ollama"

                # Test embedding
                test_vec = ollama.embeddings(model=self.embedding_model, prompt="test")['embedding']
                print(f"[Neo4j Retriever] Using Ollama embedding model: {self.embedding_model}")
                print(f"[Neo4j Retriever] Embedding dimension: {len(test_vec)}")
            except Exception as e:
                print(f"Warning: Could not use Ollama embedding model: {e}")
                self.embedding_model = None

        # Fall back to sentence-transformers
        if self.embedding_model is None and HAS_SENTENCE_TRANSFORMERS:
            try:
                model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
                print(f"[Neo4j Retriever] Loading sentence-transformer model: {model_name}")
                self.embedding_model = SentenceTransformer(model_name)
                self.embedding_type = "sentence_transformer"
                test_vec = self.embedding_model.encode("test")
                print(f"[Neo4j Retriever] Embedding dimension: {len(test_vec)}")
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}")
                self.embedding_model = None

    def generate_embedding(self, text: str) -> list:
        """Generate embedding for text using the configured model."""
        if not self.embedding_model:
            raise ValueError("No embedding model available")

        if self.embedding_type == "gemini":
            # Use google-genai package API
            result = self.gemini_client.models.embed_content(
                model=self.embedding_model,
                contents=[text],
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY",  # Use RETRIEVAL_QUERY for query embeddings
                )
            )
            return result.embeddings[0].values
        elif self.embedding_type == "ollama":
            result = ollama.embeddings(model=self.embedding_model, prompt=text)
            return result['embedding']
        elif self.embedding_type == "sentence_transformer":
            return self.embedding_model.encode(text).tolist()
        else:
            raise ValueError(f"Unknown embedding type: {self.embedding_type}")

    def _get_or_generate_embedding(self, text: str, cache_key: str = None) -> list:
        """
        Generate embedding with caching to avoid duplicate generation.

        This significantly improves performance in hybrid search where the same
        query embedding is needed by multiple strategies.

        Args:
            text: Text to generate embedding for
            cache_key: Optional cache key (defaults to first 100 chars of text)

        Returns:
            Embedding vector as list of floats
        """
        # Initialize cache if not present
        if not hasattr(self, '_embedding_cache'):
            self._embedding_cache = {}

        # Use first 100 chars as cache key if not provided
        key = cache_key or text[:100]

        # Return cached embedding if available
        if key in self._embedding_cache:
            return self._embedding_cache[key]

        # Generate and cache new embedding
        embedding = self.generate_embedding(text)
        self._embedding_cache[key] = embedding

        return embedding

    def clear_embedding_cache(self):
        """Clear the embedding cache to free memory."""
        if hasattr(self, '_embedding_cache'):
            self._embedding_cache.clear()
