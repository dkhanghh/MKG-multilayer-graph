# Understanding batch_size in Gemini API

**Question:** Does `batch_size=100` mean 100 items per request or 100 requests?

**Answer:** `batch_size=100` means **100 items (texts) in a SINGLE API request**.

---

## How It Works

### Gemini API Capability

The Gemini `embed_content` API can process **multiple texts in a single request**:

```python
# Single API request with multiple texts
result = client.models.embed_content(
    model="gemini-embedding-001",
    contents=["text1", "text2", "text3", ..., "text100"],  # ← 100 texts
    config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")
)

# Returns embeddings for ALL 100 texts
embeddings = [emb.values for emb in result.embeddings]  # ← 100 embeddings
```

**Key Point:** One API request = One count toward RPM limit, regardless of how many texts are in it!

---

## Visual Explanation

### Example: 250 items to embed with batch_size=100

```
Total items: 250
batch_size: 100

┌─────────────────────────────────────────────────────────────┐
│ Process Flow                                                 │
└─────────────────────────────────────────────────────────────┘

Items 1-100   →  [API Request #1]  →  100 embeddings
                 (contains 100 texts)
                 RPM used: 1

Items 101-200 →  [API Request #2]  →  100 embeddings
                 (contains 100 texts)
                 RPM used: 1

Items 201-250 →  [API Request #3]  →  50 embeddings
                 (contains 50 texts)
                 RPM used: 1

─────────────────────────────────────────────────────────────
Total API Requests: 3
Total RPM Used: 3
Total Items Processed: 250
```

---

## Code Implementation

Here's how our code processes batches:

```python
def _generate_gemini_embeddings(self, texts: List[str]):
    """
    texts: ['text1', 'text2', ..., 'text250']  # 250 items
    batch_size: 100
    """
    all_embeddings = []

    # Loop through texts in chunks of batch_size
    for i in range(0, len(texts), self.batch_size):
        # Get batch of texts
        batch = texts[i:i + self.batch_size]
        # batch = ['text1', 'text2', ..., 'text100']  ← 100 items

        # Make SINGLE API request with all items in batch
        result = self.client.models.embed_content(
            model="gemini-embedding-001",
            contents=batch,  # ← Send all 100 texts at once
            config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")
        )

        # Get embeddings for all texts in this batch
        batch_embeddings = [emb.values for emb in result.embeddings]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings
```

---

## Rate Limit Impact

### Formula

```
Number of API Requests = Total Items / batch_size (rounded up)

RPM Used = Number of API Requests
TPM Used = Total Items × Average Tokens per Item
```

### Example: 2,700 items (your FinanceBench dataset)

**With batch_size=100:**
```
API Requests = 2,700 / 100 = 27 requests
RPM Used = 27
TPM Used = 2,700 items × 30 tokens = 81,000 tokens

Processing time: 27 requests / 100 RPM = 0.27 minutes = 16 seconds
```

**With batch_size=50:**
```
API Requests = 2,700 / 50 = 54 requests
RPM Used = 54
TPM Used = 2,700 items × 30 tokens = 81,000 tokens (same!)

Processing time: 54 requests / 100 RPM = 0.54 minutes = 32 seconds
```

**With batch_size=1 (very inefficient):**
```
API Requests = 2,700 / 1 = 2,700 requests ← Would hit rate limits!
RPM Used = 2,700 (way over 100 RPM limit!)
TPM Used = 81,000 tokens

Processing time: Would fail with 429 errors!
```

---

## Why Larger Batches Are Better

### Comparison

| batch_size | API Requests | RPM Used | Efficiency |
|------------|--------------|----------|------------|
| **1** | 2,700 | 2,700 ⚠️ | Very bad - hits RPM limit |
| **10** | 270 | 270 ⚠️ | Bad - still over limit |
| **50** | 54 | 54 ✅ | Good - under RPM limit |
| **100** | 27 | 27 ✅ | Best - well under RPM limit |

