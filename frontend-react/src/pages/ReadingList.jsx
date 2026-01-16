import { useState, useEffect } from 'react';
import { BookOpen, Loader2, Trash2 } from 'lucide-react';
import { authAPI, discoverAPI } from '../api';
import { useUser } from '../UserContext';
import BookCard from '../components/BookCard';

export default function ReadingList({ onBookClick }) {
    const { user } = useUser();
    const [books, setBooks] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!user) {
            setLoading(false);
            return;
        }

        const fetchReadingList = async () => {
            try {
                const response = await authAPI.getReadingList(user.id);
                // Backend now returns full book objects
                setBooks(response.data.reading_list || []);
            } catch (error) {
                console.error('Failed to load reading list:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchReadingList();
    }, [user]);

    const handleRemove = async (bookId) => {
        if (!user) return;
        try {
            await authAPI.removeFromReadingList(user.id, bookId);
            setBooks((prev) => prev.filter((b) => b.id !== bookId));
        } catch (error) {
            console.error('Failed to remove book:', error);
        }
    };

    if (!user) {
        return (
            <div className="pt-24 px-6 max-w-7xl mx-auto">
                <div className="text-center py-20">
                    <BookOpen size={64} className="mx-auto text-gray-600 mb-4" />
                    <h2 className="text-2xl font-bold mb-2">Please Log In</h2>
                    <p className="text-gray-400">Sign in to see your saved books.</p>
                </div>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="pt-24 flex items-center justify-center min-h-[60vh]">
                <Loader2 size={40} className="animate-spin text-red-500" />
            </div>
        );
    }

    return (
        <div className="pt-24 px-6 max-w-7xl mx-auto pb-12">
            <h1 className="text-3xl font-bold mb-2">📖 My Reading List</h1>
            <p className="text-gray-400 mb-8">Books you've saved for later</p>

            {books.length === 0 ? (
                <div className="text-center py-20 glass rounded-2xl">
                    <BookOpen size={64} className="mx-auto text-gray-600 mb-4" />
                    <h2 className="text-xl font-semibold mb-2">Your reading list is empty</h2>
                    <p className="text-gray-400">
                        Browse books and click "Add to List" to save them here!
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
                    {books.map((book) => (
                        <div key={book.id} className="relative group">
                            <BookCard book={book} onClick={onBookClick} />
                            <button
                                onClick={() => handleRemove(book.id)}
                                className="absolute top-2 right-2 w-8 h-8 rounded-full bg-red-600/80 hover:bg-red-600 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                                <Trash2 size={14} />
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
