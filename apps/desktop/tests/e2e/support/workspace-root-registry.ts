import { createHash } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";

import { readE2eRuntimeState } from "./runtime-state";

export type E2eWorkspaceRoot = {
  displayName: string;
  displayPath: string;
  revision: number;
  rootRef: string;
  status: "active";
};

type RegistryRecord = {
  accountId: string;
  canonicalPath: string;
  createdAt: string;
  displayName: string;
  revision: number;
  rootRef: string;
  status: "active" | "revoked";
  updatedAt: string;
};

type RegistryFile = {
  revision: number;
  roots: RegistryRecord[];
  schemaVersion: 1;
};

export async function registerE2eWorkspaceRoot(
  accountId: string
): Promise<E2eWorkspaceRoot> {
  const state = readE2eRuntimeState();
  const rootPath = path.join(state.dataDirectory, "selected-roots", accountId);
  await mkdir(rootPath, { recursive: true });
  const registry = JSON.parse(
    await readFile(state.workspaceRootRegistryPath, "utf8")
  ) as RegistryFile;
  const existing = registry.roots.find(
    (item) => item.accountId === accountId && item.status === "active"
  );
  const record = existing ?? createRecord(accountId, rootPath);
  if (!existing) {
    registry.roots.push(record);
    registry.revision += 1;
    const temporary = `${state.workspaceRootRegistryPath}.tmp`;
    await writeFile(temporary, JSON.stringify(registry, null, 2), "utf8");
    await rename(temporary, state.workspaceRootRegistryPath);
  }
  return {
    displayName: record.displayName,
    displayPath: record.canonicalPath,
    revision: record.revision,
    rootRef: record.rootRef,
    status: "active"
  };
}

function createRecord(accountId: string, rootPath: string): RegistryRecord {
  const now = new Date().toISOString();
  return {
    accountId,
    canonicalPath: path.resolve(rootPath),
    createdAt: now,
    displayName: "E2E 账号工作目录",
    revision: 1,
    rootRef: `wr_${createHash("sha256").update(accountId).digest("hex").slice(0, 32)}`,
    status: "active",
    updatedAt: now
  };
}
