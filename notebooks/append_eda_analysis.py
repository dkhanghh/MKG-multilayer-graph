import json
import os

nb_path = 'notebooks/financebench_eda.ipynb'
csv_path = '.result/end_to_end_test_run_GPT-oss20B.csv'

# Define the new cells to append
new_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Test Run Analysis: GPT-oss20B\n",
            "\n",
            "Analysis of the end-to-end test run results for GPT-oss20B."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            f"test_run_path = '{csv_path}'\n",
            "try:\n",
            "    df_test = pd.read_csv(test_run_path)\n",
            "    print(f\"Loaded test run data with {len(df_test)} records.\")\n",
            "except Exception as e:\n",
            "    print(f\"Error loading file: {e}\")"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "df_test.head()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Status Distribution"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "plt.figure(figsize=(6, 4))\n",
            "sns.countplot(x='Status', data=df_test)\n",
            "plt.title('Test Case Status Distribution')\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Faithfulness & Hallucination Scores"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "fig, axes = plt.subplots(1, 2, figsize=(12, 5))\n",
            "\n",
            "sns.histplot(df_test['Faithfulness Score'], bins=10, kde=True, ax=axes[0])\n",
            "axes[0].set_title('Faithfulness Score Distribution')\n",
            "\n",
            "sns.histplot(df_test['Hallucination Score'], bins=10, kde=True, ax=axes[1])\n",
            "axes[1].set_title('Hallucination Score Distribution')\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Run Duration"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "print(f\"Average Run Duration: {df_test['Run Duration'].mean():.2f} seconds\")\n",
            "sns.histplot(df_test['Run Duration'], bins=20, kde=True)\n",
            "plt.title('Run Duration Distribution')\n",
            "plt.show()"
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
        if "## Test Run Analysis: GPT-oss20B" in "".join(cell.get('source', [])):
            section_exists = True
            break
    
    if not section_exists:
        nb['cells'].extend(new_cells)
        
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1)
        print("Successfully appended analysis cells to notebook.")
    else:
        print("Analysis section already exists. Skipping append.")

except Exception as e:
    print(f"Error modifying notebook: {e}")
