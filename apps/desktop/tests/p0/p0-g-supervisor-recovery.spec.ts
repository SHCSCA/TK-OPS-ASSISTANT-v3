import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi
} from "vitest";

const invoke = vi.hoisted(() => vi.fn());
const listen = vi.hoisted(() => vi.fn());

vi.mock("@tauri-apps/api/core", () => ({ invoke }));
vi.mock("@tauri-apps/api/event", () => ({ listen }));

import {
  installDesktopRuntimeConnectionProvider,
  onDesktopRuntimeConnectionChanged,
  onDesktopRuntimeConnectionRecovered,
  startDesktopRuntimeSupervisorMonitoring,
  stopDesktopRuntimeSupervisorMonitoring
} from "@/app/runtime-client/connection";
import { requestRuntimeV1 } from "@/app/runtime-client/core";

type StatusListener = (event: { payload: ReturnType<typeof status> }) => void;

describe("P0-G Runtime Supervisor generation 恢复", () => {
  let statusListener: StatusListener | null;
  let generation: number;
  let supervisorState: "ready" | "starting";
  let consoleError: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    generation = 1;
    supervisorState = "ready";
    statusListener = null;
    consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {}
    });
    listen.mockImplementation(async (_eventName, listener: StatusListener) => {
      statusListener = listener;
      return vi.fn();
    });
    invoke.mockImplementation(async (command: string) => {
      if (command === "get_runtime_supervisor_status") {
        return status(supervisorState, generation);
      }
      if (command === "get_runtime_connection") {
        return {
          baseUrl: `http://127.0.0.1:${18120 + generation}`,
          generation,
          sessionToken: `token-${generation}`
        };
      }
      throw new Error(`unexpected command: ${command}`);
    });
    installDesktopRuntimeConnectionProvider();
  });

  afterEach(() => {
    stopDesktopRuntimeSupervisorMonitoring();
    invoke.mockReset();
    listen.mockReset();
    vi.unstubAllGlobals();
    Reflect.deleteProperty(window, "__TAURI_INTERNALS__");
    consoleError.mockRestore();
  });

  it("新 generation 取消旧请求、暂停写入并在新会话就绪后恢复", async () => {
    const changed = vi.fn();
    const recovered = vi.fn();
    const removeChanged = onDesktopRuntimeConnectionChanged(changed);
    const removeRecovered = onDesktopRuntimeConnectionRecovered(recovered);
    await startDesktopRuntimeSupervisorMonitoring();

    vi.stubGlobal("fetch", vi.fn((_url: string, init?: RequestInit) => {
      return new Promise<Response>((_resolve, reject) => {
        if (init?.signal?.aborted) {
          reject(init.signal.reason);
          return;
        }
        init?.signal?.addEventListener("abort", () => {
          reject(init.signal?.reason);
        });
      });
    }));
    const inFlight = requestRuntimeV1("/api/v1/accounts");
    await Promise.resolve();

    generation = 2;
    supervisorState = "starting";
    statusListener?.({ payload: status("starting", generation) });

    await expect(inFlight).rejects.toMatchObject({
      errorCode: "RUNTIME_CONNECTION_CHANGED"
    });
    await expect(
      requestRuntimeV1("/api/v1/accounts", {
        method: "POST",
        body: { displayName: "draft" }
      })
    ).rejects.toMatchObject({
      errorCode: "RUNTIME_CONNECTION_CHANGED"
    });
    expect(changed).toHaveBeenCalled();
    expect(consoleError).toHaveBeenCalled();

    supervisorState = "ready";
    statusListener?.({ payload: status("ready", generation) });
    await vi.waitFor(() => expect(recovered).toHaveBeenCalledTimes(1));

    vi.stubGlobal("fetch", vi.fn(async () => new Response(
      JSON.stringify({ ok: true, data: [] }),
      {
        headers: { "Content-Type": "application/json" },
        status: 200
      }
    )));
    await expect(requestRuntimeV1("/api/v1/accounts")).resolves.toMatchObject({
      data: []
    });

    removeChanged();
    removeRecovered();
  });
});

function status(
  state: "ready" | "starting",
  generation = 1
) {
  return {
    status: state,
    phase: state === "ready" ? "ready" : "restarting",
    baseUrl: state === "ready" ? `http://127.0.0.1:${18120 + generation}` : null,
    errorCode: null,
    generation,
    logId: null,
    restartAttempt: generation - 1,
    maxRestartAttempts: 3,
    canRestart: state === "ready",
    updatedAtEpochMs: Date.now()
  } as const;
}
