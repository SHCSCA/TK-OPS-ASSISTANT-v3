import { createHash } from "node:crypto";
import {
  mkdirSync,
  readFileSync,
  renameSync,
  statSync,
  writeFileSync
} from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

export const p0hRealProviderEvidenceId = "p0-h-real-provider-execution";
export const p0hRealProviderEvidenceKind =
  "p0h_openai_compatible_real_execution";

const modulePath = fileURLToPath(import.meta.url);
const defaultRepoRoot = path.resolve(path.dirname(modulePath), "..");
const hashPattern = /^[a-f0-9]{64}$/iu;
const forbiddenKeyPattern = /^(?:credential|credentialref|apikey|authorization|headers|prompt|input|rawrequest|rawresponse|absolutepath|userprofile|cookie|token)$/iu;
const forbiddenValuePatterns = [
  /\bBearer\s+[A-Za-z0-9._~+/=-]+/iu,
  /\b(?:sk|pk|api)[-_][A-Za-z0-9_-]{16,}\b/iu,
  /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/u,
  /\b[a-z][a-z0-9+.-]*:\/\/[^\s/@]+:[^\s/@]+@/iu,
  /(?:^|[\s"'])[A-Z]:[\\/][^\s"']+/u,
  /(?:^|[\s"'])(?:\\\\[^\s\\]+\\[^\s]+|\/(?:home|Users|var|tmp|etc)\/[^\s"']+)/u,
  /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/iu,
  /(?<![A-Za-z0-9_])@[A-Za-z0-9_.-]{2,24}\b/u
];

export function buildP0HRealProviderEvidence(runtimeDocument, manifest) {
  const runtimeEvidence = unwrapRuntimeEvidence(runtimeDocument);
  assertNoSensitiveContent(runtimeEvidence);
  const provider = requireRecord(runtimeEvidence.provider, "Runtime Provider 证据缺失");
  const output = requireSuccessfulOutput(runtimeEvidence.outputs);
  const usage = aggregateUsage(runtimeEvidence.usage);
  if (
    runtimeEvidence.capabilityKey !== "script_generation"
    || runtimeEvidence.finalStatus !== "succeeded"
    || runtimeEvidence.usageReported !== true
    || provider.adapterType !== "openai_compatible"
    || provider.validationStage !== "real_small_call"
    || provider.validationStatus !== "verified"
  ) {
    throw new Error("Runtime 证据不满足真实文本执行验收条件。");
  }
  const document = {
    schemaVersion: 1,
    evidenceKind: p0hRealProviderEvidenceKind,
    appVersion: requireP0HVersion(manifest.version),
    artifactBindings: artifactBindingsFromManifest(manifest),
    provider: {
      adapterType: "openai_compatible",
      providerRefHash: requireHash(provider.providerRefHash, "Provider 引用摘要"),
      modelIdHash: requireHash(provider.modelIdHash, "模型摘要"),
      validationRunHash: requireHash(
        provider.validationRunHash,
        "验证记录摘要"
      )
    },
    execution: {
      capabilityKey: "script_generation",
      finalStatus: "succeeded",
      snapshotHash: requireHash(runtimeEvidence.snapshotHash, "执行快照摘要"),
      responseIdHash: requireHash(runtimeEvidence.responseIdHash, "响应 ID 摘要"),
      outputHash: requireHash(output.contentHash, "输出摘要"),
      durationMs: requirePositiveInteger(runtimeEvidence.durationMs, "执行耗时"),
      usage: usage.units,
      cost: usage.cost,
      responseSummary: {
        outputType: output.kind,
        schemaValid: output.schemaStatus === "valid",
        byteSize: requirePositiveInteger(output.byteSize, "输出大小")
      }
    },
    redaction: {
      passed: true,
      schemaAllowlistPassed: true
    }
  };
  return validateP0HRealProviderEvidence(document, {
    expectedArtifactBindings: artifactBindingsFromManifest(manifest),
    expectedVersion: manifest.version
  });
}

export function validateP0HRealProviderEvidence(document, options = {}) {
  const root = requireRecord(document, "P0-H 人工证据必须是 JSON 对象。");
  requireExactKeys(root, [
    "schemaVersion",
    "evidenceKind",
    "appVersion",
    "artifactBindings",
    "provider",
    "execution",
    "redaction"
  ]);
  if (
    root.schemaVersion !== 1
    || root.evidenceKind !== p0hRealProviderEvidenceKind
    || root.appVersion !== "0.5.0"
  ) {
    throw new Error("P0-H 人工证据类型或目标版本无效。");
  }
  if (options.expectedVersion && root.appVersion !== options.expectedVersion) {
    throw new Error("P0-H 人工证据未绑定当前应用版本。");
  }
  validateArtifactBindings(root.artifactBindings, options.expectedArtifactBindings);
  validateProvider(root.provider);
  validateExecution(root.execution);
  validateRedaction(root.redaction);
  assertNoSensitiveContent(root);
  return root;
}

export function prepareP0HReleaseEvidence({
  artifacts,
  evidencePath,
  evidenceRoot,
  repoRoot,
  version
}) {
  const bindings = artifactBindingsFromFiles(artifacts);
  const source = validateP0HRealProviderEvidence(readJson(evidencePath), {
    expectedArtifactBindings: bindings,
    expectedVersion: version
  });
  mkdirSync(evidenceRoot, { recursive: true });
  const copiedPath = path.join(evidenceRoot, "p0-h-real-provider-evidence.json");
  writeJsonAtomic(copiedPath, source);
  const now = new Date().toISOString();
  const wrapperPath = path.join(evidenceRoot, `${p0hRealProviderEvidenceId}.json`);
  writeJsonAtomic(wrapperPath, {
    id: p0hRealProviderEvidenceId,
    command: "人工目标机 P0-H 真实 Provider 验收",
    exitCode: 0,
    tests: 1,
    startedAt: now,
    completedAt: now,
    artifactBindings: bindings,
    evidenceKind: p0hRealProviderEvidenceKind,
    sourceEvidencePath: normalize(path.relative(repoRoot, copiedPath)),
    sourceEvidenceSha256: sha256File(copiedPath),
    redactionPassed: true
  });
  return normalize(path.relative(repoRoot, wrapperPath));
}

export function validateP0HManifestEvidence(manifest, wrapper, repoRoot) {
  if (
    wrapper.id !== p0hRealProviderEvidenceId
    || wrapper.exitCode !== 0
    || wrapper.evidenceKind !== p0hRealProviderEvidenceKind
    || wrapper.redactionPassed !== true
    || typeof wrapper.sourceEvidencePath !== "string"
    || !hashPattern.test(wrapper.sourceEvidenceSha256 || "")
  ) {
    throw new Error("P0-H 发布证据包装无效。");
  }
  const sourcePath = resolveInside(repoRoot, wrapper.sourceEvidencePath);
  if (sha256File(sourcePath) !== wrapper.sourceEvidenceSha256.toUpperCase()) {
    throw new Error("P0-H 人工证据摘要与发布包装不一致。");
  }
  return validateP0HRealProviderEvidence(readJson(sourcePath), {
    expectedArtifactBindings: artifactBindingsFromManifest(manifest),
    expectedVersion: manifest.version
  });
}

function validateArtifactBindings(value, expected) {
  const bindings = requireRecord(value, "制品绑定缺失。");
  requireExactKeys(bindings, ["desktop", "sidecar", "installer", "portable"]);
  for (const kind of ["desktop", "sidecar", "installer", "portable"]) {
    requireHash(bindings[kind], `${kind} 制品摘要`);
    if (expected && bindings[kind].toUpperCase() !== expected[kind]?.toUpperCase()) {
      throw new Error(`P0-H 人工证据未绑定当前 ${kind} 制品。`);
    }
  }
}

function validateProvider(value) {
  const provider = requireRecord(value, "Provider 证据缺失。");
  requireExactKeys(provider, [
    "adapterType",
    "providerRefHash",
    "modelIdHash",
    "validationRunHash"
  ]);
  if (provider.adapterType !== "openai_compatible") {
    throw new Error("H5 仅接受真实 OpenAI-compatible Provider 证据。");
  }
  requireHash(provider.providerRefHash, "Provider 引用摘要");
  requireHash(provider.modelIdHash, "模型摘要");
  requireHash(provider.validationRunHash, "验证记录摘要");
}

function validateExecution(value) {
  const execution = requireRecord(value, "执行证据缺失。");
  requireExactKeys(execution, [
    "capabilityKey",
    "finalStatus",
    "snapshotHash",
    "responseIdHash",
    "outputHash",
    "durationMs",
    "usage",
    "cost",
    "responseSummary"
  ]);
  if (
    execution.capabilityKey !== "script_generation"
    || execution.finalStatus !== "succeeded"
  ) {
    throw new Error("H5 只接受成功的 script_generation 执行。");
  }
  requireHash(execution.snapshotHash, "执行快照摘要");
  requireHash(execution.responseIdHash, "响应 ID 摘要");
  requireHash(execution.outputHash, "输出摘要");
  requirePositiveInteger(execution.durationMs, "执行耗时");
  validateUsage(execution.usage);
  validateCost(execution.cost);
  validateResponseSummary(execution.responseSummary);
}

function validateUsage(value) {
  const usage = requireRecord(value, "Provider reported usage 缺失。");
  requireExactKeys(usage, ["inputUnits", "outputUnits", "totalUnits"]);
  const input = requireNonNegativeInteger(usage.inputUnits, "输入用量");
  const output = requireNonNegativeInteger(usage.outputUnits, "输出用量");
  const total = requirePositiveInteger(usage.totalUnits, "总用量");
  if (total < input + output) {
    throw new Error("Provider reported usage 汇总不一致。");
  }
}

function validateCost(value) {
  const cost = requireRecord(value, "成本证据缺失。");
  const allowed = ["micros", "currency", "source"];
  if ("pricingRevision" in cost) allowed.push("pricingRevision");
  requireExactKeys(cost, allowed);
  requireNonNegativeInteger(cost.micros, "成本");
  if (typeof cost.currency !== "string" || !/^[A-Z]{3,8}$/u.test(cost.currency)) {
    throw new Error("成本币种无效。");
  }
  if (!new Set(["reported", "estimated"]).has(cost.source)) {
    throw new Error("H5 不接受 unavailable 成本证据。");
  }
  if (cost.source === "estimated") {
    requirePositiveInteger(cost.pricingRevision, "定价修订");
  } else if ("pricingRevision" in cost && cost.pricingRevision !== null) {
    requirePositiveInteger(cost.pricingRevision, "定价修订");
  }
}

function validateResponseSummary(value) {
  const summary = requireRecord(value, "响应摘要缺失。");
  requireExactKeys(summary, ["outputType", "schemaValid", "byteSize"]);
  if (!new Set(["text", "json"]).has(summary.outputType) || summary.schemaValid !== true) {
    throw new Error("AI 输出类型或 Schema 验证未通过。");
  }
  requirePositiveInteger(summary.byteSize, "输出大小");
}

function validateRedaction(value) {
  const redaction = requireRecord(value, "脱敏证据缺失。");
  requireExactKeys(redaction, ["passed", "schemaAllowlistPassed"]);
  if (redaction.passed !== true || redaction.schemaAllowlistPassed !== true) {
    throw new Error("P0-H 人工证据未通过脱敏或 allowlist 校验。");
  }
}

function aggregateUsage(value) {
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error("Provider reported usage 缺失。");
  }
  const currencies = new Set(value.map((item) => item.currency));
  const sources = new Set(value.map((item) => item.costSource));
  const pricing = new Set(
    value.map((item) => item.pricingRevision).filter((item) => item !== null)
  );
  if (
    currencies.size !== 1
    || [...sources].some((item) => !new Set(["reported", "estimated"]).has(item))
  ) {
    throw new Error("用量成本币种或来源不满足 H5 要求。");
  }
  const units = {
    inputUnits: sumRequired(value, "inputUnits"),
    outputUnits: sumRequired(value, "outputUnits"),
    totalUnits: sumRequired(value, "totalUnits")
  };
  const source = sources.has("estimated") ? "estimated" : "reported";
  const cost = {
    micros: sumRequired(value, "costMicros"),
    currency: [...currencies][0],
    source
  };
  if (source === "estimated") {
    if (pricing.size !== 1) throw new Error("估算成本缺少唯一 pricing revision。");
    cost.pricingRevision = [...pricing][0];
  }
  return { units, cost };
}

function sumRequired(items, key) {
  return items.reduce(
    (total, item) => total + requireNonNegativeInteger(item[key], key),
    0
  );
}

function requireSuccessfulOutput(value) {
  if (!Array.isArray(value)) throw new Error("AI 输出证据缺失。");
  const output = value.find(
    (item) => item?.quarantined === false && item?.schemaStatus === "valid"
  );
  if (!output) throw new Error("没有可用于 H5 的有效 AI 输出。");
  return output;
}

function artifactBindingsFromFiles(artifacts) {
  return Object.fromEntries(
    ["desktop", "sidecar", "installer", "portable"].map((kind) => {
      const filePath = artifacts?.[kind];
      if (typeof filePath !== "string" || !statSync(filePath).isFile()) {
        throw new Error(`缺少 ${kind} 制品。`);
      }
      return [kind, sha256File(filePath)];
    })
  );
}

function artifactBindingsFromManifest(manifest) {
  if (!manifest || !Array.isArray(manifest.artifacts)) {
    throw new Error("Release Manifest 制品清单缺失。");
  }
  const bindings = Object.fromEntries(
    manifest.artifacts.map((item) => [item.kind, requireHash(item.sha256, "制品摘要")])
  );
  validateArtifactBindings(bindings);
  return bindings;
}

function unwrapRuntimeEvidence(value) {
  const document = requireRecord(value, "Runtime 证据无效。");
  if (document.ok === true) return requireRecord(document.data, "Runtime data 缺失。");
  return document;
}

function assertNoSensitiveContent(value) {
  if (Array.isArray(value)) {
    value.forEach(assertNoSensitiveContent);
    return;
  }
  if (value && typeof value === "object") {
    for (const [key, item] of Object.entries(value)) {
      if (forbiddenKeyPattern.test(key.replaceAll(/[^a-z0-9]/giu, ""))) {
        throw new Error("证据包含禁止字段。");
      }
      assertNoSensitiveContent(item);
    }
    return;
  }
  if (
    typeof value === "string"
    && forbiddenValuePatterns.some((pattern) => pattern.test(value))
  ) {
    throw new Error("证据包含禁止输出的敏感值。");
  }
}

function requireRecord(value, message) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(message);
  }
  return value;
}

function requireExactKeys(value, expected) {
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  if (JSON.stringify(actual) !== JSON.stringify(wanted)) {
    throw new Error("P0-H 人工证据包含缺失或未授权字段。");
  }
}

function requireHash(value, label) {
  if (typeof value !== "string" || !hashPattern.test(value)) {
    throw new Error(`${label}无效。`);
  }
  return value.toUpperCase();
}

function requireNonNegativeInteger(value, label) {
  if (!Number.isSafeInteger(value) || value < 0) throw new Error(`${label}无效。`);
  return value;
}

function requirePositiveInteger(value, label) {
  if (!Number.isSafeInteger(value) || value <= 0) throw new Error(`${label}无效。`);
  return value;
}

function requireP0HVersion(value) {
  if (value !== "0.5.0") throw new Error("H5 证据只能绑定 0.5.0 制品。");
  return value;
}

function resolveInside(root, relativePath) {
  if (path.isAbsolute(relativePath)) throw new Error("证据路径必须是仓库内相对路径。");
  const resolved = path.resolve(root, relativePath);
  if (!resolved.startsWith(`${path.resolve(root)}${path.sep}`)) {
    throw new Error("证据路径越过仓库边界。");
  }
  return resolved;
}

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, "utf8").replace(/^\uFEFF/u, ""));
}

