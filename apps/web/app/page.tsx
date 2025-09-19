'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import OneTapComponent from './google-auth'
import { Navigation, LoadingSpinner } from './components'
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
    return <LoadingSpinner message="Loading..." />
  }

  return (
    <>
      <Navigation user={user} onSignOut={handleSignOut} />
      <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="max-w-7xl mx-auto px-8 py-16">
          {/* Hero Section */}
          <div className="text-center mb-16">
            <h1 className="text-5xl font-bold text-gray-900 mb-6">
              LLMs.txt Generator
            </h1>
            <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
              Automatically track website changes and generate up-to-date <code className="bg-gray-200 px-2 py-1 rounded text-sm font-mono">llms.txt</code> files for AI systems. Sign in with Google to get started.
            </p>
            {!user && <OneTapComponent />}
          

            {user && (
              <div className="bg-green-50 border-2 border-green-200 rounded-2xl p-8 max-w-md mx-auto">
                <div className="text-green-800 text-center">
                  <div className="text-4xl mb-4">🎉</div>
                  <h2 className="text-xl font-semibold mb-2">Welcome back!</h2>
                  <p>Redirecting to your projects...</p>
                </div>
              </div>
            )}
          </div>

          {/* What is llms.txt Section */}
          <div className="bg-white rounded-2xl shadow-lg p-8 mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-6 text-center">
              What is llms.txt?
            </h2>
            <div className="grid md:grid-cols-2 gap-8 items-center">
              <div>
                <p className="text-lg text-gray-700 mb-4">
                  <code className="bg-gray-100 px-2 py-1 rounded font-mono">llms.txt</code> is a standardized file that provides AI systems with essential information about your website's content, structure, and capabilities.
                </p>
                <p className="text-gray-600 mb-4">
                  Similar to <code className="bg-gray-100 px-2 py-1 rounded font-mono">robots.txt</code>, it helps AI models understand your site's purpose, content types, and usage guidelines.
                </p>
                <div className="bg-blue-50 rounded-lg p-4">
                  <h3 className="font-semibold text-blue-900 mb-2">Key Benefits:</h3>
                  <ul className="text-blue-800 space-y-1 text-sm">
                    <li>• Helps AI understand your content better</li>
                    <li>• Provides usage guidelines and restrictions</li>
                    <li>• Improves AI-generated responses about your site</li>
                    <li>• Standardizes how AI systems interact with your content</li>
                  </ul>
                </div>
              </div>
              <div className="bg-gray-900 rounded-lg p-6 text-green-400 font-mono text-sm">
                <div className="text-gray-400 mb-2"># Example llms.txt</div>
                <div># FastHTML</div>
                <div></div>
                <div>&gt; Educational resources for learning web development</div>
                <div></div>
                <div>## Pages</div>
                <div></div>
                <div>- [Home](https://fasthtml.dev/): Learn FastHTML web framework</div>
                <div>- [Documentation](https://fasthtml.dev/docs/): Complete API reference</div>
                <div>- [Tutorials](https://fasthtml.dev/tutorials/): Step-by-step guides</div>
                <div>- [Examples](https://fasthtml.dev/examples/): Code samples and demos</div>
              </div>
            </div>
          </div>

          {/* How It Works Section */}
          <div className="bg-white rounded-2xl shadow-lg p-8">
            <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
              How the service works
            </h2>
            <div className="grid md:grid-cols-3 gap-8">
              <div className="text-center">
                <div className="bg-blue-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">🔍</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">
                  1. Track Changes
                </h3>
                <p className="text-gray-600">
                  We monitor your websites at scheduled intervals to detect content changes, new pages, and updates.
                </p>
              </div>
              
              <div className="text-center">
                <div className="bg-green-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">🤖</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">
                  2. Auto-Generate
                </h3>
                <p className="text-gray-600">
                  When changes are detected, we automatically generate a new <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">llms.txt</code> file with updated information.
                </p>
              </div>
              
              <div className="text-center">
                <div className="bg-purple-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">📊</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">
                  3. Monitor & Manage
                </h3>
                <p className="text-gray-600">
                  View your tracked sites, monitor change history, and manage your <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">llms.txt</code> files from a simple dashboard. Add webhooks to automatically update your site when changes are detected.
                </p>
              </div>
            </div>
            
          </div>
        </div>
      </main>
    </>
  )
}