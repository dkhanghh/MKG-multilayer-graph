{
    "instruction": "You are an expert in named entity recognition. Please extract entities from the input that match the schema definition. If no entities of that type exist, please return an empty list. Please respond in JSON string format. You can refer to the example for extraction guidance.",
    "schema": {{ schema }},
    "example": [
        {
            "input": "Restlessness, delirium, and insomnia may require sedatives, but avoid sedatives that suppress respiration.\n3. Treatment of complications: After antimicrobial treatment, high fever usually subsides within 24 hours or gradually decreases over several days.\nIf temperature drops and then rises again, or remains elevated after 3 days, consider extrapulmonary SP infection.\nTreatment: Connect chest pressure regulation tube + suction machine negative pressure suction bottle device for closed negative pressure suction, which should be continuous. If the lung has not re-expanded after 12 hours, investigate the cause.",
            "output": [
                    {"name": "restlessness", "category": "Symptom"},
                    {"name": "delirium", "category": "Symptom"},
                    {"name": "insomnia", "category": "Symptom"},
                    {"name": "sedatives", "category": "Medicine"},
                    {"name": "extrapulmonary infection", "category": "Disease"},
                    {"name": "chest pressure regulation tube", "category": "MedicalEquipment"},
                    {"name": "suction machine negative pressure suction bottle device", "category": "MedicalEquipment"},
                    {"name": "closed negative pressure suction", "category": "SurgicalOperation"}
                ]
        }
    ],
    "input": "{{ input_text }}"
}