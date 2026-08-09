import { describe, expect, it } from "vitest";

import { resolveInternalRedirect } from "@/app/router/internal-redirect";

describe("P0 内部重定向", () => {
  it("只接受单斜杠开头的本应用路径", () => {
    expect(
      resolveInternalRedirect(
        "%2Fstrategy-knowledge%3Fsection%3Dprofile",
        "/workspace"
      )
    ).toBe("/strategy-knowledge?section=profile");
    expect(
      resolveInternalRedirect("%2F%2Fevil.example", "/workspace")
    ).toBe("/workspace");
    expect(
      resolveInternalRedirect("https%3A%2F%2Fevil.example", "/workspace")
    ).toBe("/workspace");
    expect(resolveInternalRedirect("%E0%A4%A", "/workspace")).toBe(
      "/workspace"
    );
  });
});
