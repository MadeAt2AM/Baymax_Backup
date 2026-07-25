import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { DashboardError, fetchReels } from "../lib/dashboard";
import type { ReelSummary } from "../lib/types";

import styles from "../lib/styles.module.css";

export function ReelsPage() {
  const [items, setItems] = useState<ReelSummary[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const result = await fetchReels({ limit: 50, offset: 0 });
        if (!cancelled) {
          setItems(result.items);
          setTotal(result.total);
        }
      } catch (err) {
        if (!cancelled) {
          const message =
            err instanceof DashboardError ? err.message : "Failed to load reels";
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
      <h2>Reels</h2>
      {error && <p style={{ color: "#d32f2f" }}>{error}</p>}
      {items && (
        <div className={styles.reelsTable}>
          <table>
            <thead>
              <tr>
                <th>Competitor</th>
                <th>Shortcode</th>
                <th>Published</th>
                <th>Views</th>
                <th>Likes</th>
                <th>Comments</th>
                <th>Analysis</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", color: "#888" }}>
                    No reels yet ({total} total).
                  </td>
                </tr>
              )}
              {items.map((reel) => (
                <tr key={reel.id} data-testid={`reel-row-${reel.shortcode}`}>
                  <td>@{reel.competitor_username}</td>
                  <td>
                    <Link to={`/reels/${reel.id}`}>{reel.shortcode}</Link>
                  </td>
                  <td>{reel.published_at ?? "—"}</td>
                  <td>{reel.view_count ?? "—"}</td>
                  <td>{reel.like_count ?? "—"}</td>
                  <td>{reel.comment_count ?? "—"}</td>
                  <td>{reel.has_analysis ? "✓" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
