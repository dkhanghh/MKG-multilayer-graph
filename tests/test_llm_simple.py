"""
Simple test script to debug LLM endpoint connection (no dependencies).
"""

import os
import json

# Try to read from environment or use defaults
base_url = os.environ.get("OPENAI_BASE_URL", "https://llm.duykhangh.net/v1")
api_key = os.environ.get("OPENAI_API_KEY", "")

print(f"Testing connection to: {base_url}")
print(f"API Key: {'*' * min(len(api_key), 10) if api_key else 'NOT SET'}")
print("-" * 60)

# Test using urllib (built-in, no dependencies)
import urllib.request
import urllib.error

endpoint = f"{base_url}/chat/completions"
print(f"\nTest 1: Checking endpoint: {endpoint}")

# Prepare request
payload = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.1,
    "max_tokens": 10
}

data = json.dumps(payload).encode('utf-8')

# Test with Authorization header
headers = {
    "Content-Type": "application/json",
}

if api_key:
    headers["Authorization"] = f"Bearer {api_key}"

try:
    req = urllib.request.Request(endpoint, data=data, headers=headers, method='POST')
    response = urllib.request.urlopen(req, timeout=10)

    print(f"Status Code: {response.status}")
    print(f"✅ SUCCESS: Connection working!")
    body = response.read().decode('utf-8')
    print(f"Response: {body[:500]}")

except urllib.error.HTTPError as e:
    print(f"Status Code: {e.code}")
    print(f"Response: {e.read().decode('utf-8')[:500]}")

    if e.code == 403:
        print("\n🔴 ERROR: 403 Forbidden")
        print("\nPossible causes:")
        print("1. Invalid or missing API key")
        print("2. IP address not whitelisted")
        print("3. API key doesn't have permission for this endpoint")
        print("4. Endpoint requires different authentication method")

except urllib.error.URLError as e:
    print(f"❌ ERROR: Connection error - {e.reason}")
except Exception as e:
    print(f"❌ ERROR: {e}")

# Test 2: Try without API key
print("\n" + "="*60)
print("Test 2: Trying without Authorization header")

headers_no_auth = {"Content-Type": "application/json"}

try:
    req = urllib.request.Request(endpoint, data=data, headers=headers_no_auth, method='POST')
    response = urllib.request.urlopen(req, timeout=10)

    print(f"Status Code: {response.status}")
    print("✅ Endpoint works WITHOUT authentication!")
    print('Set OPENAI_API_KEY to any dummy value: OPENAI_API_KEY="sk-dummy"')

except urllib.error.HTTPError as e:
    print(f"Status Code: {e.code}")
    if e.code != 403:
        print(f"Response: {e.read().decode('utf-8')[:200]}")
except Exception as e:
    print(f"❌ ERROR: {e}")

print("\n" + "="*60)
print("\nTo fix:")
print("1. Create a .env file in the project root directory")
print("2. Add: OPENAI_BASE_URL=https://llm.duykhangh.net/v1")
print("3. Add: OPENAI_API_KEY=your_actual_key")
print("4. Or export as environment variables")
