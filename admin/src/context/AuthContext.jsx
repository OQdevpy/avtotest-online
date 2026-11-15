import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  claimTelegram, logout as apiLogout, fetchJSON, refreshAccessToken, clearTokens,
} from '../services/api';

const AuthContext = createContext();

// Panel faqat shef (admin roli) uchun; boshqa rol bilan kirgan sessiya yopiladi.
const NOT_ADMIN = 'Bu panel faqat shef uchun.';

function isAdmin(user) {
  return user?.role === 'admin';
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Dastur ochilganda refresh token bilan foydalanuvchini tekshirish
    const initAuth = async () => {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        try {
          const userData = await fetchJSON('/auth/me/');
          if (isAdmin(userData)) setUser(userData);
          else await apiLogout();
        } catch {
          clearTokens();
        }
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  /** Bot tasdiqlagan Telegram sessiyasi bilan kirish. */
  const loginWithTelegram = async (token) => {
    const data = await claimTelegram(token);
    if (!isAdmin(data.user)) {
      await apiLogout();
      throw new Error(NOT_ADMIN);
    }
    setUser(data.user);
    return data;
  };

  const logout = async () => {
    await apiLogout();
    setUser(null);
  };

  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white">Yuklanmoqda...</div>;
  }

  return (
    <AuthContext.Provider value={{ user, loginWithTelegram, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
