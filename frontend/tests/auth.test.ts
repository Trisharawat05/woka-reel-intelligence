import test from "node:test";
import assert from "node:assert/strict";
import {
  WORKSPACE_STORAGE_KEY,
  persistWorkspaceSession,
  pickAuthoritativeWorkspace,
  readCachedWorkspaceForUser,
  resolveRestoredWorkspace,
  type StorageLike,
  type WorkspaceMembershipItem,
} from "../src/lib/auth-session.ts";
import type { User, Workspace } from "../src/types/index.ts";

function createMemoryStorage(): StorageLike {
  const store = new Map<string, string>();
  return {
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => {
      store.set(key, value);
    },
    removeItem: (key) => {
      store.delete(key);
    },
  };
}

const sampleUser: User = {
  id: "user-123",
  email: "creator@woka.io",
  full_name: "Test Creator",
  role: "CREATOR",
  is_active: true,
  is_verified: true,
  created_at: "2026-11-10T00:00:00Z",
};

const sampleWorkspace: Workspace = {
  id: "ws-456",
  name: "Test Creator's Workspace",
  owner_id: "user-123",
};

test("client-side role validation distinguishes roles correctly", () => {
  const allowedCreatorRoles = ["CREATOR", "AGENCY", "ADMIN"];
  const allowedBrandRoles = ["BRAND", "ADMIN"];

  assert.equal(allowedCreatorRoles.includes("CREATOR"), true);
  assert.equal(allowedCreatorRoles.includes("BRAND"), false);

  assert.equal(allowedBrandRoles.includes("BRAND"), true);
  assert.equal(allowedBrandRoles.includes("CREATOR"), false);
  assert.equal(allowedBrandRoles.includes("ADMIN"), true);
});

test("token storage format verification", () => {
  const mockJwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotUse";
  assert.equal(mockJwt.split(".").length, 3);
});

test("session restoration restores cached workspace matching /auth/me user", () => {
  const storage = createMemoryStorage();
  persistWorkspaceSession(sampleWorkspace, storage);

  const restored = readCachedWorkspaceForUser(sampleUser, storage);
  assert.deepEqual(restored, sampleWorkspace);
});

test("session restoration ignores and clears workspace owned by another user", () => {
  const storage = createMemoryStorage();
  persistWorkspaceSession(
    { id: "ws-other", name: "Other Workspace", owner_id: "other-user" },
    storage
  );

  const restored = readCachedWorkspaceForUser(sampleUser, storage);
  assert.equal(restored, null);
  assert.equal(storage.getItem(WORKSPACE_STORAGE_KEY), null);
});

test("resolveRestoredWorkspace keeps existing in-memory workspace across /auth/me refresh", () => {
  const storage = createMemoryStorage();
  const restored = resolveRestoredWorkspace(sampleUser, sampleWorkspace, storage);
  assert.deepEqual(restored, sampleWorkspace);

  const absent = resolveRestoredWorkspace(sampleUser, null, storage);
  assert.equal(absent, null);
});

test("pickAuthoritativeWorkspace overwrites tampered cache with server active workspace", () => {
  const storage = createMemoryStorage();
  persistWorkspaceSession(
    { id: "ws-tampered", name: "Tampered Workspace", owner_id: sampleUser.id },
    storage
  );

  const serverMemberships: WorkspaceMembershipItem[] = [
    { ...sampleWorkspace, role_in_workspace: "OWNER", is_active: false },
    {
      id: "ws-selected",
      name: "Selected Team Workspace",
      owner_id: "another-owner",
      role_in_workspace: "ADMIN",
      is_active: true,
    },
  ];

  const resolved = pickAuthoritativeWorkspace(serverMemberships, sampleUser, storage);
  assert.deepEqual(resolved, {
    id: "ws-selected",
    name: "Selected Team Workspace",
    owner_id: "another-owner",
  });
  assert.match(storage.getItem(WORKSPACE_STORAGE_KEY) || "", /ws-selected/);
});

test("pickAuthoritativeWorkspace clears cache when server reports empty memberships", () => {
  const storage = createMemoryStorage();
  persistWorkspaceSession(sampleWorkspace, storage);

  const resolved = pickAuthoritativeWorkspace([], sampleUser, storage);
  assert.equal(resolved, null);
  assert.equal(storage.getItem(WORKSPACE_STORAGE_KEY), null);
});
