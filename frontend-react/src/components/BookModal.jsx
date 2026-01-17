import { motion, AnimatePresence } from 'framer-motion';
import { X, Star, BookOpen, ShoppingCart, Plus, Check, Loader2, Sparkles } from 'lucide-react';
import { useState, useEffect } from 'react';
import { authAPI, booksAPI } from '../api';
import { useUser } from '../UserContext';

export default function BookModal({ book, isOpen, onClose }) {
    const { user } = useUser();
    const [addedToList, setAddedToList] = useState(false);
    const [loading, setLoading] = useState(false);
    const [description, setDescription] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);

    useEffect(() => {
        if (isOpen && book) {
            // Reset state first
            setIsGenerating(false);

            // Check if we have a valid description
            if (book.description && book.description.length > 50) {
                setDescription(book.description);
            } else {
                // No description? Start generation
                setDescription('');
                fetchDescription(book.id);
            }
        } else {
            // Reset when closed
            setDescription('');
            setIsGenerating(false);
        }
    }, [isOpen, book?.id]); // Depend on ID, not object ref

    const fetchDescription = async (bookId) => {
        if (!bookId) return;

        setIsGenerating(true);
        try {
            const response = await booksAPI.getDescription(bookId);
            if (response.data?.description) {
                setDescription(response.data.description);
            } else {
                setDescription('Description unavailable.');
            }
        } catch (error) {
            console.error('Failed to generate description', error);
            setDescription('Description unavailable at this time.');
        } finally {
            setIsGenerating(false);
        }
    };

    if (!book) return null;

    const handleAddToList = async () => {
        if (!user) {
            alert('Please login to add books to your list');
            return;
        }

        setLoading(true);
        try {
            await authAPI.addToReadingList(user.id, String(book.id));
            setAddedToList(true);
            setTimeout(() => setAddedToList(false), 3000);
        } catch (error) {
            console.error('Failed to add to reading list', error);
        } finally {
            setLoading(false);
        }
    };

    const handleBuyLink = () => {
        const query = encodeURIComponent(`${book.title} ${book.author}`);
        window.open(`https://www.amazon.com/s?k=${query}&i=stripbooks`, '_blank');
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
                        className="glass rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Close button */}
                        <button
                            onClick={onClose}
                            className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"
                        >
                            <X size={20} />
                        </button>

                        <div className="flex flex-col md:flex-row gap-6 p-6">
                            {/* Cover */}
                            <div className="flex-shrink-0 mx-auto md:mx-0">
                                {book.cover_url ? (
                                    <img
                                        src={book.cover_url}
                                        alt={book.title}
                                        className="w-48 h-72 object-cover rounded-xl shadow-2xl"
                                    />
                                ) : (
                                    <div className="w-48 h-72 bg-gradient-to-br from-gray-700 to-gray-900 rounded-xl flex items-center justify-center text-4xl font-bold text-gray-500">
                                        {book.title?.substring(0, 2).toUpperCase()}
                                    </div>
                                )}
                            </div>

                            {/* Info */}
                            <div className="flex-1">
                                <h2 className="text-2xl font-bold mb-2">{book.title}</h2>
                                <p className="text-gray-400 mb-4">by {book.author}</p>

                                <div className="flex items-center gap-4 mb-4">
                                    {book.genre && (
                                        <span className="px-3 py-1 bg-red-600/20 text-red-400 rounded-full text-sm">
                                            {book.genre}
                                        </span>
                                    )}
                                    <div className="flex items-center gap-1 text-yellow-400">
                                        <Star size={16} className="fill-yellow-400" />
                                        <span className="font-medium">{book.rating?.toFixed(1) || 'N/A'}</span>
                                    </div>
                                </div>

                                <div className="min-h-[100px] mb-6">
                                    {isGenerating ? (
                                        <div className="flex flex-col gap-2 items-start text-indigo-400 animate-pulse">
                                            <div className="flex items-center gap-2">
                                                <Sparkles size={16} />
                                                <span className="text-sm font-medium">Powering up AI for description...</span>
                                            </div>
                                            <div className="h-4 bg-white/10 rounded w-full"></div>
                                            <div className="h-4 bg-white/10 rounded w-5/6"></div>
                                            <div className="h-4 bg-white/10 rounded w-4/6"></div>
                                        </div>
                                    ) : (
                                        <p className="text-gray-300 text-sm leading-relaxed">
                                            {description || 'No description available.'}
                                        </p>
                                    )}
                                </div>

                                {/* Actions */}
                                <div className="flex flex-wrap gap-3">
                                    <button className="flex items-center gap-2 px-6 py-3 btn-gradient rounded-full font-medium">
                                        <BookOpen size={18} />
                                        Read Now
                                    </button>
                                    <button
                                        onClick={handleBuyLink}
                                        className="flex items-center gap-2 px-6 py-3 bg-white/10 hover:bg-white/20 rounded-full font-medium transition-colors"
                                    >
                                        <ShoppingCart size={18} />
                                        Buy / Find
                                    </button>
                                    <button
                                        onClick={handleAddToList}
                                        disabled={loading || addedToList}
                                        className="flex items-center gap-2 px-6 py-3 border border-white/20 hover:border-white/40 rounded-full font-medium transition-colors disabled:opacity-50"
                                    >
                                        {addedToList ? (
                                            <>
                                                <Check size={18} className="text-green-400" />
                                                Added!
                                            </>
                                        ) : (
                                            <>
                                                <Plus size={18} />
                                                Add to List
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
