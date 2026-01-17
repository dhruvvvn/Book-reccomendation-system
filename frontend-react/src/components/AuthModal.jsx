import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Eye, EyeOff } from 'lucide-react';
import { authAPI } from '../api';
import { useUser } from '../UserContext';

export default function AuthModal({ isOpen, onClose }) {
    const { login } = useUser();
    const [tab, setTab] = useState('login');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [showPassword, setShowPassword] = useState(false);

    // Form data
    const [form, setForm] = useState({
        username: '',
        password: '',
        confirmPassword: '',
        displayName: '',
    });

    const handleChange = (e) => {
        setForm({ ...form, [e.target.name]: e.target.value });
        setError('');
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            if (tab === 'login') {
                const response = await authAPI.login(form.username, form.password);
                if (response.data.success) {
                    login(response.data.user);
                    onClose();
                } else {
                    setError(response.data.message || 'Login failed');
                }
            } else {
                if (form.password !== form.confirmPassword) {
                    setError('Passwords do not match');
                    setLoading(false);
                    return;
                }
                const response = await authAPI.signup(
                    form.username,
                    form.password,
                    form.displayName || form.username
                );
                if (response.data.success) {
                    login(response.data.user);
                    onClose();
                } else {
                    setError(response.data.message || 'Signup failed');
                }
            }
        } catch (err) {
            setError('Connection error. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                    onClick={onClose}
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.9, opacity: 0 }}
                        className="glass rounded-2xl w-full max-w-md p-6"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Close button */}
                        <button
                            onClick={onClose}
                            className="absolute top-4 right-4 w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center"
                        >
                            <X size={18} />
                        </button>

                        {/* Tabs */}
                        <div className="flex gap-4 mb-6">
                            {['login', 'signup'].map((t) => (
                                <button
                                    key={t}
                                    onClick={() => {
                                        setTab(t);
                                        setError('');
                                    }}
                                    className={`flex-1 py-2 border-b-2 font-medium transition-colors ${tab === t
                                            ? 'border-red-500 text-white'
                                            : 'border-transparent text-gray-400 hover:text-white'
                                        }`}
                                >
                                    {t === 'login' ? 'Login' : 'Sign Up'}
                                </button>
                            ))}
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm text-gray-400 mb-1">Username</label>
                                <input
                                    type="text"
                                    name="username"
                                    value={form.username}
                                    onChange={handleChange}
                                    required
                                    className="w-full px-4 py-3 bg-white/10 rounded-xl outline-none focus:ring-2 focus:ring-red-500/50"
                                    placeholder="Enter username"
                                />
                            </div>

                            {tab === 'signup' && (
                                <div>
                                    <label className="block text-sm text-gray-400 mb-1">Display Name</label>
                                    <input
                                        type="text"
                                        name="displayName"
                                        value={form.displayName}
                                        onChange={handleChange}
                                        className="w-full px-4 py-3 bg-white/10 rounded-xl outline-none focus:ring-2 focus:ring-red-500/50"
                                        placeholder="How should we call you?"
                                    />
                                </div>
                            )}

                            <div>
                                <label className="block text-sm text-gray-400 mb-1">Password</label>
                                <div className="relative">
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        name="password"
                                        value={form.password}
                                        onChange={handleChange}
                                        required
                                        className="w-full px-4 py-3 bg-white/10 rounded-xl outline-none focus:ring-2 focus:ring-red-500/50 pr-12"
                                        placeholder="Enter password"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                                    >
                                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                    </button>
                                </div>
                            </div>

                            {tab === 'signup' && (
                                <div>
                                    <label className="block text-sm text-gray-400 mb-1">Confirm Password</label>
                                    <input
                                        type="password"
                                        name="confirmPassword"
                                        value={form.confirmPassword}
                                        onChange={handleChange}
                                        required
                                        className="w-full px-4 py-3 bg-white/10 rounded-xl outline-none focus:ring-2 focus:ring-red-500/50"
                                        placeholder="Confirm your password"
                                    />
                                </div>
                            )}

                            {error && (
                                <p className="text-red-400 text-sm">{error}</p>
                            )}

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full py-4 btn-gradient rounded-xl font-semibold disabled:opacity-50"
                            >
                                {loading ? 'Please wait...' : tab === 'login' ? 'Login' : 'Sign Up'}
                            </button>
                        </form>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
