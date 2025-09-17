// Helper function to convert cron expression to display text
export function getScheduleDisplayText(cronExpression: string | null): string {
  if (!cronExpression) return 'None'
  if (cronExpression === '0 2 * * *') return 'Daily'
  if (cronExpression === '0 2 * * 0') return 'Weekly'
  return 'Custom'
}

// Helper function to safely get project config (handles Supabase array response)
export function getProjectConfig(project: any) {
  if (!project.project_configs) return null
  if (Array.isArray(project.project_configs)) {
    return project.project_configs[0] || null
  }
  return project.project_configs
}

// Helper function to get status color classes
export function getStatusColor(status: string) {
  switch (status) {
    case 'COMPLETE_WITH_DIFFS': return 'text-green-600 bg-green-50'
    case 'COMPLETE_NO_DIFFS': return 'text-blue-600 bg-blue-50'
    case 'IN_PROGRESS': return 'text-orange-600 bg-orange-50'
    case 'FAILED': return 'text-red-600 bg-red-50'
    case 'RETRYING': return 'text-yellow-600 bg-yellow-50'
    case 'QUEUED': return 'text-gray-600 bg-gray-50'
    default: return 'text-gray-600 bg-gray-50'
  }
}

// Helper function to get status display text
export function getStatusDisplayText(status: string) {
  switch (status) {
    case 'COMPLETE_WITH_DIFFS': return 'Changes Detected'
    case 'COMPLETE_NO_DIFFS': return 'No Changes'
    case 'IN_PROGRESS': return 'In Progress'
    case 'FAILED': return 'Failed'
    case 'RETRYING': return 'Retrying'
    case 'QUEUED': return 'Queued'
    default: return status
  }
}

// Helper function to format dates
export function formatDate(dateString: string | null) {
  if (!dateString) return 'Not started'
  return new Date(dateString).toLocaleString()
}

// Helper function to get webhook event status
export function getWebhookEventStatus(webhookId: string, webhookEvents: Record<string, any>) {
  const event = webhookEvents[webhookId]
  if (!event) {
    return { lastAttempted: 'Not run yet', status: null }
  }
  
  const lastAttempted = formatDate(event.attempted_at)
  let status = null
  if (event.status_code !== null) {
    if (event.status_code >= 200 && event.status_code < 300) {
      status = 'Success'
    } else if (event.status_code >= 400) {
      status = 'Failure'
    }
  }
  
  return { lastAttempted, status }
}
