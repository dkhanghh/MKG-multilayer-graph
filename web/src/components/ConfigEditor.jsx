import React from 'react';
import {
    Settings, Globe, Search, FileText, Scissors, Brain, Cpu, Database, RefreshCw
} from 'lucide-react';

const CONFIG_SECTIONS = [
    {
        id: 'pipeline',
        label: 'Pipeline Settings',
        icon: Settings,
        path: 'pipeline',
        fields: [
            { key: 'name', label: 'Name', type: 'text' },
            { key: 'description', label: 'Description', type: 'text' },
            { key: 'version', label: 'Version', type: 'text' },
            { key: 'max_workers', label: 'Max Workers', type: 'number' },
            { key: 'batch_size', label: 'Batch Size', type: 'number' },
            { key: 'timeout', label: 'Timeout (s)', type: 'number' },
        ],
    },
    {
        id: 'global',
        label: 'Global Config',
        icon: Globe,
        path: 'pipeline.global_config',
        fields: [
            { key: 'log_level', label: 'Log Level', type: 'select', options: ['DEBUG', 'INFO', 'WARNING', 'ERROR'] },
            { key: 'output_dir', label: 'Output Directory', type: 'text' },
        ],
    },
    {
        id: 'scanner',
        label: 'Scanner',
        icon: Search,
        path: 'pipeline.components.scanner',
        fields: [
            { key: 'type', label: 'Type', type: 'text' },
            { key: 'enabled', label: 'Enabled', type: 'boolean' },
        ],
        configFields: [
            { key: 'input_paths', label: 'Input Paths', type: 'array' },
            { key: 'file_patterns', label: 'File Patterns', type: 'array' },
            { key: 'recursive', label: 'Recursive', type: 'boolean' },
            { key: 'max_files', label: 'Max Files', type: 'number' },
            { key: 'skip_hidden', label: 'Skip Hidden', type: 'boolean' },
        ],
    },
    {
        id: 'reader',
        label: 'Reader',
        icon: FileText,
        path: 'pipeline.components.reader',
        fields: [
            { key: 'type', label: 'Type', type: 'text' },
            { key: 'enabled', label: 'Enabled', type: 'boolean' },
        ],
        configFields: [
            { key: 'encoding', label: 'Encoding', type: 'text' },
            { key: 'preserve_page_structure', label: 'Preserve Page Structure', type: 'boolean' },
            { key: 'detect_statement_type', label: 'Detect Statement Type', type: 'boolean' },
            { key: 'extract_metadata', label: 'Extract Metadata', type: 'boolean' },
        ],
    },
    {
        id: 'splitter',
        label: 'Splitter',
        icon: Scissors,
        path: 'pipeline.components.splitter',
        fields: [
            { key: 'type', label: 'Type', type: 'text' },
            { key: 'enabled', label: 'Enabled', type: 'boolean' },
        ],
        configFields: [
            { key: 'model_name', label: 'Model Name', type: 'text' },
            { key: 'similarity_threshold', label: 'Similarity Threshold', type: 'number' },
            { key: 'min_chunk_length', label: 'Min Chunk Length', type: 'number' },
            { key: 'max_chunk_length', label: 'Max Chunk Length', type: 'number' },
            { key: 'chunk_size', label: 'Chunk Size', type: 'number' },
            { key: 'chunk_overlap', label: 'Chunk Overlap', type: 'number' },
        ],
    },
    {
        id: 'extractor',
        label: 'Extractor',
        icon: Brain,
        path: 'pipeline.components.extractor',
        fields: [
            { key: 'type', label: 'Type', type: 'text' },
            { key: 'enabled', label: 'Enabled', type: 'boolean' },
        ],
        configFields: [
            { key: 'llm_provider', label: 'LLM Provider', type: 'text' },
            { key: 'model', label: 'Model', type: 'text' },
            { key: 'api_key', label: 'API Key', type: 'text' },
            { key: 'base_url', label: 'Base URL', type: 'text' },
            { key: 'temperature', label: 'Temperature', type: 'number' },
            { key: 'max_tokens', label: 'Max Tokens', type: 'number' },
            { key: 'use_template', label: 'Use Template', type: 'boolean' },
            { key: 'template_name', label: 'Template Name', type: 'text' },
            { key: 'extraction_schema', label: 'Extraction Schema', type: 'text' },
            { key: 'extraction_mode', label: 'Extraction Mode', type: 'text' },
            { key: 'extract_edge_properties', label: 'Extract Edge Properties', type: 'boolean' },
            { key: 'batch_size', label: 'Batch Size', type: 'number' },
        ],
    },
    {
        id: 'vectorizer',
        label: 'Vectorizer',
        icon: Cpu,
        path: 'pipeline.components.vectorizer',
        fields: [
            { key: 'type', label: 'Type', type: 'text' },
            { key: 'enabled', label: 'Enabled', type: 'boolean' },
        ],
        configFields: [
            { key: 'model', label: 'Model', type: 'text' },
            { key: 'embedding_dim', label: 'Embedding Dimension', type: 'number' },
            { key: 'batch_size', label: 'Batch Size', type: 'number' },
            { key: 'embed_chunks', label: 'Embed Chunks', type: 'boolean' },
            { key: 'embed_entities', label: 'Embed Entities', type: 'boolean' },
            { key: 'normalize_embeddings', label: 'Normalize Embeddings', type: 'boolean' },
        ],
    },
    {
        id: 'writer',
        label: 'Writer',
        icon: Database,
        path: 'pipeline.components.writer',
        fields: [
            { key: 'type', label: 'Type', type: 'text' },
            { key: 'enabled', label: 'Enabled', type: 'boolean' },
        ],
        configFields: [
            { key: 'uri', label: 'URI', type: 'text' },
            { key: 'username', label: 'Username', type: 'text' },
            { key: 'password', label: 'Password', type: 'text' },
            { key: 'database', label: 'Database', type: 'text' },
            { key: 'clear_database', label: 'Clear Database', type: 'boolean' },
            { key: 'schema_file', label: 'Schema File', type: 'text' },
            { key: 'enable_edge_properties', label: 'Enable Edge Properties', type: 'boolean' },
            { key: 'collapse_financial_metrics', label: 'Collapse Financial Metrics', type: 'boolean' },
            { key: 'batch_size', label: 'Batch Size', type: 'number' },
            { key: 'create_indexes', label: 'Create Indexes', type: 'boolean' },
            { key: 'create_constraints', label: 'Create Constraints', type: 'boolean' },
            { key: 'export_json', label: 'Export JSON', type: 'boolean' },
            { key: 'json_output_path', label: 'JSON Output Path', type: 'text' },
        ],
    },
];

