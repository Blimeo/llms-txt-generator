'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Navigation from '../../components/Navigation'
import { createClient } from '@/utils/supabase/client'
import type { User } from '@supabase/supabase-js'

interface Project {
  id: string
  name: string
  domain: string
  description: string | null
  is_public: boolean
  created_at: string
  updated_at: string
  metadata: any
  project_configs: ProjectConfig | null
}

interface ProjectConfig {
  crawl_depth: number
  cron_expression: string | null
  last_run_at: string | null
  next_run_at: string | null
  is_enabled: boolean
  config: any
}

interface Run {
  id: string
  project_id: string
  initiated_by: string | null
  started_at: string | null
  finished_at: string | null
  summary: string | null
  status: 'QUEUED' | 'IN_PROGRESS' | 'RETRYING' | 'FAILED' | 'COMPLETE_NO_DIFFS' | 'COMPLETE_WITH_DIFFS'
  created_at: string
  updated_at: string
  metrics: any
}

// Helper function to convert cron expression to display text
function getScheduleDisplayText(cronExpression: string | null): string {
  if (!cronExpression) return 'None'
  if (cronExpression === '0 2 * * *') return 'Daily'
  if (cronExpression === '0 2 * * 0') return 'Weekly'
  return 'Custom'
}

// Helper function to safely get project config (handles Supabase array response)
function getProjectConfig(project: Project): ProjectConfig | null {
  if (!project.project_configs) return null
  if (Array.isArray(project.project_configs)) {
    return project.project_configs[0] || null
  }
  return project.project_configs
}

export default function ProjectDetailPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  
  const [project, setProject] = useState<Project | null>(null)
  const [runs, setRuns] = useState<Run[]>([])
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<User | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const supabase = createClient()

  // Sign out function
  const handleSignOut = async () => {
    await supabase.auth.signOut()
    setUser(null)
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

  // Check authentication and fetch data
  useEffect(() => {
    const fetchData = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      setUser(user)
      if (user) {
        await Promise.all([fetchProject(), fetchRuns()])
      }
      setLoading(false)
    }

    fetchData()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event: any, session: any) => {
        setUser(session?.user ?? null)
        if (session?.user) {
          await Promise.all([fetchProject(), fetchRuns()])
        } else {
          setProject(null)
          setRuns([])
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

  const getStatusColor = (status: string) => {
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

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Not started'
    return new Date(dateString).toLocaleString()
  }

  // Filter runs to show only COMPLETE_WITH_DIFFS runs (llms.txt history)
  const llmsHistoryRuns = runs.filter(run => run.status === 'COMPLETE_WITH_DIFFS')
    .sort((a, b) => new Date(b.finished_at || b.created_at).getTime() - new Date(a.finished_at || a.created_at).getTime())

  // Get the last complete run (either COMPLETE_WITH_DIFFS or COMPLETE_NO_DIFFS)
  const lastCompleteRun = runs
    .filter(run => run.status === 'COMPLETE_WITH_DIFFS' || run.status === 'COMPLETE_NO_DIFFS')
    .sort((a, b) => new Date(b.finished_at || b.created_at).getTime() - new Date(a.finished_at || a.created_at).getTime())[0]

  // Get status display text
  const getStatusDisplayText = (status: string) => {
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

  if (loading) {
    return (
      <main className="p-8">
        <div className="flex items-center justify-center min-h-32">
          <div className="text-lg">Loading...</div>
        </div>
      </main>
    )
  }

  if (!user) {
    return (
      <main className="p-8">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800">
            Please sign in to view project details.
          </p>
        </div>
      </main>
    )
  }

  if (!project) {
    return (
      <main className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">
            Project not found.
          </p>
        </div>
      </main>
    )
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
            <p className="text-gray-600">{project.domain}</p>
            {project.description && (
              <p className="text-sm text-gray-500 mt-1">{project.description}</p>
            )}
          </div>

        {message && (
          <div className={`mb-4 p-4 rounded ${
            message.includes('started') || message.includes('success')
              ? 'bg-green-50 border border-green-200 text-green-800'
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}>
            {message}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Project Info */}
          <div className="lg:col-span-1">
            <div className="bg-white border rounded-lg p-4">
              <h2 className="text-lg font-semibold mb-4 text-gray-900">Project Details</h2>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium">Domain:</span> {project.domain}
                </div>
                <div>
                  <span className="font-medium">Created:</span> {new Date(project.created_at).toLocaleDateString()}
                </div>
                <div>
                  <span className="font-medium">Crawl Depth:</span> {getProjectConfig(project)?.crawl_depth || 2}
                </div>
                <div>
                  <span className="font-medium">Schedule:</span> {getScheduleDisplayText(getProjectConfig(project)?.cron_expression || null)}
                </div>
                <div>
                  <span className="font-medium">Auto-runs:</span> {getProjectConfig(project)?.is_enabled ? 'Enabled' : 'Disabled'}
                </div>
                {getProjectConfig(project)?.last_run_at && (
                  <div>
                    <span className="font-medium">Last run:</span> {new Date(getProjectConfig(project)!.last_run_at!).toLocaleString()}
                  </div>
                )}
                {getProjectConfig(project)?.next_run_at && (
                  <div>
                    <span className="font-medium">Next run:</span> {new Date(getProjectConfig(project)!.next_run_at!).toLocaleString()}
                  </div>
                )}
                {project.is_public && (
                  <div className="text-green-600 font-medium">Public Project</div>
                )}
              </div>
            </div>
          </div>

          {/* llms.txt History */}
          <div className="lg:col-span-2">
            <div className="bg-white border rounded-lg p-4">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">llms.txt History</h2>
                  {lastCompleteRun ? (
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-sm text-gray-600">Last check:</span>
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getStatusColor(lastCompleteRun.status)}`}>
                        {getStatusDisplayText(lastCompleteRun.status)}
                      </span>
                      <span className="text-sm text-gray-500">
                        {formatDate(lastCompleteRun.finished_at)}
                      </span>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-600 mt-1">
                      Generated files when changes were detected
                    </p>
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
                  {llmsHistoryRuns.map((run) => (
                    <div key={run.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                      <div className="flex justify-between items-center">
                        <div className="flex-1">
                          <span className="text-sm text-gray-500">
                            Generated {formatDate(run.finished_at)}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <a
                            href={`/api/projects/${projectId}/runs/${run.id}/llms.txt`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors font-medium"
                          >
                            📄 Download llms.txt
                          </a>
                        </div>
                      </div>
                    </div>
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

