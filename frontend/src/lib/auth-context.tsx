"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { User, Workspace } from "@/types";
import { api } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  workspace: Workspace | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: any) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const savedToken = localStorage.getItem("woka_token");
    if (savedToken) {
      setToken(savedToken);
      api.getMe()
        .then((res) => {
          setUser(res.user);
          setWorkspace(res.workspace);
        })
        .catch(() => {
          api.clearToken();
          setToken(null);
          setUser(null);
          setWorkspace(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await api.login({ email, password });
      setUser(res.user);
      setWorkspace(res.workspace);
      setToken(res.access_token);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: any) => {
    setIsLoading(true);
    try {
      const res = await api.register(data);
      setUser(res.user);
      setWorkspace(res.workspace);
      setToken(res.access_token);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    api.clearToken();
    setUser(null);
    setWorkspace(null);
    setToken(null);
  };

  const refreshUser = async () => {
    try {
      const res = await api.getMe();
      setUser(res.user);
      setWorkspace(res.workspace);
    } catch {
      // Ignored
    }
  };

  return (
    <AuthContext.Provider value={{ user, workspace, token, isLoading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
