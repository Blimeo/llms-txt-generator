import { NextRequest, NextResponse } from 'next/server'
import { redis } from '../../../../utils/redis/scheduler'

// GET /api/scheduler/jobs - View all scheduled jobs
export async function GET(req: NextRequest) {
  try {
    const allJobs = await redis.zrange('scheduled:jobs', 0, -1, 'WITHSCORES')
    
    const jobs = allJobs
      .filter((_, index) => index % 2 === 0) // Get only the job data (every other item)
      .map((jobStr, index) => {
        const score = allJobs[index * 2 + 1] // Get the corresponding score
        const job = JSON.parse(jobStr)
        return {
          ...job,
          scheduled_at: new Date(parseFloat(score) * 1000).toISOString(),
          score: parseFloat(score)
        }
      })
    
    return NextResponse.json({ 
      jobs,
      count: jobs.length
    })
  } catch (err: any) {
    console.error('Error fetching scheduled jobs:', err)
    return NextResponse.json({ 
      error: err?.message ?? 'Internal server error' 
    }, { status: 500 })
  }
}
