import json
import os

nb_path = 'notebooks/financebench_eda.ipynb'

# Define the new cells to append
new_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Refined Hallucination Analysis\n",
            "\n",
            "Handling missing values for Hallucination Score (treating NaN as 0.0) and re-evaluating performance.  \n",
            "**Note:** For Hallucination Score, a **lower** value indicates better performance (fewer hallucinations)."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Fill NaN values in 'Hallucination Score' with 0.0\n",
            "df_merged['Hallucination Score'] = df_merged['Hallucination Score'].fillna(0.0)\n",
            "print(\"Filled NaN values in 'Hallucination Score' with 0.0\")\n"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Re-calculate mean scores with filled values\n",
            "refined_mean_scores = df_merged.groupby('question_type')[['Faithfulness Score', 'Hallucination Score']].mean()\n",
            "print(\"Refined Mean Scores by Question Type (Lower Hallucination is Better):\")\n",
            "print(refined_mean_scores)\n"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Visualize refined scores\n",
            "refined_mean_scores.plot(kind='bar', figsize=(10, 6))\n",
            "plt.title('Refined Mean Scores by Question Type')\n",
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
        if "## Refined Hallucination Analysis" in "".join(cell.get('source', [])):
            section_exists = True
            break
    
    if not section_exists:
        nb['cells'].extend(new_cells)
        
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1)
        print("Successfully appended hallucination refinement cells to notebook.")
    else:
        print("Hallucination refinement section already exists. Skipping append.")

except Exception as e:
    print(f"Error modifying notebook: {e}")
