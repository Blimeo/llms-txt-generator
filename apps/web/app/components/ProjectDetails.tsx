'use client'

import React from 'react'
import type { ProjectDetailsProps, Run } from '@/types'
import { getScheduleDisplayText, getProjectConfig } from '../utils/helpers'

export default function ProjectDetails({ 
  project, 
  lastCompleteRun, 
  onGenerateRun, 
  generating, 
  onManualRefresh, 
  autoRefresh 
}: ProjectDetailsProps) {
  const config = getProjectConfig(project)

  return (
    <div className="bg-white border rounded-lg p-4 mb-6">
      <h2 className="text-lg font-semibold mb-4 text-gray-900">Project Details</h2>
      <div className="space-y-2 text-sm">
        <div>
          <span className="font-medium">Domain:</span> 
          <a 
            href={project.domain} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 hover:underline ml-1"
          >
            {project.domain}
          </a>
        </div>
        <div>
          <span className="font-medium">Created:</span> {new Date(project.created_at).toLocaleDateString()}
        </div>
        <div>
          <span className="font-medium">Crawl Depth:</span> {config?.crawl_depth || 2}
        </div>
        <div>
          <span className="font-medium">Schedule:</span> {getScheduleDisplayText(config?.cron_expression || null)}
        </div>
        {config?.last_run_at && (
          <div>
            <span className="font-medium">Last run:</span> {new Date(config.last_run_at).toLocaleString()}
          </div>
        )}
        {config?.next_run_at && (
          <div>
            <span className="font-medium">Next run:</span> {new Date(config.next_run_at).toLocaleString()}
          </div>
        )}
      </div>
    </div>
  )
}
