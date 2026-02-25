import json
import os

nb_path = 'notebooks/financebench_eda.ipynb'

description_text = """
## Dataset Description: FinanceBench

**FinanceBench** is a specialized benchmark dataset designed to evaluate the performance of Large Language Models (LLMs) on financial question answering tasks. It focuses on retrieving and reasoning over information contained in financial documents, primarily annual reports (10-Ks).

### Key Characteristics:
- **Domain**: Finance (Public Company Filings)
- **Source Documents**: 10-K Filings from various fiscal years.
- **Task**: Open-book Question Answering (Retrieval-Augmented Generation).

### Data Structure:
Based on the open-source subset analyzed, the dataset typically contains:
- **financebench_id**: Unique identifier for each question.
- **company**: The name of the company usually involved (e.g., 3M, Best Buy).
- **doc_name**: The specific source document (e.g., `3M_2018_10K`).
- **question**: The query posed to the model.
- **answer**: The ground truth answer.
- **evidence**: Text snippets from the document that support the answer.
- **question_type**: Categorization of the question logic (see below).
- **question_reasoning**: Detailed reasoning type (e.g., "Information extraction").

### Question Categories:
The benchmark includes diverse question types to test different capabilities:
1.  **metrics-generated**: Questions that ask for direct extraction of specific financial metrics or numbers from the documents.
2.  **domain-relevant**: Questions that require applying financial domain knowledge or logical reasoning to the extracted information.
3.  **novel-generated**: Questions involving hypotheticals, exclusions, or synthesized insights not directly present as a single line item.

### Purpose:
This dataset is essential for assessing how well LLMs can handle the specific lexicon, structure, and reasoning requirements of the financial domain, moving beyond general-purpose QA benchmarks.
"""

# Define the new cell to append
new_cell = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [description_text]
}

# Load, insert at top, and save
try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # Check if section already exists to avoid duplication
    section_exists = False
    for cell in nb['cells']:
        if "## Dataset Description: FinanceBench" in "".join(cell.get('source', [])):
            section_exists = True
            break
    
    if not section_exists:
        # Insert after the title cell (index 1)
        nb['cells'].insert(1, new_cell)
        
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1)
        print("Successfully inserted dataset description to notebook.")
    else:
        print("Dataset description section already exists. Skipping insertion.")

except Exception as e:
    print(f"Error modifying notebook: {e}")
