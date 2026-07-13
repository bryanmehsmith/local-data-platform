const BASE_URL =
  window.__CONFIG__?.API_BASE_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000/api";
const API_KEY = window.__CONFIG__?.API_KEY || import.meta.env.VITE_API_KEY || "";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...options.headers,
    },
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${body}`);
  }
  return resp.json();
}

export const apiGet = <T>(path: string) => request<T>(path);
export const apiPost = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

// Posts to an SSE endpoint that streams frames shaped like
// `data: {"content": "..."}\n\n` and invokes onChunk with each frame's
// `content` as it arrives. Malformed frames are skipped rather than thrown,
// since a single bad frame shouldn't abort an otherwise-working stream.
export async function apiPostStream(
  path: string,
  body: unknown,
  onChunk: (content: string) => void,
): Promise<void> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${text}`);
  }
  if (!resp.body) {
    throw new Error("Streaming response has no body");
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const processFrame = (frame: string) => {
    const dataLines = frame
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim());
    if (dataLines.length === 0) return;

    const payload = dataLines.join("\n");
    if (payload === "[DONE]") return;

    try {
      const parsed = JSON.parse(payload);
      if (typeof parsed.error === "string") {
        throw new Error(parsed.error);
      }
      if (typeof parsed.content === "string") {
        onChunk(parsed.content);
      }
    } catch (err) {
      if (err instanceof SyntaxError) {
        // Not valid JSON — skip this frame rather than aborting the stream.
        return;
      }
      throw err;
    }
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      if (frame.trim()) processFrame(frame);
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) processFrame(buffer);
}
