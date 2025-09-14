'use client'

import React, { useState, useEffect } from 'react'
import Navigation from '../components/Navigation'
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
}

interface ProjectConfig {
  crawl_depth: number
  cron_expression: string | null
  last_run_at: string | null
  next_run_at: string | null
  is_enabled: boolean
  config: any
}

interface ProjectWithConfig extends Project {
  project_configs: ProjectConfig | null
}

// Helper function to convert cron expression to display text
function getScheduleDisplayText(cronExpression: string | null): string {
  if (!cronExpression) return 'None'
  if (cronExpression === '0 2 * * *') return 'Daily'
  if (cronExpression === '0 2 * * 0') return 'Weekly'
  return 'Custom'
}

// Helper function to safely get project config (handles Supabase array response)
function getProjectConfig(project: ProjectWithConfig): ProjectConfig | null {
  if (!project.project_configs) return null
  if (Array.isArray(project.project_configs)) {
    return project.project_configs[0] || null
  }
  return project.project_configs
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectWithConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<User | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [createLoading, setCreateLoading] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const supabase = createClient()

  // Sign out function
  const handleSignOut = async () => {
    await supabase.auth.signOut()
    setUser(null)
    // Redirect to home page after signing out
    window.location.href = '/'
  }

  // Form state for creating new project
  const [formData, setFormData] = useState({
    name: '',
    domain: '',
    description: '',
    is_public: false,
    crawl_depth: 2,
    cron_expression: 'daily',
    is_enabled: true
  })

  // Check authentication state on component mount
  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      setUser(user)
      if (user) {
        fetchProjects()
      }
      setLoading(false)
    }

    getUser()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        setUser(session?.user ?? null)
        if (session?.user) {
          fetchProjects()
        } else {
          setProjects([])
        }
        setLoading(false)
      }
    )

    return () => subscription.unsubscribe()
  }, [supabase.auth])

  const fetchProjects = async () => {
    try {
      const response = await fetch('/api/projects')
      if (response.ok) {
        const data = await response.json()
        setProjects(data.projects || [])
      } else {
        console.error('Failed to fetch projects')
      }
    } catch (error) {
      console.error('Error fetching projects:', error)
    }
  }

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreateLoading(true)
    setMessage(null)

    try {
      const response = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })

      const data = await response.json()

      if (response.ok) {
        setMessage('Project created successfully!')
        setShowCreateForm(false)
        setFormData({
          name: '',
          domain: '',
          description: '',
          is_public: false,
          crawl_depth: 2,
          cron_expression: 'daily',
          is_enabled: true
        })
        fetchProjects()
      } else {
        setMessage(data.error || 'Failed to create project')
      }
    } catch (error) {
      setMessage('Error creating project')
    } finally {
      setCreateLoading(false)
    }
  }

  const handleDeleteProject = async (projectId: string) => {
    if (!confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
      return
    }

    setDeleteLoading(projectId)
    setMessage(null)

    try {
      const response = await fetch(`/api/projects/${projectId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        setMessage('Project deleted successfully!')
        fetchProjects()
      } else {
        const data = await response.json()
        setMessage(data.error || 'Failed to delete project')
      }
    } catch (error) {
      setMessage('Error deleting project')
    } finally {
      setDeleteLoading(null)
    }
  }


  // Show loading state while checking authentication
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
            Please sign in to manage your projects.
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
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-2xl font-bold">Project Management</h1>
              <p className="text-gray-600 mt-1">Create and manage your website projects</p>
            </div>
            <button
              onClick={() => setShowCreateForm(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
            >
              Create New Project
            </button>
          </div>

      {message && (
        <div className={`mb-4 p-4 rounded ${
          message.includes('success') || message.includes('enqueued')
            ? 'bg-green-50 border border-green-200 text-green-800'
            : 'bg-red-50 border border-red-200 text-red-800'
        }`}>
          {message}
        </div>
      )}

      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4 text-gray-900">Create New Project</h2>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1 text-gray-900">Project Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="border rounded p-2 w-full text-gray-900"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1 text-gray-900">Domain *</label>
                <input
                  type="url"
                  value={formData.domain}
                  onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                  placeholder="https://example.com"
                  className="border rounded p-2 w-full text-gray-900"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1 text-gray-900">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="border rounded p-2 w-full text-gray-900"
                  rows={3}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1 text-gray-900">Crawl Depth</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={formData.crawl_depth}
                  onChange={(e) => setFormData({ ...formData, crawl_depth: parseInt(e.target.value) })}
                  className="border rounded p-2 w-full text-gray-900"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1 text-gray-900">Schedule</label>
                <select
                  value={formData.cron_expression}
                  onChange={(e) => setFormData({ ...formData, cron_expression: e.target.value })}
                  className="border rounded p-2 w-full text-gray-900"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="custom">Custom (disabled)</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  How often to check for changes and update llms.txt
                </p>
              </div>

              <div className="flex items-center space-x-4">
                <label className="flex items-center text-gray-900">
                  <input
                    type="checkbox"
                    checked={formData.is_public}
                    onChange={(e) => setFormData({ ...formData, is_public: e.target.checked })}
                    className="mr-2"
                  />
                  Public Project
                </label>

                <label className="flex items-center text-gray-900">
                  <input
                    type="checkbox"
                    checked={formData.is_enabled}
                    onChange={(e) => setFormData({ ...formData, is_enabled: e.target.checked })}
                    className="mr-2"
                  />
                  Enable Scheduled Runs
                </label>
              </div>

              <div className="flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="px-4 py-2 border rounded hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {createLoading ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="grid gap-4">
        {projects.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No projects yet. Create your first project to get started!
          </div>
        ) : (
          projects.map((project) => (
            <div key={project.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold">{project.name}</h3>
                  <p className="text-gray-600">{project.domain}</p>
                  {project.description && (
                    <p className="text-sm text-gray-500 mt-1">{project.description}</p>
                  )}
                  <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                    <span>Created: {new Date(project.created_at).toLocaleDateString()}</span>
                    <span>Depth: {getProjectConfig(project)?.crawl_depth || 2}</span>
                    <span>Schedule: {getScheduleDisplayText(getProjectConfig(project)?.cron_expression || null)}</span>
                    {getProjectConfig(project)?.is_enabled && <span className="text-green-600">Auto-enabled</span>}
                    {project.is_public && <span className="text-blue-600">Public</span>}
                  </div>
                  {getProjectConfig(project)?.last_run_at && (
                    <div className="text-xs text-gray-400 mt-1">
                      Last run: {new Date(getProjectConfig(project)!.last_run_at!).toLocaleString()}
                    </div>
                  )}
                </div>
                <div className="flex space-x-2">
                  <a
                    href={`/projects/${project.id}`}
                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                  >
                    View Details
                  </a>
                  <button
                    onClick={() => handleDeleteProject(project.id)}
                    disabled={deleteLoading === project.id}
                    className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:opacity-50"
                  >
                    {deleteLoading === project.id ? 'Deleting...' : 'Delete'}
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
        </div>
      </main>
    </>
  )
}
