import { readFile, stat } from "node:fs/promises";
import { join } from "node:path";

const lifecyclePrefix = Buffer.from("TK_OPS_LIFECYCLE ", "ascii");
const expectedLifecycle = [
  ["starting", "bootstrap"],
  ["starting", "http"],
  ["stopping", "shutdown"],
  ["stopped", "shutdown"]
];
const maxLifecycleBufferBytes = 64 * 1024;
const maxLifecycleEventBytes = 16 * 1024;
const maxLifecycleEvents = 32;
const maxStderrCharacters = 2_000;

export function createEvidenceCollector(child, secrets) {
  const lifecycle = [];
  const stdoutSecretScanner = createSecretScanner(secrets);
  const stderrSecretScanner = createSecretScanner(secrets);
  let stdoutBuffer = Buffer.alloc(0);
  let stderr = "";
  let failureMessage = null;

  child.stdout.on("data", (chunk) => {
    stdoutSecretScanner.scan(chunk);
    if (failureMessage) {
      return;
    }
    if (
      chunk.length > maxLifecycleBufferBytes
      || stdoutBuffer.length + chunk.length > maxLifecycleBufferBytes
    ) {
      failureMessage = "Runtime 生命周期缓冲超出上限";
      stdoutBuffer = Buffer.alloc(0);
      return;
    }
    stdoutBuffer = Buffer.concat([stdoutBuffer, chunk]);
    while (true) {
      const newlineIndex = stdoutBuffer.indexOf(0x0a);
      if (newlineIndex < 0) {
        break;
      }
      let line = stdoutBuffer.subarray(0, newlineIndex);
      stdoutBuffer = stdoutBuffer.subarray(newlineIndex + 1);
      if (line.at(-1) === 0x0d) {
        line = line.subarray(0, line.length - 1);
      }
      if (line.length > maxLifecycleEventBytes) {
        failureMessage = "Runtime 生命周期事件超出上限";
        stdoutBuffer = Buffer.alloc(0);
        return;
      }
      consumeLifecycleLine(line, lifecycle, (message) => {
        failureMessage = message;
      });
      if (failureMessage) {
        stdoutBuffer = Buffer.alloc(0);
        return;
      }
    }
    if (stdoutBuffer.length > maxLifecycleEventBytes) {
      failureMessage = "Runtime 未完成生命周期事件超出上限";
      stdoutBuffer = Buffer.alloc(0);
    }
  });

  child.stderr.on("data", (chunk) => {
    stderrSecretScanner.scan(chunk);
    stderr = `${stderr}${chunk.toString("utf8")}`
      .slice(-maxStderrCharacters);
  });

  return {
    assertComplete() {
      if (stdoutBuffer.length > 0 && !failureMessage) {
        failureMessage = "Runtime 存在未完成的生命周期事件";
      }
      if (failureMessage) {
        throw new Error(failureMessage);
      }
      if (
        stdoutSecretScanner.hasLeak()
        || stderrSecretScanner.hasLeak()
      ) {
        throw new Error("Runtime 进程输出泄露了会话令牌");
      }
      const actual = lifecycle.map((event) => [
        event.status,
        event.stage
      ]);
      if (JSON.stringify(actual) !== JSON.stringify(expectedLifecycle)) {
        throw new Error(
          `Runtime 生命周期顺序不符合契约：${formatLifecycle(actual)}`
        );
      }
    },
    summary() {
      const actual = lifecycle.map((event) => [
        event.status,
        event.stage
      ]);
      return (
        `lifecycle=${formatLifecycle(actual)} `
        + `stderrChars=${stderr.length}`
      );
    }
  };
}

