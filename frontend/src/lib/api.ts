import { ChatRequest, ChatResponse, Citation, HealthStatus, PropertyItem, ToolExecutionTrace, ActiveFilters } from "./types";

function resolveBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!envUrl) return "/api/v1";
  const clean = envUrl.trim().replace(/\/+$/, "");
  return clean.endsWith("/api/v1") ? clean : `${clean}/api/v1`;
}

const BASE_URL = resolveBaseUrl();

export async function fetchHealth(): Promise<HealthStatus> {
  const resp = await fetch(`${BASE_URL}/health`, { cache: "no-store" });
  if (!resp.ok) {
    throw new Error(`Failed to fetch health: ${resp.status}`);
  }
  return resp.json();
}

export async function fetchProperties(params?: {
  source?: string;
  city?: string;
  search?: string;
}): Promise<PropertyItem[]> {
  const query = new URLSearchParams();
  if (params?.source && params.source !== "all") query.append("source", params.source);
  if (params?.city) query.append("city", params.city);
  if (params?.search) query.append("search", params.search);

  const url = `${BASE_URL}/properties?${query.toString()}`;
  const resp = await fetch(url, { cache: "no-store" });
  if (!resp.ok) {
    throw new Error(`Failed to fetch properties: ${resp.status}`);
  }
  return resp.json();
}

export async function sendChatMessage(req: ChatRequest): Promise<ChatResponse> {
  const resp = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!resp.ok) {
    throw new Error(`Failed to send chat message: ${resp.status}`);
  }
  return resp.json();
}

export async function streamChatMessage(
  req: ChatRequest,
  handlers: {
    onToolExecution?: (toolTrace: ToolExecutionTrace) => void;
    onMetadata?: (data: {
      model: string;
      citations: Citation[];
      retrieval_count: number;
      execution_trace?: ToolExecutionTrace[];
      active_filters?: ActiveFilters | null;
      intent?: string | null;
      conversation_id?: string | null;
    }) => void;
    onToken?: (delta: string) => void;
    onDone?: () => void;
    onError?: (err: unknown) => void;
  }
): Promise<void> {
  try {
    const resp = await fetch(`${BASE_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });

    if (!resp.ok || !resp.body) {
      throw new Error(`Streaming failed: HTTP ${resp.status}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const jsonStr = line.slice(6).trim();
        if (!jsonStr) continue;

        try {
          const parsed = JSON.parse(jsonStr);
          if (parsed.type === "tool_execution" && handlers.onToolExecution) {
            handlers.onToolExecution(parsed);
          } else if (parsed.type === "metadata" && handlers.onMetadata) {
            handlers.onMetadata(parsed);
          } else if (parsed.type === "token" && handlers.onToken) {
            handlers.onToken(parsed.delta);
          } else if (parsed.type === "done" && handlers.onDone) {
            handlers.onDone();
          }
        } catch (e) {
          console.warn("Error parsing stream chunk:", e);
        }
      }
    }

    if (handlers.onDone) {
      handlers.onDone();
    }
  } catch (error) {
    if (handlers.onError) {
      handlers.onError(error);
    } else {
      console.error("Stream error:", error);
    }
  }
}