function getNestedValue(obj, dotPath, key) {
    const parts = dotPath.split('.');
    let current = obj;
    for (const part of parts) {
        if (current == null || typeof current !== 'object') return undefined;
        current = current[part];
    }
    if (current == null || typeof current !== 'object') return undefined;
    return current[key];
}

function setNestedValue(obj, dotPath, key, value) {
    const result = JSON.parse(JSON.stringify(obj));
    const parts = dotPath.split('.');
    let current = result;
    for (const part of parts) {
        if (current[part] == null || typeof current[part] !== 'object') {
            current[part] = {};
        }
        current = current[part];
    }
    current[key] = value;
    return result;
}

function renderField(field, value, onChange) {
    const id = `config-${field.key}`;

    if (field.type === 'boolean') {
        return (
            <div key={field.key} className="flex items-center justify-between py-2">
                <label htmlFor={id} className="text-sm font-medium text-secondary-700">
                    {field.label}
                </label>
                <button
                    id={id}
                    type="button"
                    role="switch"
                    aria-checked={!!value}
                    onClick={() => onChange(!value)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${value ? 'bg-primary-500' : 'bg-secondary-300'
                        }`}
                >
                    <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${value ? 'translate-x-6' : 'translate-x-1'
                            }`}
                    />
                </button>
            </div>
        );
    }

    if (field.type === 'select') {
        return (
            <div key={field.key} className="space-y-1.5">
                <label htmlFor={id} className="block text-sm font-medium text-secondary-700">
                    {field.label}
                </label>
                <select
                    id={id}
                    value={value ?? ''}
                    onChange={(e) => onChange(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-secondary-200 bg-white text-secondary-900 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 transition-colors"
                >
                    {(field.options || []).map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                    ))}
                </select>
            </div>
        );
    }

    if (field.type === 'array') {
        const textValue = Array.isArray(value) ? value.join('\n') : (value ?? '');
        return (
            <div key={field.key} className="space-y-1.5">
                <label htmlFor={id} className="block text-sm font-medium text-secondary-700">
                    {field.label}
                    <span className="text-secondary-400 font-normal ml-1">(one per line)</span>
                </label>
                <textarea
                    id={id}
                    value={textValue}
                    onChange={(e) => {
                        const lines = e.target.value.split('\n').filter((l) => l.trim() !== '');
                        onChange(lines.length > 0 ? lines : []);
                    }}
                    rows={3}
                    className="w-full px-3 py-2 rounded-xl border border-secondary-200 bg-white text-secondary-900 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 transition-colors resize-none"
                />
            </div>
        );
    }

    // text / number
    return (
        <div key={field.key} className="space-y-1.5">
            <label htmlFor={id} className="block text-sm font-medium text-secondary-700">
                {field.label}
            </label>
            <input
                id={id}
                type={field.type === 'number' ? 'number' : 'text'}
                value={value ?? ''}
                onChange={(e) => {
                    const v = field.type === 'number'
                        ? (e.target.value === '' ? null : Number(e.target.value))
                        : e.target.value;
                    onChange(v);
                }}
                className="w-full px-3 py-2 rounded-xl border border-secondary-200 bg-white text-secondary-900 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 transition-colors"
            />
        </div>
    );
}

