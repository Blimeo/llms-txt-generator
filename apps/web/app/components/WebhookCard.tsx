'use client'

import React from 'react'
import type { WebhookCardProps } from '@/types'

export default function WebhookCard({ webhook, eventStatus, onToggle, onDelete }: WebhookCardProps) {
  return (
    <div className="border rounded-lg p-3">
      <div className="flex justify-between items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-gray-900 truncate">{webhook.url}</span>
            <span className={`px-2 py-1 rounded-full text-xs font-semibold flex-shrink-0 ${
              webhook.is_active 
                ? 'text-green-600 bg-green-50' 
                : 'text-gray-600 bg-gray-50'
            }`}>
              {webhook.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
          <div className="text-xs text-gray-500 space-y-1">
            <div>Last attempted: {eventStatus.lastAttempted}</div>
            {eventStatus.status && (
              <div className={`font-medium ${
                eventStatus.status === 'Success' 
                  ? 'text-green-600' 
                  : 'text-red-600'
              }`}>
                {eventStatus.status}
              </div>
            )}
          </div>
        </div>
        <div className="flex gap-1 flex-shrink-0">
          <button
            onClick={() => onToggle(webhook.id, webhook.is_active)}
            className={`px-2 py-1 rounded text-xs whitespace-nowrap ${
              webhook.is_active
                ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
                : 'bg-green-100 text-green-700 hover:bg-green-200'
            }`}
          >
            {webhook.is_active ? 'Disable' : 'Enable'}
          </button>
          <button
            onClick={() => onDelete(webhook.id)}
            className="px-2 py-1 rounded text-xs bg-red-100 text-red-700 hover:bg-red-200 whitespace-nowrap"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}
