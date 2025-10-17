# Gemini Embedding API Rate Limits & Batch Size Recommendations

**Last Updated:** October 12, 2025
**API Model:** gemini-embedding-001

---

## Official Rate Limits

### Free Tier (Default)
| Metric | Limit | Description |
|--------|-------|-------------|
| **RPM** (Requests per Minute) | 100 | Maximum API calls per minute |
| **TPM** (Tokens per Minute) | 30,000 | Maximum tokens processed per minute |
| **RPD** (Requests per Day) | 1,000 | Maximum API calls per day |

### Paid Tier 1
| Metric | Limit | Description |
|--------|-------|-------------|
| **RPM** | 3,000 | Maximum API calls per minute |
| **TPM** | 1,000,000 | Maximum tokens processed per minute |
| **RPD** | Unlimited* | No daily limit |

### Paid Tier 2
| Metric | Limit | Description |
|--------|-------|-------------|
| **RPM** | 5,000 | Maximum API calls per minute |
| **TPM** | 5,000,000 | Maximum tokens processed per minute |
| **RPD** | Unlimited* | No daily limit |

### Paid Tier 3
| Metric | Limit | Description |
|--------|-------|-------------|
| **RPM** | 10,000 | Maximum API calls per minute |
| **TPM** | 10,000,000 | Maximum tokens processed per minute |
| **RPD** | Unlimited* | No daily limit |

*Note: Actual capacity may vary. Limits are not guaranteed.*

---

## Understanding Rate Limiting

### What Causes 429 Errors?

The **429 Too Many Requests** error occurs when you exceed either:
1. **RPM limit** - Too many API requests in a minute
2. **TPM limit** - Too many tokens processed in a minute

### Key Insight: Batching Strategy

The Gemini API allows you to send **multiple texts in a single request**:

```python
# Single request with batch of texts
result = client.models.embed_content(
    model="gemini-embedding-001",
    contents=["text1", "text2", "text3", ...],  # Multiple texts
)
```

This means:
- **1 API request can embed 100 items** → Uses 1 RPM, but ~100 tokens worth of quota
- **Larger batches = Fewer requests = Less likely to hit RPM limit**

---

## Batch Size Calculation

### For Free Tier

**Constraints:**
- 100 RPM (requests per minute)
- 30,000 TPM (tokens per minute)
- Average text length: ~100 characters (~25 tokens per item)

#### Scenario 1: Small Items (~25 tokens each)

**Maximum items per minute:**
```
TPM limit: 30,000 tokens / 25 tokens per item = 1,200 items/minute
RPM limit: 100 requests × batch_size = 100 × batch_size items/minute
```

**Optimal batch size:**
```
To maximize TPM usage: 1,200 items / 100 requests = 12 items per batch
```

**Recommendation:**
- **Batch size: 10-20 items**
- Process ~1,000-1,200 items per minute
- Stay within both RPM and TPM limits

#### Scenario 2: Large Items (~100 tokens each)

**Maximum items per minute:**
```
TPM limit: 30,000 tokens / 100 tokens per item = 300 items/minute
RPM limit: 100 requests × batch_size = 100 × batch_size items/minute
```

**Optimal batch size:**
```
300 items / 100 requests = 3 items per batch
```

**Recommendation:**
- **Batch size: 3-5 items**
- Process ~300 items per minute
- TPM becomes the bottleneck with larger texts

---

### For Paid Tier 1

**Constraints:**
- 3,000 RPM
- 1,000,000 TPM
- Average text length: ~100 characters (~25 tokens)

#### Small Items (~25 tokens each)

**Maximum items per minute:**
```
TPM limit: 1,000,000 / 25 = 40,000 items/minute
RPM limit: 3,000 × batch_size items/minute
```

**Optimal batch size:**
```
40,000 items / 3,000 requests = ~13 items per batch
```

**Recommendation:**
- **Batch size: 10-50 items**
- Process ~30,000-40,000 items per minute
- Very high throughput

