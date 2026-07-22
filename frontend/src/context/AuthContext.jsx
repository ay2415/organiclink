import React, { createContext, useState, useEffect } from 'react';
import api from '../api/axios';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('organiclink_token');
    if (token) {
      api.get('/api/auth/me')
        .then((res) => {
          setUser(res.data);
        })
        .catch(() => {
          localStorage.removeItem('organiclink_token');
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const res = await api.post('/api/auth/login', { email, password });
    localStorage.setItem('organiclink_token', res.data.access_token);
    const meRes = await api.get('/api/auth/me');
    setUser(meRes.data);
    return meRes.data;
  };

  const register = async (userData) => {
    const res = await api.post('/api/auth/register', userData);
    localStorage.setItem('organiclink_token', res.data.access_token);
    const meRes = await api.get('/api/auth/me');
    setUser(meRes.data);
    return meRes.data;
  };

  const logout = () => {
    localStorage.removeItem('organiclink_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
