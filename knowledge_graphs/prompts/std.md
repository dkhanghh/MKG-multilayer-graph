{
    "instruction": "The `input` field contains a user provided context. The `named_entities` field contains extracted named entities from the context, which may be unclear abbreviations, aliases, or slang. To eliminate ambiguity, please attempt to provide the official names of these entities based on the context and your own knowledge. Note that entities with the same meaning can only have ONE official name. Please respond in the format of a single JSONArray string without any explanation, as shown in the `output` field of the provided example.",
    "example": {
        "input": "American History.When did the political party that favored harsh punishment of southern states after the Civil War, gain control of the House? Republicans regained control of the chamber they had lost in the 2006 midterm elections.",
        "named_entities": [
            {"name": "American", "category": "GeographicLocation"},
            {"name": "political party", "category": "Organization"},
            {"name": "southern states", "category": "GeographicLocation"},
            {"name": "Civil War", "category": "Keyword"},
            {"name": "House", "category": "Organization"},
            {"name": "Republicans", "category": "Organization"},
            {"name": "chamber", "category": "Organization"},
            {"name": "2006 midterm elections", "category": "Date"}
        ],
        "output": [
            {
                "name": "American",
                "category": "GeographicLocation",
                "official_name": "United States of America"
            },
            {
                "name": "political party",
                "category": "Organization",
                "official_name": "Radical Republicans"
            },
            {
                "name": "southern states",
                "category": "GeographicLocation",
                "official_name": "Confederacy"
            },
            {
                "name": "Civil War",
                "category": "Keyword",
                "official_name": "American Civil War"
            },
            {
                "name": "House",
                "category": "Organization",
                "official_name": "United States House of Representatives"
            },
            {
                "name": "Republicans",
                "category": "Organization",
                "official_name": "Republican Party"
            },
            {
                "name": "chamber",
                "category": "Organization",
                "official_name": "United States House of Representatives"
            },
            {
                "name": "midterm elections",
                "category": "Date",
                "official_name": "United States midterm elections"
            }
        ]
    },
    "input": "$input",
    "named_entities": $named_entities
}