#### Large Items (~100 tokens each)

**Optimal batch size:**
```
1,000,000 tokens / 100 tokens = 10,000 items possible
10,000 items / 3,000 requests = ~3 items per batch
```

**Recommendation:**
- **Batch size: 3-10 items**
- Process ~9,000-10,000 items per minute

---

## Recommended Batch Sizes by Tier

### Quick Reference Table

| Tier | Item Size | Recommended Batch Size | Items/Minute | Requests/Minute |
|------|-----------|------------------------|--------------|-----------------|
| **Free** | Small (~25 tokens) | **10-20** | 1,000-1,200 | 50-100 |
| **Free** | Medium (~50 tokens) | **5-10** | 500-600 | 50-100 |
| **Free** | Large (~100 tokens) | **3-5** | 300-400 | 100 |
| **Paid Tier 1** | Small (~25 tokens) | **50-100** | 30,000-40,000 | 300-800 |
| **Paid Tier 1** | Medium (~50 tokens) | **25-50** | 15,000-20,000 | 300-800 |
| **Paid Tier 1** | Large (~100 tokens) | **10-25** | 5,000-10,000 | 500-1,000 |

---

## Token Estimation Guide

### Average Tokens by Content Type

| Content Type | Characters | Tokens (est.) | Example |
|--------------|-----------|---------------|---------|
| Entity Name | 20-50 | 5-15 | "Apple Inc." |
| Short Description | 50-150 | 15-40 | "Technology company based in Cupertino" |
| Full Node Text | 100-300 | 25-75 | Template: "{name} is a {type}. {description}" |
| Edge Text | 30-80 | 8-20 | "Apple Inc. has_metric Total Revenue" |
| Long Context | 500-2000 | 125-500 | Full financial statement paragraph |

**Rule of thumb:** 1 token ≈ 4 characters for English text

---

## FinanceBench Pipeline Analysis

### Your Current Configuration

```python
config = {
    "model": "gemini-embedding-001",
    "batch_size": 100,  # Current setting
    "embed_nodes": True,
    "embed_edges": True
}
```

### Dataset Characteristics

**From test results:**
- 150 financebench files
- ~10 nodes per file = 1,500 nodes
- ~8 edges per file = 1,200 edges
- **Total items: 2,700**

**Average item characteristics:**
- Node text: ~150 characters = ~38 tokens
- Edge text: ~50 characters = ~13 tokens
- Weighted average: ~28 tokens per item

### Rate Limit Analysis

#### Current Settings (batch_size=100)

**Free Tier:**
```
Items to process: 2,700
Batch size: 100
Requests needed: 2,700 / 100 = 27 requests

Time calculation:
- RPM limit: 100 requests/minute
- Time needed: 27 requests / 100 RPM = 0.27 minutes = 16 seconds ✅

Token calculation:
- Tokens per item: ~28 tokens
- Tokens per batch: 100 × 28 = 2,800 tokens
- Tokens per minute: 27 requests × 2,800 = 75,600 tokens
- TPM limit: 30,000 tokens/minute
- Time needed: 75,600 / 30,000 = 2.52 minutes ✅
```

**Result:** ✅ Batch size 100 works well for FinanceBench dataset on free tier!

#### Safer Configuration (batch_size=50)

**Free Tier:**
```
Requests needed: 2,700 / 50 = 54 requests
Time (RPM): 54 / 100 = 0.54 minutes = 32 seconds ✅
Tokens per batch: 50 × 28 = 1,400 tokens
Tokens per minute: 54 × 1,400 = 75,600 tokens
Time (TPM): 75,600 / 30,000 = 2.52 minutes ✅
```

**Result:** ✅ More conservative, same total time

---

## Recommendations by Use Case

### For FinanceBench Dataset (2,700 items)

#### Free Tier
```python
config = {
    "batch_size": 50,  # Conservative and safe
    "max_retries": 3,
    "retry_delay": 60  # seconds
}
```

