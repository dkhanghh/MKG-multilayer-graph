import React, { useState, useRef, useEffect } from 'react';
import api from '../api';
import { Send, User, Bot, RefreshCw, MessageSquare, Sparkles, AlertCircle } from 'lucide-react';

const ChatInput = React.memo(({ onSend, loading }) => {
    const inputRef = useRef(null);

    const handleSubmit = (e) => {
        e.preventDefault();
        const value = inputRef.current?.value || '';
        if (value.trim()) {
            onSend(value);
            if (inputRef.current) {
                inputRef.current.value = '';
                // Trigger change event manually or force blur/focus to update UI?
                // Actually peer-placeholder-shown works automatically on input value change via user.
                // But programmatically clearing it might not trigger re-paint of peer immediately in some browsers?
                // Usually it does.
            }
        }
    };

    return (
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto relative flex items-end gap-2 bg-secondary-50 p-2 rounded-[28px] border border-secondary-200 focus-within:border-primary-300 focus-within:ring-4 focus-within:ring-primary-50/50 transition-all duration-300">
            <input
                type="text"
                ref={inputRef}
                defaultValue=""
                placeholder="Ask about your data..."
                className="flex-grow pl-4 py-3 bg-transparent border-none focus:ring-0 focus:outline-none text-secondary-900 placeholder-secondary-400 text-base peer"
                disabled={loading}
            />
            <button
                type="submit"
                disabled={loading}
                className="p-3 bg-primary-600 text-white rounded-full hover:bg-primary-700 transition-all disabled:opacity-50 disabled:bg-secondary-300 shadow-sm hover:shadow-md flex-shrink-0 peer-placeholder-shown:opacity-50 peer-placeholder-shown:cursor-not-allowed peer-placeholder-shown:bg-secondary-300"
            >
                <Send size={20} className={loading ? 'opacity-0' : 'opacity-100'} />
                {loading && <div className="absolute inset-0 flex items-center justify-center"><div className="w-4 h-4 border-2 border-white/50 border-t-white rounded-full animate-spin"></div></div>}
            </button>
        </form>
    );
});

const ChatPage = () => {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Hello! I am your Knowledge Graph Assistant. Ask me anything about your documents.' }
    ]);
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);



    // Re-implementation of handleSend with useCallback and correct dependencies
    const handleSend = React.useCallback(async (text) => {
        const userMessage = { role: 'user', content: text };
        setMessages(prev => [...prev, userMessage]);
        setLoading(true);

        try {
            // Note: messages state here is from closure.
            // If we depend on [messages], it's up to date.
            const history = messages.map(m => ({ role: m.role, content: m.content }));
            // Add current message to history for the API call?
            // Original code: history was map of current messages BEFORE this one.
            // Wait, original code:
            // const userMessage = ...; setMessages(...);
            // const history = messages.map(...) 
            // 'messages' in the function body would be the old state because setMessages is async.
            // So history did NOT include the new user message in the original code?
            // "const userMessage = ... setMessages ... const history = messages.map"
            // Yes, 'messages' was stale.
            // So we can replicate that behavior. 

            const response = await api.post('/chat/chat', {
                message: userMessage.content,
                history: history
            });

            const botMessage = { role: 'assistant', content: response.data.response };
            setMessages(prev => [...prev, botMessage]);
        } catch (error) {
            console.error("Chat error", error);
            setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error processing your request.' }]);
        }
        setLoading(false);
    }, [messages]);

    const handleClear = () => {
        setMessages([
            { role: 'assistant', content: 'Hello! I am your Knowledge Graph Assistant. Ask me anything about your documents.' }
        ]);
    };



    return (
        <div className="h-[calc(100vh-140px)] max-w-4xl mx-auto flex flex-col bg-white rounded-[28px] shadow-sm border border-secondary-200 overflow-hidden animate-fade-in mt-6">
            <div className="px-6 py-4 bg-white/80 backdrop-blur-sm border-b border-secondary-100 flex justify-between items-center z-10">
                <div className="flex items-center">
                    <div className="h-10 w-10 bg-primary-100/50 rounded-full flex items-center justify-center mr-4">
                        <MessageSquare className="text-primary-600" size={20} />
                    </div>
                    <div>
                        <h1 className="text-lg font-medium text-secondary-900 leading-tight">Assistant</h1>
                        <p className="text-xs text-secondary-500 font-medium">Knowledge Graph RAG</p>
                    </div>
                </div>
                <button
                    onClick={handleClear}
                    className="btn-text text-xs hover:bg-red-50 hover:text-red-600"
                    title="Clear Conversation"
                >
                    <RefreshCw size={16} className="mr-1.5" /> Clear
                </button>
            </div>

            <div className="flex-grow overflow-y-auto px-6 py-6 space-y-8 bg-white">
                {messages.map((msg, index) => (
                    <div
                        key={index}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up group`}
                        style={{ animationDelay: `${index * 0.05}s` }}
                    >
                        <div className={`flex max-w-[85%] md:max-w-[75%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                            {/* Avatar */}
                            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center mt-auto mb-1 shadow-sm border border-secondary-100 overflow-hidden ${msg.role === 'user' ? 'bg-primary-600 text-white ml-3' : 'bg-white text-primary-600 mr-3'
                                }`}>
                                {msg.role === 'user'
                                    ? <User size={16} strokeWidth={2.5} />
                                    : <div className="h-full w-full bg-gradient-to-tr from-primary-100 to-white flex items-center justify-center"><Bot size={18} className="text-primary-600" /></div>
                                }
                            </div>

                            {/* Message Bubble */}
                            <div
                                className={`px-5 py-3.5 shadow-sm text-[15px] leading-relaxed relative ${msg.role === 'user'
                                    ? 'bg-primary-600 text-white rounded-[24px] rounded-tr-sm'
                                    : 'bg-secondary-50 text-secondary-800 rounded-[24px] rounded-tl-sm border border-secondary-100'
                                    }`}
                            >
                                <div className="whitespace-pre-wrap markdown-body">{msg.content}</div>
                            </div>
                        </div>
                    </div>
                ))}

                {loading && (
                    <div className="flex justify-start animate-fade-in">
                        <div className="flex flex-row max-w-[85%]">
                            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white border border-secondary-100 flex items-center justify-center mt-auto mb-1 mr-3 shadow-sm">
                                <Sparkles size={16} className="text-primary-500 animate-pulse" />
                            </div>
                            <div className="bg-secondary-50 border border-secondary-100 rounded-[24px] rounded-tl-sm px-5 py-4 shadow-sm flex items-center space-x-1.5">
                                <div className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
                                <div className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }}></div>
                                <div className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></div>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="p-4 bg-white/90 backdrop-blur-sm border-t border-secondary-100">
                <ChatInput onSend={handleSend} loading={loading} />
                <div className="text-center mt-3">
                    <p className="text-[11px] text-secondary-400 font-medium flex items-center justify-center gap-1">
                        <AlertCircle size={10} /> AI generated content may be inaccurate.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default ChatPage;
