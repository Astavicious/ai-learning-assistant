import type { components } from "./api-types";
export type Document = components["schemas"]["Document"];
export type Job = components["schemas"]["Job"];
export type Citation = components["schemas"]["Citation"];
export type ChatAnswer = components["schemas"]["ChatAnswer"];
export type Summary = components["schemas"]["Summary"];
export type Quiz = components["schemas"]["Quiz"];
export type FlashcardSet = components["schemas"]["FlashcardSet"];
export type Material = Summary | Quiz | FlashcardSet;
export const base = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export class SessionEnded extends Error {}
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = sessionStorage.getItem("study-token");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch(base + path, { ...init, headers });
  if (response.status === 401)
    throw new SessionEnded(
      "Your temporary session ended. Start a new session to continue.",
    );
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({
        detail: "The service is starting or unavailable. Please retry shortly.",
      }));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : "Check your selection and retry.",
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
export async function createSession() {
  const session = await api<components["schemas"]["Session"]>("/api/sessions", {
    method: "POST",
  });
  sessionStorage.setItem("study-token", session.access_token);
}
