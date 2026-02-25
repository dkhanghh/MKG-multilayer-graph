import json
import os

nb_path = 'notebooks/financebench_eda.ipynb'

# Define the new cells to append
new_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Deep Dive: Information Extraction Failures\n",
            "\n",
            "Inspecting specific failure cases for 'Information extraction' questions to understand retrieval and reasoning issues."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Filter for Information extraction failures\n",
            "info_extraction_failures = df_merged[\n",
            "    (df_merged['question_reasoning'] == 'Information extraction') &\n",
            "    (df_merged['Status'] != 'Passed')\n",
            "]\n",
            "\n",
            "print(f\"Found {len(info_extraction_failures)} failed 'Information extraction' cases.\")\n"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Display details for each failure\n",
            "for index, row in info_extraction_failures.iterrows():\n",
            "    print(f\"--- Case {index} ---\")\n",
            "    print(f\"Question: {row['Input']}\")\n",
            "    print(f\"Expected: {row['Expected Output']}\")\n",
            "    print(f\"Actual:   {row['Actual Output']}\")\n",
            "    print(f\"\\nRetrieval Context:\\n{row['Retrieval Context']}\")\n",
            "    print(f\"\\nFaithfulness Reason:\\n{row['Faithfulness Reason']}\")\n",
            "    print(f\"\\nHallucination Reason:\\n{row['Hallucination Reason']}\")\n",
            "    print(\"\\n\" + \"=\"*80 + \"\\n\")\n"
        ]
    }
]

# Load, append, and save
try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # Check if section already exists to avoid duplication
    section_exists = False
    for cell in nb['cells']:
        if "## Deep Dive: Information Extraction Failures" in "".join(cell.get('source', [])):
            section_exists = True
            break
    
    if not section_exists:
        nb['cells'].extend(new_cells)
        
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1)
        print("Successfully appended information extraction failure analysis cells to notebook.")
    else:
        print("Information extraction failure analysis section already exists. Skipping append.")

except Exception as e:
    print(f"Error modifying notebook: {e}")
