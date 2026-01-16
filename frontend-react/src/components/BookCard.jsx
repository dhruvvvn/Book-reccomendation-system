import { useState } from 'react';
import { motion } from 'framer-motion';
import { Star } from 'lucide-react';

export default function BookCard({ book, onClick }) {
    const [imageError, setImageError] = useState(false);
    const [imageLoaded, setImageLoaded] = useState(false);

    // Generate initials for fallback
    const initials = book.title?.substring(0, 2).toUpperCase() || '📚';

    return (
        <motion.div
            className="book-card cursor-pointer flex-shrink-0 w-44"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onClick(book)}
        >
            {/* Cover */}
            <div className="relative w-44 h-64 rounded-xl overflow-hidden bg-gradient-to-br from-gray-800 to-gray-900 shadow-xl">
                {!imageError && book.cover_url ? (
                    <img
                        src={book.cover_url}
                        alt={book.title}
                        className={`w-full h-full object-cover transition-opacity duration-300 ${imageLoaded ? 'opacity-100' : 'opacity-0'
                            }`}
                        onLoad={() => setImageLoaded(true)}
                        onError={() => setImageError(true)}
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center text-4xl font-bold text-gray-600">
                        {initials}
                    </div>
                )}

                {/* Loading skeleton */}
                {!imageLoaded && !imageError && book.cover_url && (
                    <div className="absolute inset-0 bg-gradient-to-br from-gray-800 to-gray-900 animate-pulse" />
                )}

                {/* Rating badge */}
                <div className="absolute bottom-2 right-2 flex items-center gap-1 px-2 py-1 rounded-full bg-black/70 backdrop-blur-sm text-xs font-medium">
                    <Star size={12} className="text-yellow-400 fill-yellow-400" />
                    <span>{book.rating?.toFixed(1) || 'N/A'}</span>
                </div>

                {/* Genre badge */}
                {book.genre && (
                    <div className="absolute bottom-2 left-2 px-2 py-1 rounded-full bg-black/70 backdrop-blur-sm text-[10px] font-medium text-gray-200 truncate max-w-[80px]">
                        {book.genre}
                    </div>
                )}
            </div>

            {/* Info */}
            <div className="mt-3 px-1">
                <h3 className="font-medium text-sm line-clamp-2 leading-tight">
                    {book.title}
                </h3>
                <p className="text-xs text-gray-400 mt-1 truncate">
                    {book.author}
                </p>
            </div>
        </motion.div>
    );
}
