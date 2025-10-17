"""Test if extract_json_from_response can handle the provided JSON array."""

import json
from knowledge_graphs.utils.llm_client import extract_json_from_response

# Test case 1: JSON array in code block
test_response_1 = """
Here are the extracted entities:

```json
[
  {
    "name": "Operational Sonion Measurement Instruction template",
    "category": "TestInstruction",
    "description": "A document template for operational measurement instructions."
  },
  {
    "name": "SMI 203a",
    "category": "TestInstruction",
    "description": "A specific SMI number assigned after CR3072."
  }
]
```

That's what I extracted!
"""

# Test case 2: JSON array without code block
test_response_2 = """
[
  {
    "name": "Mechanical shock test",
    "category": "TestType",
    "description": "The original name of a test procedure."
  }
]
"""

# Test case 3: JSON array wrapped in text
test_response_3 = """
The entities are: [{"name": "SMI 203", "category": "TestInstruction", "description": "A generic SMI number."}]
"""

# Test case 4: Your full JSON
test_response_4 = """
```json
[
  {
    "name": "Operational Sonion Measurement Instruction template",
    "category": "TestInstruction",
    "description": "A document template for operational measurement instructions related to Sonion, outlining procedures and requirements."
  },
  {
    "name": "SMI 203a",
    "category": "TestInstruction",
    "description": "A specific SMI (Sonion Measurement Instruction) number assigned after CR3072, used for a particular test instruction."
  },
  {
    "name": "SMI 203",
    "category": "TestInstruction",
    "description": "A generic SMI number intended for shared use with customers, referenced in the context of CR3072."
  }
]
```
"""

print("Testing extract_json_from_response with different formats:\n")
print("="*70)

for i, test in enumerate([test_response_1, test_response_2, test_response_3, test_response_4], 1):
    print(f"\nTest {i}:")
    print(f"Input preview: {test[:100]}...")
    
    result = extract_json_from_response(test)
    
    if result:
        print(f"✅ SUCCESS - Extracted: {type(result)}")
        if isinstance(result, list):
            print(f"   Array with {len(result)} items")
            print(f"   First item: {result[0].get('name', 'N/A')}")
        elif isinstance(result, dict):
            print(f"   Dict with keys: {list(result.keys())}")
    else:
        print(f"❌ FAILED - Could not extract JSON")
    
    print("-"*70)

print("\n" + "="*70)
print("CONCLUSION:")
print("If any test failed, the function needs to be fixed to handle JSON arrays.")
