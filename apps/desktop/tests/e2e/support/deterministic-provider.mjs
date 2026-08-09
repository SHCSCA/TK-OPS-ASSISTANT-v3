import http from "node:http";

const host = "127.0.0.1";
const port = 18121;
const expectedCredential = (
  process.env.TK_OPS_E2E_PROVIDER_CREDENTIAL || ""
).trim();
const evidence = {
  authorizedRequests: 0,
  modelsRequests: 0,
  systemStatsRequests: 0
};

if (!expectedCredential) {
  console.error("[e2e-provider] 缺少受控测试凭据。");
  process.exit(1);
}

const server = http.createServer((request, response) => {
  try {
    const url = new URL(
      request.url || "/",
      `http://${request.headers.host || `${host}:${port}`}`
    );
    if (request.method !== "GET") {
      sendJson(response, 405, { error: "method_not_allowed" });
      return;
    }
    if (url.pathname === "/__e2e__/health") {
      sendJson(response, 200, { ok: true });
      return;
    }
    if (url.pathname === "/__e2e__/evidence") {
      sendJson(response, 200, { ...evidence });
      return;
    }
    if (
      request.headers.authorization
      !== `Bearer ${expectedCredential}`
    ) {
      sendJson(response, 401, { error: "invalid_credential" });
      return;
    }
    evidence.authorizedRequests += 1;
    if (url.pathname === "/v1/models") {
      evidence.modelsRequests += 1;
      sendJson(response, 200, {
        data: [
          {
            id: "tk-e2e-text-1",
            display_name: "E2E 文本能力模型"
          }
        ]
      });
      return;
    }
    if (url.pathname === "/system_stats") {
      evidence.systemStatsRequests += 1;
      sendJson(response, 200, {
        devices: [],
        system: { runtime: "tk-ops-e2e" }
      });
      return;
    }
    sendJson(response, 404, { error: "not_found" });
  } catch (error) {
    console.error(
      `[e2e-provider] 请求处理失败：${
        error instanceof Error ? error.message : "未知错误"
      }`
    );
    sendJson(response, 500, { error: "internal_error" });
  }
});

server.on("clientError", (error, socket) => {
  console.error(`[e2e-provider] 客户端连接失败：${error.message}`);
  socket.end("HTTP/1.1 400 Bad Request\r\n\r\n");
});
server.on("error", (error) => {
  console.error(`[e2e-provider] 服务异常：${error.message}`);
  process.exitCode = 1;
});
server.listen(port, host);

function sendJson(response, statusCode, payload) {
  const body = JSON.stringify(payload);
  response.writeHead(statusCode, {
    "Content-Length": Buffer.byteLength(body),
    "Content-Type": "application/json; charset=utf-8"
  });
  response.end(body);
}
