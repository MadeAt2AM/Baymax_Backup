import { useEffect, useState } from "react";

import { DashboardError } from "../lib/dashboard";

interface PipelineRun {
  id: string;
  started_at: string;
  finished_at: string | null;
  state: string;
  reels_collected: number;
  reels_published: number;
  notes: string | null;
}

export function RunsPage() {
  const [runs, setRuns] = useState<PipelineRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const response = await fetch("/api/runs", {
          method: "GET",
          credentials: "same-origin",
        });
        if (!response.ok) {
          throw new DashboardError(response.status, `${response.status} ${response.statusText}`);
        }
        const body = (await response.json()) as { items: PipelineRun[] };
        if (!cancelled) setRuns(body.items);
      } catch (err) {
        if (!cancelled) {
          const message =
            err instanceof DashboardError ? err.message : "Failed to load runs";
          setError(message);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <h2>Pipeline runs</h2>
      {error && <p style={{ color: "#d32f2f" }}>{error}</p>}
      {runs && (
        <table className="reelsTable" style={{ width: "100%" }}>
          <thead>
            <tr>
              <th>Started</th>
              <th>State</th>
              <th>Collected</th>
              <th>Published</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 && (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", color: "#888" }}>
                  No runs yet.
                </td>
              </tr>
            )}
            {runs.map((r) => (
              <tr key={r.id}>
                <td>{r.started_at}</td>
                <td>{r.state}</td>
                <td>{r.reels_collected}</td>
                <td>{r.reels_published}</td>
                <td>{r.notes ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
