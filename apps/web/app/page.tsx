'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import OneTapComponent from './google-auth'
import Navigation from './components/Navigation'
import { createClient } from '@/utils/supabase/client'
import type { User } from '@supabase/supabase-js'

export default function HomePage() {
  const [user, setUser] = useState<User | null>(null)
  const [loadingAuth, setLoadingAuth] = useState(true)
  const router = useRouter()
  const supabase = createClient()

  // Check authentication state on component mount
  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      setUser(user)
      setLoadingAuth(false)
      
      // Redirect authenticated users to projects page
      if (user) {
        console.log('User authenticated, redirecting to projects...')
        router.replace('/projects')
      }
    }

    getUser()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event: any, session: any) => {
        console.log('Auth state change:', event, session?.user?.email)
        setUser(session?.user ?? null)
        setLoadingAuth(false)
        
        // Redirect authenticated users to projects page
        if (session?.user) {
          console.log('User authenticated via auth change, redirecting to projects...')
          router.replace('/projects')
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [supabase.auth, router])

  // Additional effect to handle redirect when user state changes
  useEffect(() => {
    if (user && !loadingAuth) {
      console.log('User state changed to authenticated, redirecting...')
      // Use both router.replace and window.location as fallback
      router.replace('/projects')
      // Fallback redirect after a short delay
      setTimeout(() => {
        if (window.location.pathname === '/') {
          console.log('Router redirect failed, using window.location fallback')
          window.location.href = '/projects'
        }
      }, 100)
    }
  }, [user, loadingAuth, router])

  // Sign out function
  const handleSignOut = async () => {
    await supabase.auth.signOut()
    setUser(null)
  }

  // Show loading state while checking authentication
  if (loadingAuth) {
    return (
      <main className="p-8">
        <div className="flex items-center justify-center min-h-32">
          <div className="text-lg">Loading...</div>
        </div>
      </main>
    )
  }

  return (
    <>
      <Navigation user={user} onSignOut={handleSignOut} />
      <main className="p-8">
        <div className="max-w-7xl mx-auto">
          {!user && <OneTapComponent />}
          
          <div className="mb-6">
            <h1 className="text-2xl font-bold">LLMs.txt Generator</h1>
            <p className="text-gray-600 mt-1">Generate llms.txt files for your websites</p>
          </div>

        {user ? (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-green-800">
                🎉 You're successfully signed in! Redirecting to your projects...
              </p>
            </div>
          </div>
        ) : (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-yellow-800">
              Please sign in with Google to use the LLMs.txt Generator.
            </p>
          </div>
        )}
        </div>
      </main>
    </>
  )
}