**Why 50?**
- Safe margin below limits
- Processes in ~2-3 minutes total
- Unlikely to trigger rate limits
- Good balance of speed and safety

#### Paid Tier 1
```python
config = {
    "batch_size": 100,  # Your current setting is perfect!
    "max_retries": 3,
    "retry_delay": 10
}
```

**Why 100?**
- Takes full advantage of higher limits
- Processes in ~1-2 minutes total
- Very fast throughput
- Well within Tier 1 capacity

---

### For Large-Scale Production (10,000+ items)

#### Free Tier
```python
config = {
    "batch_size": 20,          # Smaller batches
    "requests_per_minute": 80, # Leave 20% headroom
    "delay_between_batches": 0.75  # 750ms delay
}
```

**Strategy:** Rate limiting with delays
- Process ~1,000 items per minute
- Add delays to stay under limits
- Implement exponential backoff

#### Paid Tier 1
```python
config = {
    "batch_size": 100,
    "requests_per_minute": 2500,  # 83% of limit
    "enable_parallel": True
}
```

**Strategy:** Parallel processing
- Process ~250,000 items per minute
- Use concurrent requests
- Maximum throughput

---

## Implementation: Adaptive Batch Sizing

### Smart Batch Size Calculator

```python
def calculate_optimal_batch_size(
    tier: str = "free",
    avg_tokens_per_item: int = 30,
    target_items_per_minute: int = 1000
):
    """
    Calculate optimal batch size based on API tier and content.

    Args:
        tier: API tier ("free", "tier1", "tier2", "tier3")
        avg_tokens_per_item: Average tokens per item
        target_items_per_minute: Desired processing rate

    Returns:
        Optimal batch size
    """

    # Rate limits by tier
    limits = {
        "free": {"rpm": 100, "tpm": 30000},
        "tier1": {"rpm": 3000, "tpm": 1000000},
        "tier2": {"rpm": 5000, "tpm": 5000000},
        "tier3": {"rpm": 10000, "tpm": 10000000}
    }

    rpm_limit = limits[tier]["rpm"]
    tpm_limit = limits[tier]["tpm"]

    # Calculate max items based on token limit
    max_items_by_tokens = tpm_limit // avg_tokens_per_item

    # Calculate optimal batch size
    # Aim for 80% of RPM limit for safety
    safe_rpm = int(rpm_limit * 0.8)

    # Batch size = items per minute / requests per minute
    optimal_batch = min(
        target_items_per_minute // safe_rpm,
        max_items_by_tokens // safe_rpm,
        100  # Max batch size cap
    )

    return max(1, optimal_batch)  # At least 1


# Examples
print(calculate_optimal_batch_size("free", 30, 1000))
# Output: 12

print(calculate_optimal_batch_size("tier1", 30, 10000))
# Output: 4
```

---

## Rate Limit Error Handling

### Retry Strategy with Exponential Backoff

```python
import time
import random

def embed_with_retry(
    vectorizer,
    texts,
    max_retries=3,
    base_delay=60
):
    """
    Embed texts with automatic retry on rate limit errors.

    Args:
        vectorizer: GeminiVectorizer instance
        texts: List of texts to embed
        max_retries: Maximum retry attempts
        base_delay: Base delay in seconds (doubles each retry)

    Returns:
        List of embeddings
    """

    for attempt in range(max_retries):
        try:
            return vectorizer._generate_gemini_embeddings(texts)

        except Exception as e:
            error_msg = str(e)

            # Check if it's a rate limit error
            if "429" in error_msg or "quota" in error_msg.lower():
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    delay = base_delay * (2 ** attempt)
                    jitter = random.uniform(0, delay * 0.1)
                    total_delay = delay + jitter

                    print(f"Rate limit hit. Retrying in {total_delay:.1f}s "
                          f"(attempt {attempt + 1}/{max_retries})")
                    time.sleep(total_delay)
                else:
                    print(f"Max retries reached. Failing.")
                    raise
            else:
                # Not a rate limit error, raise immediately
                raise

    return []
```

