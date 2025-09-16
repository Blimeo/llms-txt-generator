import { CloudTasksClient } from '@google-cloud/tasks'

const PROJECT_ID = 'api-project-1042553923996'
const LOCATION = 'us-west1'
const QUEUE_NAME = 'llms-txt-gen'

const client = new CloudTasksClient()

export interface TaskJob {
  id: string
  projectId: string
  runId?: string
  url: string
  priority?: string
  render_mode?: string
  scheduledAt?: number // Unix timestamp for future execution
  metadata?: any
}

/**
 * Create a Cloud Task for immediate execution
 */
// Update the enqueueImmediateJob function
export async function enqueueImmediateJob(job: Omit<TaskJob, 'scheduledAt'>) {
    const queuePath = client.queuePath(PROJECT_ID, LOCATION, QUEUE_NAME)
    console.log('queuePath', queuePath)
    const task = {
      httpRequest: {
        httpMethod: 'POST' as const,
        url: process.env.WORKER_URL || 'https://worker-service-url',
        headers: {
          'Content-Type': 'application/json',
        },
        body: Buffer.from(JSON.stringify(job)).toString('base64'),
        // Add OIDC token for authentication
      },
      // Add task name for deduplication
      name: client.taskPath(PROJECT_ID, LOCATION, QUEUE_NAME, job.id),
    }
    console.log('task', task)
    try {
      const [response] = await client.createTask({ parent: queuePath, task })
      console.log(`Created task: ${response.name}`)
      return response
    } catch (error) {
      console.error('Error creating Cloud Task:', error)
      throw error
    }
  }
  
  // Update the scheduleJob function
  export async function scheduleJob(job: TaskJob) {
    if (!job.scheduledAt) {
      throw new Error('scheduledAt is required for scheduled jobs')
    }
  
    const queuePath = client.queuePath(PROJECT_ID, LOCATION, QUEUE_NAME)
    
    const task = {
      httpRequest: {
        httpMethod: 'POST' as const,
        url: process.env.WORKER_URL || 'https://worker-service-url',
        headers: {
          'Content-Type': 'application/json',
        },
        body: Buffer.from(JSON.stringify(job)).toString('base64'),
        // Add OIDC token for authentication
        oidcToken: {
          serviceAccountEmail: 'cloud-tasks-invoker@api-project-1042553923996.iam.gserviceaccount.com',
          audience: process.env.WORKER_URL || 'https://worker-service-url',
        },
      },
      // Schedule the task for future execution
      scheduleTime: {
        seconds: Math.floor(job.scheduledAt / 1000),
        nanos: (job.scheduledAt % 1000) * 1000000,
      },
      // Add task name for deduplication
      name: client.taskPath(PROJECT_ID, LOCATION, QUEUE_NAME, job.id),
    }
  
    try {
      const [response] = await client.createTask({ parent: queuePath, task })
      console.log(`Created scheduled task: ${response.name}`)
      return response
    } catch (error) {
      console.error('Error creating scheduled Cloud Task:', error)
      throw error
    }
  }

/**
 * Cancel a scheduled task
 */
export async function cancelScheduledJob(jobId: string) {
  const taskName = client.taskPath(PROJECT_ID, LOCATION, QUEUE_NAME, jobId)
  
  try {
    await client.deleteTask({ name: taskName })
    console.log(`Deleted task: ${taskName}`)
    return true
  } catch (error) {
    console.error('Error deleting Cloud Task:', error)
    return false
  }
}

/**
 * Get task status (optional - for monitoring)
 */
export async function getTaskStatus(jobId: string) {
  const taskName = client.taskPath(PROJECT_ID, LOCATION, QUEUE_NAME, jobId)
  
  try {
    const [task] = await client.getTask({ name: taskName })
    return {
      name: task.name,
      scheduleTime: task.scheduleTime,
      createTime: task.createTime,
      dispatchCount: task.dispatchCount,
      responseCount: task.responseCount,
      firstAttempt: task.firstAttempt,
      lastAttempt: task.lastAttempt,
    }
  } catch (error) {
    console.error('Error getting task status:', error)
    return null
  }
}
