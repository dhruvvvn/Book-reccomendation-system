/**
 * BookAI - Netflix-Style Frontend
 * 
 * Handles:
 * - User authentication (login/signup)
 * - Homepage data fetching & rendering
 * - Book preview modal
 * - Search functionality
 * - Chat widget with AI assistant
 * - Theme & personality toggles
 */

// ============================================
// State Management
// ============================================
const state = {
    user: null,
    currentBook: null,
    theme: localStorage.getItem('theme') || 'dark',
    personality: localStorage.getItem('personality') || 'friendly',
    heroBook: null
};

// ============================================
// API Helpers
// ============================================
const API_BASE = '/api/v1';

async function api(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
        headers: { 'Content-Type': 'application/json' },
        ...options
    };
    if (options.body && typeof options.body === 'object') {
        config.body = JSON.stringify(options.body);
    }

    const response = await fetch(url, config);
    return response.json();
}

// ============================================
// DOM Elements
// ============================================
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

// ============================================
// Initialization
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initAuth();
    initModals();
    initSearch();
    initChat();
    initSettings();
    loadHomepage();

    // Header scroll effect
    window.addEventListener('scroll', () => {
        const header = $('.header');
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });
});

// ============================================
// Theme Management
// ============================================
function initTheme() {
    document.documentElement.setAttribute('data-theme', state.theme);
    updateThemeIcons();

    $('#theme-toggle').addEventListener('click', toggleTheme);
}

function toggleTheme() {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', state.theme);
    localStorage.setItem('theme', state.theme);
    updateThemeIcons();

    if (state.user) {
        api(`/auth/user/${state.user.id}/preferences`, {
            method: 'PUT',
            body: { theme: state.theme }
        });
    }
}

function updateThemeIcons() {
    const darkIcon = $('.theme-icon-dark');
    const lightIcon = $('.theme-icon-light');

    if (state.theme === 'dark') {
        darkIcon.classList.remove('hidden');
        lightIcon.classList.add('hidden');
    } else {
        darkIcon.classList.add('hidden');
        lightIcon.classList.remove('hidden');
    }
}

// ============================================
// Authentication
// ============================================
function initAuth() {
    // Load saved user
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
        state.user = JSON.parse(savedUser);
        updateUserUI();
    }

    // Auth tabs
    $$('.auth-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            $$('.auth-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            if (tabName === 'login') {
                $('#login-form').classList.remove('hidden');
                $('#signup-form').classList.add('hidden');
            } else {
                $('#login-form').classList.add('hidden');
                $('#signup-form').classList.remove('hidden');
            }
        });
    });

    // Login form
    $('#login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = $('#login-username').value;
        const password = $('#login-password').value;

        const result = await api('/auth/login', {
            method: 'POST',
            body: { username, password }
        });

        if (result.success) {
            state.user = result.user;
            localStorage.setItem('user', JSON.stringify(result.user));
            closeModal('auth-modal');
            updateUserUI();
            showToast(`Welcome back, ${result.user.display_name}!`);

            // Apply user preferences
            if (result.user.theme) {
                state.theme = result.user.theme;
                document.documentElement.setAttribute('data-theme', state.theme);
                updateThemeIcons();
            }
            if (result.user.personality) {
                state.personality = result.user.personality;
            }
        } else {
            $('#login-error').textContent = result.message;
        }
    });

    // Signup form
    $('#signup-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = $('#signup-username').value;
        const display_name = $('#signup-display').value;
        const password = $('#signup-password').value;

        const result = await api('/auth/signup', {
            method: 'POST',
            body: { username, password, display_name }
        });

        if (result.success) {
            state.user = result.user;
            localStorage.setItem('user', JSON.stringify(result.user));
            closeModal('auth-modal');
            updateUserUI();
            showToast(`Welcome to BookAI, ${result.user.display_name}!`);
        } else {
            $('#signup-error').textContent = result.message;
        }
    });

    // User menu
    $('#user-btn').addEventListener('click', () => {
        $('#user-dropdown').classList.toggle('hidden');
    });

    $('#btn-show-login').addEventListener('click', () => {
        openModal('auth-modal');
        $('#user-dropdown').classList.add('hidden');
    });

    $('#btn-logout').addEventListener('click', () => {
        state.user = null;
        localStorage.removeItem('user');
        updateUserUI();
        $('#user-dropdown').classList.add('hidden');
        showToast('Logged out successfully');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.user-menu')) {
            $('#user-dropdown').classList.add('hidden');
        }
    });
}