export async function readSafeMigrationFailure(dataDir) {
  const journalPath = join(
    dataDir,
    ".runtime.db.migrations",
    "cutover-journal.json"
  );
  try {
    const file = await stat(journalPath);
    if (!file.isFile() || file.size <= 0 || file.size > 2_097_152) {
      return "";
    }
    const document = JSON.parse(await readFile(journalPath, "utf8"));
    const events = Array.isArray(document?.events) ? document.events : [];
    const lastEvent = events.at(-1);
    const event = events.findLast((item) => item?.stage === "migration_failed");
    if (!event && /^[a-z0-9_]{1,96}$/u.test(lastEvent?.stage)) {
      return `migrationStage=${lastEvent.stage}`;
    }
    const evidence = event?.evidence;
    if (!evidence || typeof evidence !== "object") {
      return "";
    }
    const errorType = /^[A-Za-z][A-Za-z0-9_]{0,95}$/u.test(
      evidence.errorType
    )
      ? evidence.errorType
      : "UnknownError";
    const currentRevision = /^[0-9]{4}_[a-z0-9_]{1,96}$/u.test(
      evidence.currentRevision
    )
      ? evidence.currentRevision
      : "unknown";
    const sqliteErrorName = /^SQLITE_[A-Z0-9_]{1,64}$/u.test(
      evidence.sqliteErrorName
    )
      ? evidence.sqliteErrorName
      : "SQLITE_UNKNOWN";
    return [
      `errorType=${errorType}`,
      `currentRevision=${currentRevision}`,
      `sqliteErrorName=${sqliteErrorName}`,
      `mutationStarted=${evidence.mutationStarted === true}`
    ].join(" ");
  } catch {
    return "";
  }
}

export async function readSafeRuntimeState(dataDir) {
  const logPath = join(dataDir, "logs", "runtime.jsonl");
  try {
    const file = await stat(logPath);
    if (!file.isFile() || file.size <= 0 || file.size > 8_388_608) {
      return "";
    }
    const lines = (await readFile(logPath, "utf8"))
      .trim()
      .split(/\r?\n/u)
      .slice(-300);
    const records = lines.flatMap((line) => {
      try {
        return [JSON.parse(line)];
      } catch {
        return [];
      }
    });
    const operations = records
      .map((record) => record?.operation)
      .filter((value) => /^[a-z0-9._-]{1,96}$/u.test(value))
      .slice(-5);
    const lastException = records
      .map((record) => record?.exception)
      .filter((value) => (
        /^[A-Za-z][A-Za-z0-9_]{0,95}: 异常详情已脱敏$/u.test(value)
      ))
      .at(-1);
    const parts = [];
    if (operations.length > 0) {
      parts.push(`operations=${operations.join(",")}`);
    }
    if (lastException) {
      parts.push(`exceptionType=${lastException.split(":", 1)[0]}`);
    }
    return parts.join(" ");
  } catch {
    return "";
  }
}

function consumeLifecycleLine(line, lifecycle, reportFailure) {
  if (!line.subarray(0, lifecyclePrefix.length).equals(lifecyclePrefix)) {
    return;
  }
  if (lifecycle.length >= maxLifecycleEvents) {
    reportFailure("Runtime 生命周期事件数量超出上限");
    return;
  }
  try {
    const event = JSON.parse(
      line.subarray(lifecyclePrefix.length).toString("utf8")
    );
    if (
      event?.kind !== "runtime_lifecycle"
      || typeof event.status !== "string"
      || typeof event.stage !== "string"
    ) {
      reportFailure("Runtime 生命周期事件结构无效");
      return;
    }
    lifecycle.push({
      stage: event.stage,
      status: event.status
    });
  } catch {
    reportFailure("Runtime 生命周期事件 JSON 无效");
  }
}

function createSecretScanner(secrets) {
  const safeSecrets = secrets.filter((value) => (
    typeof value === "string" && value.length > 0
  ));
  const tailLength = Math.max(
    0,
    ...safeSecrets.map((value) => value.length - 1)
  );
  let tail = "";
  let leaked = false;
  return {
    scan(chunk) {
      const combined = `${tail}${chunk.toString("utf8")}`;
      if (safeSecrets.some((secret) => combined.includes(secret))) {
        leaked = true;
      }
      tail = tailLength > 0
        ? combined.slice(-tailLength)
        : "";
    },
    hasLeak: () => leaked
  };
}

function formatLifecycle(sequence) {
  return sequence
    .map(([status, stage]) => `${status}/${stage}`)
    .join(" -> ");
}
