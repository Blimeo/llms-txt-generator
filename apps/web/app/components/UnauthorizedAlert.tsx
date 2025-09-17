'use client'

import React from 'react'

interface UnauthorizedAlertProps {
  message?: string
}

export default function UnauthorizedAlert({ message = 'Please sign in to access this page.' }: UnauthorizedAlertProps) {
  return (
    <main className="p-8">
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-yellow-800">{message}</p>
      </div>
    </main>
  )
}