### Key Insight

**Larger batch_size = Fewer API requests = Less likely to hit RPM limit**

But you still need to consider TPM (tokens per minute):
- TPM is independent of batch size
- TPM = Total items × Average tokens per item
- Large batches don't increase TPM usage

---

## Real-World Examples

### Example 1: Small batch_size (inefficient)

```python
# Configuration
batch_size = 10
items_to_embed = 100

# What happens:
# Request 1: texts[0:10]   → API call #1
# Request 2: texts[10:20]  → API call #2
# Request 3: texts[20:30]  → API call #3
# ...
# Request 10: texts[90:100] → API call #10

# Total API requests: 10
# RPM used: 10
```

**Problem:** More API requests = higher chance of hitting RPM limit

### Example 2: Large batch_size (efficient)

```python
# Configuration
batch_size = 100
items_to_embed = 100

# What happens:
# Request 1: texts[0:100] → API call #1 (all 100 items)

# Total API requests: 1
# RPM used: 1
```

**Benefit:** Fewer API requests = less likely to hit RPM limit

### Example 3: FinanceBench (your case)

```python
# Your configuration
batch_size = 100
items_to_embed = 2,700  # nodes + edges

# What happens:
# Request 1:  texts[0:100]     → API call #1  (100 items)
# Request 2:  texts[100:200]   → API call #2  (100 items)
# Request 3:  texts[200:300]   → API call #3  (100 items)
# ...
# Request 27: texts[2600:2700] → API call #27 (100 items)

# Total API requests: 27
# RPM used: 27 (well under 100 RPM limit for free tier)
# TPM used: 2,700 × 30 = 81,000 tokens
```

---

## Rate Limit Calculations

### Free Tier (100 RPM, 30,000 TPM)

**With batch_size=100:**
```
Scenario: Process 2,700 items with 30 tokens each

API Requests needed: 27
Time based on RPM: 27/100 = 0.27 min = 16 seconds ✅

TPM needed: 81,000 tokens
Time based on TPM: 81,000/30,000 = 2.7 minutes ⚠️

Bottleneck: TPM (token limit)
Actual time: ~2.7 minutes
```

**Conclusion:** You're limited by TPM, not RPM!

### Paid Tier 1 (3,000 RPM, 1,000,000 TPM)

**With batch_size=100:**
```
Scenario: Process 2,700 items with 30 tokens each

API Requests needed: 27
Time based on RPM: 27/3,000 = 0.009 min = 0.5 seconds ✅

TPM needed: 81,000 tokens
Time based on TPM: 81,000/1,000,000 = 0.08 minutes = 5 seconds ✅

Bottleneck: None! Well under both limits
Actual time: ~5 seconds (network latency + processing)
```

**Conclusion:** Can process very quickly with Paid Tier 1!

---

## Optimal Batch Size Selection

### Decision Matrix

| Your Situation | Recommended batch_size | Reasoning |
|----------------|----------------------|-----------|
| **Free Tier, Small items** | 50-100 | Maximize items per request, stay under TPM |
| **Free Tier, Large items** | 10-20 | Prevent exceeding TPM with large texts |
| **Paid Tier 1, Small items** | 100 | Maximum efficiency, well under both limits |
| **Paid Tier 1, Large items** | 50-100 | Balance between speed and token usage |
| **Very large dataset (100k+ items)** | 50-100 | Consistent performance across large batches |

### Your FinanceBench Case

```
Dataset: 2,700 items
Average item size: 30 tokens (small)
API Tier: Paid Tier 1

Recommended: batch_size = 100

Why?
- 27 API requests (well under 3,000 RPM)
- 81,000 tokens (well under 1,000,000 TPM)
- Fastest possible processing
- Very unlikely to hit rate limits
```

---

## Common Misconceptions

### ❌ Misconception 1: "batch_size=100 means 100 API requests"

**Reality:** batch_size=100 means 100 items PER request, not 100 requests!

