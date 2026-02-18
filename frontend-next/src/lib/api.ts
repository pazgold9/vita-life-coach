const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface StepRecord {
  module: string;
  prompt: Record<string, unknown>;
  response: Record<string, unknown>;
}

export interface ExecuteResponse {
  status: "ok" | "error";
  error: string | null;
  response: string | null;
  steps: StepRecord[];
}

export interface HistoryItem {
  id: string;
  session_id: string;
  prompt: string;
  response: string;
  created_at: string;
}

export interface ConversationTurn {
  role: "user" | "assistant";
  content: string;
}

export interface StreamEvent {
  event: string;
  specialist?: string;
  specialists?: string[];
  iteration?: number;
  message?: string;
  task?: string;
  summary?: string;
  status?: string;
  response?: string;
  steps?: StepRecord[];
  error?: string;
}

export async function executeAgentStream(
  prompt: string,
  conversationHistory: ConversationTurn[] = [],
  onEvent: (event: StreamEvent) => void,
): Promise<ExecuteResponse> {
  const res = await fetch(`${API_BASE}/api/execute_stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, conversation_history: conversationHistory }),
  });

  if (!res.ok || !res.body) {
    const text = await res.text();
    return {
      status: "error",
      error: `Server returned ${res.status}: ${text.slice(0, 200)}`,
      response: null,
      steps: [],
    };
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: ExecuteResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const event: StreamEvent = JSON.parse(line.slice(6));
        onEvent(event);

        if (event.event === "result") {
          finalResult = {
            status: (event.status as "ok" | "error") || "ok",
            error: null,
            response: event.response || null,
            steps: event.steps || [],
          };
        } else if (event.event === "error") {
          finalResult = {
            status: "error",
            error: event.error || "Unknown error",
            response: null,
            steps: [],
          };
        }
      } catch {
        // skip malformed events
      }
    }
  }

  return finalResult || { status: "error", error: "Stream ended without result", response: null, steps: [] };
}

export async function executeAgent(
  prompt: string,
  conversationHistory: ConversationTurn[] = [],
): Promise<ExecuteResponse> {
  const res = await fetch(`${API_BASE}/api/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, conversation_history: conversationHistory }),
  });

  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    return {
      status: "error",
      error: `Server returned ${res.status}: ${text.slice(0, 200)}`,
      response: null,
      steps: [],
    };
  }
}

export async function fetchHistory(): Promise<HistoryItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/history?limit=20`);
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

export interface UserProfile {
  name?: string;
  age?: number;
  sex?: string;
  weight_kg?: number;
  height_cm?: number;
  activity_level?: string;
  dietary_restrictions?: string;
  medical_conditions?: string;
  goals?: string;
}

export async function fetchProfile(): Promise<UserProfile> {
  try {
    const res = await fetch(`${API_BASE}/api/profile`);
    const data = await res.json();
    return data || {};
  } catch {
    return {};
  }
}
