import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle, X, Send, Sparkles } from 'lucide-react';
import { chatAPI } from '../api';
import { useUser } from '../UserContext';

export default function ChatWidget({ onBookClick }) {
    const { user, personality } = useUser();
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([
        {
            type: 'bot',
            content: "Hey there! 👋 I'm your personal book assistant. Tell me what you're in the mood for!",
        },
    ]);
    const [input, setInput] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const messagesEndRef = useRef(null);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = async () => {
        if (!input.trim()) return;

        const userMessage = input.trim();
        setInput('');

        // Add user message
        setMessages((prev) => [...prev, { type: 'user', content: userMessage }]);
        setIsTyping(true);

        try {
            const response = await chatAPI.send(userMessage, user?.id, personality);
            const data = response.data;

            // Construct message with error context if present
            let botMessage = data.message || "Here are some recommendations:";

            // If a specific book wasn't found, add context
            if (data.book_not_found) {
                botMessage = `I couldn't find "${data.book_not_found}" in my database, but here's what I know about it. ${botMessage}`;
            }

            // If there was a partial error, append it
            if (data.error_message) {
                console.warn('Backend partial error:', data.error_message);
            }

            setMessages((prev) => [
                ...prev,
                {
                    type: 'bot',
                    content: botMessage,
                    books: data.recommendations || [],
                    hasError: !!data.error_message,
                },
            ]);
        } catch (error) {
            console.error('Chat error:', error);
            setMessages((prev) => [
                ...prev,
                {
                    type: 'bot',
                    content: "Hmm, I had a little trouble there. Let me try again - just rephrase your request!",
                },
            ]);
        } finally {
            setIsTyping(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <>
            {/* Toggle Button */}
            <motion.button
                className="fixed bottom-6 right-6 w-14 h-14 rounded-full btn-gradient flex items-center justify-center shadow-2xl z-50"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsOpen(!isOpen)}
            >
                {isOpen ? <X size={24} /> : <MessageCircle size={24} />}
            </motion.button>

            {/* Chat Window */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 20, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 20, scale: 0.95 }}
                        className="fixed bottom-24 right-6 w-96 h-[500px] glass rounded-2xl shadow-2xl z-50 flex flex-col overflow-hidden"
                    >
                        {/* Header */}
                        <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-red-600/20 to-orange-600/20 border-b border-white/10">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center">
                                <Sparkles size={20} className="text-white" />
                            </div>
                            <div>
                                <h3 className="font-semibold">BookAI Assistant</h3>
                                <p className="text-xs text-gray-400">
                                    {personality === 'friendly' ? '😊 Friendly' : '🎩 Professional'} mode
                                </p>
                            </div>
                        </div>

                        {/* Messages */}
                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                            {messages.map((msg, i) => (
                                <div
                                    key={i}
                                    className={`chat-message flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'
                                        }`}
                                >
                                    <div
                                        className={`max-w-[80%] rounded-2xl px-4 py-2 ${msg.type === 'user'
                                            ? 'bg-gradient-to-r from-red-600 to-red-700 text-white'
                                            : 'bg-white/10 text-gray-100'
                                            }`}
                                    >
                                        {/* Simple text rendering instead of ReactMarkdown */}
                                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>

                                        {/* Book recommendations as rich cards */}
                                        {msg.books && msg.books.length > 0 && (
                                            <div className="mt-3 space-y-3">
                                                {msg.books.slice(0, 5).map((book, idx) => (
                                                    <div
                                                        key={`${book.book_id || book.id}-${idx}`}
                                                        className="flex gap-3 p-2 bg-white/5 rounded-xl hover:bg-white/10 transition-colors cursor-pointer group"
                                                        onClick={() => onBookClick({
                                                            id: book.book_id || book.id,
                                                            title: book.title,
                                                            author: book.author,
                                                            description: book.description,
                                                            genre: book.genre,
                                                            rating: book.rating,
                                                            cover_url: book.cover_url
                                                        })}
                                                    >
                                                        {/* Cover Image */}
                                                        <div className="flex-shrink-0 w-16 h-24 bg-gray-800 rounded-lg overflow-hidden">
                                                            {book.cover_url ? (
                                                                <img
                                                                    src={book.cover_url}
                                                                    alt={book.title}
                                                                    className="w-full h-full object-cover"
                                                                    onError={(e) => {
                                                                        e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 96"><rect fill="%23374151" width="64" height="96"/><text x="32" y="48" fill="%239CA3AF" font-size="10" text-anchor="middle">📖</text></svg>';
                                                                    }}
                                                                />
                                                            ) : (
                                                                <div className="w-full h-full flex items-center justify-center text-2xl">📖</div>
                                                            )}
                                                        </div>

                                                        {/* Book Info */}
                                                        <div className="flex-1 min-w-0">
                                                            <h4 className="font-semibold text-sm line-clamp-1 group-hover:text-red-400 transition-colors">
                                                                {book.title}
                                                            </h4>
                                                            <p className="text-xs text-gray-400 line-clamp-1">{book.author}</p>
                                                            <div className="flex items-center gap-1 mt-1">
                                                                <span className="text-yellow-400 text-xs">★</span>
                                                                <span className="text-xs text-gray-400">{book.rating?.toFixed(1) || 'N/A'}</span>
                                                                <span className="text-xs text-gray-500 ml-2">{book.genre}</span>
                                                            </div>
                                                            {book.explanation && (
                                                                <p className="text-xs text-gray-300 mt-1 line-clamp-2 italic">
                                                                    "{book.explanation}"
                                                                </p>
                                                            )}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}

                            {/* Typing indicator */}
                            {isTyping && (
                                <div className="flex justify-start">
                                    <div className="bg-white/10 rounded-2xl px-4 py-3">
                                        <div className="flex gap-1">
                                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div ref={messagesEndRef} />
                        </div>

                        {/* Input */}
                        <div className="p-4 border-t border-white/10">
                            <div className="flex gap-2">
                                <input
                                    type="text"
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    placeholder="Ask for book recommendations..."
                                    className="flex-1 bg-white/10 rounded-full px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-red-500/50"
                                />
                                <button
                                    onClick={sendMessage}
                                    disabled={!input.trim() || isTyping}
                                    className="w-10 h-10 rounded-full btn-gradient flex items-center justify-center disabled:opacity-50"
                                >
                                    <Send size={18} />
                                </button>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
