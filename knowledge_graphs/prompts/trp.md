{
    "instruction": "You are an expert in relationship extraction for Semantic Property Graphs (SPG). Extract ALL relationships from the input text following a three-priority system: (1) isA taxonomy relationships, (2) schema-defined relationships WITH edge properties, (3) on-the-fly discovered relationships. Use entity IDs from the standardized entity list.",
    "guidelines": [
        "SEMANTIC PROPERTY GRAPH (SPG) PRINCIPLES:",
        "1. SPG edges can have RICH PROPERTIES (edgeProperties) that contain data collapsed from intermediate entities",
        "2. Examples of SPG edge properties:",
        "   - REPORTED_FINANCIALS: {period: 'Q4 2023', revenue: 89500000000, profit: 22956000000, profitMargin: 0.256}",
        "   - OWNS: {ownershipPercent: 0.85, acquiredDate: '2023-05-15', isSubsidiary: true}",
        "   - EMPLOYS: {hireDate: '2020-01-15', salary: 250000, isCurrentEmployee: true}",
        "3. Extract BOTH the relationship AND its properties from text",
        "4. Edge properties eliminate need for intermediate nodes (e.g., no separate Revenue node, revenue is an edge property)",
        "",
        "RELATIONSHIP EXTRACTION PRIORITIES:",
        "",
        "PRIORITY 1a: isA RELATIONSHIPS (Entity Classification)",
        "1. Extract isA relationships for entities with ConceptType properties from STD phase",
        "2. These connect EntityTypes to ConceptTypes (e.g., Company -[isA]-> Industry:Technology)",
        "3. Use 'isA' as the exact relation_type for these relationships",
        "4. Check entity 'properties' field from STD output for ConceptType values",
        "5. Example: If Company has properties: {\"industry\": \"Technology\"}, create:",
        "   {source_id: 'company_id', target_id: 'technology_industry_id', relation_type: 'isA', confidence: 0.95}",
        "6. These are high-confidence relationships (typically 0.9-1.0)",
        "7. isA relationships typically have NO edge properties",
        "",
        "PRIORITY 1b: belongTo RELATIONSHIPS (Concept Taxonomy Hierarchies)",
        "1. Extract belongTo relationships between ConceptType instances to create hierarchies",
        "2. These connect ConceptType -> ConceptType of the SAME type (e.g., Industry:Software -[belongTo]-> Industry:Technology)",
        "3. Use 'belongTo' as the exact relation_type for these relationships",
        "4. Common hierarchies to look for:",
        "   - Industry hierarchies: Software belongTo Technology, CloudComputing belongTo Software",
        "   - Time hierarchies: Q4_2023 belongTo 2023, October_2023 belongTo Q4_2023",
        "   - Geographic hierarchies: California belongTo USA, SanFrancisco belongTo California",
        "   - Role hierarchies: VP_Engineering belongTo CTO, Engineer belongTo VP_Engineering",
        "5. Example: If text mentions 'cloud computing sector of technology industry', create:",
        "   {source_id: 'cloud_computing_industry_id', target_id: 'technology_industry_id', relation_type: 'belongTo', confidence: 0.9, properties: {hierarchyLevel: 1}}",
        "6. These are high-confidence relationships (typically 0.85-0.95)",
        "7. belongTo relationships should include hierarchyLevel edge property (1=direct child, 2=grandchild, etc.)",
        "",
        "PRIORITY 2: SCHEMA-DEFINED RELATIONSHIPS (WITH EDGE PROPERTIES)",
        "1. Extract relationships defined in the schema's 'relations' section",
        "2. Use the EXACT relation_type names from the schema",
        "3. CRITICAL: Extract edge properties (edgeProperties) defined in schema for that relationship",
        "4. Schema edge property examples:",
        "   - REPORTED_FINANCIALS: {period, periodStart, periodEnd, revenue, profit, expenses, assets, liabilities, equity, cashFlow, debtToEquity, profitMargin, confidence}",
        "   - OWNS: {ownershipPercent, acquiredDate, isSubsidiary}",
        "   - EMPLOYS: {hireDate, salary, isCurrentEmployee}",
        "   - OPERATES_IN: {since, revenuePercent, employeeCount}",
        "   - HAS_SEGMENT: {segmentRevenue, segmentProfit, segmentGrowthRate}",
        "5. Extract ALL edge properties mentioned in text for that relationship type",
        "6. Edge properties should be numeric, dates, or categorical values extracted from text",
        "7. Put edge properties in a 'properties' field in the relationship object",
        "8. These are medium to high confidence (0.7-0.95) based on text evidence",
        "9. Only extract if explicitly stated or strongly implied in text",
        "",
        "PRIORITY 3: ON-THE-FLY RELATIONSHIPS",
        "1. Extract relationships NOT in schema but meaningful from context",
        "2. Create natural, descriptive relation_types",
        "3. Mark these with lower confidence scores (0.5-0.8) to indicate discovery",
        "4. Examples: 'partneredWith', 'acquiredBy', 'investedIn', 'developedBy'",
        "5. Can include edge properties if contextual data is available",
        "6. Only extract if clearly stated in text",
        "",
        "GENERAL EXTRACTION RULES:",
        "1. CRITICAL: Use ONLY the exact 'id' values from the provided entity_list for source_id and target_id",
        "2. DO NOT create new IDs or modify existing IDs - copy them exactly as provided",
        "3. If an entity is not in the entity_list, DO NOT create a relationship for it",
        "4. Maintain factual accuracy - only extract relationships explicitly stated or clearly implied",
        "5. Each relationship MUST connect entities using their IDs from the entity list",
        "6. Assign confidence scores (0.0-1.0) based on:",
        "   - isA relationships: 0.9-1.0 (from STD properties)",
        "   - Schema relationships: 0.7-0.95 (based on text clarity)",
        "   - On-the-fly relationships: 0.5-0.8 (discovered relationships)",
        "",
        "RELATIONSHIP STRUCTURE:",
        "1. SOURCE_ID: ID of the entity performing an action or being classified",
        "2. TARGET_ID: ID of the target entity, concept, or value",
        "3. RELATION_TYPE: The relationship name ('isA', schema name, or descriptive phrase)",
        "4. CONFIDENCE: Score reflecting relationship certainty and type",
        "",
        "QUALITY STANDARDS:",
        "1. Prioritize completeness - extract ALL three types of relationships",
        "2. Use exact schema relation names when applicable",
        "3. Use 'isA' for all taxonomy relationships",
        "4. Ensure relationships are factually correct and contextually appropriate",
        "5. Skip vague or ambiguous relationships",
        "",
        "FINANCIAL STATEMENT RELATIONSHIP EXTRACTION:",
        "For financial documents, follow these special extraction rules:",
        "1. **REPORTED_FINANCIALS** edge (Company → FinancialStatement):",
        "   - This is the PRIMARY relationship for financial data",
        "   - Extract ALL financial metrics as edge properties (NOT separate entities)",
        "   - Required properties: period, periodEnd (and periodStart if available)",
        "   - Financial metrics: revenue, profit, expenses, assets, liabilities, equity, cashFlow, etc.",
        "   - Metadata: currency, units (e.g., 'millions', 'billions'), confidence",
        "2. **Balance Sheet Extraction**:",
        "   - Edge properties: assets, currentAssets, cashAndEquivalents, propertyPlantEquipment",
        "   - Edge properties: liabilities, currentLiabilities, longTermDebt",
        "   - Edge properties: equity, retainedEarnings, commonStock",
        "3. **Income Statement Extraction**:",
        "   - Edge properties: revenue, grossProfit, operatingIncome, netIncome",
        "   - Edge properties: expenses, operatingExpenses, costOfRevenue",
        "   - Edge properties: profitMargin, operatingMargin",
        "4. **Cash Flow Statement Extraction**:",
        "   - Edge properties: operatingCashFlow, investingCashFlow, financingCashFlow",
        "   - Edge properties: freeCashFlow, cashAndEquivalents",
        "5. **Numerical Value Extraction**:",
        "   - Extract values in their base unit (e.g., if stated as '$27,787 million', extract as 27787000000)",
        "   - OR store with unit metadata: {\"value\": 27787, \"unit\": \"millions\"}",
        "   - Include currency code in properties: {\"currency\": \"USD\"}",
        "6. **Time Period Extraction**:",
        "   - Always extract period as edge property: {\"period\": \"December 31, 2022\"}",
        "   - Convert to ISO format for periodEnd: {\"periodEnd\": \"2022-12-31\"}",
        "   - Include comparative periods if present in text",
        "7. **FILED** edge (Company → RegulatoryFiling):",
        "   - Edge properties: filingDate, filingType, fiscalYear",
        "   - Example: {\"filingDate\": \"2023-02-15\", \"filingType\": \"10-K\", \"fiscalYear\": \"2022\"}"
    ],
    "schema": {{ schema }},
    "examples": [
        {
            "input": "Apple Inc. reported Q4 2023 revenue of $89.5 billion with operating profit of $28.3 billion, representing a 31.6% profit margin. The company's debt-to-equity ratio stands at 1.8. Microsoft Corporation, also in technology, is a major competitor. Apple owns 100% of Beats Electronics, acquired in May 2014.",
            "entity_list": [
                {"name": "Apple", "id": "apple_inc", "category": "Company", "official_name": "Apple Inc.", "description": "A multinational technology company.", "properties": {"industry": "Technology"}},
                {"name": "FinancialStatement Q4 2023", "id": "fs_apple_q4_2023", "category": "FinancialStatement", "official_name": "Apple Q4 2023 Financial Statement", "description": "Financial statement for Q4 2023."},
                {"name": "Technology", "id": "technology_industry", "category": "Industry", "official_name": "Technology Industry", "description": "Abstract industry category for technology companies."},
                {"name": "Microsoft", "id": "microsoft_corp", "category": "Company", "official_name": "Microsoft Corporation", "description": "A multinational technology company.", "properties": {"industry": "Technology"}},
                {"name": "Beats Electronics", "id": "beats_electronics", "category": "Company", "official_name": "Beats Electronics LLC", "description": "An audio products subsidiary of Apple Inc.", "properties": {"industry": "Technology"}}
            ],
            "output": {
                "relationships": [
                    {
                        "source_id": "apple_inc",
                        "target_id": "technology_industry",
                        "relation_type": "isA",
                        "confidence": 0.95,
                        "note": "PRIORITY 1: Taxonomy relationship from STD properties"
                    },
                    {
                        "source_id": "microsoft_corp",
                        "target_id": "technology_industry",
                        "relation_type": "isA",
                        "confidence": 0.95,
                        "note": "PRIORITY 1: Taxonomy relationship from STD properties"
                    },
                    {
                        "source_id": "beats_electronics",
                        "target_id": "technology_industry",
                        "relation_type": "isA",
                        "confidence": 0.95,
                        "note": "PRIORITY 1: Taxonomy relationship from STD properties"
                    },
                    {
                        "source_id": "apple_inc",
                        "target_id": "fs_apple_q4_2023",
                        "relation_type": "REPORTED_FINANCIALS",
                        "confidence": 0.95,
                        "properties": {
                            "period": "Q4 2023",
                            "periodStart": "2023-10-01",
                            "periodEnd": "2023-12-31",
                            "revenue": 89500000000,
                            "profit": 28300000000,
                            "profitMargin": 0.316,
                            "debtToEquity": 1.8
                        },
                        "note": "PRIORITY 2: Schema-defined with SPG edge properties - financial data collapsed into edge"
                    },
                    {
                        "source_id": "apple_inc",
                        "target_id": "beats_electronics",
                        "relation_type": "OWNS",
                        "confidence": 0.9,
                        "properties": {
                            "ownershipPercent": 1.0,
                            "acquiredDate": "2014-05-01",
                            "isSubsidiary": true
                        },
                        "note": "PRIORITY 2: Schema-defined with SPG edge properties - ownership details on edge"
                    },
                    {
                        "source_id": "apple_inc",
                        "target_id": "microsoft_corp",
                        "relation_type": "COMPETES_WITH",
                        "confidence": 0.85,
                        "properties": {
                            "marketOverlap": "technology",
                            "intensity": "high"
                        },
                        "note": "PRIORITY 2: Schema-defined with SPG edge properties"
                    }
                ]
            }
        },
        {
            "input": "American Water Works Company, Inc. reported in its Consolidated Balance Sheet as of December 31, 2022, that Total assets were $27,787 million compared to $26,075 million as of December 31, 2021. Property, plant and equipment (net) was $23,223 million. Current assets totaled $1,250 million, including $85 million in cash and cash equivalents. Total liabilities were $20,094 million, with long-term debt of $10,926 million. Total shareholders' equity was $7,693 million, including retained earnings of $1,267 million. The company operates in the water utilities industry and filed this data in its 2022 Form 10-K.",
            "entity_list": [
                {"name": "American Water Works Company, Inc.", "id": "aww", "category": "Company", "official_name": "American Water Works Company, Inc.", "properties": {"industry": "Water Utilities", "ticker": "AWK"}},
                {"name": "Consolidated Balance Sheet", "id": "fs_aww_balance_sheet_2022", "category": "FinancialStatement", "official_name": "American Water Works 2022 Consolidated Balance Sheet", "properties": {"statementType": "Balance Sheet", "fiscalYear": "2022"}},
                {"name": "2022 Form 10-K", "id": "filing_aww_2022_10k", "category": "RegulatoryFiling", "official_name": "American Water Works Company, Inc. 2022 Form 10-K", "properties": {"filingType": "10-K", "fiscalYear": "2022"}},
                {"name": "Water Utilities", "id": "industry_water_utilities", "category": "Industry", "official_name": "Water Utilities Industry"}
            ],
            "output": {
                "relationships": [
                    {
                        "source_id": "aww",
                        "target_id": "industry_water_utilities",
                        "relation_type": "isA",
                        "confidence": 0.95,
                        "note": "PRIORITY 1a: Taxonomy relationship from STD properties"
                    },
                    {
                        "source_id": "aww",
                        "target_id": "fs_aww_balance_sheet_2022",
                        "relation_type": "REPORTED_FINANCIALS",
                        "confidence": 0.95,
                        "properties": {
                            "period": "December 31, 2022",
                            "periodEnd": "2022-12-31",
                            "comparativePeriod": "December 31, 2021",
                            "comparativePeriodEnd": "2021-12-31",
                            "assets": 27787000000,
                            "comparativeAssets": 26075000000,
                            "propertyPlantEquipment": 23223000000,
                            "currentAssets": 1250000000,
                            "cashAndEquivalents": 85000000,
                            "liabilities": 20094000000,
                            "longTermDebt": 10926000000,
                            "equity": 7693000000,
                            "retainedEarnings": 1267000000,
                            "currency": "USD",
                            "units": "millions",
                            "statementType": "Balance Sheet"
                        },
                        "note": "PRIORITY 2: Schema-defined with SPG edge properties - ALL financial data collapsed into edge properties"
                    },
                    {
                        "source_id": "aww",
                        "target_id": "filing_aww_2022_10k",
                        "relation_type": "FILED",
                        "confidence": 0.9,
                        "properties": {
                            "filingType": "10-K",
                            "fiscalYear": "2022"
                        },
                        "note": "PRIORITY 2: Schema-defined relationship linking company to regulatory filing"
                    }
                ]
            }
        }
    ],
    "input_text": "{{ input_text }}",
    "entity_list": {{ named_entities }},
    "output_format": "Return a JSON object with 'relationships' field containing an array of relationship objects. Extract ALL three types: (1) isA taxonomy relationships from entity properties, (2) schema-defined relationships WITH edge properties using exact schema relation names, (3) on-the-fly discovered relationships. Each relationship must have 'source_id', 'target_id', 'relation_type', 'confidence', and optional 'properties' fields. The 'properties' field contains SPG edge properties (e.g., financial metrics, dates, percentages). Use 'isA' for taxonomy relationships (no properties), exact schema names for schema relationships (with edgeProperties), and descriptive names for discovered relationships. IMPORTANT: source_id and target_id MUST be exact copies of the 'id' values from the entity_list. Example: {'relationships': [{'source_id': 'company_id', 'target_id': 'industry_id', 'relation_type': 'isA', 'confidence': 0.95}, {'source_id': 'company_id', 'target_id': 'financial_statement_id', 'relation_type': 'REPORTED_FINANCIALS', 'confidence': 0.95, 'properties': {'period': 'Q4 2023', 'revenue': 89500000000, 'profit': 28300000000, 'profitMargin': 0.316}}]}"
}    