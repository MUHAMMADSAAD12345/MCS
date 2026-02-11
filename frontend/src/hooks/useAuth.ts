import { useState, useCallback } from 'react';
import { useChatStore } from '../stores/chatStore';

export function useAuth() {
  const { auth, setAuth, logout } = useChatStore();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const login = useCallback(async (username: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Login failed');
      }
      const data = await res.json();
      setAuth({
        token: data.access_token,
        user: { id: data.user_id, username: data.username },
      });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (username: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Registration failed');
      }
      // Auto-login after registration
      await login(username, password);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [login]);

  return { auth, login, register, logout, error, loading, setError };
}
