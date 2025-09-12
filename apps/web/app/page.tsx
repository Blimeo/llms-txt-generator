'use client'


import React, { useState } from 'react'


export default function HomePage() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)


  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setMessage(null)


    try {
      const parsed = new URL(url)
      if (!['http:', 'https:'].includes(parsed.protocol)) {
        setMessage('Please enter a valid http(s) URL')
        return
      }
    } catch (err) {
      setMessage('Please enter a valid URL')
      return
    }


    setLoading(true)


    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      })


      const payload = await res.json()


      if (!res.ok) {
        setMessage(payload?.error || 'Failed to enqueue job')
      } else {
        setMessage(`Enqueued — job id: ${payload?.job?.id ?? 'unknown'}`)
        setUrl('')
      }
    } catch (err) {
      setMessage(String(err))
    } finally {
      setLoading(false)
    }
  }


  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">LLMs.txt Generator</h1>


      <form className="mt-4 space-y-2" onSubmit={handleSubmit}>
        <input
          type="url"
          name="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com"
          className="border rounded p-2 w-full"
          required
        />
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-60"
          disabled={loading}
        >
          {loading ? 'Enqueuing...' : 'Generate'}
        </button>
      </form>
      {message && <p className="mt-4 text-sm">{message}</p>}
    </main>
  )
}
