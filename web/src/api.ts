export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const REQUEST_TIMEOUT_MS = 60_000;
export type Person = {
  id: string;
  name: string;
  sex: string;
  birth_date: string;
  state: string;
  city: string;
  face: { landmarks: number[][]; dimensions: number };
};
export type Animal = {
  id: string;
  name: string;
  species: string;
  representation: { dimensions: number };
};
export type Match = {
  person?: Person;
  animal?: Animal;
  score: number;
  distance?: number;
};
export type SearchResponse = {
  matches: Match[];
  timing_ms?: { inference: number; search: number };
};

export async function api<T>(
  path: string,
  token: string,
  locale: string,
  body?: unknown,
  method?: string,
  signal?: AbortSignal,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const result = await fetch("/api/v1/" + path, {
      method: method ?? (body ? "POST" : "GET"),
      signal: signal
        ? AbortSignal.any([controller.signal, signal])
        : controller.signal,
      headers: {
        Authorization: "Bearer " + token,
        "Accept-Language": locale,
        Accept: "application/problem+json, application/json",
        ...(body instanceof FormData
          ? {}
          : { "Content-Type": "application/json" }),
      },
      body:
        body instanceof FormData
          ? body
          : body
            ? JSON.stringify(body)
            : undefined,
    });
    if (result.status === 204) return undefined as T;
    const content = await result.json().catch(() => null);
    if (!result.ok || content === null)
      throw new Error(
        content?.detail ?? content?.error?.message ?? `HTTP ${result.status}`,
      );
    return content as T;
  } finally {
    clearTimeout(timeout);
  }
}

export function imageMultipart(file: File, metadata: object): FormData {
  const body = new FormData();
  body.set(
    "image",
    file,
    "image" + (file.type === "image/png" ? ".png" : ".jpg"),
  );
  body.set("metadata", JSON.stringify(metadata));
  return body;
}
