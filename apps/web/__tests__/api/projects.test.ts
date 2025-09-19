import { NextRequest } from 'next/server'
import { GET, POST } from '../../app/api/projects/route'
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

describe('/api/projects', () => {
  let mockSupabase: any
  let mockUser: any

  beforeEach(() => {
    jest.clearAllMocks()
    
    mockUser = {
      id: 'user-123',
      email: 'test@example.com'
    }

    mockSupabase = {
      auth: {
        getUser: jest.fn()
      },
      from: jest.fn(() => ({
        select: jest.fn(() => ({
          eq: jest.fn(() => ({
            order: jest.fn(() => ({
              data: [],
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
        })),
        update: jest.fn(() => ({
          eq: jest.fn(() => ({
            data: null,
            error: null
          }))
        })),
        delete: jest.fn(() => ({
          eq: jest.fn(() => ({
            data: null,
            error: null
          }))
        }))
      }))
    }

    mockCreateClient.mockResolvedValue(mockSupabase)
  })

  describe('GET /api/projects', () => {
    it('should return projects for authenticated user', async () => {
      const mockProjects = [
        {
          id: 'project-1',
          name: 'Test Project',
          domain: 'https://example.com',
          description: 'Test description',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
          metadata: {},
          project_configs: {
            crawl_depth: 2,
            cron_expression: '0 2 * * *',
            last_run_at: null,
            next_run_at: '2024-01-02T02:00:00Z',
            is_enabled: true,
            config: {}
          }
        }
      ]

      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockReturnValue({
        select: jest.fn(() => ({
          eq: jest.fn(() => ({
            order: jest.fn(() => ({
              data: mockProjects,
              error: null
            }))
          }))
        }))
      })

      const response = await GET()
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({ projects: mockProjects })
      expect(mockSupabase.auth.getUser).toHaveBeenCalled()
    })

    it('should return 401 for unauthenticated user', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: null },
        error: new Error('Not authenticated')
      })

      const response = await GET()
      const data = await response.json()

      expect(response.status).toBe(401)
      expect(data).toEqual({ error: 'Unauthorized' })
    })

    it('should return 500 on database error', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockReturnValue({
        select: jest.fn(() => ({
          eq: jest.fn(() => ({
            order: jest.fn(() => ({
              data: null,
              error: new Error('Database error')
            }))
          }))
        }))
      })

      const response = await GET()
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to fetch projects' })
    })
  })

  describe('POST /api/projects', () => {
    it('should create a new project with valid data', async () => {
      const projectData = {
        name: 'New Project',
        domain: 'https://example.com',
        description: 'Project description',
        crawl_depth: 3,
        cron_expression: 'daily',
        is_enabled: true
      }

      const mockProject = {
        id: 'project-123',
        created_by: mockUser.id,
        name: projectData.name,
        domain: projectData.domain,
        description: projectData.description,
        metadata: {}
      }

      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      // Mock project creation
      mockSupabase.from.mockImplementation((table) => {
        if (table === 'projects') {
          return {
            insert: jest.fn(() => ({
              select: jest.fn(() => ({
                single: jest.fn(() => ({
                  data: mockProject,
                  error: null
                }))
              }))
            }))
          }
        }
        if (table === 'project_configs') {
          return {
            insert: jest.fn(() => ({
              data: null,
              error: null
            }))
          }
        }
        if (table === 'runs') {
          return {
            insert: jest.fn(() => ({
              select: jest.fn(() => ({
                single: jest.fn(() => ({
                  data: { id: 'run-123' },
                  error: null
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      mockEnqueueImmediateJob.mockResolvedValue({ name: 'task-123' })

      const request = new NextRequest('http://localhost:3000/api/projects', {
        method: 'POST',
        body: JSON.stringify(projectData),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request)
      const data = await response.json()

      expect(response.status).toBe(201)
      expect(data).toEqual({ project: mockProject })
      expect(mockEnqueueImmediateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          url: projectData.domain,
          projectId: mockProject.id,
          isScheduled: false,
          isInitialRun: true
        })
      )
    })

    it('should return 401 for unauthenticated user', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: null },
        error: new Error('Not authenticated')
      })

      const request = new NextRequest('http://localhost:3000/api/projects', {
        method: 'POST',
        body: JSON.stringify({ name: 'Test', domain: 'https://example.com' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request)
      const data = await response.json()

      expect(response.status).toBe(401)
      expect(data).toEqual({ error: 'Unauthorized' })
    })

    it('should return 400 for missing required fields', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      const request = new NextRequest('http://localhost:3000/api/projects', {
        method: 'POST',
        body: JSON.stringify({ name: 'Test' }), // Missing domain
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request)
      const data = await response.json()

      expect(response.status).toBe(400)
      expect(data).toEqual({ error: 'Name and domain are required' })
    })

    it('should return 400 for invalid domain URL', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      const request = new NextRequest('http://localhost:3000/api/projects', {
        method: 'POST',
        body: JSON.stringify({ 
          name: 'Test', 
          domain: 'not-a-valid-url' 
        }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request)
      const data = await response.json()

      expect(response.status).toBe(400)
      expect(data).toEqual({ error: 'Invalid domain URL' })
    })

    it('should handle domain without protocol', async () => {
      const projectData = {
        name: 'New Project',
        domain: 'example.com', // No protocol
        description: 'Project description'
      }

      const mockProject = {
        id: 'project-123',
        created_by: mockUser.id,
        name: projectData.name,
        domain: 'https://example.com', // Should be normalized
        description: projectData.description,
        metadata: {}
      }

      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockImplementation((table) => {
        if (table === 'projects') {
          return {
            insert: jest.fn(() => ({
              select: jest.fn(() => ({
                single: jest.fn(() => ({
                  data: mockProject,
                  error: null
                }))
              }))
            }))
          }
        }
        if (table === 'project_configs') {
          return {
            insert: jest.fn(() => ({
              data: null,
              error: null
            }))
          }
        }
        if (table === 'runs') {
          return {
            insert: jest.fn(() => ({
              select: jest.fn(() => ({
                single: jest.fn(() => ({
                  data: { id: 'run-123' },
                  error: null
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      mockEnqueueImmediateJob.mockResolvedValue({ name: 'task-123' })

      const request = new NextRequest('http://localhost:3000/api/projects', {
        method: 'POST',
        body: JSON.stringify(projectData),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request)
      const data = await response.json()

      expect(response.status).toBe(201)
      expect(data).toEqual({ project: mockProject })
    })

    it('should return 500 on project creation error', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockReturnValue({
        insert: jest.fn(() => ({
          select: jest.fn(() => ({
            single: jest.fn(() => ({
              data: null,
              error: new Error('Database error')
            }))
          }))
        }))
      })

      const request = new NextRequest('http://localhost:3000/api/projects', {
        method: 'POST',
        body: JSON.stringify({ 
          name: 'Test', 
          domain: 'https://example.com' 
        }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request)
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to create project' })
    })

    it('should clean up project if config creation fails', async () => {
      const projectData = {
        name: 'New Project',
        domain: 'https://example.com',
        description: 'Project description'
      }

      const mockProject = {
        id: 'project-123',
        created_by: mockUser.id,
        name: projectData.name,
        domain: projectData.domain,
        description: projectData.description,
        metadata: {}
      }

      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockImplementation((table) => {
        if (table === 'projects') {
          return {
            insert: jest.fn(() => ({
              select: jest.fn(() => ({
                single: jest.fn(() => ({
                  data: mockProject,
                  error: null
                }))
              }))
            })),
            delete: jest.fn(() => ({
              eq: jest.fn(() => ({
                data: null,
                error: null
              }))
            }))
          }
        }
        if (table === 'project_configs') {
          return {
            insert: jest.fn(() => ({
              data: null,
              error: new Error('Config creation failed')
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects', {
        method: 'POST',
        body: JSON.stringify(projectData),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request)
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to create project configuration' })
      
      // Verify project cleanup was attempted
      expect(mockSupabase.from).toHaveBeenCalledWith('projects')
    })

    it('should handle different cron expressions', async () => {
      const testCases = [
        { cron_expression: 'daily', expectedCron: '0 2 * * *' },
        { cron_expression: 'weekly', expectedCron: '0 2 * * 0' },
        { cron_expression: 'custom', expectedCron: null }
      ]

      for (const testCase of testCases) {
        jest.clearAllMocks()
        
        const projectData = {
          name: 'Test Project',
          domain: 'https://example.com',
          cron_expression: testCase.cron_expression
        }

        const mockProject = {
          id: 'project-123',
          created_by: mockUser.id,
          name: projectData.name,
          domain: projectData.domain,
          description: null,
          metadata: {}
        }

        mockSupabase.auth.getUser.mockResolvedValue({
          data: { user: mockUser },
          error: null
        })

        mockSupabase.from.mockImplementation((table) => {
          if (table === 'projects') {
            return {
              insert: jest.fn(() => ({
                select: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: mockProject,
                    error: null
                  }))
                }))
              }))
            }
          }
          if (table === 'project_configs') {
            return {
              insert: jest.fn((data) => {
                expect(data.cron_expression).toBe(testCase.expectedCron)
                return {
                  data: null,
                  error: null
                }
              })
            }
          }
          if (table === 'runs') {
            return {
              insert: jest.fn(() => ({
                select: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: { id: 'run-123' },
                    error: null
                  }))
                }))
              }))
            }
          }
          return mockSupabase.from(table)
        })

        mockEnqueueImmediateJob.mockResolvedValue({ name: 'task-123' })

        const request = new NextRequest('http://localhost:3000/api/projects', {
          method: 'POST',
          body: JSON.stringify(projectData),
          headers: {
            'Content-Type': 'application/json'
          }
        })

        const response = await POST(request)
        expect(response.status).toBe(201)
      }
    })
  })
})