function updateUserUI() {
    if (state.user) {
        $('#user-name').textContent = state.user.display_name;
        $('#user-avatar').textContent = state.user.display_name.charAt(0).toUpperCase();
        $('#dropdown-logged-out').classList.add('hidden');
        $('#dropdown-logged-in').classList.remove('hidden');
        $('#dropdown-user-name').textContent = state.user.display_name;
    } else {
        $('#user-name').textContent = 'Guest';
        $('#user-avatar').textContent = '👤';
        $('#dropdown-logged-out').classList.remove('hidden');
        $('#dropdown-logged-in').classList.add('hidden');
    }
}

// ============================================
// Homepage Loading
// ============================================
async function loadHomepage() {
    try {
        const data = await api('/discover');

        // Render hero
        if (data.hero) {
            state.heroBook = data.hero;
            renderHero(data.hero);
        }

        // Render categories
        if (data.categories && data.categories.length > 0) {
            renderCategories(data.categories);
        } else {
            $('#categories').innerHTML = `
                <div class="loading-spinner">
                    <p>No books found. Please ingest some books first.</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Failed to load homepage:', error);
        $('#categories').innerHTML = `
            <div class="loading-spinner">
                <p>Failed to load books. Is the server running?</p>
            </div>
        `;
    }
}

function renderHero(book) {
    const backdrop = $('#hero-backdrop');
    if (book.cover_url) {
        backdrop.style.backgroundImage = `url(${book.cover_url})`;
    } else {
        backdrop.style.background = 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)';
    }

    $('#hero-title').textContent = book.title;
    $('#hero-author').textContent = book.author;
    $('#hero-description').textContent = book.description || 'Discover this amazing book...';

    $('#hero-read-btn').onclick = () => showToast('📖 Coming Soon: Read functionality');
    $('#hero-info-btn').onclick = () => openBookModal(book);
}

function renderCategories(categories) {
    const container = $('#categories');
    container.innerHTML = '';

    categories.forEach(category => {
        if (category.books.length === 0) return;

        const row = document.createElement('div');
        row.className = 'category-row';

        row.innerHTML = `
            <div class="category-header">
                <h2 class="category-title">${category.name}</h2>
                <div class="carousel-nav">
                    <button class="carousel-btn prev-btn" aria-label="Scroll left">‹</button>
                    <button class="carousel-btn next-btn" aria-label="Scroll right">›</button>
                </div>
            </div>
            <div class="carousel-container">
                <div class="carousel">
                    ${category.books.map(book => createBookCard(book)).join('')}
                </div>
            </div>
        `;

        container.appendChild(row);

        // Carousel navigation
        const carousel = row.querySelector('.carousel');
        const prevBtn = row.querySelector('.prev-btn');
        const nextBtn = row.querySelector('.next-btn');

        prevBtn.addEventListener('click', () => {
            carousel.scrollBy({ left: -400, behavior: 'smooth' });
        });

        nextBtn.addEventListener('click', () => {
            carousel.scrollBy({ left: 400, behavior: 'smooth' });
        });
    });

    // Add click handlers to all book cards
    $$('.book-card').forEach(card => {
        card.addEventListener('click', () => {
            // Decode base64 book data
            const encoded = card.dataset.bookEncoded;
            const bookJson = decodeURIComponent(escape(atob(encoded)));
            const bookData = JSON.parse(bookJson);
            openBookModal(bookData);
        });
    });
}

function createBookCard(book) {
    // Use base64 encoding to avoid JSON escaping issues
    const bookJson = JSON.stringify(book);
    const encodedBook = btoa(unescape(encodeURIComponent(bookJson)));

    // Generate initials for fallback cover
    const initials = book.title ? book.title.substring(0, 2).toUpperCase() : '📚';

    const coverHtml = book.cover_url
        ? `<img src="${book.cover_url}" alt="${book.title}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
           <div class="no-cover" style="display:none">${initials}</div>`
        : `<div class="no-cover">${initials}</div>`;

    return `
        <div class="book-card" data-book-encoded="${encodedBook}">
            <div class="book-cover">
                ${coverHtml}
                <span class="book-rating">⭐ ${book.rating?.toFixed(1) || 'N/A'}</span>
            </div>
            <div class="book-info">
                <p class="book-title">${book.title}</p>
                <p class="book-author">${book.author}</p>
            </div>
        </div>
    `;
}

// ============================================
// Modals
// ============================================
function initModals() {
    // Close modals when clicking backdrop
    $$('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });

    // Book modal close
    $('#close-book-modal').addEventListener('click', () => closeModal('book-modal'));

    // Book modal buttons
    $('#btn-read-now').addEventListener('click', () => {
        showToast('📖 Coming Soon: Read functionality will be added!');
    });

    $('#btn-buy-link').addEventListener('click', () => {
        if (state.currentBook) {
            showToast('🔗 Coming Soon: Buy/Find links will be added!');
        }
    });

    $('#btn-add-list').addEventListener('click', () => {
        if (!state.user) {
            showToast('Please login to add books to your list');
            return;
        }
        showToast('➕ Added to your reading list!');
    });

    // Settings modal
    $('#btn-settings').addEventListener('click', () => {
        $('#user-dropdown').classList.add('hidden');
        openModal('settings-modal');
    });

    $('#close-settings').addEventListener('click', () => closeModal('settings-modal'));
}

function openModal(modalId) {
    $(`#${modalId}`).classList.add('active');
}

function closeModal(modalId) {
    $(`#${modalId}`).classList.remove('active');
}

function openBookModal(book) {
    state.currentBook = book;

    $('#modal-title').textContent = book.title;
    $('#modal-author').textContent = book.author;
    $('#modal-genre').textContent = book.genre || 'Unknown';
    $('#modal-rating').textContent = book.rating?.toFixed(1) || 'N/A';
    $('#modal-description').textContent = book.description || 'No description available.';

    const img = $('#modal-cover');
    if (book.cover_url) {
        img.src = book.cover_url;
        img.onerror = () => { img.src = ''; img.alt = 'No cover'; };
    } else {
        img.src = '';
        img.alt = 'No cover available';
    }

    openModal('book-modal');
}

// ============================================
// Search
// ============================================
function initSearch() {
    const input = $('#search-input');
    const results = $('#search-results');
    let debounceTimer;

    input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        const query = input.value.trim();

        if (query.length < 2) {
            results.classList.add('hidden');
            return;
        }

        debounceTimer = setTimeout(async () => {
            const data = await api(`/discover/search?q=${encodeURIComponent(query)}`);

            if (data.results && data.results.length > 0) {
                results.innerHTML = data.results.slice(0, 8).map(book => `
                    <div class="search-result-item" data-book='${JSON.stringify(book)}'>
                        <img src="${book.cover_url || ''}" alt="${book.title}" onerror="this.style.display='none'">
                        <div class="search-result-info">
                            <h4>${book.title}</h4>
                            <p>${book.author}</p>
                        </div>
                    </div>
                `).join('');

                results.classList.remove('hidden');

                // Add click handlers
                results.querySelectorAll('.search-result-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const book = JSON.parse(item.dataset.book);
                        openBookModal(book);
                        results.classList.add('hidden');
                        input.value = '';
                    });
                });
            } else {
                results.innerHTML = '<div class="search-result-item"><p>No results found</p></div>';
                results.classList.remove('hidden');
            }
        }, 300);
    });

    // Close results when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-container')) {
            results.classList.add('hidden');
        }
    });

    // Handle Enter key for semantic search
    input.addEventListener('keypress', async (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const query = input.value.trim();
            if (query) {
                results.classList.add('hidden');
                // Open chat and send the query
                openChat();
                sendChatMessage(`Find me books about: ${query}`);
                input.value = '';
            }
        }
    });
}