### Usage in Vectorizer

```python
class GeminiVectorizerWithRetry(GeminiVectorizer):
    """Extended vectorizer with built-in retry logic."""

    def __init__(self, config):
        super().__init__(config)
        self.max_retries = self.get_config_value("max_retries", 3)
        self.base_retry_delay = self.get_config_value("retry_delay", 60)

    def _generate_gemini_embeddings(self, texts):
        """Override with retry logic."""
        return embed_with_retry(
            super(),
            texts,
            self.max_retries,
            self.base_retry_delay
        )
```

---

## Monitoring and Optimization

### Track Rate Limit Usage

```python
class RateLimitTracker:
    """Track API usage to stay within limits."""

    def __init__(self, rpm_limit=100, tpm_limit=30000):
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.requests_this_minute = 0
        self.tokens_this_minute = 0
        self.minute_start = time.time()

    def check_and_wait(self, estimated_tokens):
        """Check limits and wait if necessary."""
        current_time = time.time()

        # Reset if new minute
        if current_time - self.minute_start >= 60:
            self.requests_this_minute = 0
            self.tokens_this_minute = 0
            self.minute_start = current_time

        # Check if adding this request would exceed limits
        if (self.requests_this_minute >= self.rpm_limit * 0.9 or
            self.tokens_this_minute + estimated_tokens >= self.tpm_limit * 0.9):

            # Wait until next minute
            wait_time = 60 - (current_time - self.minute_start)
            if wait_time > 0:
                print(f"Approaching rate limit. Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                self.requests_this_minute = 0
                self.tokens_this_minute = 0
                self.minute_start = time.time()

        # Record this request
        self.requests_this_minute += 1
        self.tokens_this_minute += estimated_tokens
```

---

## Summary & Final Recommendations

### For Your FinanceBench Project

#### Current Status
- ✅ Your current `batch_size=100` is **perfect for Paid Tier 1**
- ⚠️ For Free Tier, reduce to `batch_size=50` for safety

#### Recommended Configuration

**Free Tier (Conservative):**
```python
vectorizer_config = {
    "type": "gemini_vectorizer",
    "model": "gemini-embedding-001",
    "batch_size": 50,           # Safe for free tier
    "max_tokens": 2048,
    "embed_nodes": True,
    "embed_edges": True,
    "max_retries": 3,
    "retry_delay": 60
}
```

**Paid Tier 1 (Optimal):**
```python
vectorizer_config = {
    "type": "gemini_vectorizer",
    "model": "gemini-embedding-001",
    "batch_size": 100,          # Your current setting - perfect!
    "max_tokens": 2048,
    "embed_nodes": True,
    "embed_edges": True,
    "max_retries": 3,
    "retry_delay": 10
}
```

### Key Takeaways

1. **Free Tier Limits:**
   - 100 RPM, 30,000 TPM
   - Use batch_size: **10-50**
   - Process ~1,000 items/minute

2. **Paid Tier 1 Limits:**
   - 3,000 RPM, 1,000,000 TPM
   - Use batch_size: **50-100**
   - Process ~30,000 items/minute

3. **For 2,700 FinanceBench Items:**
   - Free Tier: ~3 minutes total
   - Paid Tier 1: ~2 minutes total

4. **Error Prevention:**
   - Implement exponential backoff
   - Add 10-20% safety margin
   - Monitor token usage

5. **Optimization:**
   - Larger batches = fewer requests
   - Balance between speed and safety
   - Track usage to stay within limits

---

## References

- [Gemini API Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Test Results: [GEMINI_VECTORIZER_TEST_RESULTS.md](GEMINI_VECTORIZER_TEST_RESULTS.md)

---

**Last Updated:** October 12, 2025