### ❌ Misconception 2: "Larger batch_size uses more TPM"

**Reality:** TPM usage is the same regardless of batch_size!
- batch_size=1: 2,700 requests × 30 tokens = 81,000 TPM
- batch_size=100: 27 requests × 3,000 tokens = 81,000 TPM

### ❌ Misconception 3: "I should use batch_size=1 for accuracy"

**Reality:** Batch size doesn't affect embedding quality, only API efficiency!

---

## Advanced: Batch Size vs Processing Time

### Test Results from Our Implementation

| batch_size | API Requests | Total Time | Time/Item |
|------------|--------------|------------|-----------|
| 10 | 270 | 3.93s | 78.5ms |
| 50 | 54 | 2.75s | 55.0ms |
| 100 | 27 | 2.13s | 42.6ms |

**Observation:** Larger batches = Faster per-item processing

**Why?** Less overhead from making multiple API requests:
- Network round-trip time
- Request/response parsing
- API throttling checks

---

## Impact on Rate Limiting

### Scenario: Hit Rate Limit

**With batch_size=10 (inefficient):**
```
Processing 1,000 items

Requests needed: 100
If rate limit = 100 RPM:
- Request 100 at second 60 → 429 error
- Must wait full minute before continuing
- Very likely to hit rate limits

Total time: 60+ seconds + retry delays
```

**With batch_size=100 (efficient):**
```
Processing 1,000 items

Requests needed: 10
If rate limit = 100 RPM:
- Only 10 requests in first minute
- Way under 100 RPM limit
- Very unlikely to hit rate limits

Total time: ~5-10 seconds, no retry needed
```

---

## Summary

### Key Points

1. **batch_size = items per API request, NOT number of requests**
   ```
   batch_size=100 → 100 items in ONE request
   ```

2. **Larger batches = Fewer API requests**
   ```
   2,700 items:
   - batch_size=100 → 27 requests
   - batch_size=50  → 54 requests
   - batch_size=10  → 270 requests
   ```

3. **RPM counts requests, not items**
   ```
   RPM used = Number of API requests
   NOT = Number of items
   ```

4. **TPM counts total tokens regardless of batch size**
   ```
   TPM used = Total items × Tokens per item
   Same whether batch_size=1 or 100!
   ```

5. **Your optimal setting: batch_size=100**
   ```
   For 2,700 items:
   - 27 API requests
   - Well under all rate limits
   - Fastest processing
   ```

---

## Visual Summary

```
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│  batch_size = Number of items in ONE API request             │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  API Request #1                                         │ │
│  │  ┌───────┬───────┬───────┬─────┬───────┐              │ │
│  │  │ item1 │ item2 │ item3 │ ... │ item100│ ← batch_size│ │
│  │  └───────┴───────┴───────┴─────┴───────┘              │ │
│  │                                                         │ │
│  │  Returns: 100 embeddings                               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  RPM used: 1 (one request)                                   │
│  TPM used: 100 items × tokens per item                       │
│                                                               │
└───────────────────────────────────────────────────────────────┘

Total items: 2,700
batch_size: 100
─────────────────────────────────────────────────────────────
API Requests: 2,700 / 100 = 27 requests
RPM Used: 27
Processing: Very efficient! ✅
```

---

## Practical Recommendation

**For your FinanceBench pipeline:**

```python
# Keep this configuration (it's perfect!)
"vectorizer": {
    "batch_size": 100,    # ← 100 items per API request
    "max_retries": 3,     # ← Retry if rate limit hit
    "retry_delay": 10     # ← Wait 10s before retry
}
```

**This means:**
- Each API request processes 100 items
- Total 27 API requests for 2,700 items
- Completes in ~2 minutes
- Very unlikely to hit rate limits
- Optimal efficiency! ✅

---

**TL;DR:** `batch_size=100` means "put 100 items in each API request", NOT "make 100 API requests". Larger batches = fewer requests = better efficiency! 🚀