// ============================================
// Chat Widget
// ============================================
function initChat() {
    const toggle = $('#chat-toggle');
    const window = $('#chat-window');
    const form = $('#chat-form');
    const input = $('#chat-input');

    toggle.addEventListener('click', () => {
        const isOpen = !window.classList.contains('hidden');

        if (isOpen) {
            window.classList.add('hidden');
            $('.chat-icon').classList.remove('hidden');
            $('.chat-close').classList.add('hidden');
        } else {
            openChat();
        }
    });

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const message = input.value.trim();
        if (message) {
            sendChatMessage(message);
            input.value = '';
        }
    });

    // Personality toggle
    $('#personality-toggle').addEventListener('click', togglePersonality);
}

function openChat() {
    $('#chat-window').classList.remove('hidden');
    $('.chat-icon').classList.add('hidden');
    $('.chat-close').classList.remove('hidden');
    $('#chat-input').focus();
}

function togglePersonality() {
    state.personality = state.personality === 'friendly' ? 'formal' : 'friendly';
    localStorage.setItem('personality', state.personality);

    const icon = $('#personality-icon');
    icon.textContent = state.personality === 'friendly' ? '😊' : '🎩';

    showToast(`Switched to ${state.personality === 'friendly' ? 'Friendly' : 'Professional'} mode`);

    if (state.user) {
        api(`/auth/user/${state.user.id}/preferences`, {
            method: 'PUT',
            body: { personality: state.personality }
        });
    }
}

