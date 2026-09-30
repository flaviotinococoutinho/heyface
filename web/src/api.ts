export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
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
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60_000);
  try {
    const result = await fetch("/api/v1/" + path, {
      method: method ?? (body ? "POST" : "GET"),
      signal: controller.signal,
      headers: {
        Authorization: "Bearer " + token,
        "Accept-Language": locale,
        Accept: "application/json",
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
    const content = await result.json();
    if (!result.ok)
      throw new Error(content.error?.message ?? `HTTP ${result.status}`);
    return content as T;
  } finally {
    clearTimeout(timeout);
  }
}

export async function imageBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve((reader.result as string).split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
