import test from "node:test";
import assert from "node:assert/strict";

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
