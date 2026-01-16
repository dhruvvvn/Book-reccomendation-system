import { createContext, useContext, useState, useEffect } from 'react';

const UserContext = createContext(null);

export function UserProvider({ children }) {
    const [user, setUser] = useState(null);
    const [personality, setPersonality] = useState(
        localStorage.getItem('personality') || 'friendly'
    );
    const [theme, setTheme] = useState(
        localStorage.getItem('theme') || 'dark'
    );

    // Load user from localStorage on mount
    useEffect(() => {
        const savedUser = localStorage.getItem('user');
        if (savedUser) {
            try {
                setUser(JSON.parse(savedUser));
            } catch (e) {
                localStorage.removeItem('user');
            }
        }
    }, []);

    // Persist personality changes
    useEffect(() => {
        localStorage.setItem('personality', personality);
    }, [personality]);

    // Persist theme changes
    useEffect(() => {
        localStorage.setItem('theme', theme);
        document.documentElement.setAttribute('data-theme', theme);
    }, [theme]);

    const login = (userData) => {
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
        if (userData.personality) setPersonality(userData.personality);
        if (userData.theme) setTheme(userData.theme);
    };

    const logout = () => {
        setUser(null);
        localStorage.removeItem('user');
    };

    return (
        <UserContext.Provider value={{
            user,
            login,
            logout,
            personality,
            setPersonality,
            theme,
            setTheme,
        }}>
            {children}
        </UserContext.Provider>
    );
}

export function useUser() {
    const context = useContext(UserContext);
    if (!context) {
        throw new Error('useUser must be used within a UserProvider');
    }
    return context;
}
