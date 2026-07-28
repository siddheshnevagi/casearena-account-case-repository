import { Link } from "react-router-dom";

const DIFFICULTY_STYLES = {
  EASY: "bg-emerald-100 text-emerald-700",
  MEDIUM: "bg-amber-100 text-amber-700",
  HARD: "bg-rose-100 text-rose-700",
};

const CASE_TYPE_LABELS = {
  PROFITABILITY: "Profitability",
  MARKET_ENTRY: "Market Entry",
  MERGERS_ACQUISITIONS: "M&A",
  PRICING: "Pricing",
  OPERATIONS: "Operations",
  OTHER: "Other",
};

/** US-04 AC: "when a case card is displayed, then it shows title, case
 * type, difficulty and contributor." Nothing more is required, but
 * practice count is shown too since it's the visible signal behind the
 * "most practised" sort option. */
export default function CaseCard({ caseItem }) {
  return (
    <Link
      to={`/cases/${caseItem.id}`}
      className="block rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-medium text-slate-900">{caseItem.title}</h3>
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
            DIFFICULTY_STYLES[caseItem.difficulty] || "bg-slate-100 text-slate-700"
          }`}
        >
          {caseItem.difficulty}
        </span>
      </div>
      <p className="mt-1 text-sm text-slate-500">
        {CASE_TYPE_LABELS[caseItem.case_type] || caseItem.case_type}
        {caseItem.industry ? ` · ${caseItem.industry}` : ""}
      </p>
      <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
        <span>by {caseItem.contributor}</span>
        <span>{caseItem.practice_count} practice{caseItem.practice_count === 1 ? "" : "s"}</span>
      </div>
    </Link>
  );
}
