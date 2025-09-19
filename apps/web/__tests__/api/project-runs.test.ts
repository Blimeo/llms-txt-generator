import { NextRequest } from 'next/server'
import { GET, POST } from '../../app/api/projects/[id]/runs/route'
import { createClient } from '../../utils/supabase/server'
import { enqueueImmediateJob } from '../../utils/cloud-tasks/scheduler'

// Mock dependencies
jest.mock('../../utils/supabase/server')
jest.mock('../../utils/cloud-tasks/scheduler')
jest.mock('next/headers', () => ({
  cookies: jest.fn(() => Promise.resolve([]))
}))
jest.mock('uuid', () => ({
  v4: jest.fn(() => 'mock-uuid-123')
}))

// Mock URL constructor
global.URL = class URL {
  constructor(url) {
    if (url === 'not-a-valid-url' || url === 'https://not-a-valid-url') {
      throw new Error('Invalid URL')
    }
    this.href = url
  }
}

const mockCreateClient = createClient as jest.MockedFunction<typeof createClient>
const mockEnqueueImmediateJob = enqueueImmediateJob as jest.MockedFunction<typeof enqueueImmediateJob>

describe('/api/projects/[id]/runs', () => {
  let mockSupabase: any
  let mockUser: any
  let mockParams: any

  beforeEach(() => {
    jest.clearAllMocks()
    
    mockUser = {
      id: 'user-123',
      email: 'test@example.com'
    }

    mockParams = {
      id: 'project-123'
    }

    mockSupabase = {
      auth: {
        getUser: jest.fn()
      },
      from: jest.fn(() => ({
        select: jest.fn(() => ({
          eq: jest.fn(() => ({
            single: jest.fn(() => ({
              data: null,
              error: null
            }))
          }))
        })),
        insert: jest.fn(() => ({
          select: jest.fn(() => ({
            single: jest.fn(() => ({
              data: null,
              error: null
            }))
          }))
        }))
      }))
    }

    mockCreateClient.mockResolvedValue(mockSupabase)
  })

  describe('GET /api/projects/[id]/runs', () => {
    it('should return runs for authenticated user', async () => {
      const mockRuns = [
        {
          id: 'run-1',
          project_id: 'project-123',
          initiated_by: 'user-123',
          started_at: '2024-01-01T00:00:00Z',
          finished_at: '2024-01-01T01:00:00Z',
          summary: 'Test run',
          status: 'COMPLETE',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T01:00:00Z',
          metrics: {}
        }
      ]

      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockImplementation((table) => {
        if (table === 'projects') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: { id: 'project-123' },
                    error: null
                  }))
                }))
              }))
            }))
          }
        }
        if (table === 'runs') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                order: jest.fn(() => ({
                  data: mockRuns,
                  error: null
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({ runs: mockRuns })
    })

    it('should return 401 for unauthenticated user', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: null },
        error: new Error('Not authenticated')
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(401)
      expect(data).toEqual({ error: 'Unauthorized' })
    })

    it('should return 404 for non-existent project', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockReturnValue({
        select: jest.fn(() => ({
          eq: jest.fn(() => ({
            eq: jest.fn(() => ({
              single: jest.fn(() => ({
                data: null,
                error: new Error('Not found')
              }))
            }))
          }))
        }))
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(404)
      expect(data).toEqual({ error: 'Project not found' })
    })

    it('should return 500 on database error', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockImplementation((table) => {
        if (table === 'projects') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: { id: 'project-123' },
                    error: null
                  }))
                }))
              }))
            }))
          }
        }
        if (table === 'runs') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                order: jest.fn(() => ({
                  data: null,
                  error: new Error('Database error')
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to fetch runs' })
    })
  })

  describe('POST /api/projects/[id]/runs', () => {
    it('should create a new run with valid data', async () => {
      const runData = {
        url: 'https://example.com',
        priority: 'HIGH',
        render_mode: 'DYNAMIC',
        metadata: { test: true }
      }

      const mockProject = {
        id: 'project-123',
        domain: 'https://example.com',
        project_configs: {
          crawl_depth: 2
        }
      }

      const mockRun = {
        id: 'run-123',
        project_id: 'project-123',
        initiated_by: 'user-123',
        status: 'QUEUED',
        summary: 'Generation run for https://example.com',
        metrics: {}
      }

      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockImplementation((table) => {
        if (table === 'projects') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: mockProject,
                    error: null
                  }))
                }))
              }))
            }))
          }
        }
        if (table === 'runs') {
          return {
            insert: jest.fn(() => ({
              select: jest.fn(() => ({
                single: jest.fn(() => ({
                  data: mockRun,
                  error: null
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      mockEnqueueImmediateJob.mockResolvedValue({ name: 'task-123' })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/runs', {
        method: 'POST',
        body: JSON.stringify(runData),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({
        run: {
          id: mockRun.id,
          project_id: mockRun.project_id,
          status: mockRun.status,
          summary: mockRun.summary,
          created_at: mockRun.created_at
        },
        job: {
          id: 'mock-uuid-123',
          status: 'queued',
          url: runData.url,
          projectId: 'project-123'
        }
      })
      expect(mockEnqueueImmediateJob).toHaveBeenCalledWith({
        id: 'mock-uuid-123',
        url: runData.url,
        projectId: 'project-123',
        runId: mockRun.id,
        priority: runData.priority,
        render_mode: runData.render_mode,
        isScheduled: false
      })
    })

    it('should return 401 for unauthenticated user', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: null },
        error: new Error('Not authenticated')
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/runs', {
        method: 'POST',
        body: JSON.stringify({ url: 'https://example.com' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(401)
      expect(data).toEqual({ error: 'Unauthorized' })
    })

    it('should return 400 for missing URL', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/runs', {
        method: 'POST',
        body: JSON.stringify({ priority: 'HIGH' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(400)
      expect(data).toEqual({ error: 'URL is required' })
    })

    it('should return 400 for invalid URL', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/runs', {
        method: 'POST',
        body: JSON.stringify({ url: 'not-a-valid-url' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(400)
      expect(data).toEqual({ error: 'Invalid URL' })
    })

    it('should return 404 for non-existent project', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockReturnValue({
        select: jest.fn(() => ({
          eq: jest.fn(() => ({
            eq: jest.fn(() => ({
              single: jest.fn(() => ({
                data: null,
                error: new Error('Not found')
              }))
            }))
          }))
        }))
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/runs', {
        method: 'POST',
        body: JSON.stringify({ url: 'https://example.com' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(404)
      expect(data).toEqual({ error: 'Project not found' })
    })

    it('should return 500 on run creation error', async () => {
      const mockProject = {
        id: 'project-123',
        domain: 'https://example.com',
        project_configs: {
          crawl_depth: 2
        }
      }

      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockImplementation((table) => {
        if (table === 'projects') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: mockProject,
                    error: null
                  }))
                }))
              }))
            }))
          }
        }
        if (table === 'runs') {
          return {
            insert: jest.fn(() => ({
              select: jest.fn(() => ({
                single: jest.fn(() => ({
                  data: null,
                  error: new Error('Run creation failed')
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/runs', {
        method: 'POST',
        body: JSON.stringify({ url: 'https://example.com' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to create run' })
    })

    it('should use default values for optional parameters', async () => {
      const runData = {
        url: 'https://example.com'
        // No priority, render_mode, or metadata
      }

      const mockProject = {
        id: 'project-123',
        domain: 'https://example.com',
        project_configs: {
          crawl_depth: 2
        }
      }

      const mockRun = {
        id: 'run-123',
        project_id: 'project-123',
        initiated_by: 'user-123',
        status: 'QUEUED',
        summary: 'Generation run for https://example.com',
        metrics: {}
      }

      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockImplementation((table) => {
        if (table === 'projects') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: mockProject,
                    error: null
                  }))
                }))
              }))
            }))
          }
        }
        if (table === 'runs') {
          return {
            insert: jest.fn(() => ({
              select: jest.fn(() => ({
                single: jest.fn(() => ({
                  data: mockRun,
                  error: null
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      mockEnqueueImmediateJob.mockResolvedValue({ name: 'task-123' })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/runs', {
        method: 'POST',
        body: JSON.stringify(runData),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(mockEnqueueImmediateJob).toHaveBeenCalledWith({
        id: 'mock-uuid-123',
        url: runData.url,
        projectId: 'project-123',
        runId: mockRun.id,
        priority: 'NORMAL', // Default value
        render_mode: 'STATIC', // Default value
        isScheduled: false
      })
    })
  })
})
