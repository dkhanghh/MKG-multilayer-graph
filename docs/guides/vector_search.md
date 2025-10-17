# Vector-Based Entity Search Implementation

## Summary of Changes

I've updated the RAG chatbot to use **vector similarity search** for entity matching using the `_name_vector` and `_desc_vector` properties in your Neo4j database.

## Key Improvements

### 1. **Vector Similarity for Entity Search**
Instead of text matching (e.g., `WHERE toLower(e.name) CONTAINS...`), the chatbot now:
- Generates embeddings for entity names using the same model as your Neo4j vectors
- Uses **cosine similarity** on `_name_vector` and `_desc_vector` fields
- Finds the best matching entity (similarity ≥ 0.5)
- Returns entity with **similarity score** to show match quality

### 2. **Ollama Embedding Support**
The code now supports **both** embedding approaches:
- **Ollama models** (like `nomic-embed-text`) - **YOUR SETUP**
- **sentence-transformers** models (fallback)

### 3. **Automatic Model Detection**
The system automatically detects which embedding library to use based on:
- Model name (if contains "nomic" or "ollama", uses Ollama)
- Availability (tries Ollama first if available)

## Configuration

### Update your `.env` file:

```bash
# Use the SAME embedding model that generated your Neo4j vectors
EMBEDDING_MODEL=nomic-embed-text

# Make sure Ollama is configured
OLLAMA_BASE_URL=http://localhost:11434
```

### **IMPORTANT**: Start Ollama

Before running the chatbot, ensure Ollama is running:

```bash
ollama serve
```

Or check if it's running:

```bash
curl http://localhost:11434/api/tags
```

## How It Works

### Entity Search Flow:

1. **User query** → Preprocessing extracts entities (e.g., "temperature cycling", "thermal shock")
2. **For each entity**:
   - Generate embedding using `nomic-embed-text` via Ollama
   - Search Neo4j using vector similarity on `_name_vector` and `_desc_vector`
   - Find best match with similarity ≥ 0.5
   - Traverse 1-2 levels of relationships
3. **Return** entity + relationships + similarity score

### Example Output:

```
## Entity: temperature cycling [similarity: 0.892]
- Note: Found via semantic similarity (query: 'temperature testing')

### Direct Connections (Level 1):
  - ← dualChamber: smi 202b
  - → source: SMI 202b Temperature Cycling Dual Chamber
```

## Benefits

✅ **Robust Matching**: Finds entities even with different wording
- Query: "thermal testing" → Finds: "temperature cycling" (if semantically similar)
- Query: "JEDEC" → Finds: "JEDEC standards" or related standard docs

✅ **No Exact Name Required**: Uses semantic similarity instead of exact text match

✅ **Similarity Scores**: Shows how confident the match is (0.5-1.0)

✅ **Model Consistency**: Uses the SAME model that generated Neo4j vectors

## Testing

Run the test to verify it works:

```bash
# Make sure Ollama is running first!
ollama serve  # In separate terminal

# Then test:
uv run python test_ollama_entity.py
```

Expected output:
- Should find entities with similarity scores > 0.5
- Should show graph relationships
- Should complete in ~1-2 seconds per entity

## Troubleshooting

### "Failed to connect to Ollama"
**Solution**: Start Ollama server
```bash
ollama serve
```

### "No embedding model available"
**Solution**: Check your `.env` has `EMBEDDING_MODEL=nomic-embed-text`

### "Entity not found" (but you know it exists)
**Possible causes**:
1. **Dimension mismatch**: Your Neo4j vectors might be from a different model
   - Check: What model did you use in the KAG pipeline?
   - Solution: Set `EMBEDDING_MODEL` to match

2. **Low similarity**: Try lowering the threshold
   - Edit line 365 in `rag_graph.py`: `WHERE max_similarity >= 0.3` (instead of 0.5)

3. **Vector field missing**: Entity doesn't have `_name_vector`
   - Check in Neo4j: `MATCH (n {name: "entity_name"}) RETURN n._name_vector IS NOT NULL`

## Files Modified

1. **`chatbot_graphs/rag_graph.py`**:
   - Added Ollama embedding support
   - Updated `entity_graph_search()` to use vector similarity
   - Added `generate_embedding()` method for both model types
   - Updated `vector_similarity_search()` to use new method

2. **`chatbot_graphs/README.md`**:
   - Added embedding model configuration instructions
   - Added Ollama setup notes
   - Updated vector dimension notes

## Next Steps

1. **Start Ollama**: `ollama serve`
2. **Update `.env`**: Set `EMBEDDING_MODEL=nomic-embed-text`
3. **Test**: `uv run python test_ollama_entity.py`
4. **Run chatbot**: `uv run chatbot_graphs/rag_graph.py`

The chatbot will now use vector similarity to find entities, making it much more robust and flexible! 🚀
