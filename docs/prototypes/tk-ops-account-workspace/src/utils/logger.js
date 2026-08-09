const records = [];

function append(level, message, detail) {
  const record = {
    level,
    message,
    detail: detail instanceof Error ? detail.message : detail,
    time: new Date().toISOString(),
  };
  records.push(record);
  if (level === "error") {
    console.error("[TK-OPS 原型]", message, detail);
    return;
  }
  console.info("[TK-OPS 原型]", message, detail || "");
}

export const prototypeLogger = {
  error(message, detail) {
    append("error", message, detail);
  },
  info(message, detail) {
    append("info", message, detail);
  },
  records() {
    return [...records];
  },
};
