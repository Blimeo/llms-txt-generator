'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { 
  Navigation, 
  ProjectDetails, 
  WebhookCard, 
  WebhookForm, 
  RunCard, 
  MessageAlert, 
  LoadingSpinner, 
  UnauthorizedAlert, 
  NotFoundAlert 
} from '../../components'
import { createClient } from '@/utils/supabase/client'
import { getWebhookEventStatus, getStatusColor, getStatusDisplayText, formatDate } from '../../utils/helpers'
import type { User } from '@supabase/supabase-js'
import type { Project, Run, Webhook, WebhookEvent, WebhookFormData } from '@/types'

export default function ProjectDetailPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  
  const [project, setProject] = useState<Project | null>(null)
  const [runs, setRuns] = useState<Run[]>([])
  const [webhooks, setWebhooks] = useState<Webhook[]>([])
  const [webhookEvents, setWebhookEvents] = useState<Record<string, WebhookEvent>>({})
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<User | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [showWebhookForm, setShowWebhookForm] = useState(false)
  const [webhookForm, setWebhookForm] = useState<WebhookFormData>({
    url: '',
    event_types: ['run.complete'],
    secret: '',
    is_active: true
  })
  const supabase = createClient()

  // Sign out function
  const handleSignOut = async () => {
    await supabase.auth.signOut()
    setUser(null)
    // Redirect to home page after signing out
    window.location.href = '/'
  }

  const fetchProject = useCallback(async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}`)
      if (response.ok) {
        const data = await response.json()
        setProject(data.project)
      } else {
        console.error('Failed to fetch project')
        router.push('/projects')
      }
    } catch (error) {
      console.error('Error fetching project:', error)
      router.push('/projects')
    }
  }, [projectId, router])

  const fetchRuns = useCallback(async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}/runs`)
      if (response.ok) {
        const data = await response.json()
        setRuns(data.runs || [])
      } else {
        console.error('Failed to fetch runs')
      }
    } catch (error) {
      console.error('Error fetching runs:', error)
    }
  }, [projectId])

  const fetchWebhooks = useCallback(async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}/webhooks`)
      if (response.ok) {
        const data = await response.json()
        setWebhooks(data.webhooks || [])
      } else {
        console.error('Failed to fetch webhooks')
      }
    } catch (error) {
      console.error('Error fetching webhooks:', error)
    }
  }, [projectId])

  const fetchWebhookEvents = useCallback(async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}/webhooks/events`)
      if (response.ok) {
        const data = await response.json()
        setWebhookEvents(data.events || {})
      } else {
        console.error('Failed to fetch webhook events')
      }
    } catch (error) {
      console.error('Error fetching webhook events:', error)
    }
  }, [projectId])

  // Check authentication and fetch data
  useEffect(() => {
    const fetchData = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      setUser(user)
      if (user) {
        await Promise.all([fetchProject(), fetchRuns(), fetchWebhooks(), fetchWebhookEvents()])
      }
      setLoading(false)
    }

    fetchData()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event: any, session: any) => {
        setUser(session?.user ?? null)
        if (session?.user) {
          await Promise.all([fetchProject(), fetchRuns(), fetchWebhooks(), fetchWebhookEvents()])
        } else {
          setProject(null)
          setRuns([])
          setWebhooks([])
          setWebhookEvents({})
        }
        setLoading(false)
      }
    )

    return () => subscription.unsubscribe()
  }, [supabase.auth, fetchProject, fetchRuns])

  // Auto-refresh effect for queued and in-progress jobs
  useEffect(() => {
    const hasActiveRuns = runs.some(run => run.status === 'IN_PROGRESS')
    
    if (hasActiveRuns && !autoRefresh) {
      setAutoRefresh(true)
    } else if (!hasActiveRuns && autoRefresh) {
      setAutoRefresh(false)
    }
  }, [runs, autoRefresh])

  // Auto-refresh timer
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      fetchRuns()
    }, 10000) // 10 seconds

    return () => clearInterval(interval)
  }, [autoRefresh, fetchRuns])

  const handleGenerateRun = async () => {
    setGenerating(true)
    setMessage(null)

    try {
      const response = await fetch(`/api/projects/${projectId}/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: project?.domain,
          priority: 'NORMAL',
          render_mode: 'STATIC'
        })
      })

      const data = await response.json()

      if (response.ok) {
        setMessage(`Generation run started! Run ID: ${data.run.id}`)
        fetchRuns() // Refresh runs list
      } else {
        setMessage(data.error || 'Failed to start generation run')
      }
    } catch (error) {
      setMessage('Error starting generation run')
    } finally {
      setGenerating(false)
    }
  }

  const handleManualRefresh = () => {
    fetchRuns()
  }

  const handleCreateWebhook = async (formData: WebhookFormData) => {
    if (!formData.url) {
      setMessage('URL is required')
      return
    }

    try {
      const response = await fetch(`/api/projects/${projectId}/webhooks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })

      const data = await response.json()

      if (response.ok) {
        setMessage('Webhook created successfully!')
        setShowWebhookForm(false)
        await Promise.all([fetchWebhooks(), fetchWebhookEvents()])
      } else {
        setMessage(data.error || 'Failed to create webhook')
      }
    } catch (error) {
      setMessage('Error creating webhook')
    }
  }

  const handleDeleteWebhook = async (webhookId: string) => {
    if (!confirm('Are you sure you want to delete this webhook?')) {
      return
    }

    try {
      const response = await fetch(`/api/projects/${projectId}/webhooks/${webhookId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        setMessage('Webhook deleted successfully!')
        await Promise.all([fetchWebhooks(), fetchWebhookEvents()])
      } else {
        const data = await response.json()
        setMessage(data.error || 'Failed to delete webhook')
      }
    } catch (error) {
      setMessage('Error deleting webhook')
    }
  }

  const handleToggleWebhook = async (webhookId: string, isActive: boolean) => {
    try {
      const response = await fetch(`/api/projects/${projectId}/webhooks/${webhookId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !isActive })
      })

      if (response.ok) {
        setMessage(`Webhook ${!isActive ? 'enabled' : 'disabled'} successfully!`)
        await Promise.all([fetchWebhooks(), fetchWebhookEvents()])
      } else {
        const data = await response.json()
        setMessage(data.error || 'Failed to update webhook')
      }
    } catch (error) {
      setMessage('Error updating webhook')
    }
  }


  // Filter runs to show only COMPLETE_WITH_DIFFS runs (llms.txt history)
  const llmsHistoryRuns = runs.filter(run => run.status === 'COMPLETE_WITH_DIFFS')
    .sort((a, b) => new Date(b.finished_at || b.created_at).getTime() - new Date(a.finished_at || a.created_at).getTime())

  // Get the last complete run (either COMPLETE_WITH_DIFFS or COMPLETE_NO_DIFFS)
  const lastCompleteRun = runs
    .filter(run => run.status === 'COMPLETE_WITH_DIFFS' || run.status === 'COMPLETE_NO_DIFFS')
    .sort((a, b) => new Date(b.finished_at || b.created_at).getTime() - new Date(a.finished_at || a.created_at).getTime())[0]

  if (loading) {
    return <LoadingSpinner message="Loading..." />
  }

  if (!user) {
    return <UnauthorizedAlert message="Please sign in to view project details." />
  }

  if (!project) {
    return <NotFoundAlert message="Project not found." />
  }

  return (
    <>
      <Navigation user={user} onSignOut={handleSignOut} />
      <main className="p-8">
        <div className="max-w-7xl mx-auto">
          <div className="mb-6">
            <div className="flex items-center gap-4 mb-2">
              <button
                onClick={() => router.push('/projects')}
                className="text-blue-600 hover:text-blue-800"
              >
                ← Back to Projects
              </button>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
            {project.description && (
              <p className="text-sm text-gray-500 mt-1">{project.description}</p>
            )}
          </div>

        <MessageAlert message={message} />

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Project Info */}
          <div className="lg:col-span-2">
            <ProjectDetails
              project={project}
              lastCompleteRun={lastCompleteRun}
              onGenerateRun={handleGenerateRun}
              generating={generating}
              onManualRefresh={handleManualRefresh}
              autoRefresh={autoRefresh}
            />

            {/* Webhooks */}
            <div className="bg-white border rounded-lg p-4">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Webhooks</h2>
                <button
                  onClick={() => setShowWebhookForm(!showWebhookForm)}
                  className="bg-blue-600 text-white px-3 py-2 rounded text-sm hover:bg-blue-700"
                >
                  {showWebhookForm ? 'Cancel' : '+ Add Webhook'}
                </button>
              </div>

              <WebhookForm
                isOpen={showWebhookForm}
                onClose={() => setShowWebhookForm(false)}
                onSubmit={handleCreateWebhook}
              />

              {webhooks.length === 0 ? (
                <div className="text-center py-4 text-gray-500 text-sm">
                  No webhooks configured. Add one to get notified when a new llms.txt is generated.
                </div>
              ) : (
                <div className="space-y-3">
                  {webhooks.map((webhook) => {
                    const eventStatus = getWebhookEventStatus(webhook.id, webhookEvents)
                    return (
                      <WebhookCard
                        key={webhook.id}
                        webhook={webhook}
                        eventStatus={eventStatus}
                        onToggle={handleToggleWebhook}
                        onDelete={handleDeleteWebhook}
                      />
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* llms.txt History */}
          <div className="lg:col-span-2">
            <div className="bg-white border rounded-lg p-4">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">llms.txt History</h2>
                  {lastCompleteRun ? (
                    <div className="mt-1">
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-gray-600">Last check:</span>
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getStatusColor(lastCompleteRun.status)}`}>
                          {getStatusDisplayText(lastCompleteRun.status)}
                        </span>
                        <span className="text-sm text-gray-500">
                          {formatDate(lastCompleteRun.finished_at)}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        "Check for changes" will enqueue a one-off run to update llms.txt and attempt to invoke all webhooks
                      </p>
                    </div>
                  ) : (
                    <div className="mt-1">
                      <p className="text-sm text-gray-600">
                        Generated files when changes were detected
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        "Check for changes" will enqueue a one-off run to update llms.txt and attempt to invoke all webhooks
                      </p>
                    </div>
                  )}
                  {autoRefresh && (
                    <p className="text-sm text-blue-600 mt-1">
                      🔄 Auto-refreshing every 10 seconds (active jobs detected)
                    </p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleManualRefresh}
                    className="px-3 py-2 border border-gray-300 rounded hover:bg-gray-50 text-sm"
                  >
                    🔄 Refresh
                  </button>
                  <button
                    onClick={handleGenerateRun}
                    disabled={generating}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {generating ? 'Starting...' : 'Check for Changes'}
                  </button>
                </div>
              </div>

              {llmsHistoryRuns.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  {runs.length === 0 
                    ? "No runs yet. Check for changes to generate your first llms.txt file!"
                    : "No llms.txt files generated yet. Changes will be detected automatically."
                  }
                </div>
              ) : (
                <div className="space-y-3">
                  {llmsHistoryRuns.map((run, index) => (
                    <RunCard
                      key={run.id}
                      run={run}
                      projectId={projectId}
                      isLatest={index === 0}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
        </div>
      </main>
    </>
  )
}

