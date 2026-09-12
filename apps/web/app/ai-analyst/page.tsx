"use client";

import { useState } from "react";
import { useBuilding } from "@/lib/building-context";
import { useAskAi } from "@/lib/hooks";
import { AiAnalysis } from "@/lib/types";
import { Badge, Button, Card, SectionTitle } from "@/components/ui";

const SUGGESTED_QUESTIONS = [
  "Why did energy increase recently?",
  "Which asset is causing the largest anomaly?",
  "What are the largest savings opportunities?",
  "What will tomorrow's demand look like?",
  "Which optimization scenario has the best cost impact?",
  "Give me an executive summary",
];

export default function AiAnalystPage() {
  const { buildingId } = useBuilding();
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<AiAnalysis[]>([]);
  const ask = useAskAi();

  async function submit(q?: string) {
    const finalQ = q ?? question;
    if (!finalQ.trim()) return;
    const result = await ask.mutateAsync({ question: finalQ, building_id: buildingId });
    setHistory((prev) => [result, ...prev]);
    setQuestion("");
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">AI Energy Analyst</h1>
      <p className="text-xs text-gray-500">
        Answers are grounded in structured evidence from the deterministic engines — the AI narrates facts, it does not
        invent them. See the evidence panel under each answer.
      </p>

      <Card>
        <div className="flex gap-2 flex-wrap mb-3">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => submit(q)}
              className="text-[11px] px-2 py-1 rounded-md border border-border text-gray-400 hover:text-accent hover:border-accent"
            >
              {q}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
          className="flex gap-2"
        >
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about energy, anomalies, waste, forecasts, optimization, or carbon…"
            className="flex-1 bg-panel border border-border rounded-md px-3 py-2 text-sm text-gray-100"
          />
          <Button type="submit" disabled={ask.isPending}>
            {ask.isPending ? "Thinking…" : "Ask"}
          </Button>
        </form>
      </Card>

      <div className="space-y-3">
        {history.map((h) => (
          <Card key={h.id}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-500">
                {h.agent.replace(/_/g, " ")} · {h.provider}
              </span>
              <Badge tone={h.confidence === "HIGH" ? "good" : h.confidence === "LOW" ? "HIGH" : "MEDIUM"}>
                {h.confidence} confidence
              </Badge>
            </div>
            <p className="text-sm text-gray-400 mb-2 italic">&ldquo;{h.question}&rdquo;</p>
            <p className="text-sm text-gray-100">{h.answer}</p>
            {h.limitations && <p className="text-[11px] text-gray-500 mt-2">Limitations: {h.limitations}</p>}
            <details className="mt-3">
              <summary className="text-xs text-accent cursor-pointer">Evidence used</summary>
              <pre className="text-[10px] text-gray-500 bg-black/30 rounded p-2 mt-2 overflow-x-auto">
                {JSON.stringify(h.evidence, null, 2)}
              </pre>
            </details>
          </Card>
        ))}
        {history.length === 0 && <p className="text-xs text-gray-500">Ask a question to get started.</p>}
      </div>
    </div>
  );
}
