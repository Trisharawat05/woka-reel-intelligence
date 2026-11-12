import type { User, Workspace } from "../types";

export const WORKSPACE_STORAGE_KEY = "woka_workspace";

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

function resolveStorage(storage?: StorageLike | null): StorageLike | null {
  if (storage !== undefined) {
    return storage;
  }
  if (typeof window !== "undefined" && window.localStorage) {
    return window.localStorage;
  }
  return null;
}

export function persistWorkspaceSession(
  workspace: Workspace | null | undefined,
  storage?: StorageLike | null
): void {
  const store = resolveStorage(storage);
  if (!store) return;

  if (!workspace) {
    store.removeItem(WORKSPACE_STORAGE_KEY);
    return;
  }

  store.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify(workspace));
}

export function readCachedWorkspaceForUser(
  user: User,
  storage?: StorageLike | null
): Workspace | null {
  const store = resolveStorage(storage);
  if (!store) return null;

  const raw = store.getItem(WORKSPACE_STORAGE_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Partial<Workspace> | null;
    if (
      parsed &&
      typeof parsed.id === "string" &&
      typeof parsed.name === "string" &&
      typeof parsed.owner_id === "string" &&
      parsed.owner_id === user.id
    ) {
      return {
        id: parsed.id,
        name: parsed.name,
        owner_id: parsed.owner_id,
      };
    }
    store.removeItem(WORKSPACE_STORAGE_KEY);
  } catch {
    store.removeItem(WORKSPACE_STORAGE_KEY);
  }

  return null;
}

export interface WorkspaceMembershipItem extends Workspace {
  role_in_workspace: string;
  is_active: boolean;
}

export function pickAuthoritativeWorkspace(
  memberships: WorkspaceMembershipItem[] | null | undefined,
  user: User,
  storage?: StorageLike | null
): Workspace | null {
  if (Array.isArray(memberships)) {
    if (memberships.length === 0) {
      persistWorkspaceSession(null, storage);
      return null;
    }
    const chosen = memberships.find((w) => w.is_active) ?? memberships[0];
    const cleanWorkspace: Workspace = {
      id: chosen.id,
      name: chosen.name,
      owner_id: chosen.owner_id,
    };
    persistWorkspaceSession(cleanWorkspace, storage);
    return cleanWorkspace;
  }
  return readCachedWorkspaceForUser(user, storage);
}

export function resolveRestoredWorkspace(
  user: User,
  currentWorkspace: Workspace | null,
  storage?: StorageLike | null
): Workspace | null {
  if (currentWorkspace && currentWorkspace.owner_id === user.id) {
    return currentWorkspace;
  }
  return readCachedWorkspaceForUser(user, storage);
}
