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
                <section className="relative py-20 min-h-[500px] flex items-center bg-[var(--color-surface)]">
                    {/* Background Glow */}
                    <div className="absolute inset-0 overflow-hidden">
                        <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-[var(--color-primary-dark)]/20 to-transparent blur-3xl" />
                        <div className="absolute bottom-0 left-0 w-1/2 h-full bg-gradient-to-r from-blue-900/10 to-transparent blur-3xl" />
                    </div>

                    <div className="relative z-10 max-w-7xl mx-auto px-6 w-full grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
                        {/* Text Content (Left) */}
                        <div className="space-y-6">
                            <span className="inline-block px-4 py-1 bg-gradient-to-r from-red-600 to-red-700 rounded-full text-xs font-bold tracking-wider uppercase shadow-lg shadow-red-900/20">
                                Featured Pick
                            </span>

                            <div>
                                <h1 className="text-4xl md:text-6xl font-black mb-2 leading-tight tracking-tight text-white drop-shadow-sm">
                                    {data.hero.title}
                                </h1>
                                <p className="text-xl md:text-2xl text-[var(--color-primary)] font-medium">
                                    by {data.hero.author}
                                </p>
                            </div>

                            <p className="text-gray-300 text-lg leading-relaxed max-w-xl line-clamp-3">
                                {data.hero.description || 'Discover this amazing book and explore its world through our AI-powered recommendations.'}
                            </p>

                            <div className="flex gap-4 pt-4">
                                <button
                                    onClick={() => onBookClick(data.hero)}
                                    className="px-8 py-3.5 btn-gradient rounded-full font-bold text-lg shadow-lg shadow-primary/25 hover:shadow-primary/40 transform hover:-translate-y-1 transition-all duration-300 flex items-center gap-2"
                                >
                                    <span>Read More</span>
                                    <ChevronRight size={20} />
                                </button>
                            </div>
                        </div>

                        {/* Book Cover (Right) */}
                        <div className="flex justify-center md:justify-end">
                            <div className="relative group">
                                <div className="absolute -inset-1 bg-gradient-to-r from-[var(--color-primary)] to-purple-600 rounded-lg blur opacity-25 group-hover:opacity-50 transition duration-1000"></div>
                                <img
                                    src={data.hero.cover_url}
                                    alt={data.hero.title}
                                    className="relative rounded-lg shadow-2xl shadow-black/50 w-48 h-72 object-contain bg-gray-900 transform group-hover:scale-[1.02] transition-transform duration-500"
                                />
                            </div>
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
