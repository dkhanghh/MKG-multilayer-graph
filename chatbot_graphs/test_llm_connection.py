"""
Test script to debug LLM endpoint connection issues.
Run this to test your custom OpenAI-compatible endpoint.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

base_url = os.getenv("OPENAI_BASE_URL", "https://llm.duykhangh.net/v1")
api_key = os.getenv("OPENAI_API_KEY", "")

print(f"Testing connection to: {base_url}")
print(f"API Key: {'*' * len(api_key) if api_key else 'NOT SET'}")
print("-" * 60)

# Test 1: Check if endpoint is reachable
endpoint = f"{base_url}/chat/completions"
print(f"\nTest 1: Checking endpoint: {endpoint}")

# Test with Authorization header
headers = {
    "Content-Type": "application/json",
}

if api_key:
    headers["Authorization"] = f"Bearer {api_key}"

payload = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.1,
    "max_tokens": 10
}

try:
    response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text[:500]}")

    if response.status_code == 403:
        print("\n🔴 ERROR: 403 Forbidden")
        print("\nPossible causes:")
        print("1. Invalid or missing API key")
        print("2. IP address not whitelisted")
        print("3. API key doesn't have permission for this endpoint")
        print("4. Endpoint requires different authentication method")
        print("\nTroubleshooting steps:")
        print("- Verify OPENAI_API_KEY in .env file")
        print("- Check with your endpoint administrator about auth requirements")
        print("- Try accessing the endpoint from a different network")

    elif response.status_code == 200:
        print("\n✅ SUCCESS: Connection working!")
        print(f"Response: {response.json()}")

    else:
        print(f"\n⚠️  Unexpected status code: {response.status_code}")

except requests.exceptions.Timeout:
    print("❌ ERROR: Request timed out")
except requests.exceptions.ConnectionError as e:
    print(f"❌ ERROR: Connection error - {e}")
except Exception as e:
    print(f"❌ ERROR: {e}")

# Test 2: Try without API key (some endpoints don't require it)
print("\n" + "="*60)
print("Test 2: Trying without Authorization header")
headers_no_auth = {"Content-Type": "application/json"}

try:
    response = requests.post(endpoint, json=payload, headers=headers_no_auth, timeout=10)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        print("✅ Endpoint works WITHOUT authentication!")
        print("Solution: Set OPENAI_API_KEY to any dummy value in .env")
        print('Example: OPENAI_API_KEY="sk-dummy"')
    else:
        print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"❌ ERROR: {e}")

# Test 3: Try with different auth header
print("\n" + "="*60)
print("Test 3: Trying with X-API-Key header (alternative auth method)")

if api_key:
    headers_alt = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }

    try:
        response = requests.post(endpoint, json=payload, headers=headers_alt, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("✅ Endpoint works with X-API-Key header!")
            print("Note: You may need to customize the LangChain OpenAI client")
        else:
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
else:
    print("Skipping (no API key set)")

print("\n" + "="*60)
print("\nNext steps:")
print("1. Check which test succeeded above")
print("2. Update your .env file accordingly")
print("3. Contact your endpoint administrator if issues persist")
