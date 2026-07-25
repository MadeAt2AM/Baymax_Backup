import { useEffect, useState } from "react";

import { InstagramAuthBanner } from "../components/InstagramAuthBanner";
import { DashboardError, fetchSummary } from "../lib/dashboard";
import type { DashboardSummary } from "../lib/types";

import styles from "../lib/styles.module.css";

function formatSgt(iso: string | null): string {
  if (!iso) return "—";
  // The API returns SGT ISO 8601; render as-is.
  return iso;
}

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const s = await fetchSummary();
        if (!cancelled) setSummary(s);
      } catch (err) {
        if (!cancelled) {
          const message =
            err instanceof DashboardError ? err.message : "Failed to load dashboard";
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
      <InstagramAuthBanner />

      <h2>Dashboard</h2>
      {error && <p style={{ color: "#d32f2f" }}>{error}</p>}
      {summary && (
        <div className={styles.kpiGrid}>
          <div className={styles.kpiCard}>
            <div className="label">Reels</div>
            <div className="value" data-testid="kpi-reels">
              {summary.total_reels}
            </div>
          </div>
          <div className={styles.kpiCard}>
            <div className="label">Competitors</div>
            <div className="value" data-testid="kpi-competitors">
              {summary.total_competitors}
            </div>
          </div>
          <div className={styles.kpiCard}>
            <div className="label">Pipeline runs</div>
            <div className="value" data-testid="kpi-runs">
              {summary.total_pipeline_runs}
            </div>
          </div>
          <div className={styles.kpiCard}>
            <div className="label">Last run</div>
            <div className="value" style={{ fontSize: 14 }}>
              {formatSgt(summary.last_pipeline_run_at)}
            </div>
          </div>
          <div className={styles.kpiCard}>
            <div className="label">Last published</div>
            <div className="value" style={{ fontSize: 14 }}>
              {formatSgt(summary.last_published_at)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
