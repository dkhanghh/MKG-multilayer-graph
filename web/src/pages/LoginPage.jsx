import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

const LoginPage = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await login(username, password);
            navigate('/');
        } catch (err) {
            setError('Invalid username or password');
        }
        setLoading(false);
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-[#f0f4f8] relative overflow-hidden font-sans">
            {/* M3 Background Shapes */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0">
                <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] rounded-full bg-primary-200/20 blur-[100px]"></div>
                <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-blue-300/20 blur-[100px]"></div>
            </div>

            <div className="bg-white p-10 rounded-[32px] shadow-sm w-full max-w-[400px] z-10 border border-white/50 animate-fade-in flex flex-col items-center">
                <div className="h-14 w-14 bg-primary-600 rounded-[18px] flex items-center justify-center text-white font-bold text-2xl shadow-lg shadow-primary-200 mb-6">
                    KG
                </div>

                <h2 className="text-[28px] font-normal text-secondary-900 mb-1 tracking-tight">Sign in</h2>
                <p className="text-secondary-500 text-[15px] mb-8">Access the Graph Builder</p>

                {error && (
                    <div className="w-full bg-red-50 border border-red-100 text-red-600 px-4 py-3 rounded-2xl mb-6 text-14 flex items-center justify-center animate-slide-up">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="w-full space-y-5">
                    <div className="relative group">
                        <input
                            className="input-field peer placeholder-transparent pt-6 pb-2"
                            id="username"
                            type="text"
                            placeholder="Username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                        <label
                            htmlFor="username"
                            className="absolute left-4 top-4 text-secondary-500 text-base transition-all peer-focus:text-xs peer-focus:top-2 peer-focus:text-primary-600 peer-placeholder-shown:text-base peer-placeholder-shown:top-3.5 peer-valid:text-xs peer-valid:top-2 pointer-events-none"
                        >
                            Username
                        </label>
                    </div>

                    <div className="relative group">
                        <input
                            className="input-field peer placeholder-transparent pt-6 pb-2"
                            id="password"
                            type="password"
                            placeholder="Password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                        <label
                            htmlFor="password"
                            className="absolute left-4 top-4 text-secondary-500 text-base transition-all peer-focus:text-xs peer-focus:top-2 peer-focus:text-primary-600 peer-placeholder-shown:text-base peer-placeholder-shown:top-3.5 peer-valid:text-xs peer-valid:top-2 pointer-events-none"
                        >
                            Password
                        </label>
                    </div>

                    <div className="pt-2">
                        <button
                            className="w-full btn-primary py-3 text-base rounded-full shadow-md hover:shadow-lg hover:translate-y-[-1px] transition-all"
                            type="submit"
                            disabled={loading}
                        >
                            {loading ? (
                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                            ) : (
                                <>
                                    Sign In <ArrowRight size={18} />
                                </>
                            )}
                        </button>
                    </div>
                </form>

                <div className="mt-8 text-center bg-secondary-50 px-4 py-2 rounded-full border border-secondary-100">
                    <p className="text-secondary-500 text-xs">
                        {/* Use <span className="font-bold text-secondary-700">admin</span> / <span className="font-bold text-secondary-700">secret</span> */}
                    </p>
                </div>
            </div>

            <div className="absolute bottom-6 text-secondary-400 text-xs font-medium">
                © 2025 Knowledge Graph Builder
            </div>
        </div>
    );
};

export default LoginPage;
