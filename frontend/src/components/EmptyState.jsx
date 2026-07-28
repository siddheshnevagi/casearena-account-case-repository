/** US-04 AC: "Given no cases match the applied filters, when results are
 * empty, then a clear empty state is shown with an option to reset
 * filters." */
export default function EmptyState({ message, onReset }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 p-10 text-center">
      <p className="text-slate-500">{message || "No cases match your filters."}</p>
      {onReset && (
        <button
          onClick={onReset}
          className="mt-3 rounded-md border border-slate-300 px-4 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        >
          Reset filters
        </button>
      )}
    </div>
  );
}