function writeJsonAtomic(filePath, value) {
  mkdirSync(path.dirname(filePath), { recursive: true });
  const temporaryPath = `${filePath}.tmp-${process.pid}`;
  writeFileSync(temporaryPath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  renameSync(temporaryPath, filePath);
}

function sha256File(filePath) {
  return createHash("sha256").update(readFileSync(filePath)).digest("hex").toUpperCase();
}

function normalize(value) {
  return value.replaceAll("\\", "/");
}

function parseCli(args) {
  return {
    evidence: readSingle(args, "--evidence"),
    runtimeEvidence: readSingle(args, "--runtime-evidence"),
    manifest: readSingle(args, "--manifest"),
    output: readSingle(args, "--output")
  };
}

function readSingle(args, key) {
  const index = args.indexOf(key);
  if (index < 0) return "";
  const value = args[index + 1];
  if (!value || value.startsWith("--")) throw new Error(`${key} 缺少值。`);
  return value;
}

function runCli() {
  const options = parseCli(process.argv.slice(2));
  if (options.runtimeEvidence) {
    if (!options.manifest || !options.output) {
      throw new Error("生成证据必须提供 --manifest 与 --output。");
    }
    const document = buildP0HRealProviderEvidence(
      readJson(path.resolve(options.runtimeEvidence)),
      readJson(path.resolve(options.manifest))
    );
    writeJsonAtomic(path.resolve(options.output), document);
  } else {
    if (!options.evidence || !options.manifest) {
      throw new Error("校验证据必须提供 --evidence 与 --manifest。");
    }
    const manifest = readJson(path.resolve(options.manifest));
    validateP0HRealProviderEvidence(readJson(path.resolve(options.evidence)), {
      expectedArtifactBindings: artifactBindingsFromManifest(manifest),
      expectedVersion: manifest.version
    });
  }
  process.stdout.write("[p0-h-evidence] 人工真实 Provider 证据校验通过。\n");
}

if (path.resolve(process.argv[1] || "") === modulePath) {
  try {
    runCli();
  } catch (error) {
    process.stderr.write(
      `[p0-h-evidence] 校验失败：${error instanceof Error ? error.message : "未知错误"}\n`
    );
    process.exitCode = 1;
  }
}
