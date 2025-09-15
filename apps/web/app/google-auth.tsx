'use client'
import Script from 'next/script'
import { createClient } from '@/utils/supabase/client'
import type { accounts, CredentialResponse } from 'google-one-tap'
import { useRouter } from 'next/navigation'
declare const google: { accounts: accounts }
// generate nonce to use for google id token sign-in
const generateNonce = async (): Promise<string[]> => {
  const nonce = btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(32))))
  const encoder = new TextEncoder()
  const encodedNonce = encoder.encode(nonce)
  const hashBuffer = await crypto.subtle.digest('SHA-256', encodedNonce)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  const hashedNonce = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('')
  return [nonce, hashedNonce]
}
const OneTapComponent = () => {
  const supabase = createClient()
  const router = useRouter()
  const initializeGoogleOneTap = async () => {
    console.log('Initializing Google One Tap')
    
    // Check if Google client ID is available
    if (!process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID) {
      console.error('Google Client ID is not defined')
      return
    }
    
    const [nonce, hashedNonce] = await generateNonce()
    console.log('Nonce: ', nonce, hashedNonce)
    
    // check if there's already an existing session before initializing the one-tap UI
    const { data, error } = await supabase.auth.getSession()
    if (error) {
      console.error('Error getting session', error)
    }
    if (data.session) {
      router.replace('/')
      return
    }
    /* global google */
    console.log('Initializing Google One Tap', process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID)
    console.log('Current URL:', window.location.href)
    console.log('Browser FedCM support:', 'IdentityCredential' in window)
    
    try {
      google.accounts.id.initialize({
        client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!,
        callback: async (response: CredentialResponse) => {
          try {
            // send id token returned in response.credential to supabase
            const { data, error } = await supabase.auth.signInWithIdToken({
              provider: 'google',
              token: response.credential,
              nonce,
            })
            if (error) throw error
            console.log('Session data: ', data)
            console.log('Successfully logged in with Google One Tap')
            // redirect to projects page directly
            router.replace('/projects')
            // Fallback redirect after a short delay
            setTimeout(() => {
              if (window.location.pathname === '/') {
                console.log('Router redirect failed, using window.location fallback')
                window.location.href = '/projects'
              }
            }, 100)
          } catch (error) {
            console.error('Error logging in with Google One Tap', error)
          }
        },
        nonce: hashedNonce,
        context: 'signin',
        ux_mode: 'popup',
        auto_select: false,
        cancel_on_tap_outside: false,
        // FedCM is now mandatory for Google One Tap as of Oct 2024
        use_fedcm_for_prompt: true,
      })
      
      google.accounts.id.prompt() // Display the One Tap UI
    } catch (error) {
      console.error('Error initializing Google One Tap:', error)
    }
  }
  return <Script onReady={() => { initializeGoogleOneTap() }} src="https://accounts.google.com/gsi/client" />
}
export default OneTapComponent