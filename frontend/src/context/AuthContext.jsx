import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => {
    try {
      return localStorage.getItem('agronex_token') || null;
    } catch {
      return null;
    }
  });

  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem('agronex_user');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });

  // Sync state with storage events across tabs & custom auth events
  useEffect(() => {
    const syncAuth = () => {
      try {
        const storedToken = localStorage.getItem('agronex_token');
        const storedUser = localStorage.getItem('agronex_user');
        setToken(storedToken || null);
        setUser(storedUser ? JSON.parse(storedUser) : null);
      } catch {
        setToken(null);
        setUser(null);
      }
    };

    window.addEventListener('storage', syncAuth);
    window.addEventListener('agronex_auth_change', syncAuth);
    return () => {
      window.removeEventListener('storage', syncAuth);
      window.removeEventListener('agronex_auth_change', syncAuth);
    };
  }, []);

  const login = useCallback((userData, tokenData) => {
    try {
      if (tokenData) {
        localStorage.setItem('agronex_token', tokenData);
        setToken(tokenData);
      }
      if (userData) {
        localStorage.setItem('agronex_user', JSON.stringify(userData));
        setUser(userData);
      }
      window.dispatchEvent(new Event('agronex_auth_change'));
    } catch (err) {
      console.error('Error persisting auth state:', err);
    }
  }, []);

  const logout = useCallback(() => {
    try {
      localStorage.removeItem('agronex_token');
      localStorage.removeItem('agronex_user');
      localStorage.removeItem('agronex_alert_preferences');
      setToken(null);
      setUser(null);
      window.dispatchEvent(new Event('agronex_auth_change'));
    } catch (err) {
      console.error('Error clearing auth state:', err);
    }
  }, []);

  const updateUser = useCallback((updatedFields) => {
    setUser((prev) => {
      const next = { ...(prev || {}), ...updatedFields };
      try {
        localStorage.setItem('agronex_user', JSON.stringify(next));
      } catch (err) {
        console.error('Error updating user state:', err);
      }
      window.dispatchEvent(new Event('agronex_auth_change'));
      return next;
    });
  }, []);

  const isAuthenticated = Boolean(token && user);

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated, login, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

