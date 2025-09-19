'use client'

import React, { useState } from 'react'
import type { CreateProjectModalProps, CreateProjectFormData } from '@/types'

export default function CreateProjectModal({ isOpen, onClose, onSubmit, loading }: CreateProjectModalProps) {
  const [formData, setFormData] = useState<CreateProjectFormData>({
    name: '',
    domain: '',
    description: '',
    crawl_depth: 2,
    cron_expression: 'daily'
  })
  const [domainError, setDomainError] = useState<string | null>(null)

  // URL validation regex
  const urlRegex = /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$/

  const validateDomain = (domain: string) => {
    if (!domain.trim()) {
      setDomainError(null)
      return true
    }
    
    if (!urlRegex.test(domain)) {
      setDomainError('Please enter a valid URL (e.g., https://example.com)')
      return false
    }
    
    setDomainError(null)
    return true
  }

  const handleDomainChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setFormData({ ...formData, domain: value })
    validateDomain(value)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate domain before submission
    if (!validateDomain(formData.domain)) {
      return
    }
    
    await onSubmit(formData)
    // Reset form after successful submission
    setFormData({
      name: '',
      domain: '',
      description: '',
      crawl_depth: 2,
      cron_expression: 'daily'
    })
    setDomainError(null)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white p-6 rounded-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4 text-gray-900">Create New Project</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
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
              onChange={handleDomainChange}
              placeholder="https://example.com"
              className={`border rounded p-2 w-full text-gray-900 ${
                domainError ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''
              }`}
              required
            />
            {domainError ? (
              <p className="text-xs text-red-500 mt-1">
                {domainError}
              </p>
            ) : (
              <p className="text-xs text-gray-500 mt-1">
                Only static sites are currently supported.
              </p>
            )}
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
              max="3"
              value={formData.crawl_depth}
              onChange={(e) => setFormData({ ...formData, crawl_depth: parseInt(e.target.value) })}
              className="border rounded p-2 w-full text-gray-900"
            />
            <p className="text-xs text-gray-500 mt-1">
              How many layers deep to crawl on the website (1-3 limit)
            </p>
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
            </select>
            <p className="text-xs text-gray-500 mt-1">
              How often to check for changes and update llms.txt
            </p>
          </div>

          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !!domainError}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
