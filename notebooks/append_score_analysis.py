import json
import os

nb_path = 'notebooks/financebench_eda.ipynb'

# Define the new cells to append
new_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Deep Dive: Faithfulness & Hallucination Scores\n",
            "\n",
            "Detailed analysis of how Faithfulness and Hallucination scores correlate with test status and question categories."
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Scores vs Test Status"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "fig, axes = plt.subplots(1, 2, figsize=(14, 6))\n",
            "\n",
            "sns.boxplot(x='Status', y='Faithfulness Score', data=df_merged, ax=axes[0])\n",
            "axes[0].set_title('Faithfulness Score by Status')\n",
            "\n",
            "sns.boxplot(x='Status', y='Hallucination Score', data=df_merged, ax=axes[1])\n",
            "axes[1].set_title('Hallucination Score by Status')\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Scores by Question Type"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "fig, axes = plt.subplots(2, 1, figsize=(12, 12))\n",
            "\n",
            "sns.boxplot(x='Faithfulness Score', y='question_type', data=df_merged, ax=axes[0])\n",
            "axes[0].set_title('Faithfulness Score by Question Type')\n",
            "\n",
            "sns.boxplot(x='Hallucination Score', y='question_type', data=df_merged, ax=axes[1])\n",
            "axes[1].set_title('Hallucination Score by Question Type')\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Scores by Question Reasoning"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "fig, axes = plt.subplots(2, 1, figsize=(12, 14))\n",
            "\n",
            "sns.boxplot(x='Faithfulness Score', y='question_reasoning', data=df_merged, ax=axes[0])\n",
            "axes[0].set_title('Faithfulness Score by Question Reasoning')\n",
            "\n",
            "sns.boxplot(x='Hallucination Score', y='question_reasoning', data=df_merged, ax=axes[1])\n",
            "axes[1].set_title('Hallucination Score by Question Reasoning')\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Faithfulness vs Hallucination Correlation"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "plt.figure(figsize=(8, 6))\n",
            "sns.scatterplot(x='Faithfulness Score', y='Hallucination Score', hue='Status', data=df_merged, alpha=0.7)\n",
            "plt.title('Faithfulness vs. Hallucination Score')\n",
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
        if "## Deep Dive: Faithfulness & Hallucination Scores" in "".join(cell.get('source', [])):
            section_exists = True
            break
    
    if not section_exists:
        nb['cells'].extend(new_cells)
        
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1)
        print("Successfully appended score analysis cells to notebook.")
    else:
        print("Score analysis section already exists. Skipping append.")

except Exception as e:
    print(f"Error modifying notebook: {e}")
