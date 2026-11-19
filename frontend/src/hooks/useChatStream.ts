"use client";

import { useState, useCallback, useEffect } from "react";
import { ChatMessage, Citation, ChatSession } from "@/lib/types";
import { streamChatMessage, sendChatMessage } from "@/lib/api";

const SESSIONS_STORAGE_KEY = "darglobal_chat_sessions_v1";

export function useChatStream() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  // Load saved sessions from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(SESSIONS_STORAGE_KEY);
      if (stored) {
        const parsed: ChatSession[] = JSON.parse(stored);
        setSessions(parsed);
      }
    } catch (e) {
      console.warn("Could not load sessions from localStorage", e);
    }
  }, []);

  // Save sessions to localStorage when updated
  const persistSessions = (updated: ChatSession[]) => {
    setSessions(updated);
    try {
      localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(updated));
    } catch (e) {
      console.warn("Could not save sessions to localStorage", e);
    }
  };

  const startNewConversation = useCallback(() => {
    setMessages([]);
    setCurrentSessionId(null);
    setSelectedCitation(null);
  }, []);

  const selectSession = useCallback(
    (sessionId: string) => {
      const target = sessions.find((s) => s.id === sessionId);
      if (target) {
        setCurrentSessionId(target.id);
        setMessages(target.messages);
      }
    },
    [sessions]
  );

  const deleteSession = useCallback(
    (sessionId: string) => {
      const updated = sessions.filter((s) => s.id !== sessionId);
      persistSessions(updated);
      if (currentSessionId === sessionId) {
        startNewConversation();
      }
    },
    [sessions, currentSessionId, startNewConversation]
  );

  const sendMessage = useCallback(
    async (userInput: string) => {
      const text = userInput.trim();
      if (!text || isLoading) return;

      const nowTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: text,
        timestamp: nowTime,
      };

      const assistantId = `assistant-${Date.now()}`;
      const placeholderAssistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        citations: [],
        execution_trace: [],
        timestamp: nowTime,
      };

      const newMessages = [...messages, userMsg, placeholderAssistantMsg];
      setMessages(newMessages);
      setIsLoading(true);

      // Session tracking
      const activeId = currentSessionId || `session-${Date.now()}`;
      if (!currentSessionId) {
        setCurrentSessionId(activeId);
      }

      // Collect prior conversation history for contextual reasoning
      const chatHistory = messages
        .filter((m) => m.content && m.content.trim() !== "")
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }));

      const requestPayload = {
        message: text,
        history: chatHistory,
        conversation_id: activeId,
        source_filter: sourceFilter !== "all" ? sourceFilter : undefined,
        top_k: 5,
      };

      let streamSucceeded = false;

      const finalizeSession = (finalMsgs: ChatMessage[]) => {
        setIsLoading(false);
        const title = text.length > 40 ? text.slice(0, 37) + "..." : text;
        const existingIdx = sessions.findIndex((s) => s.id === activeId);

        let updated: ChatSession[];
        if (existingIdx >= 0) {
          updated = [...sessions];
          updated[existingIdx] = {
            ...updated[existingIdx],
            updatedAt: new Date().toISOString(),
            messages: finalMsgs,
          };
        } else {
          updated = [
            {
              id: activeId,
              title,
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              messages: finalMsgs,
            },
            ...sessions,
          ];
        }
        persistSessions(updated);
      };

      try {
        await streamChatMessage(requestPayload, {
          onToolExecution: (toolTrace) => {
            streamSucceeded = true;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      execution_trace: [...(msg.execution_trace || []), toolTrace],
                    }
                  : msg
              )
            );
          },
          onMetadata: (meta) => {
            streamSucceeded = true;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      citations: meta.citations || [],
                      model_used: meta.model,
                      execution_trace: meta.execution_trace || msg.execution_trace || [],
                      active_filters: meta.active_filters || null,
                      intent: meta.intent || null,
                    }
                  : msg
              )
            );
          },
          onToken: (delta) => {
            streamSucceeded = true;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      content: msg.content + delta,
                    }
                  : msg
              )
            );
          },
          onDone: () => {
            setMessages((latest) => {
              finalizeSession(latest);
              return latest;
            });
          },
          onError: async (err) => {
            console.warn("SSE stream interrupted, attempting standard REST fallback:", err);
            if (!streamSucceeded) {
              try {
                const restRes = await sendChatMessage(requestPayload);
                setMessages((prev) => {
                  const updated = prev.map((msg) =>
                    msg.id === assistantId
                      ? {
                          ...msg,
                          content: restRes.answer,
                          citations: restRes.citations,
                          execution_trace: restRes.execution_trace || [],
                          model_used: restRes.model_used,
                        }
                      : msg
                  );
                  finalizeSession(updated);
                  return updated;
                });
              } catch (fallbackErr) {
                setMessages((prev) => {
                  const updated = prev.map((msg) =>
                    msg.id === assistantId
                      ? {
                          ...msg,
                          content:
                            "**Notice**: Unable to reach the DarGlobal Intelligence backend service. Please verify that the FastAPI backend is running.\n\n*Error details*: " +
                            String(fallbackErr),
                        }
                      : msg
                  );
                  finalizeSession(updated);
                  return updated;
                });
              }
            } else {
              setIsLoading(false);
            }
          },
        });
      } catch (err) {
        console.error("Chat error:", err);
        setIsLoading(false);
      }
    },
    [isLoading, sourceFilter, messages, currentSessionId, sessions]
  );

  return {
    messages,
    isLoading,
    sourceFilter,
    setSourceFilter,
    selectedCitation,
    setSelectedCitation,
    sendMessage,
    startNewConversation,
    currentSessionId,
    sessions,
    selectSession,
    deleteSession,
  };
}
