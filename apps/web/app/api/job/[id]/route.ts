// apps/web/app/api/job/[id]/route.ts
import { NextResponse } from 'next/server'
import IORedis from 'ioredis'

const REDIS_URL="rediss://default:AfdjAAIncDE0MmZlMWViNTJkNWU0MzVjOGEzOTYwOWQyOTQyNzAyYnAxNjMzMzE@hip-lobster-63331.upstash.io:6379"
const redis = new IORedis(REDIS_URL)

export async function GET(_req: Request, { params }: { params: { id: string } }) {
  try {
    const jobId = params.id
    if (!jobId) return NextResponse.json({ error: 'missing id' }, { status: 400 })

    const key = `job:${jobId}`
    const data = await redis.hgetall(key) // returns {} if not exist
    if (!data || Object.keys(data).length === 0) {
      return NextResponse.json({ job: null, status: 'not_found' }, { status: 404 })
    }

    // convert numeric-ish fields if you like, e.g. attempts -> number
    // if (data.attempts) data.numAttempts = Number(data.attempts)

    return NextResponse.json({ job: data })
  } catch (err: any) {
    return NextResponse.json({ error: err?.message ?? String(err) }, { status: 500 })
  }
}
