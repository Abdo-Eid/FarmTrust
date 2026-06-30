"use client";
import { useState } from "react";
import { clsx } from "clsx";
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/FormField";
import { useAssistant, type ChatEntry } from "@/hooks/useAssistant";
import type { AssistantLine, AssistantResponse } from "@/lib/types";
import { claimTypeLabel, claimTypePill } from "@/components/report/packet-style";

const SUGGESTED = [
    "What does the satellite actually show here?",
    "How confident is this read, and on what basis?",
    "What are the limitations, and what is not covered?",
];

function SourceBadge({ response }: { response: AssistantResponse }) {
    const isLlm = response.source_mode === "llm";
    return (
        <Badge
            className={clsx(
                "text-[11px]",
                isLlm
                    ? "bg-teal-100 text-teal-800 border-teal-200"
                    : "bg-gray-100 text-gray-600 border-gray-200",
            )}
        >
            <span className="material-symbols-outlined text-xs">{isLlm ? "smart_toy" : "rule"}</span>
            {isLlm ? `${response.model ?? "model"} · grounded` : "Deterministic brief"}
        </Badge>
    );
}

// Give each rendered block its own dir="auto" so mixed Arabic/English prose
// resolves direction per paragraph (not from the wrapper) — the core bidi fix.
const MD_COMPONENTS: Components = {
    p: ({ node, ...props }) => <p dir="auto" {...props} />,
    li: ({ node, ...props }) => <li dir="auto" {...props} />,
};

// Renders assistant prose as Markdown. `unicode-bidi: plaintext` makes every
// paragraph compute its base direction from its own content (like dir=auto) and
// isolates embedded opposite-direction runs (numbers, acronyms, English words),
// so Arabic + English mix without the punctuation/number reordering glitches.
function AssistantMarkdown({ text }: { text: string }) {
    return (
        <div
            dir="auto"
            className="text-sm text-gray-800 leading-relaxed text-start [unicode-bidi:plaintext] [&_p]:mb-2 [&_p:last-child]:mb-0 [&_strong]:font-semibold [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:mb-0.5 [&_a]:text-teal-700 [&_a]:underline"
        >
            <Markdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
                {text}
            </Markdown>
        </div>
    );
}

function LineRow({ line }: { line: AssistantLine }) {
    return (
        <div className="flex items-start justify-between gap-2 py-1.5">
            <p className="text-sm text-gray-800 leading-relaxed" dir="auto">
                {line.text}
                {line.confidence && (
                    <span className="text-xs text-gray-400"> · {line.confidence}</span>
                )}
            </p>
            <Badge className={clsx("flex-shrink-0 text-[10px] capitalize", claimTypePill(line.claim_type))}>
                {claimTypeLabel(line.claim_type)}
            </Badge>
        </div>
    );
}

function ResponseLines({ response }: { response: AssistantResponse }) {
    return (
        <div className="divide-y divide-gray-100">
            {response.lines.map((line, i) => (
                <LineRow key={`${line.source ?? "line"}-${i}`} line={line} />
            ))}
        </div>
    );
}

function ChatBubble({ entry }: { entry: ChatEntry }) {
    if (entry.role === "user") {
        return (
            <div className="flex justify-end">
                <div
                    dir="auto"
                    className="bg-teal-700 text-white rounded-lg rounded-br-sm px-3 py-2 max-w-[85%] text-sm text-start whitespace-pre-wrap [unicode-bidi:plaintext]"
                >
                    {entry.text}
                </div>
            </div>
        );
    }
    const isError = entry.isError;
    return (
        <div className="flex justify-start">
            <div
                className={clsx(
                    "rounded-lg rounded-bl-sm px-3 py-2 max-w-[92%] w-full",
                    isError ? "bg-red-50 border border-red-200" : "bg-gray-50 border border-gray-200",
                )}
            >
                {entry.response &&
                    (isError ? (
                        <p className="text-sm text-red-700 inline-flex items-center gap-1.5">
                            <span className="material-symbols-outlined text-base">error</span>
                            {entry.response.lines[0]?.text}
                        </p>
                    ) : (
                        <>
                            <div className="flex justify-end mb-1">
                                <SourceBadge response={entry.response} />
                            </div>
                            <div className="space-y-2">
                                {entry.response.lines.map((line, i) => (
                                    <AssistantMarkdown key={`${line.source ?? "line"}-${i}`} text={line.text} />
                                ))}
                            </div>
                        </>
                    ))}
            </div>
        </div>
    );
}

