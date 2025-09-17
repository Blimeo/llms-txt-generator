// The Google Cloud Tasks client is buggy and has several known issues with Next. 
// Much of the client initialization code consists of hacky workarounds.

let CloudTasksClient: any = null
let client: any = null

const PROJECT_ID = 'api-project-1042553923996'
const LOCATION = 'us-west1'
const QUEUE_NAME = 'llms-txt'

const clientConfig = {
  "interfaces": {
      "google.cloud.tasks.v2.CloudTasks": {
          "retry_codes": {
              "non_idempotent": [],
              "idempotent": [
                  "DEADLINE_EXCEEDED",
                  "UNAVAILABLE"
              ]
          },
          "retry_params": {
              "default": {
                  "initial_retry_delay_millis": 100,
                  "retry_delay_multiplier": 1.3,
                  "max_retry_delay_millis": 60000,
                  "initial_rpc_timeout_millis": 20000,
                  "rpc_timeout_multiplier": 1,
                  "max_rpc_timeout_millis": 20000,
                  "total_timeout_millis": 600000
              },
              "2607cc7256ff9acb2ee9b232c5722dbbaab18846": {
                  "initial_retry_delay_millis": 100,
                  "retry_delay_multiplier": 1.3,
                  "max_retry_delay_millis": 10000,
                  "initial_rpc_timeout_millis": 20000,
                  "rpc_timeout_multiplier": 1,
                  "max_rpc_timeout_millis": 20000,
                  "total_timeout_millis": 600000
              }
          },
          "methods": {
              "ListQueues": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "idempotent",
                  "retry_params_name": "2607cc7256ff9acb2ee9b232c5722dbbaab18846"
              },
              "GetQueue": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "idempotent",
                  "retry_params_name": "2607cc7256ff9acb2ee9b232c5722dbbaab18846"
              },
              "CreateQueue": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "non_idempotent",
                  "retry_params_name": "default"
              },
              "UpdateQueue": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "non_idempotent",
                  "retry_params_name": "default"
              },
              "DeleteQueue": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "idempotent",
                  "retry_params_name": "2607cc7256ff9acb2ee9b232c5722dbbaab18846"
              },
              "PurgeQueue": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "non_idempotent",
                  "retry_params_name": "default"
              },
              "PauseQueue": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "non_idempotent",
                  "retry_params_name": "default"
              },
              "ResumeQueue": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "non_idempotent",
                  "retry_params_name": "default"
              },
              "GetIamPolicy": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "idempotent",
                  "retry_params_name": "2607cc7256ff9acb2ee9b232c5722dbbaab18846"
              },
              "SetIamPolicy": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "non_idempotent",
                  "retry_params_name": "default"
              },
              "TestIamPermissions": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "idempotent",
                  "retry_params_name": "2607cc7256ff9acb2ee9b232c5722dbbaab18846"
              },
              "ListTasks": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "idempotent",
                  "retry_params_name": "2607cc7256ff9acb2ee9b232c5722dbbaab18846"
              },
              "GetTask": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "idempotent",
                  "retry_params_name": "2607cc7256ff9acb2ee9b232c5722dbbaab18846"
              },
              "CreateTask": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "non_idempotent",
                  "retry_params_name": "default"
              },
              "DeleteTask": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "idempotent",
                  "retry_params_name": "2607cc7256ff9acb2ee9b232c5722dbbaab18846"
              },
              "RunTask": {
                  "timeout_millis": 20000,
                  "retry_codes_name": "non_idempotent",
                  "retry_params_name": "default"
              }
          }
      }
  }
}

// Initialize the client lazily with proper error handling
async function getClient() {
  if (!client) {
    if (typeof window !== 'undefined') {
      throw new Error('CloudTasksClient can only be used on the server side')
    }
    
    try {
      if (!CloudTasksClient) {
        const { CloudTasksClient: CloudTasksClientClass } = await import('@google-cloud/tasks')
        CloudTasksClient = CloudTasksClientClass
      }
      
      // Configure authentication for Vercel deployment
      const authOptions: any = {}
      
      // Check if we have service account key in environment variable
      if (process.env.GOOGLE_SERVICE_ACCOUNT_KEY) {
        try {
          const credentials = JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_KEY)
          authOptions.credentials = credentials
          authOptions.projectId = credentials.project_id
        } catch (error) {
          console.error('Failed to parse GOOGLE_SERVICE_ACCOUNT_KEY:', error)
          throw new Error('Invalid GOOGLE_SERVICE_ACCOUNT_KEY format')
        }
      }
      
      client = new CloudTasksClient({ 
        clientConfig,
        ...authOptions
      })
    } catch (error) {
      console.error('Failed to initialize CloudTasksClient:', error)
      throw error
    }
  }
  return client
}

export interface TaskJob {
  id: string
  projectId: string
  runId?: string
  url: string
  priority?: string
  render_mode?: string
  scheduledAt?: number // Unix timestamp for future execution
  isScheduled: boolean // Whether this is a scheduled job or immediate job
  metadata?: any
}

/**
 * Create a Cloud Task for immediate execution
 */
// Update the enqueueImmediateJob function
export async function enqueueImmediateJob(job: Omit<TaskJob, 'scheduledAt'>) {
    const client = await getClient()
    const queuePath = client.queuePath(PROJECT_ID, LOCATION, QUEUE_NAME)
    console.log('queuePath', queuePath)
    
    // Ensure isScheduled is set to false for immediate jobs
    const jobWithScheduledFlag = { ...job, isScheduled: false }
    
    const task = {
      httpRequest: {
        httpMethod: 'POST' as const,
        url: process.env.WORKER_URL || 'https://worker-service-url',
        headers: {
          'Content-Type': 'application/json',
        },
        body: Buffer.from(JSON.stringify(jobWithScheduledFlag)).toString('base64'),
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
  
    const client = await getClient()
    const queuePath = client.queuePath(PROJECT_ID, LOCATION, QUEUE_NAME)
    
    // Ensure isScheduled is set to true for scheduled jobs
    const jobWithScheduledFlag = { ...job, isScheduled: true }
    
    const task = {
      httpRequest: {
        httpMethod: 'POST' as const,
        url: process.env.WORKER_URL || 'https://worker-service-url',
        headers: {
          'Content-Type': 'application/json',
        },
        body: Buffer.from(JSON.stringify(jobWithScheduledFlag)).toString('base64'),
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
  const client = await getClient()
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
  const client = await getClient()
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
