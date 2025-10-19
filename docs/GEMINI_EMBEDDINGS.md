# Using Gemini Embeddings in RAG Chatbot

The RAG chatbot now supports **Google Gemini embeddings** for semantic similarity search in Neo4j.

## Setup

### 1. Install Dependencies

```bash
pip install google-generativeai
```

### 2. Configure Environment Variables

Create a `.env` file in the `chatbot_graphs/` directory:

```bash
# Embedding Configuration
EMBEDDING_PROVIDER=gemini
GOOGLE_API_KEY=your_google_api_key_here
EMBEDDING_MODEL=embedding-001

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

# OpenAI (for chat)
OPENAI_API_KEY=your_openai_key
```

### 3. Model Information

**Model**: `models/embedding-001` (Gemini embedding model)
- **Dimension**: 768
- **Task types**:
  - `retrieval_document` - For embedding documents/entities in Neo4j
  - `retrieval_query` - For embedding user queries

## How It Works

### Document Embeddings (Pipeline)

When building your knowledge graph:

```python
# In vectorizer config
{
    "vectorizer_type": "gemini",
    "model_name": "models/embedding-001",
    "api_key": os.getenv("GOOGLE_API_KEY"),
    "task_type": "retrieval_document"  # For embedding entities
}
```

### Query Embeddings (Chatbot)

When searching Neo4j:

```python
# Automatically uses retrieval_query task type
query_embedding = retriever.generate_embedding("find test instructions")

# Searches Neo4j using cosine similarity
cypher = """
MATCH (n)
WHERE n.embeddings IS NOT NULL
WITH n,
     reduce(dot = 0.0, i IN range(0, size(n.embeddings)-1) |
          dot + n.embeddings[i] * $query_vector[i]) /
          (sqrt(reduce(sum = 0.0, x IN n.embeddings | sum + x * x)) *
           sqrt(reduce(sum = 0.0, x IN $query_vector | sum + x * x))) AS similarity
WHERE similarity >= 0.7
RETURN n, similarity
ORDER BY similarity DESC
"""
```

## Supported Embedding Providers

| Provider | Model | Dimension | Notes |
|----------|-------|-----------|-------|
| **Gemini** (default) | `embedding-001` | 768 | Google's embedding model, requires API key |
| Ollama | `nomic-embed-text` | 768 | Local model, requires Ollama server |
| Sentence Transformers | `all-mpnet-base-v2` | 768 | Local model, no API key needed |

## Usage Example

```python
from chatbot_graphs.rag_graph import create_rag_chat_graph

# Create graph (automatically uses Gemini if configured)
graph = create_rag_chat_graph()

# Ask questions
result = graph.invoke({
    "messages": [("user", "What is SMI 203a?")]
})

print(result["messages"][-1].content)
```

## Vector Similarity Search

The chatbot uses **cosine similarity** to find relevant entities:

1. **Generate query embedding** using Gemini
2. **Search Neo4j** for entities with high similarity scores
3. **Retrieve context** including relationships
4. **Answer question** using ChatOpenAI with retrieved context

## Benefits of Gemini Embeddings

✅ **High quality** - State-of-the-art embedding model from Google
✅ **Task-specific** - Different embeddings for documents vs queries
✅ **768 dimensions** - Good balance between quality and storage
✅ **API-based** - No local model loading required
✅ **Semantic search** - Finds entities even with different wording

## Troubleshooting

### Error: "GOOGLE_API_KEY environment variable is required"
- Set your Google API key in `.env` file
- Get API key from: https://makersuite.google.com/app/apikey

### Error: "Could not use Gemini embedding model"
- Check your API key is valid
- Verify `google-generativeai` package is installed
- Check internet connection

### Low similarity scores
- Ensure your Neo4j entities were embedded with the same model (768-dim)
- Try lowering the similarity threshold (default is 0.7)
- Check if embeddings exist: `MATCH (n) WHERE n.embeddings IS NOT NULL RETURN count(n)`

## Switching Embedding Providers

To switch from Gemini to another provider, update `.env`:

```bash
# Switch to Ollama
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text

# Or switch to Sentence Transformers
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
```

The chatbot will automatically detect and use the configured provider.
