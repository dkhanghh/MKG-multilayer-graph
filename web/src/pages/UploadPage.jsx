import React, { useState } from 'react';
import api from '../api';
import { Upload, FileText, CheckCircle, AlertCircle, Play, File, X, RefreshCw } from 'lucide-react';

const UploadPage = () => {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [dragActive, setDragActive] = useState(false);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    };

    const handleFileChange = (e) => {
        if (e.target.files[0]) {
            handleFile(e.target.files[0]);
        }
    };

    const handleFile = (selectedFile) => {
        if (selectedFile.type === "application/pdf") {
            setFile(selectedFile);
            setResult(null);
            setError('');
        } else {
            setError("Please upload a PDF file.");
        }
    };

    const clearFile = () => {
        setFile(null);
        setResult(null);
        setError('');
    };

    const handleUpload = async () => {
        if (!file) return;

        setUploading(true);
        setError('');
        setResult(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await api.post('/pipeline/upload-and-run', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            setResult(response.data);
        } catch (err) {
            console.error(err);
            setError(err.response?.data?.detail || 'Upload failed');
        }
        setUploading(false);
    };

    return (
        <div className="max-w-6xl mx-auto animate-fade-in py-8 px-4">
            <div className="text-center mb-12">
                <div className="inline-flex h-16 w-16 items-center justify-center rounded-[24px] bg-primary-100 text-primary-600 mb-6 shadow-sm">
                    <Upload size={32} />
                </div>
                <h1 className="text-4xl font-normal text-secondary-900 tracking-tight mb-3">Add to Knowledge Store</h1>
                <p className="text-lg text-secondary-500 max-w-2xl mx-auto leading-relaxed">
                    Upload documents to extract entities and build your graph.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Upload Section */}
                <div className="lg:col-span-5 space-y-6">
                    <div
                        className={`bg-white rounded-[28px] border-2 border-dashed transition-all duration-300 overflow-hidden relative group ${dragActive ? 'border-primary-500 bg-primary-50/30' : 'border-secondary-200 hover:border-primary-300 hover:bg-secondary-50/30'
                            } ${!file ? 'h-[400px]' : 'h-auto p-1'}`}
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                    >
                        {!file ? (
                            <label className="cursor-pointer flex flex-col items-center justify-center w-full h-full p-8 z-10 relative">
                                <input
                                    type="file"
                                    accept=".pdf"
                                    onChange={handleFileChange}
                                    className="hidden"
                                />
                                <div className="w-20 h-20 bg-primary-50 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-sm border border-primary-100">
                                    <FileText size={40} className="text-primary-500" strokeWidth={1.5} />
                                </div>
                                <h3 className="text-lg font-medium text-secondary-900 mb-2">Drag PDF here</h3>
                                <p className="text-secondary-500 text-sm mb-6 text-center">or click to browse from device</p>
                                <span className="px-4 py-2 bg-white border border-secondary-200 rounded-full text-secondary-600 text-sm font-medium shadow-sm group-hover:bg-primary-50 group-hover:text-primary-700 group-hover:border-primary-200 transition-colors">
                                    Select File
                                </span>
                            </label>
                        ) : (
                            <div className="bg-white rounded-[24px] p-6 border border-secondary-100 shadow-sm">
                                <div className="flex items-start mb-6">
                                    <div className="h-12 w-12 bg-red-50 text-red-500 rounded-2xl flex items-center justify-center mr-4 flex-shrink-0">
                                        <FileText size={24} />
                                    </div>
                                    <div className="flex-grow min-w-0 pt-0.5">
                                        <h3 className="font-medium text-secondary-900 truncate pr-4 text-base">{file.name}</h3>
                                        <p className="text-secondary-500 text-sm">{(file.size / 1024 / 1024).toFixed(2)} MB • PDF</p>
                                    </div>
                                    <button
                                        onClick={clearFile}
                                        className="text-secondary-400 hover:text-red-500 p-2 hover:bg-red-50 rounded-full transition-colors"
                                    >
                                        <X size={20} />
                                    </button>
                                </div>

                                <div className="flex gap-3">
                                    <button
                                        onClick={handleUpload}
                                        disabled={uploading}
                                        className="h-12 flex-1 btn-primary text-base shadow-lg shadow-primary-500/20"
                                    >
                                        {uploading ? (
                                            <>
                                                <RefreshCw size={18} className="animate-spin mr-2" /> Processing
                                            </>
                                        ) : (
                                            <>
                                                <Play size={18} className="mr-2 fill-current" /> Run Pipeline
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>
                        )}

                        {error && (
                            <div className="absolute bottom-4 left-4 right-4 bg-red-50 border border-red-100 text-red-600 p-3 rounded-2xl text-sm flex items-center shadow-lg animate-slide-up">
                                <AlertCircle size={18} className="mr-2 flex-shrink-0" />
                                {error}
                            </div>
                        )}
                    </div>

                    <div className="bg-secondary-50 rounded-[24px] p-6 border border-secondary-100">
                        <h4 className="flex items-center text-sm font-medium text-secondary-900 mb-3">
                            <CheckCircle size={16} className="text-primary-600 mr-2" />
                            Supported Features
                        </h4>
                        <ul className="space-y-2 text-sm text-secondary-600 ml-6 list-disc marker:text-secondary-300">
                            <li>Semantic Entity Extraction</li>
                            <li>Relationship Discovery</li>
                            <li>PDF Text Parsing</li>
                        </ul>
                    </div>
                </div>

                {/* Results Section */}
                <div className="lg:col-span-7">
                    <div className="bg-white rounded-[32px] border border-secondary-200 shadow-sm h-full overflow-hidden flex flex-col min-h-[500px]">
                        <div className="px-8 py-6 border-b border-secondary-100 bg-secondary-50/50 flex items-center justify-between">
                            <h2 className="text-lg font-medium text-secondary-900">Pipeline Output</h2>
                            {result && <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium border border-green-200">Completed</span>}
                        </div>

                        {!result && !uploading && (
                            <div className="flex-grow flex flex-col items-center justify-center text-secondary-400 p-12">
                                <div className="w-24 h-24 bg-secondary-50 rounded-full flex items-center justify-center mb-6">
                                    <Play size={36} className="text-secondary-300 ml-1" />
                                </div>
                                <p className="text-lg font-medium text-secondary-500">Ready to run</p>
                                <p className="text-sm mt-1">Output details will appear here</p>
                            </div>
                        )}

                        {uploading && (
                            <div className="flex-grow flex flex-col items-center justify-center p-12">
                                <div className="relative w-20 h-20 mb-8">
                                    <svg className="animate-spin w-full h-full text-primary-200" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                </div>
                                <h3 className="text-xl font-medium text-secondary-900 mb-2">Analyzing Document</h3>
                                <div className="w-64 h-1.5 bg-secondary-100 rounded-full overflow-hidden">
                                    <div className="h-full bg-primary-500 rounded-full animate-progress origin-left"></div>
                                </div>
                                <p className="text-secondary-500 text-center mt-4 text-sm">
                                    This may take a minute...
                                </p>
                            </div>
                        )}

                        {result && (
                            <div className="flex-grow p-8 animate-fade-in space-y-8 overflow-y-auto">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="bg-secondary-50 p-5 rounded-[24px] border border-secondary-100">
                                        <h4 className="text-xs font-bold text-secondary-500 uppercase tracking-wider mb-4">Metrics</h4>
                                        <div className="space-y-3">
                                            {Object.entries(result.metrics || {}).map(([key, value]) => (
                                                <div key={key} className="flex justify-between items-center text-sm">
                                                    <span className="text-secondary-600 capitalize">{key.replace(/_/g, ' ')}</span>
                                                    <span className="font-mono font-medium text-secondary-900 bg-white px-2 py-0.5 rounded border border-secondary-200 shadow-sm">
                                                        {typeof value === 'number' ? value.toFixed(2) : value}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="bg-secondary-50 p-5 rounded-[24px] border border-secondary-100">
                                        <h4 className="text-xs font-bold text-secondary-500 uppercase tracking-wider mb-4">Meta Data</h4>
                                        <div className="space-y-3 text-sm">
                                            <div className="flex justify-between items-center">
                                                <span className="text-secondary-600">Pipeline ID</span>
                                                <span className="text-xs bg-white text-secondary-900 px-2 py-1 rounded border border-secondary-200 font-mono truncate max-w-[100px]">{result.pipeline_id}</span>
                                            </div>
                                            <div className="flex justify-between items-center">
                                                <span className="text-secondary-600">Timestamp</span>
                                                <span className="text-secondary-900">{new Date(result.timestamp).toLocaleTimeString()}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div>
                                    <h4 className="text-xs font-bold text-secondary-500 uppercase tracking-wider mb-3 ml-2">Execution Log</h4>
                                    <div className="bg-[#282c34] text-gray-300 p-6 rounded-[24px] overflow-x-auto font-mono text-xs leading-relaxed shadow-inner border border-secondary-800">
                                        <pre>{JSON.stringify(result.execution_summary, null, 2)}</pre>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UploadPage;
