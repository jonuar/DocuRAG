export type Technology = { key: string; name: string; chunks: number };
export type TechnologiesResponse = { technologies: Technology[]; total_chunks: number };

export type ChatMode = "rag" | "agent";

export type SourceItem = { url: string; technology?: string; section?: string };
export type ChatResponse = { answer: string; sources: SourceItem[]; latency_ms: number };

export async function fetchTechnologies(signal?: AbortSignal): Promise<TechnologiesResponse> {
  const res = await fetch("/api/v1/technologies", { signal });
  if (!res.ok) throw new Error(`Failed to load technologies (${res.status})`);
  return res.json();
}

export async function sendChat(
  message: string,
  technology: string | null,
  mode: ChatMode,
  signal?: AbortSignal
): Promise<ChatResponse> {
  const res = await fetch("/api/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, technology: technology ?? undefined, mode }),
    signal,
  });
  if (!res.ok) throw new Error(`Chat failed (${res.status})`);
  return res.json();
}

