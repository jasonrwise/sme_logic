import { useState } from "react";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Textarea } from "./components/ui/textarea";

interface WorkflowStep {
  step_number: number;
  action_name: string;
  description: string;
  actor_role: string;
  is_compliance_critical: boolean;
  deterministic_rule: string | null;
}

interface ComplianceChecklist {
  workflow_name: string;
  domain: string;
  summary_of_tacit_knowledge: string;
  steps: WorkflowStep[];
  identified_risks: string[];
}

const API_URL = "http://localhost:8000/api/v1/ingest";

export default function App() {
  const [rawText, setRawText] = useState("");
  const [result, setResult] = useState<ComplianceChecklist | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit() {
    setError(null);
    setResult(null);
    setIsLoading(true);
    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_text: rawText }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `Request failed with status ${response.status}`);
      }
      setResult(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-bold text-slate-900">SME Logic Ingestion Agent</h1>
      <p className="mt-1 text-sm text-slate-500">
        Paste raw SME notes or a transcript below to extract a structured compliance workflow.
      </p>

      <Card className="mt-6">
        <CardContent className="space-y-4 pt-4">
          <Textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            placeholder="Paste SME notes here..."
            disabled={isLoading}
          />
          <Button onClick={handleSubmit} disabled={isLoading || !rawText.trim()}>
            {isLoading ? "Extracting..." : "Extract Workflow"}
          </Button>
        </CardContent>
      </Card>

      {error && (
        <div className="mt-6 rounded-md border border-red-300 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {isLoading && (
        <div className="mt-6 space-y-4">
          <Card className="animate-pulse">
            <CardHeader>
              <div className="h-5 w-1/3 rounded bg-slate-200" />
              <div className="mt-2 h-3 w-1/5 rounded bg-slate-200" />
            </CardHeader>
            <CardContent>
              <div className="h-3 w-full rounded bg-slate-200" />
              <div className="mt-2 h-3 w-2/3 rounded bg-slate-200" />
            </CardContent>
          </Card>
          <Card className="animate-pulse">
            <CardHeader>
              <div className="h-5 w-1/4 rounded bg-slate-200" />
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="h-12 w-full rounded bg-slate-200" />
              <div className="h-12 w-full rounded bg-slate-200" />
            </CardContent>
          </Card>
        </div>
      )}

      {!isLoading && !error && !result && (
        <p className="mt-6 text-sm text-slate-400">
          No workflow extracted yet — paste notes above and click "Extract Workflow".
        </p>
      )}

      {!isLoading && result && (
        <div className="mt-6 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{result.workflow_name}</CardTitle>
              <p className="text-sm text-slate-500">{result.domain}</p>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-700">{result.summary_of_tacit_knowledge}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Steps</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {result.steps.map((step) => (
                <div
                  key={step.step_number}
                  className={
                    "rounded-md border p-3 " +
                    (step.is_compliance_critical
                      ? "border-amber-300 bg-amber-50"
                      : "border-slate-200")
                  }
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">
                      {step.step_number}. {step.action_name}
                    </span>
                    <span className="text-xs text-slate-500">{step.actor_role}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-600">{step.description}</p>
                  {step.is_compliance_critical && (
                    <p className="mt-1 text-xs font-semibold text-amber-700">
                      ⚠ Compliance-critical
                    </p>
                  )}
                  {step.deterministic_rule && (
                    <p className="mt-1 text-xs text-slate-500">Rule: {step.deterministic_rule}</p>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          {result.identified_risks.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Identified Risks</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                  {result.identified_risks.map((risk, i) => (
                    <li key={i}>{risk}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </main>
  );
}
