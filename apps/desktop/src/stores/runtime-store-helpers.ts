import { RuntimeRequestError } from "@/app/runtime-client";
import type { RuntimeRequestErrorShape } from "@/types/runtime";

export type CollectionViewState = "idle" | "loading" | "empty" | "ready" | "error";

export function toRuntimeErrorShape(
  error: unknown,
  fallbackMessage: string
): RuntimeRequestErrorShape {
  const runtimeError =
    error instanceof RuntimeRequestError
      ? error
      : new RuntimeRequestError(fallbackMessage);

  return {
    details: runtimeError.details,
    message: runtimeError.message,
    requestId: runtimeError.requestId,
    status: runtimeError.status
  };
}

export function toRuntimeErrorMessage(error: unknown, fallbackMessage: string): string {
  return toRuntimeErrorShape(error, fallbackMessage).message;
}

export function resolveCollectionStatus(length: number): "empty" | "ready" {
  return length > 0 ? "ready" : "empty";
}
