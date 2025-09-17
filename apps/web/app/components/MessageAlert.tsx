'use client'

import React from 'react'

interface MessageAlertProps {
  message: string | null
  type?: 'success' | 'error' | 'info'
}

export default function MessageAlert({ message, type = 'info' }: MessageAlertProps) {
  if (!message) return null

  const getAlertClasses = () => {
    switch (type) {
      case 'success':
        return 'bg-green-50 border border-green-200 text-green-800'
      case 'error':
        return 'bg-red-50 border border-red-200 text-red-800'
      case 'info':
      default:
        return 'bg-blue-50 border border-blue-200 text-blue-800'
    }
  }

  const isSuccess = message.includes('success') || message.includes('enqueued') || message.includes('started')
  const alertType = isSuccess ? 'success' : 'error'

  return (
    <div className={`mb-4 p-4 rounded ${getAlertClasses()}`}>
      {message}
    </div>
  )
}
