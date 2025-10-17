{
    "instruction": "You are an expert in named entity recognition. Extract entities from the input text, focusing on accurate entity names and correct categorization based on the schema. Distinguish between concrete EntityTypes and abstract ConceptTypes.",
    "guidelines": [
        "SCHEMA TYPE AWARENESS:",
        "1. ConceptType: Abstract categories used for taxonomy (e.g., Industry, Technology, Category)",
        "   - These form hierarchies and classifications",
        "   - Extract when text mentions abstract concepts that classify other entities",
        "2. EntityType: Concrete, specific entities that exist in the domain (e.g., Company, Person, FinancialMetric)",
        "   - These are the main entities with properties and relationships",
        "   - Extract when text mentions specific, tangible entities",
        "",
        "ENTITY NAME RULES:",
        "1. Use the EXACT name as it appears in the text (preserve original spelling and format)",
        "2. For compound terms, use the complete meaningful phrase (e.g., 'machine learning', not just 'learning')",
        "3. For proper nouns, maintain original capitalization (e.g., 'John Smith', 'Microsoft')",
        "4. Extract the most specific form of the entity name mentioned",
        "",
        "CATEGORIZATION RULES:",
        "1. Choose the MOST APPROPRIATE category from the provided schema (EntityType or ConceptType)",
        "2. For EntityTypes with properties referencing ConceptTypes, extract BOTH:",
        "   - The concrete entity (e.g., 'Apple' as Company)",
        "   - The abstract concept it belongs to (e.g., 'Technology' as Industry)",
        "3. If uncertain between categories, pick the primary/dominant one",
        "4. Only use the entity types provided in the schema",
        "5. If an entity doesn't clearly fit any category, use 'Others' if available",
        "",
        "EXTRACTION PRINCIPLES:",
        "1. Extract only entities explicitly mentioned in the text",
        "2. Extract both concrete entities (EntityType) and abstract concepts (ConceptType)",
        "3. For hierarchical terms, extract both the specific entity and its category",
        "4. Each entity must have a meaningful, specific name",
        "",
        "DESCRIPTION RULES:",
        "1. Provide a brief, factual description for each entity (1-2 sentences)",
        "2. Include key attributes, roles, or context from the text",
        "3. For ConceptTypes, describe their taxonomic role",
        "4. For EntityTypes, focus on information that helps identify and understand the entity",
        "5. Keep descriptions concise but informative",
        "",
        "FINANCIAL DOCUMENT EXTRACTION (IMPORTANT):",
        "When extracting from financial statements (10-K, 10-Q, balance sheets, income statements):",
        "1. **Company**: Extract the reporting company name (e.g., 'American Water Works Company, Inc.')",
        "2. **FinancialStatement**: Extract statement type (e.g., 'Consolidated Balance Sheet', 'Statement of Operations')",
        "3. **RegulatoryFiling**: Extract filing type if mentioned (e.g., '10-K', '10-Q', 'Form 8-K')",
        "4. **DO NOT extract individual line items** (Total Assets, Cash, Revenue, etc.) as entities",
        "   - These will be extracted as edge properties in later stages",
        "   - Exception: If a metric is discussed as a concept (e.g., 'debt-to-equity ratio as a measure')",
        "5. **DO NOT extract numerical values** alone (e.g., '$27,787 million') as entities",
        "6. **DO NOT extract time periods** (e.g., 'December 31, 2022') as entities",
        "   - Time periods become edge properties, not separate entities",
        "7. **Industry**: Extract if company's industry is mentioned (e.g., 'Utilities', 'Water Utilities')",
        "8. Focus on high-level entities: companies, documents, statement types, industries",
        "",
        "WHAT TO EXTRACT FROM FINANCIAL STATEMENTS:",
        "✓ Company names (reporting entity)",
        "✓ Financial statement types (Balance Sheet, Income Statement, Cash Flow)",
        "✓ Regulatory filing types (10-K, 10-Q, 8-K, DEF 14A)",
        "✓ Industry categories if mentioned",
        "✓ Executive names if mentioned",
        "✓ Subsidiary company names if mentioned",
        "✗ Individual balance sheet line items (assets, liabilities, equity)",
        "✗ Specific financial metrics as entities (revenue, profit, expenses)",
        "✗ Numerical values without entity context",
        "✗ Date/time periods as entities"
    ],
    "schema": {{ schema }},
    "examples": [
        {
            "input": "Apple reported Q4 revenue of $90 billion in the technology sector.",
            "output": [
                {"name": "Apple", "category": "Company", "description": "A technology company that reported Q4 revenue of $90 billion."},
                {"name": "Q4 revenue", "category": "FinancialMetric", "description": "A financial performance metric representing revenue for the fourth quarter."},
                {"name": "Technology", "category": "Industry", "description": "An abstract industry category that classifies companies like Apple."},
                {"name": "90 billion", "category": "Revenue", "description": "The specific revenue amount reported by Apple in Q4."}
            ]
        },
        {
            "input": "Microsoft's Azure cloud platform competes with Amazon Web Services in the enterprise software market.",
            "output": [
                {"name": "Microsoft", "category": "Company", "description": "A technology company that operates the Azure cloud platform."},
                {"name": "Azure", "category": "Product", "description": "A cloud computing platform operated by Microsoft."},
                {"name": "Amazon Web Services", "category": "Product", "description": "A cloud computing platform that competes with Microsoft Azure."},
                {"name": "Enterprise Software", "category": "Industry", "description": "An abstract market category for business-focused software solutions."}
            ]
        },
        {
            "input": "Dr. Sarah Johnson from Stanford University published research on neural networks.",
            "output": [
                {"name": "Sarah Johnson", "category": "Person", "description": "A doctor affiliated with Stanford University who published research on neural networks."},
                {"name": "Stanford University", "category": "Organization", "description": "An educational institution where Dr. Sarah Johnson is affiliated."},
                {"name": "neural networks", "category": "Technology", "description": "An abstract technology category representing a machine learning technique."}
            ]
        },
        {
            "input": "American Water Works Company, Inc. reported in its 2022 Form 10-K Consolidated Balance Sheet that Total assets were $27,787 million as of December 31, 2022, compared to $26,075 million as of December 31, 2021. The company operates in the water utilities industry.",
            "output": [
                {"name": "American Water Works Company, Inc.", "category": "Company", "description": "A water utility company that filed a 2022 Form 10-K with consolidated financial statements showing total assets of $27.8 billion."},
                {"name": "Consolidated Balance Sheet", "category": "FinancialStatement", "description": "A financial statement showing the company's assets, liabilities, and equity for comparative periods ending December 31, 2022 and 2021."},
                {"name": "2022 Form 10-K", "category": "RegulatoryFiling", "description": "An annual report filed with the SEC containing audited financial statements for fiscal year 2022."},
                {"name": "Water Utilities", "category": "Industry", "description": "An abstract industry category for companies providing water and wastewater services."}
            ],
            "note": "DO NOT extract: 'Total assets', '$27,787 million', 'December 31, 2022' - these become edge properties in TRP phase"
        }
    ],
    "input_text": "{{ input_text }}",
    "output_format": "Return a JSON array of objects with 'name', 'category', and 'description' fields. Example: [{'name': 'Entity Name', 'category': 'EntityType', 'description': 'Brief factual description of the entity'}]"
}