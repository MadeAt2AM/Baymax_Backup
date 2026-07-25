/**
 * Dashboard-domain types. Shared between the API wrapper and the
 * dashboard pages.
 */

export interface DashboardSummary {
  total_reels: number;
  total_competitors: number;
  total_pipeline_runs: number;
  last_pipeline_run_at: string | null;
  last_pipeline_run_state: string | null;
  last_published_at: string | null;
}

export interface ReelSummary {
  id: string;
  shortcode: string;
  competitor_username: string;
  published_at: string | null;
  view_count: number | null;
  like_count: number | null;
  comment_count: number | null;
  has_analysis: boolean;
  pipeline_run_id: string | null;
  created_at: string;
}

export interface ReelDetail {
  id: string;
  shortcode: string;
  competitor_username: string;
  url: string;
  caption: string | null;
  published_at: string | null;
  duration_seconds: number | null;
  view_count: number | null;
  like_count: number | null;
  comment_count: number | null;
  analysis: ReelAnalysis | null;
  pipeline_run_id: string | null;
  created_at: string;
}

export interface ReelAnalysis {
  summary: string;
  hook: string;
  emotion: string;
  pacing: string;
  notable_phrases: string[];
  recommendation: string;
  notes: string;
  source_url: string | null;
  generated_at: string;
}
