"use client";
import { useCallback, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AssistantResponse, ChatTurn } from "@/lib/types";

export interface ChatEntry {
    role: "user" | "assistant";
    text?: string; // user question
    response?: AssistantResponse; // assistant turn
    isError?: boolean; // the send failed (not a real deterministic brief)
}

function assistantText(response?: AssistantResponse): string {
    return (response?.lines ?? []).map((l) => l.text).join(" ");
}

const ERROR_RESPONSE: AssistantResponse = {
    lines: [{ text: "The assistant is unavailable right now. Please try again.", claim_type: "unknown", section: "chat" }],
    source_mode: "deterministic",
    fallback_used: true,
};

export function useAssistant(landId: string) {
    const [narration, setNarration] = useState<AssistantResponse | null>(null);
    const [messages, setMessages] = useState<ChatEntry[]>([]);

    const narrateMutation = useMutation({
        mutationFn: () => api.assistant.narrate(landId),
        onSuccess: (data) => setNarration(data),
    });

    const chatMutation = useMutation({
        mutationFn: (vars: { question: string; history: ChatTurn[] }) =>
            api.assistant.chat(landId, vars),
    });

    const send = useCallback(
        (question: string) => {
            const q = question.trim();
            if (!q || chatMutation.isPending) return;
            // History = prior turns only (excludes the question being asked now).
            const history: ChatTurn[] = messages.map((m): ChatTurn =>
                m.role === "user"
                    ? { role: "user", content: m.text ?? "" }
                    : { role: "assistant", content: assistantText(m.response) },
            );
            setMessages((prev) => [...prev, { role: "user", text: q }]);
            chatMutation.mutate(
                { question: q, history },
                {
                    onSuccess: (data) => setMessages((prev) => [...prev, { role: "assistant", response: data }]),
                    onError: () =>
                        setMessages((prev) => [...prev, { role: "assistant", response: ERROR_RESPONSE, isError: true }]),
                },
            );
        },
        [messages, chatMutation],
    );

    return {
        narration,
        narrate: () => narrateMutation.mutate(),
        narrating: narrateMutation.isPending,
        narrateError: narrateMutation.isError,
        messages,
        send,
        sending: chatMutation.isPending,
    };
}
