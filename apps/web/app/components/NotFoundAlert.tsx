'use client'

import React from 'react'

interface NotFoundAlertProps {
  message?: string
}

export default function NotFoundAlert({ message = 'Resource not found.' }: NotFoundAlertProps) {
  return (
    <main className="p-8">
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{message}</p>
      </div>
    </main>
  )
}
