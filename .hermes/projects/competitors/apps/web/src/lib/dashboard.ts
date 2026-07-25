/**
 * Dashboard domain API wrapper.
 */

import type {
  DashboardSummary,
  ReelDetail,
  ReelSummary,
} from "./types";

export class DashboardError extends Error {
  constructor(public readonly statusCode: number, message: string) {
    super(message);
    this.name = "DashboardError";
  }
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body && typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // ignore
    }
    throw new DashboardError(response.status, detail);
  }
  return (await response.json()) as T;
}

export async function fetchSummary(): Promise<DashboardSummary> {
  const response = await fetch("/api/dashboard/summary", {
    method: "GET",
    credentials: "same-origin",
  });
  return readJson<DashboardSummary>(response);
}

export async function fetchReels(params: {
  limit?: number;
  offset?: number;
  competitor?: string;
} = {}): Promise<{ items: ReelSummary[]; total: number }> {
  const search = new URLSearchParams();
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.offset !== undefined) search.set("offset", String(params.offset));
  if (params.competitor) search.set("competitor", params.competitor);
  const url = `/api/reels${search.toString() ? `?${search.toString()}` : ""}`;
  const response = await fetch(url, {
    method: "GET",
    credentials: "same-origin",
  });
  return readJson<{ items: ReelSummary[]; total: number }>(response);
}

export async function fetchReel(id: string): Promise<ReelDetail> {
  const response = await fetch(`/api/reels/${id}`, {
    method: "GET",
    credentials: "same-origin",
  });
  return readJson<ReelDetail>(response);
}
