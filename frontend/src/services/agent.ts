import { api } from "./api";
import type { AgentChatRequest, AgentChatResponse } from "./types";

/**
 * Send a message to the LLM advertising agent and get a response.
 */
export async function chatAgent(
  message: string,
  campaignId?: number
): Promise<AgentChatResponse> {
  const body: AgentChatRequest = { message };
  if (campaignId != null) {
    body.campaign_id = campaignId;
  }
  const { data } = await api.post<AgentChatResponse>(
    "/api/agent/chat",
    body
  );
  return data;
}

/**
 * Stream the agent's response via Server-Sent Events (SSE).
 * Returns a ReadableStream<Uint8Array> for the caller to consume.
 *
 * The fetch API is used directly here (not axios) so the caller can
 * read the response body as a stream — see useSSE for a React hook
 * that wraps this.
 */
export function streamAgent(
  message: string,
  campaignId?: number
): Promise<Response> {
  const params = new URLSearchParams({ message });
  if (campaignId != null) {
    params.set("campaign_id", String(campaignId));
  }
  const url = `/api/agent/stream?${params.toString()}`;

  // Use raw fetch so the caller gets a ReadableStream via response.body
  return fetch(url, {
    headers: {
      Accept: "text/event-stream",
      "Cache-Control": "no-cache",
    },
  });
}
