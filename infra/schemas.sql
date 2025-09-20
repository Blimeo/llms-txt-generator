-- ======================================================
-- Required extension
-- ======================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ======================================================
-- ENUMS (create if absent via DO blocks)
-- ======================================================

-- Job lifecycle states for background work (valid states):
--   QUEUED      : job created and waiting to be picked up
--   IN_PROGRESS : job being processed by a worker
--   RETRYING    : job failed but scheduled for retry
--   FAILED      : job failed and will not be retried
--   COMPLETE    : job finished successfully
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_status') THEN
    CREATE TYPE job_status AS ENUM (
      'QUEUED',
      'IN_PROGRESS',
      'RETRYING',
      'FAILED',
      'COMPLETE'
    );
  END IF;
END$$;

-- Page render modes (valid values):
--   STATIC : server returned HTML; no JS rendering required
--   JS     : page requires JS rendering (use Playwright)
--   HYBRID : partial JS; prefer static but optionally render
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'render_mode') THEN
    CREATE TYPE render_mode AS ENUM ('STATIC', 'JS', 'HYBRID');
  END IF;
END$$;


-- Artifact types for generated outputs:
--   LLMS_TXT : the generated llms.txt textual artifact
--   JSON     : JSON export of the llms.txt structured data
--   OTHER    : miscellaneous
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'artifact_type') THEN
    CREATE TYPE artifact_type AS ENUM ('LLMS_TXT', 'JSON', 'OTHER');
  END IF;
END$$;

-- ======================================================
-- PROJECTS & CONFIGURATION (projects associated with auth.users)
-- ======================================================
CREATE TABLE IF NOT EXISTS projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  -- creator / owner user id from Supabase Auth
  created_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  name text NOT NULL,
  domain text NOT NULL,
  description text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS project_configs (
  project_id uuid PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
  crawl_depth integer NOT NULL DEFAULT 2,

  -- schedule fields
  cron_expression text,          -- e.g. "0 2 * * *" or NULL if none
  last_run_at timestamptz,
  next_run_at timestamptz,
  is_enabled boolean NOT NULL DEFAULT true,

  config jsonb DEFAULT '{}'::jsonb -- any future or extension options
);

CREATE INDEX IF NOT EXISTS idx_project_configs_project ON project_configs(project_id);

CREATE TABLE IF NOT EXISTS webhooks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES projects(id) ON DELETE CASCADE,
  url text NOT NULL,
  event_types text[] NOT NULL DEFAULT ARRAY['run.complete']::text[],
  secret text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- ======================================================
-- RUNS
-- ======================================================
CREATE TABLE IF NOT EXISTS runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  initiated_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  started_at timestamptz,
  finished_at timestamptz,
  summary text,
  status job_status NOT NULL DEFAULT 'QUEUED',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  metrics jsonb DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_runs_project_status ON runs(project_id, status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);

-- ======================================================
-- PAGES (created without current_revision_id to avoid circular FK)
-- ======================================================
CREATE TABLE IF NOT EXISTS pages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  url text NOT NULL,
  path text NOT NULL,
  canonical_url text,
  last_seen_at timestamptz,
  -- current_revision_id will be added after page_revisions exists
  render_mode render_mode NOT NULL DEFAULT 'STATIC',
  discovered_at timestamptz NOT NULL DEFAULT now(),
  is_indexable boolean NOT NULL DEFAULT true,
  metadata jsonb DEFAULT '{}'::jsonb,
  UNIQUE(project_id, url)
);
CREATE INDEX IF NOT EXISTS idx_pages_project_path ON pages(project_id, path);
CREATE INDEX IF NOT EXISTS idx_pages_url_lower ON pages USING btree ((lower(url)));

-- ======================================================
-- PAGE REVISIONS
-- ======================================================
CREATE TABLE IF NOT EXISTS page_revisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  page_id uuid NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
  run_id uuid REFERENCES runs(id) ON DELETE SET NULL,
  content text,
  content_sha256 text,
  title text,
  meta_description text,
  created_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_page_revisions_page ON page_revisions(page_id);
CREATE INDEX IF NOT EXISTS idx_page_revisions_sha ON page_revisions(content_sha256);
CREATE INDEX IF NOT EXISTS idx_page_revisions_metadata_gin ON page_revisions USING gin (metadata);

-- Add current_revision_id to pages now that page_revisions exists
ALTER TABLE pages
  ADD COLUMN IF NOT EXISTS current_revision_id uuid REFERENCES page_revisions(id) ON DELETE SET NULL;

-- ======================================================
-- ARTIFACTS & EXPORTS
-- ======================================================
CREATE TABLE IF NOT EXISTS artifacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES projects(id) ON DELETE CASCADE,
  run_id uuid REFERENCES runs(id) ON DELETE SET NULL,
  type artifact_type NOT NULL DEFAULT 'LLMS_TXT',
  storage_path text,
  file_name text,
  size_bytes bigint,
  downloaded_count bigint DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_run ON artifacts(run_id);

-- ======================================================
-- WEBHOOK EVENTS (logs)
-- ======================================================
CREATE TABLE IF NOT EXISTS webhook_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  webhook_id uuid REFERENCES webhooks(id) ON DELETE SET NULL,
  event_type text NOT NULL,
  payload jsonb DEFAULT '{}'::jsonb,
  status_code integer,
  response_body text,
  attempted_at timestamptz NOT NULL DEFAULT now()
);

-- ======================================================
-- INDEXES & PERFORMANCE HINTS
-- ======================================================
CREATE INDEX IF NOT EXISTS idx_projects_metadata_gin ON projects USING gin (metadata jsonb_path_ops);

-- ======================================================
-- TRIGGER FUNCTION + TRIGGERS
-- ======================================================
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach triggers to tables that have updated_at columns
DROP TRIGGER IF EXISTS trg_projects_updated_at ON projects;
CREATE TRIGGER trg_projects_updated_at
  BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

DROP TRIGGER IF EXISTS trg_runs_updated_at ON runs;
CREATE TRIGGER trg_runs_updated_at
  BEFORE UPDATE ON runs
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