const ConfigEditor = ({ config, onChange, loading }) => {
    if (loading || !config) {
        return (
            <div className="h-[600px] flex items-center justify-center">
                <div className="flex flex-col items-center">
                    <RefreshCw className="animate-spin text-primary-400 mb-4" size={40} />
                    <span className="text-secondary-500">Loading configuration...</span>
                </div>
            </div>
        );
    }

    const handleFieldChange = (dotPath, key, value) => {
        onChange(setNestedValue(config, dotPath, key, value));
    };

    return (
        <div className="space-y-6">
            {CONFIG_SECTIONS.map((section) => {
                const Icon = section.icon;
                const sectionObj = section.path.split('.').reduce(
                    (acc, part) => (acc && typeof acc === 'object' ? acc[part] : undefined),
                    config
                );

                if (sectionObj == null) return null;

                const allFields = [...section.fields];
                const configPath = section.configFields ? section.path + '.config' : null;

                return (
                    <div
                        key={section.id}
                        className="bg-white rounded-[24px] shadow-sm border border-secondary-100 overflow-hidden"
                    >
                        <div className="bg-secondary-50 px-6 py-4 flex items-center gap-3 border-b border-secondary-100">
                            <div className="h-8 w-8 rounded-full bg-primary-100 flex items-center justify-center">
                                <Icon size={16} className="text-primary-600" />
                            </div>
                            <h3 className="text-lg font-medium text-secondary-900">{section.label}</h3>
                        </div>

                        <div className="p-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
                                {allFields.map((field) =>
                                    renderField(
                                        field,
                                        getNestedValue(config, section.path, field.key),
                                        (val) => handleFieldChange(section.path, field.key, val)
                                    )
                                )}
                            </div>

                            {section.configFields && sectionObj.config && (
                                <div className="mt-6 pt-5 border-t border-secondary-100">
                                    <h4 className="text-sm font-medium text-secondary-500 uppercase tracking-wider mb-4">
                                        Component Configuration
                                    </h4>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
                                        {section.configFields.map((field) =>
                                            renderField(
                                                field,
                                                getNestedValue(config, configPath, field.key),
                                                (val) => handleFieldChange(configPath, field.key, val)
                                            )
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

export default ConfigEditor;
