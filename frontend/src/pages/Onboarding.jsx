import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client.js";

const CASE_PREFERENCE_OPTIONS = ["Profitability", "Market Entry", "M&A", "Pricing", "Operations"];

/** US-03: onboarding capturing target firm type (mandatory) and case
 * preferences (optional) — NFR-03 requires this be completable in under 2
 * minutes, so it's a single short form, no multi-step wizard. */
export default function Onboarding() {
  const navigate = useNavigate();
  const [firmType, setFirmType] = useState("CONSULTING");
  const [preferences, setPreferences] = useState([]);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function togglePreference(option) {
    setPreferences((prev) =>
      prev.includes(option) ? prev.filter((p) => p !== option) : [...prev, option]
    );
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await api.post("/profile/onboarding", {
        target_firm_type: firmType,
        case_preferences: preferences,
      });
      navigate("/dashboard");
    } catch {
      setError("Could not save your preferences. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="text-xl font-semibold text-slate-900">Set up your prep profile</h1>
      <p className="mt-1 text-sm text-slate-500">
        This personalizes your dashboard — you can change it anytime from Profile.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-6">
        <fieldset>
          <legend className="text-sm font-medium text-slate-700">
            Target firm type <span className="text-rose-500">*</span>
          </legend>
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
          <legend className="text-sm font-medium text-slate-700">Case preferences (optional)</legend>
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

        {error && <p className="text-sm text-rose-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-slate-900 px-4 py-2 text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {submitting ? "Saving…" : "Continue to dashboard"}
        </button>
      </form>
    </div>
  );
}
