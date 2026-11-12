"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { User, Workspace } from "@/types";
import { api } from "@/lib/api";
import { pickAuthoritativeWorkspace, resolveRestoredWorkspace } from "@/lib/auth-session";

interface AuthContextType {
  user: User | null;
  workspace: Workspace | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: any) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  switchWorkspace: (workspaceId: string) => Promise<void>;
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
      Promise.all([api.getMe(), api.listWorkspaces().catch(() => null)])
        .then(([authenticatedUser, memberships]) => {
          setUser(authenticatedUser);
          setWorkspace(pickAuthoritativeWorkspace(memberships, authenticatedUser));
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
      const [authenticatedUser, memberships] = await Promise.all([
        api.getMe(),
        api.listWorkspaces().catch(() => null),
      ]);
      setUser(authenticatedUser);
      setWorkspace((prev) =>
        memberships
          ? pickAuthoritativeWorkspace(memberships, authenticatedUser)
          : resolveRestoredWorkspace(authenticatedUser, prev)
      );
    } catch {
      // Ignored
    }
  };

  const switchWorkspace = async (workspaceId: string) => {
    const res = await api.selectWorkspace(workspaceId);
    setUser(res.user);
    setWorkspace(res.workspace);
    setToken(res.access_token);
  };

  return (
    <AuthContext.Provider value={{ user, workspace, token, isLoading, login, register, logout, refreshUser, switchWorkspace }}>
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
