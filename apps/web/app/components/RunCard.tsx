'use client'

import React from 'react'
import type { RunCardProps } from '@/types'
import { getStatusColor, getStatusDisplayText, formatDate } from '../utils/helpers'

export default function RunCard({ run, projectId, isLatest = false }: RunCardProps) {
  return (
    <div className="border rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-center">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            {isLatest && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                Latest Version
              </span>
            )}
            <span className="text-sm text-gray-500">
              {formatDate(run.finished_at || run.started_at)}
            </span>
          </div>
        </div>
        {run.status === 'COMPLETE_WITH_DIFFS' && (
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
        )}
      </div>
    </div>
  )
}
