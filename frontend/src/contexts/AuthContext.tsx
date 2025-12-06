import { createContext, useState, useEffect, useContext, type ReactNode } from 'react';
import { getMe } from '../lib/api'; // The function that calls your /auth/me endpoint

// 1. Define the shape of the User object and the Context's value
interface User {
  user_id: number;
  name: string;
  email: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (userData: User) => void;
  logout: () => void;
}

// 2. Create the context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// 3. Create the Provider component
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true); // Start in a loading state

  // This effect runs once when the app loads to check for an active session
  useEffect(() => {
    const checkSession = async () => {
      try {
        const userData = await getMe();
        if (userData) {
          setUser(userData); // If session is found, set the user
        }
      } catch (error) {
        console.error("No active session found");
        setUser(null); // Ensure user is null if the check fails
      } finally {
        setLoading(false); // Stop loading once the check is complete
      }
    };

    checkSession();
  }, []); // The empty array `[]` ensures this runs only once.

  // Functions to update state, typically called from login/logout pages
  const login = (userData: User) => {
    setUser(userData);
  };

  const logout = async () => {
    await import("../lib/api").then(api => api.logout());
    setUser(null);
    setLoading(false);
    // Re-check session to ensure user is logged out
    try {
      const userData = await getMe();
      setUser(userData); // Should be null if logged out
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const value = { user, loading, login, logout };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// 4. Create a custom hook for easy access to the context
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}