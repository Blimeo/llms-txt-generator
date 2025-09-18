import type { User } from '@supabase/supabase-js'

// Project related types
export interface Project {
  id: string
  name: string
  domain: string
  description: string | null
  created_at: string
  updated_at: string
  metadata: any
}

export interface ProjectConfig {
  crawl_depth: number
  cron_expression: string | null
  last_run_at: string | null
  next_run_at: string | null
  is_enabled: boolean
  config: any
}

export interface ProjectWithConfig extends Project {
  project_configs: ProjectConfig | null
}

// Run related types
export type RunStatus = 'QUEUED' | 'IN_PROGRESS' | 'RETRYING' | 'FAILED' | 'COMPLETE_NO_DIFFS' | 'COMPLETE_WITH_DIFFS'

export interface Run {
  id: string
  project_id: string
  initiated_by: string | null
  started_at: string | null
  finished_at: string | null
  summary: string | null
  status: RunStatus
  created_at: string
  updated_at: string
  metrics: any
}

// Webhook related types
export interface Webhook {
  id: string
  project_id: string
  url: string
  event_types: string[]
  secret: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface WebhookEvent {
  webhook_id: string
  attempted_at: string
  status_code: number | null
}

// Form types
export interface CreateProjectFormData {
  name: string
  domain: string
  description: string
  crawl_depth: number
  cron_expression: string
}

export interface WebhookFormData {
  url: string
  event_types: string[]
  secret: string
  is_active: boolean
}

// Component prop types
export interface NavigationProps {
  user: User | null
  onSignOut: () => void
}

export interface ProjectCardProps {
  project: ProjectWithConfig
  onDelete: (projectId: string) => void
  deleteLoading: string | null
}

export interface CreateProjectModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (formData: CreateProjectFormData) => Promise<void>
  loading: boolean
}

export interface WebhookCardProps {
  webhook: Webhook
  eventStatus: {
    lastAttempted: string
    status: string | null
  }
  onToggle: (webhookId: string, isActive: boolean) => void
  onDelete: (webhookId: string) => void
}

export interface WebhookFormProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (formData: WebhookFormData) => Promise<void>
}

export interface RunCardProps {
  run: Run
  projectId: string
  isLatest?: boolean
}

export interface ProjectDetailsProps {
  project: Project
  lastCompleteRun: Run | undefined
  onGenerateRun: () => void
  generating: boolean
  onManualRefresh: () => void
  autoRefresh: boolean
}

// Utility types
export interface MessageState {
  message: string | null
  setMessage: (message: string | null) => void
}

export interface LoadingState {
  loading: boolean
  setLoading: (loading: boolean) => void
}
