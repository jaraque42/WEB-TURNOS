import { createContext } from 'react';
import type { CurrentUser } from '../types';

export interface AuthContextType {
  user: CurrentUser | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

export const AuthContext = createContext<AuthContextType | null>(null);