import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { UserProvider } from './UserContext';
import NavBar from './components/NavBar';
import ChatWidget from './components/ChatWidget';
import BookModal from './components/BookModal';
import AuthModal from './components/AuthModal';
import Home from './pages/Home';
import ReadingList from './pages/ReadingList';
import Settings from './pages/Settings';
import './index.css';

function App() {
  const [selectedBook, setSelectedBook] = useState(null);
  const [showAuth, setShowAuth] = useState(false);

  const handleBookClick = (book) => {
    setSelectedBook(book);
  };

  const closeBookModal = () => {
    setSelectedBook(null);
  };

  return (
    <UserProvider>
      <BrowserRouter>
        <div className="min-h-screen">
          <NavBar onLoginClick={() => setShowAuth(true)} />

          <Routes>
            <Route path="/" element={<Home onBookClick={handleBookClick} />} />
            <Route path="/reading-list" element={<ReadingList onBookClick={handleBookClick} />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>

          {/* Chat Widget */}
          <ChatWidget onBookClick={handleBookClick} />

          {/* Modals */}
          <BookModal
            book={selectedBook}
            isOpen={!!selectedBook}
            onClose={closeBookModal}
          />
          <AuthModal isOpen={showAuth} onClose={() => setShowAuth(false)} />
        </div>
      </BrowserRouter>
    </UserProvider>
  );
}

export default App;
