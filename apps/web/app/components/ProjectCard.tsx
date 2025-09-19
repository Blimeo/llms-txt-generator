'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import type { ProjectCardProps } from '@/types'
import { getScheduleDisplayText, getProjectConfig } from '../utils/helpers'

export default function ProjectCard({ project, onDelete, deleteLoading }: ProjectCardProps) {
  const config = getProjectConfig(project)
  const router = useRouter()

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't navigate if clicking on interactive elements
    if ((e.target as HTMLElement).closest('a, button')) {
      return
    }
    router.push(`/projects/${project.id}`)
  }

  return (
    <div 
      className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
      onClick={handleCardClick}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h3 className="text-lg font-semibold">{project.name}</h3>
          <p className="text-gray-600">
            <a 
              href={project.domain} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 hover:underline"
            >
              {project.domain}
            </a>
          </p>
          {project.description && (
            <p className="text-sm text-gray-500 mt-1">{project.description}</p>
          )}
          <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
            <span>Created: {new Date(project.created_at).toLocaleDateString()}</span>
            <span>Depth: {config?.crawl_depth || 2}</span>
            <span>Schedule: {getScheduleDisplayText(config?.cron_expression || null)}</span>
          </div>
          {config?.last_run_at && (
            <div className="text-xs text-gray-400 mt-1">
              Last run: {new Date(config.last_run_at).toLocaleString()}
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
            onClick={(e) => {
              e.stopPropagation()
              onDelete(project.id)
            }}
            disabled={deleteLoading === project.id}
            className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:opacity-50"
          >
            {deleteLoading === project.id ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}
