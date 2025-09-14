import IORedis from 'ioredis'

const REDIS_URL = process.env.REDIS_URL || "rediss://default:AfdjAAIncDE0MmZlMWViNTJkNWU0MzVjOGEzOTYwOWQyOTQyNzAyYnAxNjMzMzE@hip-lobster-63331.upstash.io:6379"
const redis = new IORedis(REDIS_URL)

// Redis keys for scheduled jobs
const SCHEDULED_JOBS_KEY = 'scheduled:jobs'
const IMMEDIATE_JOBS_KEY = 'generate:queue'

export interface ScheduledJob {
  id: string
  projectId: string
  runId?: string
  url: string
  priority?: string
  render_mode?: string
  scheduledAt: number // Unix timestamp
  metadata?: any
}

/**
 * Enqueue a job for immediate execution
 */
export async function enqueueImmediateJob(job: Omit<ScheduledJob, 'scheduledAt'>) {
  const jobKey = `job:${job.id}`
  
  // Store minimal metadata in a hash for status queries
  await redis.hset(jobKey, {
    id: job.id,
    url: job.url,
    projectId: job.projectId,
    runId: job.runId || '',
    status: 'queued',
    created_at: new Date().toISOString(),
    attempts: '0',
  })

  // Push job JSON onto list; Python worker will BRPOP this list
  await redis.rpush(IMMEDIATE_JOBS_KEY, JSON.stringify(job))
}

/**
 * Schedule a job for future execution using Redis sorted sets
 */
export async function scheduleJob(job: ScheduledJob) {
  const jobKey = `job:${job.id}`
  
  // Store job metadata in a hash
  await redis.hset(jobKey, {
    id: job.id,
    url: job.url,
    projectId: job.projectId,
    runId: job.runId || '',
    status: 'scheduled',
    scheduled_at: new Date(job.scheduledAt).toISOString(),
    created_at: new Date().toISOString(),
    attempts: '0',
  })

  // Add to sorted set with scheduled time as score
  await redis.zadd(SCHEDULED_JOBS_KEY, job.scheduledAt, JSON.stringify(job))
}

/**
 * Get jobs that are ready to be executed (scheduled time has passed)
 */
export async function getReadyJobs(): Promise<ScheduledJob[]> {
  const now = Date.now()
  const readyJobs = await redis.zrangebyscore(SCHEDULED_JOBS_KEY, 0, now)
  
  if (readyJobs.length === 0) {
    return []
  }

  // Remove ready jobs from scheduled set
  await redis.zremrangebyscore(SCHEDULED_JOBS_KEY, 0, now)
  
  return readyJobs.map(jobStr => JSON.parse(jobStr))
}

/**
 * Move ready jobs to immediate queue
 */
export async function processScheduledJobs() {
  const readyJobs = await getReadyJobs()
  
  for (const job of readyJobs) {
    // Update job status
    await redis.hset(`job:${job.id}`, 'status', 'queued')
    
    // Add to immediate queue
    await redis.rpush(IMMEDIATE_JOBS_KEY, JSON.stringify(job))
  }
  
  return readyJobs.length
}

/**
 * Cancel a scheduled job
 */
export async function cancelScheduledJob(jobId: string) {
  // Get all scheduled jobs to find the one with matching ID
  const allJobs = await redis.zrange(SCHEDULED_JOBS_KEY, 0, -1)
  
  for (const jobStr of allJobs) {
    const job = JSON.parse(jobStr)
    if (job.id === jobId) {
      await redis.zrem(SCHEDULED_JOBS_KEY, jobStr)
      await redis.del(`job:${jobId}`)
      return true
    }
  }
  
  return false
}

/**
 * Get all scheduled jobs for a project
 */
export async function getScheduledJobsForProject(projectId: string): Promise<ScheduledJob[]> {
  const allJobs = await redis.zrange(SCHEDULED_JOBS_KEY, 0, -1)
  
  return allJobs
    .map(jobStr => JSON.parse(jobStr))
    .filter(job => job.projectId === projectId)
}

/**
 * Clean up old completed jobs (optional maintenance function)
 */
export async function cleanupOldJobs(maxAgeHours: number = 24) {
  const cutoffTime = Date.now() - (maxAgeHours * 60 * 60 * 1000)
  
  // Get all job keys
  const jobKeys = await redis.keys('job:*')
  
  for (const jobKey of jobKeys) {
    const jobData = await redis.hgetall(jobKey)
    const createdAt = new Date(jobData.created_at).getTime()
    
    if (createdAt < cutoffTime && (jobData.status === 'completed' || jobData.status === 'failed')) {
      await redis.del(jobKey)
    }
  }
}

export { redis }
