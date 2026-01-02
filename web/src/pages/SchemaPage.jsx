import React, { useState, useEffect } from 'react';
import api from '../api';
import { Save, RefreshCw, Code, AlertCircle, CheckCircle, Database, Settings } from 'lucide-react';

const SchemaPage = () => {
    const [config, setConfig] = useState('');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState(null);

    useEffect(() => {
        fetchConfig();
    }, []);

    const fetchConfig = async () => {
        setLoading(true);
        try {
            const response = await api.get('/pipeline/config');
            setConfig(JSON.stringify(response.data.config, null, 2));
        } catch (error) {
            console.error("Failed to fetch config", error);
            setMessage({ type: 'error', text: 'Failed to load configuration.' });
        }
        setLoading(false);
    };

    const handleSave = async () => {
        setSaving(true);
        setMessage(null);
        try {
            // Validate JSON
            JSON.parse(config);

            await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate network request
            setMessage({ type: 'success', text: 'Configuration saved successfully (Simulation).' });
        } catch (error) {
            setMessage({ type: 'error', text: 'Invalid JSON format.' });
        }
        setSaving(false);
    };

    return (
        <div className="max-w-7xl mx-auto animate-fade-in py-8 px-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
                <div>
                    <h1 className="text-4xl font-normal text-secondary-900 tracking-tight flex items-center">
                        <Database className="mr-4 text-primary-500" size={36} />
                        Schema Configuration
                    </h1>
                    <p className="text-secondary-500 mt-2 text-lg">Define entities, relations, and extraction rules.</p>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={fetchConfig}
                        className="btn-secondary rounded-full"
                        disabled={loading}
                    >
                        <RefreshCw size={18} className={`mr-2 ${loading ? 'animate-spin' : ''}`} />
                        Reset
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving || loading}
                        className="btn-primary rounded-full shadow-lg shadow-primary-500/30"
                    >
                        <Save size={18} className="mr-2" />
                        {saving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
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

            <div className="bg-[#1e1e1e] rounded-[28px] overflow-hidden shadow-xl border border-secondary-300 ring-4 ring-secondary-100">
                <div className="bg-[#2d2d2d] px-6 py-3 flex items-center justify-between border-b border-[#3e3e3e]">
                    <div className="flex items-center text-gray-300 text-sm font-medium">
                        <Settings size={16} className="mr-2 text-primary-400" />
                        <span className="opacity-80">pipeline_config.json</span>
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
                            JSON
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SchemaPage;
