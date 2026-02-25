
import json
import os

nb_path = '/Users/duykhangh/Work/HCMUT/thesis-llms-multilayer-graph/notebooks/evaluation_with_deepeval.ipynb'

with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

target_source_part = "financebench_eval['retrieval'] = financebench_eval['retrieval'].apply(ast.literal_eval)"
new_line = "financebench_eval['contexts'] = financebench_eval['contexts'].apply(ast.literal_eval)\n"

found = False
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = cell['source']
        # source is a list of strings
        source_str = "".join(source)
        if target_source_part in source_str:
            # Check if already added
            if "financebench_eval['contexts']" in source_str:
                print("Contexts conversion already present.")
                found = True
                break
            
            # Find the line index
            for i, line in enumerate(source):
                if target_source_part in line:
                    # Insert the new line after
                    source.insert(i + 1, new_line)
                    found = True
                    break
        if found:
            break

if found:
    with open(nb_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)
    print("Notebook updated successfully.")
else:
    print("Target cell not found.")
