import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

const CASE_PREFERENCE_OPTIONS = ["Profitability", "Market Entry", "M&A", "Pricing", "Operations"];

/** FR-05 (Should-have): edit profile after onboarding. Also hosts account
 * deletion, which triggers the ADR-03 anonymize-shared-cases behavior on
 * the backend. */
export default function Profile() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [firmType, setFirmType] = useState("CONSULTING");
  const [preferences, setPreferences] = useState([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get("/profile/me").then((res) => {
      setProfile(res.data);
      setFirmType(res.data.target_firm_type || "CONSULTING");
      setPreferences(res.data.case_preferences || []);
    });
  }, []);

  function togglePreference(option) {
    setPreferences((prev) => (prev.includes(option) ? prev.filter((p) => p !== option) : [...prev, option]));
  }

  async function handleSave(e) {
    e.preventDefault();
    setStatus("");
    setError("");
    setSubmitting(true);
    try {
      const { data } = await api.patch("/profile/me", {
        target_firm_type: firmType,
        case_preferences: preferences,
      });
      setProfile(data);
      setStatus("Saved.");
    } catch {
      setError("Could not save changes.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteAccount() {
    if (
      !window.confirm(
        "Delete your account? Cases you've shared stay in the community under 'Anonymous'; private cases are removed."
      )
    ) {
      return;
    }
    await api.delete("/account/me");
    logout();
    navigate("/login");
  }

  if (!profile) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="mx-auto max-w-md">
      <h1 className="text-xl font-semibold text-slate-900">Your profile</h1>

      <form onSubmit={handleSave} className="mt-6 space-y-6">
        <fieldset>
          <legend className="text-sm font-medium text-slate-700">Target firm type</legend>
          <div className="mt-2 space-y-2">
            {[
              { value: "CONSULTING", label: "Consulting" },
              { value: "PRODUCT_MANAGEMENT", label: "Product Management" },
            ].map((option) => (
              <label key={option.value} className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="radio"
                  name="firmType"
                  value={option.value}
                  checked={firmType === option.value}
                  onChange={(e) => setFirmType(e.target.value)}
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-sm font-medium text-slate-700">Case preferences</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {CASE_PREFERENCE_OPTIONS.map((option) => (
              <button
                type="button"
                key={option}
                onClick={() => togglePreference(option)}
                className={`rounded-full border px-3 py-1 text-sm ${
                  preferences.includes(option)
                    ? "border-slate-900 bg-slate-900 text-white"
                    : "border-slate-300 text-slate-600"
                }`}
              >
                {option}
              </button>
            ))}
          </div>
        </fieldset>

        {status && <p className="text-sm text-emerald-600">{status}</p>}
        {error && <p className="text-sm text-rose-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-slate-900 px-4 py-2 text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {submitting ? "Saving…" : "Save changes"}
        </button>
      </form>

      <div className="mt-10 border-t border-slate-200 pt-6">
        <h2 className="text-sm font-medium text-rose-600">Danger zone</h2>
        <button
          onClick={handleDeleteAccount}
          className="mt-2 rounded-md border border-rose-300 px-4 py-1.5 text-sm text-rose-600 hover:bg-rose-50"
        >
          Delete account
        </button>
      </div>
    </div>
  );
}
