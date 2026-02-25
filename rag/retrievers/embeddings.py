"""Embedding handling for Neo4j Retriever."""
import logging

from server.core.settings import get_settings

logger = logging.getLogger(__name__)

# Optional embedding backends
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


class EmbeddingHandler:
    """Handles embedding model initialisation and generation."""

    def __init__(self):
        settings = get_settings()
        self.embedding_model = None
        self.embedding_type = None
        self.gemini_client = None

        model_name = settings.EMBEDDING_MODEL
        provider = settings.EMBEDDING_PROVIDER

        # Try Gemini
        if provider == "gemini" and HAS_GEMINI:
            self._init_gemini(model_name, settings.GOOGLE_API_KEY)

        # Try Ollama
        if self.embedding_model is None and provider == "ollama" and HAS_OLLAMA:
            self._init_ollama(model_name)

        # Fallback to sentence-transformers
        if self.embedding_model is None and HAS_SENTENCE_TRANSFORMERS:
            self._init_sentence_transformer(model_name)

        if self.embedding_model is None:
            logger.warning("No embedding model could be initialised")

    # ── Provider initialisation ──────────────────────────────────────

    def _init_gemini(self, model_name: str, api_key: str | None):
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set — skipping Gemini embeddings")
            return
        try:
            self.gemini_client = genai.Client(api_key=api_key)
            self.embedding_model = model_name
            self.embedding_type = "gemini"
            test_result = self.gemini_client.models.embed_content(
                model=self.embedding_model,
                contents=["test"],
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            dim = len(test_result.embeddings[0].values)
            logger.info("Gemini embedding ready: model=%s, dim=%d", model_name, dim)
        except Exception as exc:
            logger.warning("Could not initialise Gemini embeddings: %s", exc)
            self.embedding_model = None
            self.gemini_client = None

    def _init_ollama(self, model_name: str):
        try:
            clean_name = model_name.split("@")[0] if "@" in model_name else model_name
            self.embedding_model = clean_name
            self.embedding_type = "ollama"
            test_vec = ollama.embeddings(model=clean_name, prompt="test")["embedding"]
            logger.info("Ollama embedding ready: model=%s, dim=%d", clean_name, len(test_vec))
        except Exception as exc:
            logger.warning("Could not initialise Ollama embeddings: %s", exc)
            self.embedding_model = None

    def _init_sentence_transformer(self, model_name: str):
        try:
            logger.info("Loading sentence-transformer model: %s", model_name)
            self.embedding_model = SentenceTransformer(model_name)
            self.embedding_type = "sentence_transformer"
            test_vec = self.embedding_model.encode("test")
            logger.info("Sentence-transformer ready: dim=%d", len(test_vec))
        except Exception as exc:
            logger.warning("Could not load sentence-transformer: %s", exc)
            self.embedding_model = None

    # ── Public API ───────────────────────────────────────────────────

    def generate_embedding(self, text: str) -> list:
        """Generate embedding for text using the configured model."""
        if not self.embedding_model:
            raise ValueError("No embedding model available")

        if self.embedding_type == "gemini":
            result = self.gemini_client.models.embed_content(
                model=self.embedding_model,
                contents=[text],
                config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
            )
            return result.embeddings[0].values
        elif self.embedding_type == "ollama":
            result = ollama.embeddings(model=self.embedding_model, prompt=text)
            return result["embedding"]
        elif self.embedding_type == "sentence_transformer":
            return self.embedding_model.encode(text).tolist()
        else:
            raise ValueError(f"Unknown embedding type: {self.embedding_type}")

    def _get_or_generate_embedding(self, text: str, cache_key: str = None) -> list:
        """Generate embedding with per-instance caching."""
        if not hasattr(self, "_embedding_cache"):
            self._embedding_cache = {}

        key = cache_key or text[:100]
        if key in self._embedding_cache:
            return self._embedding_cache[key]

        embedding = self.generate_embedding(text)
        self._embedding_cache[key] = embedding
        return embedding

    def clear_embedding_cache(self):
        """Clear the embedding cache to free memory."""
        if hasattr(self, "_embedding_cache"):
            self._embedding_cache.clear()