async function sendChatMessage(message) {
    const messagesContainer = $('#chat-messages');

    // Add user message
    const userMsg = document.createElement('div');
    userMsg.className = 'chat-message user';
    userMsg.innerHTML = `<div class="message-content">${escapeHtml(message)}</div>`;
    messagesContainer.appendChild(userMsg);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Show typing indicator
    const typingMsg = document.createElement('div');
    typingMsg.className = 'chat-message bot';
    typingMsg.innerHTML = `<div class="message-content">Thinking...</div>`;
    messagesContainer.appendChild(typingMsg);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
        // Call chat API
        const response = await api('/chat', {
            method: 'POST',
            body: {
                message: message,
                preferences: null,
                emotional_context: state.personality === 'friendly' ? 'casual' : 'professional'
            }
        });

        // Remove typing indicator
        typingMsg.remove();

        // Add bot response
        const botMsg = document.createElement('div');
        botMsg.className = 'chat-message bot';

        let content = `<div class="message-content">${response.message || "Here are some recommendations:"}</div>`;

        // Add book cards if there are recommendations
        if (response.recommendations && response.recommendations.length > 0) {
            content += `<div class="chat-book-cards">`;
            response.recommendations.forEach(book => {
                const escapedBook = JSON.stringify(book).replace(/'/g, "\\'");
                content += `
                    <div class="chat-book-card" onclick='openBookModal(${escapedBook})'>
                        <img src="${book.cover_url || ''}" alt="${book.title}" onerror="this.style.display='none'">
                        <p>${book.title}</p>
                    </div>
                `;
            });
            content += `</div>`;
        }

        botMsg.innerHTML = content;
        messagesContainer.appendChild(botMsg);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

    } catch (error) {
        typingMsg.remove();

        const errorMsg = document.createElement('div');
        errorMsg.className = 'chat-message bot';
        errorMsg.innerHTML = `<div class="message-content">Sorry, I encountered an error. Please try again.</div>`;
        messagesContainer.appendChild(errorMsg);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// Settings
// ============================================
function initSettings() {
    // Load current settings into the modal
    $('#setting-theme').value = state.theme;
    $('#setting-personality').value = state.personality;

    $('#save-settings').addEventListener('click', async () => {
        const theme = $('#setting-theme').value;
        const personality = $('#setting-personality').value;

        // Apply theme
        if (theme !== state.theme) {
            state.theme = theme;
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
            updateThemeIcons();
        }

        // Apply personality
        if (personality !== state.personality) {
            state.personality = personality;
            localStorage.setItem('personality', personality);
            $('#personality-icon').textContent = personality === 'friendly' ? '😊' : '🎩';
        }

        // Save to server if logged in
        if (state.user) {
            await api(`/auth/user/${state.user.id}/preferences`, {
                method: 'PUT',
                body: { theme, personality }
            });
        }

        closeModal('settings-modal');
        showToast('Settings saved!');
    });
}

// ============================================
// Toast Notifications
// ============================================
function showToast(message, duration = 3000) {
    const toast = $('#toast');
    $('#toast-message').textContent = message;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, duration);
}

// Make openBookModal globally accessible for inline handlers
window.openBookModal = openBookModal;
