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

interface WorkflowMetadata {
  title: string;
  date: string;
  notes: string | null;
}

interface WorkflowResult {
  metadata: WorkflowMetadata;
  checklist: ComplianceChecklist;
}

const API_BASE = "http://localhost:8000/api/v1";
const ACCEPTED_FILE_TYPES = ".docx,.pdf";

type IntakeMode = "paste" | "upload";

async function downloadExport(format: "markdown" | "pdf", result: WorkflowResult) {
  const response = await fetch(`${API_BASE}/export/${format}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(result),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Export failed with status ${response.status}`);
  }

  const disposition = response.headers.get("content-disposition") ?? "";
  const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
  const fallbackExt = format === "markdown" ? "md" : "pdf";
  const filename = filenameMatch?.[1] ?? `workflow.${fallbackExt}`;

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function App() {
  const [intakeMode, setIntakeMode] = useState<IntakeMode>("paste");
  const [rawText, setRawText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [notes, setNotes] = useState("");

  const [result, setResult] = useState<WorkflowResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState<"markdown" | "pdf" | null>(null);

  const hasIntakeContent = intakeMode === "paste" ? rawText.trim().length > 0 : file !== null;
  const canSubmit = hasIntakeContent && title.trim().length > 0 && date.length > 0;

  function switchMode(mode: IntakeMode) {
    setIntakeMode(mode);
    setRawText("");
    setFile(null);
  }

  async function handleSubmit() {
    setError(null);
    setExportError(null);
    setResult(null);
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append("title", title);
      formData.append("date", date);
      if (notes.trim()) formData.append("notes", notes);
      if (intakeMode === "upload" && file) {
        formData.append("file", file);
      } else {
        formData.append("raw_text", rawText);
      }

      const response = await fetch(`${API_BASE}/ingest`, {
        method: "POST",
        body: formData,
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

  async function handleExport(format: "markdown" | "pdf") {
    if (!result) return;
    setExportError(null);
    setIsExporting(format);
    try {
      await downloadExport(format, result);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setIsExporting(null);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-bold text-slate-900">SME Logic Ingestion Agent</h1>
      <p className="mt-1 text-sm text-slate-500">
        Paste raw SME notes or upload a transcript below to extract a structured compliance workflow.
      </p>

      <Card className="mt-6">
        <CardContent className="space-y-4 pt-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="title" className="text-sm font-medium text-slate-700">
                Title
              </label>
              <input
                id="title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Cold Chain Intake QC"
                disabled={isLoading}
                className="mt-1 flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
            <div>
              <label htmlFor="date" className="text-sm font-medium text-slate-700">
                Date
              </label>
              <input
                id="date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                disabled={isLoading}
                className="mt-1 flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
          </div>

          <div>
            <label htmlFor="notes" className="text-sm font-medium text-slate-700">
              Notes <span className="font-normal text-slate-400">(optional)</span>
            </label>
            <input
              id="notes"
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Any context for this intake..."
              disabled={isLoading}
              className="mt-1 flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <div className="flex gap-2 border-b border-slate-200">
            <button
              type="button"
              onClick={() => switchMode("paste")}
              disabled={isLoading}
              className={
                "px-3 py-2 text-sm font-medium " +
                (intakeMode === "paste"
                  ? "border-b-2 border-slate-900 text-slate-900"
                  : "text-slate-500 hover:text-slate-700")
              }
            >
              Paste Text
            </button>
            <button
              type="button"
              onClick={() => switchMode("upload")}
              disabled={isLoading}
              className={
                "px-3 py-2 text-sm font-medium " +
                (intakeMode === "upload"
                  ? "border-b-2 border-slate-900 text-slate-900"
                  : "text-slate-500 hover:text-slate-700")
              }
            >
              Upload File
            </button>
          </div>

          {intakeMode === "paste" ? (
            <Textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="Paste SME notes here..."
              disabled={isLoading}
            />
          ) : (
            <input
              type="file"
              accept={ACCEPTED_FILE_TYPES}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              disabled={isLoading}
              className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-slate-800 disabled:opacity-50"
            />
          )}

          <Button onClick={handleSubmit} disabled={isLoading || !canSubmit}>
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
          No workflow extracted yet — fill in the form above and click "Extract Workflow".
        </p>
      )}

      {!isLoading && result && (
        <div className="mt-6 space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-start justify-between gap-4">
              <div>
                <CardTitle>{result.metadata.title}</CardTitle>
                <p className="text-sm text-slate-500">
                  {result.metadata.date} · {result.checklist.domain}
                </p>
                {result.metadata.notes && (
                  <p className="mt-1 text-sm text-slate-500">Notes: {result.metadata.notes}</p>
                )}
              </div>
              <div className="flex shrink-0 gap-2">
                <Button
                  variant="outline"
                  onClick={() => handleExport("markdown")}
                  disabled={isExporting !== null}
                >
                  {isExporting === "markdown" ? "Exporting..." : "Export Markdown"}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handleExport("pdf")}
                  disabled={isExporting !== null}
                >
                  {isExporting === "pdf" ? "Exporting..." : "Export PDF"}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-slate-400">
                AI-identified name: {result.checklist.workflow_name}
              </p>
              <p className="mt-2 text-sm text-slate-700">{result.checklist.summary_of_tacit_knowledge}</p>
            </CardContent>
          </Card>

          {exportError && (
            <div className="rounded-md border border-red-300 bg-red-50 p-4 text-sm text-red-700">
              {exportError}
            </div>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Steps</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {result.checklist.steps.map((step) => (
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

          {result.checklist.identified_risks.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Identified Risks</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                  {result.checklist.identified_risks.map((risk, i) => (
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
