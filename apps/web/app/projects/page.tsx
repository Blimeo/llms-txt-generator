'use client'

import React, { useState, useEffect } from 'react'
import { 
  Navigation, 
  ProjectCard, 
  CreateProjectModal, 
  MessageAlert, 
  LoadingSpinner, 
  UnauthorizedAlert 
} from '../components'
import { createClient } from '@/utils/supabase/client'
import type { User } from '@supabase/supabase-js'
import type { ProjectWithConfig, CreateProjectFormData } from '@/types'

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
  const [formData, setFormData] = useState<CreateProjectFormData>({
    name: '',
    domain: '',
    description: '',
    crawl_depth: 2,
    cron_expression: 'daily'
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

  const handleCreateProject = async (formData: CreateProjectFormData) => {
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
    return <LoadingSpinner message="Loading..." />
  }

  if (!user) {
    return <UnauthorizedAlert message="Please sign in to manage your projects." />
  }

  return (
    <>
      <Navigation user={user} onSignOut={handleSignOut} />
      <main className="p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-2xl font-bold">My projects</h1>
              <p className="text-gray-600 mt-1">Create and manage your tracked websites</p>
            </div>
            <button
              onClick={() => setShowCreateForm(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
            >
              Create New Project
            </button>
          </div>

      <MessageAlert message={message} />

      <CreateProjectModal
        isOpen={showCreateForm}
        onClose={() => setShowCreateForm(false)}
        onSubmit={handleCreateProject}
        loading={createLoading}
      />

      <div className="grid gap-4">
        {projects.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No projects yet. Create your first project to get started!
          </div>
        ) : (
          projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onDelete={handleDeleteProject}
              deleteLoading={deleteLoading}
            />
          ))
        )}
      </div>
        </div>
      </main>
    </>
  )
}
