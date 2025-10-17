"""Test to demonstrate the format issue"""

# Scenario 1: NER returns array format
ner_result_array = [
    {"name": "Test1", "category": "Cat1"},
    {"name": "Test2", "category": "Cat2"}
]

# Scenario 2: STD/TRP templates expect this in examples
expected_format = {
    "entities": [
        {"name": "Test1", "category": "Cat1"},
        {"name": "Test2", "category": "Cat2"}
    ]
}

print("Problem:")
print(f"1. NER returns: {type(ner_result_array)} - {ner_result_array[:1]}...")
print(f"2. Templates expect: named_entities to be passed")
print(f"3. If array is passed directly, STD/TRP might not understand it")
print()
print("Solution:")
print("Need to normalize array format to dict format before passing to STD/TRP")
print(f"Convert: list → {{'entities': list}}")
