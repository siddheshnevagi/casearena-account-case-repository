import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function CaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [caseItem, setCaseItem] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api
      .get(`/cases/${id}`)
      .then((res) => setCaseItem(res.data))
      .catch(() => setError("This case doesn't exist or isn't visible to you."));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleShareToggle() {
    setBusy(true);
    try {
      const endpoint = caseItem.is_shared ? "withdraw" : "share";
      const { data } = await api.post(`/cases/${id}/${endpoint}`);
      setCaseItem(data);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm("Delete this case? This cannot be undone.")) return;
    setBusy(true);
    try {
      await api.delete(`/cases/${id}`);
      navigate("/repository");
    } finally {
      setBusy(false);
    }
  }

  async function handlePractice() {
    setBusy(true);
    try {
      const { data } = await api.post(`/cases/${id}/practice`);
      setCaseItem(data);
    } finally {
      setBusy(false);
    }
  }

  async function handleModerate() {
    const reason = window.prompt("Reason for removing this case:");
    if (!reason) return;
    setBusy(true);
    try {
      await api.patch(`/cases/${id}/moderate`, { removal_reason: reason });
      navigate("/repository");
    } finally {
      setBusy(false);
    }
  }

  if (error) return <p className="text-sm text-rose-600">{error}</p>;
  if (!caseItem) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="mx-auto max-w-2xl rounded-lg border border-slate-200 bg-white p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{caseItem.title}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {caseItem.case_type.replaceAll("_", " ")} · {caseItem.difficulty}
            {caseItem.industry ? ` · ${caseItem.industry}` : ""}
          </p>
        </div>
        {caseItem.is_shared && (
          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
            Shared
          </span>
        )}
      </div>

      <p className="mt-4 text-sm text-slate-600">
        Contributed by {caseItem.contributor} · {caseItem.practice_count} practice
        {caseItem.practice_count === 1 ? "" : "s"} logged
      </p>

      {caseItem.tags?.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {caseItem.tags.map((tag) => (
            <span key={tag} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="mt-6 flex flex-wrap gap-2">
        <a
          href={`${api.defaults.baseURL}/cases/${id}/file`}
          target="_blank"
          rel="noreferrer"
          className="rounded-md border border-slate-300 px-4 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          onClick={(e) => {
            // The file needs the auth header, which a plain <a> can't send —
            // fetch it as a blob and open that instead.
            e.preventDefault();
            api
              .get(`/cases/${id}/file`, { responseType: "blob" })
              .then((res) => {
                const url = URL.createObjectURL(res.data);
                window.open(url, "_blank");
              });
          }}
        >
          View PDF
        </a>

        <button
          onClick={handlePractice}
          disabled={busy}
          className="rounded-md border border-slate-300 px-4 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          Mark practised
        </button>

        {caseItem.is_owner && (
          <>
            <button
              onClick={handleShareToggle}
              disabled={busy}
              className="rounded-md border border-slate-300 px-4 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              {caseItem.is_shared ? "Withdraw from community" : "Share to community"}
            </button>
            <button
              onClick={handleDelete}
              disabled={busy}
              className="rounded-md border border-rose-300 px-4 py-1.5 text-sm text-rose-600 hover:bg-rose-50 disabled:opacity-50"
            >
              Delete
            </button>
          </>
        )}

        {user?.is_admin && !caseItem.is_owner && (
          <button
            onClick={handleModerate}
            disabled={busy}
            className="rounded-md border border-rose-300 px-4 py-1.5 text-sm text-rose-600 hover:bg-rose-50 disabled:opacity-50"
          >
            Remove (admin)
          </button>
        )}
      </div>
    </div>
  );
}
