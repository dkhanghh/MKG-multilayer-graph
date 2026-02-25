import json
import os

nb_path = 'notebooks/financebench_eda.ipynb'

# Define the new cells to append with definitions
new_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Question Type Definitions\n",
            "\n",
            "Based on analysis of the dataset examples, the question types can be defined as follows:\n",
            "\n",
            "- **metrics-generated**: Questions that ask for direct extraction of specific financial metrics or numbers from the documents.  \n",
            "  *Example:* \"What is the FY2018 capital expenditure amount...\"\n",
            "\n",
            "- **domain-relevant**: Questions that require applying financial domain knowledge or logical reasoning to the extracted information. These often ask for qualitative assessments based on quantitative data.  \n",
            "  *Example:* \"Is 3M a capital-intensive business based on FY2022 data?\"\n",
            "\n",
            "- **novel-generated**: Questions designed to test capabilities beyond standard extraction, often involving hypotheticals, exclusions, or synthesized insights not directly present as a single line item.  \n",
            "  *Example:* \"If we exclude the impact of M&A, which segment...\""
        ]
    }
]

# Load, append, and save
try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # Check if section already exists
    section_exists = False
    for cell in nb['cells']:
        if "## Question Type Definitions" in "".join(cell.get('source', [])):
            section_exists = True
            break
    
    if not section_exists:
        nb['cells'].extend(new_cells)
        
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1)
        print("Successfully appended question type definitions to notebook.")
    else:
        print("Definitions section already exists. Skipping append.")

except Exception as e:
    print(f"Error modifying notebook: {e}")
