import json
import os

nb_path = 'notebooks/financebench_eda.ipynb'
jsonl_path = 'notebooks/.result/financebench_open_source.jsonl'

# Define the new cells to append
new_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Failure Analysis by Question Category\n",
            "\n",
            "Merging test results with the original dataset to analyze failure rates by question type and reasoning."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            f"source_path = '{jsonl_path}'\n",
            "try:\n",
            "    df_source = pd.read_json(source_path, lines=True)\n",
            "    print(f\"Loaded source data with {len(df_source)} records.\")\n",
            "except Exception as e:\n",
            "    print(f\"Error loading source file: {e}\")"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Merge on question text\n",
            "df_merged = pd.merge(df_test, df_source, left_on='Input', right_on='question', how='left')\n",
            "print(f\"Merged data shape: {df_merged.shape}\")\n",
            "df_merged[['Input', 'question', 'question_type', 'question_reasoning', 'Status']].head()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Pass/Fail by Question Type"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "plt.figure(figsize=(10, 6))\n",
            "sns.countplot(y='question_type', hue='Status', data=df_merged)\n",
            "plt.title('Pass/Fail by Question Type')\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Calculate pass rate by question type\n",
            "pass_rates_type = df_merged.groupby('question_type')['Status'].apply(lambda x: (x == 'Passed').mean()).sort_values()\n",
            "print(\"Pass Rate by Question Type:\")\n",
            "print(pass_rates_type)"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Pass/Fail by Question Reasoning"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "plt.figure(figsize=(10, 8))\n",
            "sns.countplot(y='question_reasoning', hue='Status', data=df_merged)\n",
            "plt.title('Pass/Fail by Question Reasoning')\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Calculate pass rate by question reasoning\n",
            "pass_rates_reasoning = df_merged.groupby('question_reasoning')['Status'].apply(lambda x: (x == 'Passed').mean()).sort_values()\n",
            "print(\"Pass Rate by Question Reasoning:\")\n",
            "print(pass_rates_reasoning)"
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
        if "## Failure Analysis by Question Category" in "".join(cell.get('source', [])):
            section_exists = True
            break
    
    if not section_exists:
        nb['cells'].extend(new_cells)
        
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1)
        print("Successfully appended failure analysis cells to notebook.")
    else:
        print("Failure analysis section already exists. Skipping append.")

except Exception as e:
    print(f"Error modifying notebook: {e}")
