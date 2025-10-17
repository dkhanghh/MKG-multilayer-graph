{
    "instruction": "You are an expert in entity standardization and disambiguation. Given extracted named entities from a text, provide their official, standardized names to eliminate ambiguity and ensure proper schema type categorization. This phase ONLY standardizes entities and assigns correct types - NO relationship extraction.",
    "guidelines": [
        "SCHEMA TYPE VALIDATION:",
        "1. Validate each entity against the schema and assign the correct type (EntityType or ConceptType)",
        "2. ConceptType entities are abstract categories (Industry, Technology, Category, etc.)",
        "3. EntityType entities are concrete instances (Company, Person, FinancialMetric, Product, etc.)",
        "4. If the original category is incorrect based on schema, correct it",
        "5. For entities that belong to a ConceptType, note the properties that will be used for isA relationships",
        "",
        "ENTITY STANDARDIZATION RULES:",
        "1. Provide the MOST OFFICIAL and widely recognized name for each entity",
        "2. Use context from the input text to disambiguate unclear references",
        "3. For abbreviations, expand to full official names (e.g., 'MSFT' → 'Microsoft Corporation')",
        "4. For organizations, use complete official names",
        "5. For locations, use standard geographic names",
        "6. For people, use full proper names when identifiable from context",
        "7. Generate meaningful IDs using lowercase, underscores (e.g., 'microsoft_corp', 'technology_industry')",
        "",
        "CONCEPTTYPE PROPERTY IDENTIFICATION:",
        "1. For EntityTypes with properties referencing ConceptTypes (e.g., Company.industry: Industry):",
        "   - Standardize both the entity and the concept it belongs to",
        "   - Add a 'properties' field noting ConceptType values (e.g., {'industry': 'Technology'})",
        "2. These properties will be used to create isA relationships in the next phase",
        "",
        "DISAMBIGUATION PRINCIPLES:",
        "1. Entities with the same meaning must have ONE consistent official name and ID",
        "2. Use your knowledge to resolve ambiguous references based on context",
        "3. Correct the category based on schema validation",
        "4. If an entity cannot be standardized confidently, keep the original name",
        "5. Focus on factual, verifiable official names",
        "6. Use the same ID for entities that refer to the same real-world object",
        "",
        "QUALITY STANDARDS:",
        "1. Ensure official names are accurate and widely recognized",
        "2. Maintain consistency in naming conventions",
        "3. Use proper capitalization and formatting for official names",
        "4. Validate all categories against the provided schema",
        "",
        "DESCRIPTION GUIDELINES:",
        "1. Enhance or refine descriptions from the named entities",
        "2. Include key identifying information about the standardized entity",
        "3. Use factual, concise descriptions (1-2 sentences)",
        "4. Incorporate context that helps distinguish similar entities",
        "",
        "IMPORTANT: This phase does NOT output relationships. Relationships will be extracted in the next phase (TRP).",
        "",
        "FINANCIAL ENTITY STANDARDIZATION:",
        "For financial documents, apply these specific rules:",
        "1. **Company Names**: Use complete legal name as it appears in SEC filings",
        "   - Example: 'American Water Works' → 'American Water Works Company, Inc.'",
        "   - Include 'Inc.', 'LLC', 'Corp.', 'Ltd.' when present",
        "2. **Financial Statements**: Standardize to official accounting terminology",
        "   - 'Balance Sheet' → 'Consolidated Balance Sheet'",
        "   - 'Income Statement' → 'Consolidated Statement of Operations'",
        "   - 'Cash Flow Statement' → 'Consolidated Statement of Cash Flows'",
        "3. **Regulatory Filings**: Format as 'Company YEAR Filing-Type'",
        "   - Example: '2022 10-K' → 'American Water Works 2022 Form 10-K'",
        "   - Include company name for clarity and proper identification",
        "4. **Industry Names**: Use standard industry classification names",
        "   - Match to NAICS/SIC categories when possible",
        "   - Example: 'water utility' → 'Water Utilities', 'tech' → 'Technology'",
        "5. **ID Generation for Financial Entities**:",
        "   - Company: Use ticker if known, otherwise sanitized name: 'company_ticker' or 'company_name_lowercase'",
        "   - FinancialStatement: 'fs_{company}_{type}_{year}': 'fs_aww_balance_sheet_2022'",
        "   - RegulatoryFiling: 'filing_{company}_{year}_{type}': 'filing_aww_2022_10k'",
        "   - Industry: 'industry_{name}_lowercase': 'industry_water_utilities'",
        "6. **Properties for Taxonomies**:",
        "   - Company entities should include: {\"industry\": \"IndustryName\", \"ticker\": \"TICK\"}",
        "   - FinancialStatement: {\"statementType\": \"Balance Sheet\", \"fiscalYear\": \"2022\"}",
        "   - RegulatoryFiling: {\"filingType\": \"10-K\", \"fiscalYear\": \"2022\"}"
    ],
    "schema": {{ schema }},
    "examples": [
        {
            "input": "Apple reported Q4 revenue of $90 billion in the technology sector, competing with Microsoft in enterprise software.",
            "named_entities": [
                {"name": "Apple", "category": "Company", "description": "A technology company that reported Q4 revenue."},
                {"name": "Q4 revenue", "category": "FinancialMetric", "description": "A financial performance metric."},
                {"name": "Technology", "category": "Industry", "description": "An industry category."},
                {"name": "90 billion", "category": "Revenue", "description": "A revenue amount."},
                {"name": "Microsoft", "category": "Company", "description": "A technology company."},
                {"name": "Enterprise Software", "category": "Industry", "description": "A market category."}
            ],
            "output": {
                "entities": [
                    {
                        "name": "Apple",
                        "id": "apple_inc",
                        "category": "Company",
                        "official_name": "Apple Inc.",
                        "description": "A multinational technology company headquartered in Cupertino, California.",
                        "properties": {"industry": "Technology"}
                    },
                    {
                        "name": "Q4 revenue",
                        "id": "q4_revenue_apple_2023",
                        "category": "FinancialMetric",
                        "official_name": "Apple Q4 2023 Revenue",
                        "description": "Apple's revenue for the fourth quarter, representing financial performance."
                    },
                    {
                        "name": "Technology",
                        "id": "technology_industry",
                        "category": "Industry",
                        "official_name": "Technology Industry",
                        "description": "An abstract industry category for companies developing technological products and services."
                    },
                    {
                        "name": "90 billion",
                        "id": "revenue_90b",
                        "category": "Revenue",
                        "official_name": "$90 Billion Revenue",
                        "description": "A specific revenue amount of ninety billion US dollars."
                    },
                    {
                        "name": "Microsoft",
                        "id": "microsoft_corp",
                        "category": "Company",
                        "official_name": "Microsoft Corporation",
                        "description": "A multinational technology company that develops software, hardware, and cloud services.",
                        "properties": {"industry": "Technology"}
                    },
                    {
                        "name": "Enterprise Software",
                        "id": "enterprise_software_industry",
                        "category": "Industry",
                        "official_name": "Enterprise Software Industry",
                        "description": "An abstract market category for business-focused software solutions and platforms."
                    }
                ]
            }
        },
        {
            "input": "American Water Works Company, Inc. reported in its 2022 Form 10-K Consolidated Balance Sheet...",
            "named_entities": [
                {"name": "American Water Works Company, Inc.", "category": "Company", "description": "A water utility company that filed a 2022 Form 10-K."},
                {"name": "Consolidated Balance Sheet", "category": "FinancialStatement", "description": "A balance sheet showing assets, liabilities, and equity."},
                {"name": "2022 Form 10-K", "category": "RegulatoryFiling", "description": "An annual report filed with the SEC."},
                {"name": "Water Utilities", "category": "Industry", "description": "An industry category for water services."}
            ],
            "output": {
                "entities": [
                    {
                        "name": "American Water Works Company, Inc.",
                        "id": "aww",
                        "category": "Company",
                        "official_name": "American Water Works Company, Inc.",
                        "description": "The largest publicly traded water and wastewater utility company in the United States, serving over 14 million people.",
                        "properties": {"industry": "Water Utilities", "ticker": "AWK"}
                    },
                    {
                        "name": "Consolidated Balance Sheet",
                        "id": "fs_aww_balance_sheet_2022",
                        "category": "FinancialStatement",
                        "official_name": "American Water Works 2022 Consolidated Balance Sheet",
                        "description": "Balance sheet presenting the company's financial position as of December 31, 2022, with comparative period December 31, 2021.",
                        "properties": {"statementType": "Balance Sheet", "fiscalYear": "2022"}
                    },
                    {
                        "name": "2022 Form 10-K",
                        "id": "filing_aww_2022_10k",
                        "category": "RegulatoryFiling",
                        "official_name": "American Water Works Company, Inc. 2022 Form 10-K",
                        "description": "Annual report filed with the SEC for fiscal year ended December 31, 2022, containing audited financial statements and management discussion.",
                        "properties": {"filingType": "10-K", "fiscalYear": "2022"}
                    },
                    {
                        "name": "Water Utilities",
                        "id": "industry_water_utilities",
                        "category": "Industry",
                        "official_name": "Water Utilities Industry",
                        "description": "An abstract industry category for companies providing water distribution and wastewater treatment services."
                    }
                ]
            }
        }
    ],
    "input_text": "{{ input_text }}",
    "named_entities": {{ named_entities }},
    "output_format": "Return a JSON object with an 'entities' array containing objects with 'name', 'id', 'category', 'official_name', 'description', and optional 'properties' fields. The 'properties' field should contain ConceptType values for entities that belong to taxonomies. Example: {'entities': [{'name': 'Original Name', 'id': 'unique_id', 'category': 'EntityType', 'official_name': 'Official Standardized Name', 'description': 'Brief factual description of the entity', 'properties': {'conceptType_property': 'ConceptValue'}}]}"
}