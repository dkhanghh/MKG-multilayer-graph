import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogOut, Database, Upload, Share2, MessageSquare, Menu, X, ChevronDown } from 'lucide-react';

const Navbar = () => {
    const { logout, user } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [isOpen, setIsOpen] = useState(false);
    const [userMenuOpen, setUserMenuOpen] = useState(false);

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const isActive = (path) => location.pathname === path;

    const NavLink = ({ to, icon: Icon, children }) => (
        <Link
            to={to}
            className={`relative group flex items-center px-4 py-2 text-sm font-medium rounded-full transition-all duration-200 ${isActive(to)
                    ? 'bg-primary-100 text-primary-900'
                    : 'text-secondary-600 hover:bg-secondary-100'
                }`}
        >
            <Icon className={`mr-2.5 h-[18px] w-[18px] ${isActive(to) ? 'text-primary-600' : 'text-secondary-500'
                }`} strokeWidth={2.5} />
            {children}
        </Link>
    );

    return (
        <nav className="bg-white/95 backdrop-blur-sm sticky top-0 z-50 border-b border-secondary-200/50">
            <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-[72px]">
                    <div className="flex items-center">
                        <Link to="/" className="flex-shrink-0 flex items-center space-x-3 group">
                            <div className="h-10 w-10 bg-primary-500 rounded-xl flex items-center justify-center text-white font-bold text-lg shadow-sm shadow-primary-200 group-hover:shadow-md group-hover:scale-105 transition-all duration-300">
                                KG
                            </div>
                            <span className="font-sans font-medium text-xl text-secondary-800 tracking-tight">
                                Builder
                            </span>
                        </Link>

                        <div className="hidden md:ml-10 md:flex md:items-center md:space-x-1.5 bg-secondary-50 p-1.5 rounded-full border border-secondary-200/50">
                            <NavLink to="/" icon={Database}>Schema</NavLink>
                            <NavLink to="/upload" icon={Upload}>Store</NavLink>
                            <NavLink to="/graph" icon={Share2}>Graph</NavLink>
                            <NavLink to="/chat" icon={MessageSquare}>Chat</NavLink>
                        </div>
                    </div>

                    <div className="hidden md:flex items-center">
                        <div className="relative">
                            <button
                                onClick={() => setUserMenuOpen(!userMenuOpen)}
                                className="flex items-center pl-1 pr-3 py-1 bg-white hover:bg-secondary-50 rounded-full border border-secondary-200 transition-colors shadow-sm"
                            >
                                <div className="h-8 w-8 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-bold mr-2.5">
                                    {user?.username?.charAt(0).toUpperCase()}
                                </div>
                                <span className="text-secondary-700 text-sm font-medium mr-1.5 max-w-[100px] truncate">
                                    {user?.full_name || user?.username}
                                </span>
                                <ChevronDown size={14} className="text-secondary-400" />
                            </button>

                            {userMenuOpen && (
                                <div className="absolute right-0 mt-2 w-48 bg-white rounded-2xl shadow-lg border border-secondary-100 py-2 animate-fade-in origin-top-right">
                                    <div className="px-4 py-2 border-b border-secondary-100 mb-1">
                                        <p className="text-xs font-medium text-secondary-500 uppercase tracking-wider">Account</p>
                                        <p className="text-sm text-secondary-900 truncate">{user?.username}</p>
                                    </div>
                                    <button
                                        onClick={handleLogout}
                                        className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center hover:text-red-700 transition-colors"
                                    >
                                        <LogOut size={16} className="mr-2" />
                                        Sign out
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="flex items-center md:hidden">
                        <button
                            onClick={() => setIsOpen(!isOpen)}
                            className="inline-flex items-center justify-center p-2 rounded-full text-secondary-500 hover:bg-secondary-100 focus:outline-none"
                        >
                            {isOpen ? <X size={24} /> : <Menu size={24} />}
                        </button>
                    </div>
                </div>
            </div>

            {/* Mobile menu */}
            <div className={`md:hidden transition-all duration-300 ease-in-out overflow-hidden ${isOpen ? 'max-h-96 opacity-100 border-b border-secondary-200' : 'max-h-0 opacity-0'
                } bg-white`}>
                <div className="px-4 py-4 space-y-2">
                    <Link to="/" className="flex items-center px-4 py-3 rounded-2xl bg-secondary-50 text-secondary-900 font-medium">
                        <Database className="mr-3 text-primary-600" size={20} /> Schema
                    </Link>
                    <Link to="/upload" className="flex items-center px-4 py-3 rounded-2xl hover:bg-secondary-50 text-secondary-600 font-medium transition-colors">
                        <Upload className="mr-3 text-secondary-400" size={20} /> Store
                    </Link>
                    <Link to="/graph" className="flex items-center px-4 py-3 rounded-2xl hover:bg-secondary-50 text-secondary-600 font-medium transition-colors">
                        <Share2 className="mr-3 text-secondary-400" size={20} /> Graph
                    </Link>
                    <Link to="/chat" className="flex items-center px-4 py-3 rounded-2xl hover:bg-secondary-50 text-secondary-600 font-medium transition-colors">
                        <MessageSquare className="mr-3 text-secondary-400" size={20} /> Chat
                    </Link>
                </div>
                <div className="border-t border-secondary-100 px-4 py-4 bg-secondary-50/50">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center">
                            <div className="h-10 w-10 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center font-bold">
                                {user?.username?.charAt(0).toUpperCase()}
                            </div>
                            <div className="ml-3">
                                <div className="text-sm font-medium text-secondary-900">{user?.username}</div>
                                <div className="text-xs text-secondary-500">Logged in</div>
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="w-full flex items-center justify-center px-4 py-2.5 bg-white border border-secondary-200 rounded-full text-red-600 font-medium hover:bg-red-50 transition-colors shadow-sm"
                    >
                        <LogOut size={16} className="mr-2" />
                        Sign Out
                    </button>
                </div>
            </div>
        </nav>
    );
};

export default Navbar;
