export function resolveInternalRedirect(
  value: unknown,
  fallback: string
): string {
  if (typeof value !== "string" || value.length === 0) {
    return fallback;
  }

  try {
    const decoded = decodeURIComponent(value);
    return decoded.startsWith("/") && !decoded.startsWith("//")
      ? decoded
      : fallback;
  } catch {
    return fallback;
  }
}
