import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client.js";
import CaseCard from "../components/CaseCard.jsx";
import EmptyState from "../components/EmptyState.jsx";

const FIRM_TYPE_LABELS = {
  CONSULTING: "Consulting",
  PRODUCT_MANAGEMENT: "Product Management",
};

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/dashboard")
      .then((res) => setData(res.data))
      .catch(() => setError("Could not load your dashboard."));
  }, []);

  if (error) return <p className="text-sm text-rose-600">{error}</p>;
  if (!data) return <p className="text-sm text-slate-500">Loading…</p>;

  const { profile, recommended_cases: recommendedCases } = data;

  if (!profile.onboarding_completed) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-6">
        <p className="text-amber-800">Finish setting up your prep profile to personalize your dashboard.</p>
        <Link to="/onboarding" className="mt-3 inline-block text-sm font-medium text-amber-900 underline">
          Complete onboarding
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900">Welcome back</h1>
      <p className="mt-1 text-sm text-slate-500">
        Preparing for {FIRM_TYPE_LABELS[profile.target_firm_type] || profile.target_firm_type}
        {profile.case_preferences?.length ? ` · ${profile.case_preferences.join(", ")}` : ""}
      </p>

      <h2 className="mt-6 text-sm font-medium uppercase tracking-wide text-slate-400">
        Recommended for you
      </h2>
      {recommendedCases.length === 0 ? (
        <div className="mt-3">
          <EmptyState message="No cases in the repository yet — be the first to upload one." />
        </div>
      ) : (
        <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {recommendedCases.map((c) => (
            <CaseCard key={c.id} caseItem={c} />
          ))}
        </div>
      )}
    </div>
  );
}
