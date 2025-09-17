'use client'

import React from 'react'

interface LoadingSpinnerProps {
  message?: string
  className?: string
}

export default function LoadingSpinner({ message = 'Loading...', className = '' }: LoadingSpinnerProps) {
  return (
    <main className={`p-8 ${className}`}>
      <div className="flex items-center justify-center min-h-32">
        <div className="text-lg">{message}</div>
      </div>
    </main>
  )
}
