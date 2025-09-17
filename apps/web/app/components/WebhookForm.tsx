'use client'

import React, { useState } from 'react'
import type { WebhookFormProps, WebhookFormData } from '@/types'

export default function WebhookForm({ isOpen, onClose, onSubmit }: WebhookFormProps) {
  const [formData, setFormData] = useState<WebhookFormData>({
    url: '',
    event_types: ['run.complete'],
    secret: '',
    is_active: true
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.url) return
    
    await onSubmit(formData)
    // Reset form after successful submission
    setFormData({
      url: '',
      event_types: ['run.complete'],
      secret: '',
      is_active: true
    })
  }

  if (!isOpen) return null

  return (
    <div className="mb-4 p-4 border rounded-lg bg-gray-50">
      <h3 className="font-medium mb-3">Create New Webhook</h3>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Webhook URL *
          </label>
          <input
            type="url"
            value={formData.url}
            onChange={(e) => setFormData({ ...formData, url: e.target.value })}
            placeholder="https://your-domain.com/webhook"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Secret (optional)
          </label>
          <input
            type="text"
            value={formData.secret}
            onChange={(e) => setFormData({ ...formData, secret: e.target.value })}
            placeholder="Your webhook secret"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            The secret will be sent in the X-Webhook-Secret header for verification
          </p>
        </div>
        <div className="flex items-center">
          <input
            type="checkbox"
            id="is_active"
            checked={formData.is_active}
            onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
            className="mr-2"
          />
          <label htmlFor="is_active" className="text-sm text-gray-700">
            Active
          </label>
        </div>
        <div className="flex gap-2">
          <button
            type="submit"
            className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700"
          >
            Create Webhook
          </button>
          <button
            type="button"
            onClick={onClose}
            className="bg-gray-500 text-white px-4 py-2 rounded text-sm hover:bg-gray-600"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
