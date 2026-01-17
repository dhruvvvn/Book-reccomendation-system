import axios from 'axios';

// Create axios instance with base URL
const getBaseUrl = () => {
    let url = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    // Remove trailing slash if present
    url = url.replace(/\/$/, '');
    // Append /api/v1 if not already present
    if (!url.endsWith('/api/v1')) {
        url += '/api/v1';
    }
    return url;
};

const api = axios.create({
    baseURL: getBaseUrl(),
    headers: {
        'Content-Type': 'application/json',
    },
});

// Auth API
export const authAPI = {
    login: (username, password) =>
        api.post('/auth/login', { username, password }),

    signup: (username, password, display_name) =>
        api.post('/auth/signup', { username, password, display_name }),

    getUser: (userId) =>
        api.get(`/auth/user/${userId}`),

    updatePreferences: (userId, preferences) =>
        api.put(`/auth/user/${userId}/preferences`, preferences),

    getReadingList: (userId) =>
        api.get(`/auth/user/${userId}/reading-list`),

    addToReadingList: (userId, bookId) =>
        api.post(`/auth/user/${userId}/reading-list`, { book_id: bookId }),

    removeFromReadingList: (userId, bookId) =>
        api.delete(`/auth/user/${userId}/reading-list/${bookId}`),
};

// Discover API
export const discoverAPI = {
    getHomepage: () =>
        api.get('/discover'),

    search: (query) =>
        api.get(`/discover/search?q=${encodeURIComponent(query)}`),

    getBook: (bookId) =>
        api.get(`/discover/book/${bookId}`),

    enrichBook: (bookId) =>
        api.get(`/discover/enrich/${bookId}`),
};

// Chat API
export const chatAPI = {
    send: (message, userId = null, personality = 'friendly') =>
        api.post('/chat', {
            message,
            user_id: userId,
            personality: personality,  // Now properly sent to backend
            preferences: null,
            emotional_context: null
        }),
};

// Books API
export const booksAPI = {
    getDescription: (bookId) =>
        api.post(`/books/${bookId}/description`),
};

export default api;
