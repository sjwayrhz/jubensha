import { createContext, useContext, useEffect, useState } from 'react';
import { api, getToken, setToken } from './api';

const AuthCtx = createContext(null);
const USER_KEY = 'jubensha_user';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || 'null');
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(!!getToken() && !user);

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api('/auth/me')
      .then((u) => {
        setUser(u);
        localStorage.setItem(USER_KEY, JSON.stringify(u));
      })
      .catch(() => {
        setUser(null);
        localStorage.removeItem(USER_KEY);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const form = new URLSearchParams({ username: email, password });
    const tok = await api('/auth/login', { method: 'POST', form });
    setToken(tok.access_token);
    const u = await api('/auth/me');
    setUser(u);
    localStorage.setItem(USER_KEY, JSON.stringify(u));
    return u;
  };

  const register = async (email, password, nickname) => {
    await api('/auth/register', {
      method: 'POST',
      body: { email, password, nickname },
    });
    return login(email, password);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(USER_KEY);
    location.href = '/login';
  };

  return (
    <AuthCtx.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  return useContext(AuthCtx);
}
