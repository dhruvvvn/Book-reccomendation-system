import { useState, useEffect, useRef } from 'react';
import { ChevronLeft, ChevronRight, ChevronDown, Filter } from 'lucide-react';
import { discoverAPI } from '../api';
import BookCard from '../components/BookCard';

export default function Home({ onBookClick }) {
    const [data, setData] = useState({ hero: null, categories: [] });
    const [loading, setLoading] = useState(true);
    const [isgenreMenuOpen, setIsGenreMenuOpen] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await discoverAPI.getHomepage();
                setData(response.data);
            } catch (error) {
                console.error('Failed to load homepage:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const scrollToCategory = (categoryName) => {
        const element = document.getElementById(`cat-${categoryName}`);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth' });
        }
        setIsGenreMenuOpen(false);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="spinner" />
            </div>
        );
    }

    return (
        <div className="pt-16">
            {/* Hero Section */}
            {data.hero && (
                <section className="relative h-[70vh] min-h-[500px] flex items-end">
                    {/* Background */}
                    <div
                        className="absolute inset-0 bg-cover bg-center"
                        style={{
                            backgroundImage: data.hero.cover_url
                                ? `url(${data.hero.cover_url})`
                                : 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
                        }}
                    >
                        <div className="absolute inset-0 bg-gradient-to-t from-[var(--color-bg-dark)] via-transparent to-transparent" />
                        <div className="absolute inset-0 bg-black/40" />
                    </div>

                    {/* Content */}
                    <div className="relative z-10 max-w-7xl mx-auto px-6 pb-16 w-full">
                        <span className="inline-block px-4 py-1 bg-gradient-to-r from-red-600 to-red-700 rounded text-sm font-semibold mb-4">
                            Featured Pick
                        </span>
                        <h1 className="text-4xl md:text-5xl font-bold mb-2 max-w-2xl">
                            {data.hero.title}
                        </h1>
                        <p className="text-lg text-gray-300 mb-2">by {data.hero.author}</p>
                        <p className="text-gray-400 max-w-xl mb-6 line-clamp-3">
                            {data.hero.description || 'Discover this amazing book...'}
                        </p>
                        <div className="flex gap-4">
                            <button
                                onClick={() => onBookClick(data.hero)}
                                className="px-8 py-3 btn-gradient rounded-full font-semibold flex items-center gap-2"
                            >
                                📖 More Info
                            </button>
                        </div>
                    </div>
                </section>
            )}

            {/* Categories Header & Filter */}
            <div className="max-w-7xl mx-auto px-6 mt-10 mb-6 flex justify-between items-center relative z-20">
                <h2 className="text-2xl font-bold">Browse Collection</h2>

                <div className="relative">
                    <button
                        onClick={() => setIsGenreMenuOpen(!isgenreMenuOpen)}
                        className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors font-medium border border-white/10"
                    >
                        <Filter size={16} />
                        <span>Filter by Genre</span>
                        <ChevronDown size={16} className={`transition-transform ${isgenreMenuOpen ? 'rotate-180' : ''}`} />
                    </button>

                    {isgenreMenuOpen && (
                        <div className="absolute right-0 top-full mt-2 w-64 bg-gray-900 border border-white/10 rounded-xl shadow-2xl overflow-hidden py-2 backdrop-blur-xl animate-in fade-in zoom-in-95 duration-200">
                            <div className="max-h-80 overflow-y-auto scrollbar-thin">
                                {data.categories?.map((category) => (
                                    <button
                                        key={category.name}
                                        onClick={() => scrollToCategory(category.name)}
                                        className="w-full text-left px-4 py-3 hover:bg-white/10 transition-colors text-sm flex items-center justify-between group"
                                    >
                                        <span>{category.name}</span>
                                        <span className="text-xs text-gray-500 group-hover:text-white transition-colors">
                                            {category.books?.length || 0}
                                        </span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Categories */}
            <section className="pb-20 px-6 max-w-7xl mx-auto space-y-12">
                {data.categories?.map((category) => (
                    <CategoryRow
                        key={category.name}
                        id={`cat-${category.name}`}
                        category={category}
                        onBookClick={onBookClick}
                    />
                ))}

                {(!data.categories || data.categories.length === 0) && (
                    <div className="text-center py-20 text-gray-400">
                        <p className="text-4xl mb-4">📚</p>
                        <p>No books found. Please run the ingestion script.</p>
                    </div>
                )}
            </section>
        </div>
    );
}

function CategoryRow({ category, onBookClick, id }) {
    const containerRef = useRef(null);

    const scroll = (direction) => {
        if (!containerRef.current) return;
        const scrollAmount = direction === 'left' ? -400 : 400;
        containerRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' });
    };

    if (!category.books || category.books.length === 0) return null;

    return (
        <div id={id} className="scroll-mt-24">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold">{category.name}</h2>
                <div className="flex gap-2">
                    <button
                        onClick={() => scroll('left')}
                        className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"
                    >
                        <ChevronLeft size={20} />
                    </button>
                    <button
                        onClick={() => scroll('right')}
                        className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"
                    >
                        <ChevronRight size={20} />
                    </button>
                </div>
            </div>

            <div
                ref={containerRef}
                className="flex gap-4 overflow-x-auto scrollbar-hide pb-4"
                style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
            >
                {category.books.map((book) => (
                    <BookCard key={book.id} book={book} onClick={onBookClick} />
                ))}
            </div>
        </div>
    );
}
