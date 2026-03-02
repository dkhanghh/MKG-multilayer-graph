import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import ConfigEditor from '../components/ConfigEditor';
import { Save, RefreshCw, Code, AlertCircle, CheckCircle, Database, Settings, SlidersHorizontal } from 'lucide-react';

const SchemaPage = () => {
    const [activeTab, setActiveTab] = useState('schema');

    // Schema state
    const [config, setConfig] = useState('');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState(null);

    // Pipeline config state
    const [pipelineConfig, setPipelineConfig] = useState(null);
    const [configLoading, setConfigLoading] = useState(false);
    const [configFetched, setConfigFetched] = useState(false);

    useEffect(() => {
        fetchSchema();
    }, []);

    // Lazy-load pipeline config on first tab switch
    useEffect(() => {
        if (activeTab === 'config' && !configFetched) {
            fetchPipelineConfig();
        }
    }, [activeTab, configFetched]);

    const fetchSchema = async () => {
        setLoading(true);
        try {
            const response = await api.get('/pipeline/schema');
            setConfig(response.data.content);
        } catch (error) {
            console.error("Failed to fetch schema", error);
            setMessage({ type: 'error', text: 'Failed to load schema configuration.' });
        }
        setLoading(false);
    };

    const fetchPipelineConfig = async () => {
        setConfigLoading(true);
        try {
            const response = await api.get('/pipeline/config');
            setPipelineConfig(response.data.config);
            setConfigFetched(true);
        } catch (error) {
            console.error("Failed to fetch pipeline config", error);
            setMessage({ type: 'error', text: 'Failed to load pipeline configuration.' });
        }
        setConfigLoading(false);
    };

    const handleSave = async () => {
        setSaving(true);
        setMessage(null);
        try {
            if (activeTab === 'schema') {
                await api.post('/pipeline/schema', { content: config });
                setMessage({ type: 'success', text: 'Schema saved successfully.' });
            } else {
                await api.post('/pipeline/config', { config: pipelineConfig });
                setMessage({ type: 'success', text: 'Pipeline configuration saved successfully.' });
            }
        } catch (error) {
            console.error("Failed to save", error);
            const label = activeTab === 'schema' ? 'schema' : 'pipeline configuration';
            setMessage({ type: 'error', text: `Failed to save ${label}.` });
        }
        setSaving(false);
    };

    const handleReset = () => {
        setMessage(null);
        if (activeTab === 'schema') {
            fetchSchema();
        } else {
            setConfigFetched(false);
            fetchPipelineConfig();
        }
    };

    const isLoading = activeTab === 'schema' ? loading : configLoading;

    return (
        <div className="max-w-7xl mx-auto animate-fade-in py-8 px-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-4xl font-normal text-secondary-900 tracking-tight flex items-center">
                        <Database className="mr-4 text-primary-500" size={36} />
                        Schema & Configuration
                    </h1>
                    <p className="text-secondary-500 mt-2 text-lg">Define entities, relations, and pipeline settings.</p>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={handleReset}
                        className="btn-secondary rounded-full"
                        disabled={isLoading}
                    >
                        <RefreshCw size={18} className={`mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                        Reset
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving || isLoading}
                        className="btn-primary rounded-full shadow-lg shadow-primary-500/30"
                    >
                        <Save size={18} className="mr-2" />
                        {saving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
            </div>

            {/* Tab Bar */}
            <div className="flex items-center gap-2 mb-8">
                <button
                    onClick={() => setActiveTab('schema')}
                    className={`flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium transition-all ${activeTab === 'schema'
                        ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/30'
                        : 'bg-white text-secondary-600 border border-secondary-200 hover:bg-secondary-50'
                        }`}
                >
                    <Code size={16} />
                    Schema
                </button>
                <button
                    onClick={() => setActiveTab('config')}
                    className={`flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium transition-all ${activeTab === 'config'
                        ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/30'
                        : 'bg-white text-secondary-600 border border-secondary-200 hover:bg-secondary-50'
                        }`}
                >
                    <SlidersHorizontal size={16} />
                    Pipeline Config
                </button>
            </div>

            {message && (
                <div className={`p-4 mb-8 rounded-[20px] flex items-center animate-slide-up shadow-sm border ${message.type === 'success'
                    ? 'bg-green-50 border-green-200 text-green-800'
                    : 'bg-red-50 border-red-200 text-red-800'
                    }`}>
                    <div className={`h-8 w-8 rounded-full flex items-center justify-center mr-3 ${message.type === 'success' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
                        }`}>
                        {message.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
                    </div>
                    <span className="font-medium">{message.text}</span>
                </div>
            )}

            {/* Schema Tab */}
            {activeTab === 'schema' && (
                <div className="bg-[#1e1e1e] rounded-[28px] overflow-hidden shadow-xl border border-secondary-300 ring-4 ring-secondary-100">
                    <div className="bg-[#2d2d2d] px-6 py-3 flex items-center justify-between border-b border-[#3e3e3e]">
                        <div className="flex items-center text-gray-300 text-sm font-medium">
                            <Settings size={16} className="mr-2 text-primary-400" />
                            <span className="opacity-80">financebench_spg.schema</span>
                        </div>
                        <div className="flex space-x-2">
                            <div className="w-3 h-3 rounded-full bg-[#ff5f56]"></div>
                            <div className="w-3 h-3 rounded-full bg-[#ffbd2e]"></div>
                            <div className="w-3 h-3 rounded-full bg-[#27c93f]"></div>
                        </div>
                    </div>

                    {loading ? (
                        <div className="h-[600px] flex items-center justify-center bg-[#1e1e1e]">
                            <div className="flex flex-col items-center">
                                <RefreshCw className="animate-spin text-primary-400 mb-4" size={40} />
                                <span className="text-gray-500">Loading configuration...</span>
                            </div>
                        </div>
                    ) : (
                        <div className="relative">
                            <textarea
                                value={config}
                                onChange={(e) => setConfig(e.target.value)}
                                className="w-full h-[650px] p-8 font-mono text-[13px] bg-[#1e1e1e] text-[#d4d4d4] focus:outline-none resize-none leading-relaxed"
                                spellCheck="false"
                                style={{ fontFamily: "'Fira Code', 'Roboto Mono', monospace" }}
                            />
                            <div className="absolute bottom-4 right-4 text-xs text-gray-600 bg-[#2d2d2d] px-3 py-1 rounded-full">
                                SPG
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Config Tab */}
            {activeTab === 'config' && (
                <ConfigEditor
                    config={pipelineConfig}
                    onChange={setPipelineConfig}
                    loading={configLoading}
                />
            )}
        </div>
    );
};

export default SchemaPage;
