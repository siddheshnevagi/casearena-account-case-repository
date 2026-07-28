import { useEffect, useState } from "react";
import api from "../api/client.js";
import CaseCard from "../components/CaseCard.jsx";
import EmptyState from "../components/EmptyState.jsx";

const CASE_TYPES = ["PROFITABILITY", "MARKET_ENTRY", "MERGERS_ACQUISITIONS", "PRICING", "OPERATIONS", "OTHER"];
const DIFFICULTIES = ["EASY", "MEDIUM", "HARD"];

const DEFAULT_FILTERS = {
  case_type: "",
  difficulty: "",
  industry: "",
  q: "",
  sort: "newest",
  scope: "community",
};

/** US-04: browse, keyword search (min 3 characters), and filter by case
 * type/difficulty/industry, with a clear empty state (AC) when nothing
 * matches. */
export default function Repository() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const params = {};
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params[key] = value;
    });
    // Keyword search only fires once the user has typed at least 3
    // characters — matches the AC exactly rather than sending noise to
    // the API on every keystroke.
    if (params.q && params.q.trim().length < 3) {
      delete params.q;
    }

    api
      .get("/cases", { params })
      .then((res) => setResult(res.data))
      .catch(() => setError("Could not load the case repository."));
  }, [filters]);

  function updateFilter(key, value) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  function resetFilters() {
    setFilters(DEFAULT_FILTERS);
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900">Case repository</h1>

      <div className="mt-4 flex flex-wrap gap-3">
        <select
          value={filters.scope}
          onChange={(e) => updateFilter("scope", e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        >
          <option value="community">Community</option>
          <option value="mine">My cases</option>
        </select>
        <select
          value={filters.case_type}
          onChange={(e) => updateFilter("case_type", e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        >
          <option value="">All case types</option>
          {CASE_TYPES.map((t) => (
            <option key={t} value={t}>
              {t.replaceAll("_", " ")}
            </option>
          ))}
        </select>
        <select
          value={filters.difficulty}
          onChange={(e) => updateFilter("difficulty", e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        >
          <option value="">All difficulties</option>
          {DIFFICULTIES.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Industry"
          value={filters.industry}
          onChange={(e) => updateFilter("industry", e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        />
        <select
          value={filters.sort}
          onChange={(e) => updateFilter("sort", e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        >
          <option value="newest">Newest</option>
          <option value="most_practiced">Most practised</option>
        </select>
        <input
          type="search"
          placeholder="Search (min. 3 characters)"
          value={filters.q}
          onChange={(e) => updateFilter("q", e.target.value)}
          className="min-w-[200px] flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        />
      </div>

      {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}

      {result && (
        <div className="mt-6">
          {result.is_empty ? (
            <EmptyState onReset={resetFilters} />
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {result.items.map((c) => (
                <CaseCard key={c.id} caseItem={c} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
