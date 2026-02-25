import json
import pandas as pd

jsonl_path = 'notebooks/.result/financebench_open_source.jsonl'

try:
    df = pd.read_json(jsonl_path, lines=True)
    
    # Define types to investigate
    types = ['domain-relevant', 'metrics-generated', 'novel-generated']
    
    for q_type in types:
        print(f"\n=== Examples for: {q_type} ===")
        # Get 3 random examples
        examples = df[df['question_type'] == q_type].sample(3, random_state=42)
        for i, row in examples.iterrows():
            print(f"- Question: {row['question']}")
            print(f"  Reasoning: {row['question_reasoning']}")
            print(f"  Justification: {row['justification']}")
            print()

except Exception as e:
    print(f"Error: {e}")
