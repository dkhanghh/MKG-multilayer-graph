"""Debug why edges aren't being created."""

import json

# Your TRP output
trp_output = {
  "relationships": [
    {
      "source_id": "test_instruction_008",
      "target_id": "cr3072",
      "relation_type": "follows_change_request",
      "confidence": 0.95
    },
    {
      "source_id": "test_instruction_008",
      "target_id": "smi_203a",
      "relation_type": "smi_number_changed_to",
      "confidence": 0.95
    }
  ]
}

# Example STD output - what are the actual entity IDs?
# You need to check your STD extraction results
example_std_output = {
  "entities": [
    {"id": "operational_sonion_template", "name": "Operational Sonion Measurement Instruction template"},
    {"id": "smi_203a", "name": "SMI 203a"},
    {"id": "cr3072", "name": "CR3072"}
    # Is "test_instruction_008" in here?
  ]
}

# Build entity_map like the code does
entity_map = {}
for entity in example_std_output["entities"]:
    entity_map[entity.get("id", "")] = entity["name"]

print("="*70)
print("EDGE CREATION ANALYSIS")
print("="*70)
print(f"\nEntity Map (available IDs): {list(entity_map.keys())}")
print()

# Check each relationship
for rel in trp_output["relationships"]:
    source_id = rel["source_id"]
    target_id = rel["target_id"]
    
    source_exists = source_id in entity_map
    target_exists = target_id in entity_map
    
    status = "✅ CREATED" if (source_exists and target_exists) else "❌ SKIPPED"
    
    print(f"{status}: {source_id} -> {target_id}")
    if not source_exists:
        print(f"  ⚠️  Source ID '{source_id}' NOT in entity_map")
    if not target_exists:
        print(f"  ⚠️  Target ID '{target_id}' NOT in entity_map")
    print()

print("="*70)
print("\nSOLUTION:")
print("1. Check your STD extraction output - what entity IDs does it have?")
print("2. Ensure TRP uses the same IDs that STD assigns to entities")
print("3. Check logs for: 'Relationship references unknown entities'")
print("="*70)
