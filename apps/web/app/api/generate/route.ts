// apps/web/app/api/generate/route.ts
import { NextResponse } from 'next/server'
import IORedis from 'ioredis'
import { v4 as uuidv4 } from 'uuid'

// SERVER-ONLY: set REDIS_URL in env (do NOT expose to client)
const REDIS_URL="rediss://default:AfdjAAIncDE0MmZlMWViNTJkNWU0MzVjOGEzOTYwOWQyOTQyNzAyYnAxNjMzMzE@hip-lobster-63331.upstash.io:6379"
if (!REDIS_URL) console.warn('Missing REDIS_URL for /api/generate')

// single shared ioredis connection
const redis = new IORedis(REDIS_URL)

// helper to push job and set basic job hash (status)
async function enqueueJob(job: { id: string; url: string }) {
  const jobKey = `job:${job.id}`

  // store minimal metadata in a hash for status queries
  await redis.hset(jobKey, {
    id: job.id,
    url: job.url,
    status: 'queued',
    created_at: new Date().toISOString(),
    attempts: '0',
  })

  // push job JSON onto list; Python worker will BRPOP this list
  await redis.rpush('generate:queue', JSON.stringify(job))
}

export async function POST(req: Request) {
  try {
    const body = await req.json()
    const url = (body?.url || '').toString().trim()
    if (!url) return NextResponse.json({ error: 'url is required' }, { status: 400 })

    try {
      new URL(url)
    } catch {
      return NextResponse.json({ error: 'invalid url' }, { status: 400 })
    }

    const jobId = uuidv4()
    const job = { id: jobId, url }
    await enqueueJob(job)

    return NextResponse.json({ job: { id: jobId, status: 'queued' } })
  } catch (err: any) {
    return NextResponse.json({ error: err?.message ?? String(err) }, { status: 500 })
  }
}
