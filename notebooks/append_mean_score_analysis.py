import json
import os

nb_path = 'notebooks/financebench_eda.ipynb'

# Define the new cells to append
new_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Mean Scores by Question Type\n",
            "\n",
            "Calculating average Faithfulness and Hallucination scores for each question type to identify performance trends."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Calculate mean scores\n",
            "mean_scores = df_merged.groupby('question_type')[['Faithfulness Score', 'Hallucination Score']].mean().sort_values(by='Faithfulness Score', ascending=False)\n",
            "print(\"Mean Scores by Question Type:\")\n",
            "print(mean_scores)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Visualize mean scores\n",
            "mean_scores.plot(kind='bar', figsize=(10, 6))\n",
            "plt.title('Mean Faithfulness and Hallucination Scores by Question Type')\n",
            "plt.ylabel('Score')\n",
            "plt.xlabel('Question Type')\n",
            "plt.xticks(rotation=45)\n",
            "plt.legend(loc='best')\n",
            "plt.tight_layout()\n",
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
        if "## Mean Scores by Question Type" in "".join(cell.get('source', [])):
            section_exists = True
            break
    
    if not section_exists:
        nb['cells'].extend(new_cells)
        
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1)
        print("Successfully appended mean score analysis cells to notebook.")
    else:
        print("Mean score analysis section already exists. Skipping append.")

except Exception as e:
    print(f"Error modifying notebook: {e}")
