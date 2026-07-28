import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client.js";

const CASE_TYPES = ["PROFITABILITY", "MARKET_ENTRY", "MERGERS_ACQUISITIONS", "PRICING", "OPERATIONS", "OTHER"];
const DIFFICULTIES = ["EASY", "MEDIUM", "HARD"];
const MAX_SIZE_MB = 10;

/** US-04B: upload a PDF up to 10 MB with mandatory tagging. Created
 * private by default — sharing is a separate explicit action from the
 * case detail page. */
export default function Upload() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [caseType, setCaseType] = useState(CASE_TYPES[0]);
  const [difficulty, setDifficulty] = useState(DIFFICULTIES[0]);
  const [industry, setIndustry] = useState("");
  const [tags, setTags] = useState("");
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function handleFileChange(e) {
    const selected = e.target.files?.[0];
    setError("");
    if (selected && selected.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`File exceeds the ${MAX_SIZE_MB} MB limit.`);
      setFile(null);
      return;
    }
    if (selected && selected.type !== "application/pdf") {
      setError("Only PDF files are accepted.");
      setFile(null);
      return;
    }
    setFile(selected || null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) {
      setError("Choose a PDF file to upload.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", title);
      formData.append("case_type", caseType);
      formData.append("difficulty", difficulty);
      if (industry) formData.append("industry", industry);
      if (tags) formData.append("tags", tags);

      const { data } = await api.post("/cases", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      navigate(`/cases/${data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="text-xl font-semibold text-slate-900">Upload a case</h1>
      <p className="mt-1 text-sm text-slate-500">
        PDF only, up to {MAX_SIZE_MB} MB. Saved to your personal repository — share it to the community
        afterwards if you'd like.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700">Title</label>
          <input
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-slate-700">Case type</label>
            <select
              value={caseType}
              onChange={(e) => setCaseType(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            >
              {CASE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Difficulty</label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            >
              {DIFFICULTIES.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">Industry (optional)</label>
          <input
            type="text"
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">Tags (optional, comma-separated)</label>
          <input
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">PDF file</label>
          <input
            type="file"
            accept="application/pdf"
            required
            onChange={handleFileChange}
            className="mt-1 w-full text-sm"
          />
        </div>

        {error && <p className="text-sm text-rose-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-slate-900 px-4 py-2 text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {submitting ? "Uploading…" : "Upload case"}
        </button>
      </form>
    </div>
  );
}
