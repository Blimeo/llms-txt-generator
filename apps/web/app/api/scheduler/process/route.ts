import { NextRequest, NextResponse } from 'next/server'
import { processScheduledJobs } from '../../../../utils/redis/scheduler'

// POST /api/scheduler/process - Manually trigger processing of scheduled jobs
export async function POST(req: NextRequest) {
  try {
    const processedCount = await processScheduledJobs()
    
    return NextResponse.json({ 
      success: true, 
      processed_jobs: processedCount,
      message: `Processed ${processedCount} scheduled jobs`
    })
  } catch (err: any) {
    console.error('Error processing scheduled jobs:', err)
    return NextResponse.json({ 
      error: err?.message ?? 'Internal server error' 
    }, { status: 500 })
  }
}
