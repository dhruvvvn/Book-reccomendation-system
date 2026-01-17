import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Home, BookOpen, Settings, LogIn, LogOut, User } from 'lucide-react';
import { useUser } from '../UserContext';

export default function NavBar({ onLoginClick }) {
    const location = useLocation();
    const { user, logout } = useUser();
    const [showDropdown, setShowDropdown] = useState(false);

    const navItems = [
        { path: '/', icon: Home, label: 'Browse' },
        { path: '/reading-list', icon: BookOpen, label: 'Reading List' },
        { path: '/settings', icon: Settings, label: 'Settings' },
    ];

    return (
        <header className="fixed top-0 left-0 right-0 z-50 glass">
            <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
                {/* Logo */}
                <Link to="/" className="flex items-center gap-2">
                    <span className="text-3xl">📚</span>
                    <span className="text-xl font-bold bg-gradient-to-r from-red-500 to-orange-500 bg-clip-text text-transparent">
                        BookAI
                    </span>
                </Link>

                {/* Navigation */}
                <nav className="hidden md:flex items-center gap-1">
                    {navItems.map(({ path, icon: Icon, label }) => (
                        <Link
                            key={path}
                            to={path}
                            className={`flex items-center gap-2 px-4 py-2 rounded-full transition-all relative ${location.pathname === path
                                ? 'text-white'
                                : 'text-gray-400 hover:text-white'
                                }`}
                        >
                            <div className="relative z-10 flex items-center gap-2">
                                <Icon size={18} className={location.pathname === path ? "text-[var(--color-primary)]" : ""} />
                                <span className="text-sm font-medium">{label}</span>
                            </div>
                            {location.pathname === path && (
                                <motion.div
                                    layoutId="nav-pill"
                                    className="absolute inset-0 bg-white/5 rounded-full border border-white/10"
                                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                                />
                            )}
                        </Link>
                    ))}
                </nav>

                {/* User Menu */}
                <div className="relative">
                    <button
                        onClick={() => user ? setShowDropdown(!showDropdown) : onLoginClick()}
                        className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 hover:bg-white/20 transition-all"
                    >
                        <span className="w-8 h-8 rounded-full bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center text-white font-bold">
                            {user ? user.display_name?.charAt(0).toUpperCase() : <User size={16} />}
                        </span>
                        <span className="text-sm font-medium hidden sm:block">
                            {user ? user.display_name : 'Guest'}
                        </span>
                    </button>

                    {/* Dropdown */}
                    {showDropdown && user && (
                        <div className="absolute right-0 mt-2 w-48 glass rounded-xl shadow-xl overflow-hidden">
                            <div className="p-3 border-b border-white/10">
                                <p className="font-medium">{user.display_name}</p>
                                <p className="text-xs text-gray-400">@{user.username}</p>
                            </div>
                            <button
                                onClick={() => {
                                    logout();
                                    setShowDropdown(false);
                                }}
                                className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-white/10 transition-all text-red-400"
                            >
                                <LogOut size={16} />
                                <span>Logout</span>
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </header>
    );
}