export function AssistantPanel({ landId }: { landId: string }) {
    const { narration, narrate, narrating, narrateError, messages, send, sending } = useAssistant(landId);
    const [draft, setDraft] = useState("");

    const submit = () => {
        const q = draft.trim();
        if (!q) return;
        send(q);
        setDraft("");
    };

    return (
        <div className="space-y-4">
            {/* Narration */}
            <Card>
                <CardHeader>
                    <CardTitle>Plain-language brief</CardTitle>
                    <div className="flex items-center gap-2">
                        {narration && <SourceBadge response={narration} />}
                        <Button
                            variant="secondary"
                            size="sm"
                            icon="auto_awesome"
                            loading={narrating}
                            onClick={narrate}
                        >
                            {narration ? "Regenerate" : "Narrate this report"}
                        </Button>
                    </div>
                </CardHeader>
                {narrateError ? (
                    <p className="text-sm text-red-600">
                        Could not generate the brief. The report card above still has the full evidence.
                    </p>
                ) : narration ? (
                    <ResponseLines response={narration} />
                ) : (
                    <p className="text-sm text-gray-500">
                        Generate a grounded, plain-language read of this report — each line is tagged with where
                        it comes from. Works with no AI configured (deterministic brief).
                    </p>
                )}
            </Card>

            {/* Chat */}
            <Card>
                <CardHeader>
                    <CardTitle>Ask the assistant</CardTitle>
                    <span className="text-xs text-gray-400">Bounded to this report&apos;s evidence</span>
                </CardHeader>

                {messages.length === 0 ? (
                    <div className="mb-3">
                        <p className="text-sm text-gray-500 mb-2">
                            Ask about the evidence, confidence, or limitations. Try:
                        </p>
                        <div className="flex flex-wrap gap-2">
                            {SUGGESTED.map((q) => (
                                <button
                                    key={q}
                                    onClick={() => send(q)}
                                    disabled={sending}
                                    className="text-left text-xs text-teal-800 bg-teal-50 border border-teal-100 rounded-full px-3 py-1.5 hover:bg-teal-100 disabled:opacity-50 transition-colors"
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div className="space-y-3 mb-3 max-h-[28rem] overflow-y-auto pr-1">
                        {messages.map((entry, i) => (
                            <ChatBubble key={i} entry={entry} />
                        ))}
                        {sending && (
                            <div className="flex justify-start">
                                <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-400 inline-flex items-center gap-2">
                                    <span className="material-symbols-outlined animate-spin text-base">progress_activity</span>
                                    Reading the evidence…
                                </div>
                            </div>
                        )}
                    </div>
                )}

                <div className="flex items-end gap-2">
                    <Textarea
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                submit();
                            }
                        }}
                        rows={2}
                        placeholder="Ask about this report's evidence…"
                        className="flex-1"
                    />
                    <Button
                        variant="primary"
                        size="md"
                        icon="send"
                        loading={sending}
                        disabled={!draft.trim()}
                        onClick={submit}
                    >
                        Send
                    </Button>
                </div>
            </Card>

            <p className="text-xs text-gray-400 leading-relaxed px-1">
                Decision support only. The assistant explains the existing satellite evidence and its limits — it
                does not approve or score financing, and it cannot tell you crop identity, yield, or income. Every
                line shows its claim type and source.
            </p>
        </div>
    );
}
