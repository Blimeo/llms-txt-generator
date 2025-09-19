import { NextRequest } from 'next/server'
import { GET, PUT, DELETE } from '../../app/api/projects/[id]/route'
import { createClient } from '../../utils/supabase/server'
import { deleteTasks } from '../../utils/cloud-tasks/scheduler'

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
const mockDeleteTasks = deleteTasks as jest.MockedFunction<typeof deleteTasks>

describe('/api/projects/[id]', () => {
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

  describe('GET /api/projects/[id]', () => {
    it('should return project for authenticated user', async () => {
      const mockProject = {
        id: 'project-123',
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

      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockReturnValue({
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
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({ project: mockProject })
    })

    it('should return 401 for unauthenticated user', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: null },
        error: new Error('Not authenticated')
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123'), { params: Promise.resolve(mockParams) })
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
                error: { code: 'PGRST116' }
              }))
            }))
          }))
        }))
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(404)
      expect(data).toEqual({ error: 'Project not found' })
    })

    it('should return 500 on database error', async () => {
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
                error: new Error('Database error')
              }))
            }))
          }))
        }))
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to fetch project' })
    })
  })

  describe('PUT /api/projects/[id]', () => {
    it('should update project with valid data', async () => {
      const updateData = {
        name: 'Updated Project',
        domain: 'https://updated.com',
        description: 'Updated description',
        crawl_depth: 3
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
                    data: { id: 'project-123' },
                    error: null
                  }))
                }))
              }))
            })),
            update: jest.fn(() => ({
              eq: jest.fn(() => ({
                data: null,
                error: null
              }))
            }))
          }
        }
        if (table === 'project_configs') {
          return {
            update: jest.fn(() => ({
              eq: jest.fn(() => ({
                data: null,
                error: null
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123', {
        method: 'PUT',
        body: JSON.stringify(updateData),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await PUT(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({ success: true })
    })

    it('should return 401 for unauthenticated user', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: null },
        error: new Error('Not authenticated')
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123', {
        method: 'PUT',
        body: JSON.stringify({ name: 'Updated' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await PUT(request, { params: Promise.resolve(mockParams) })
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

      const request = new NextRequest('http://localhost:3000/api/projects/project-123', {
        method: 'PUT',
        body: JSON.stringify({ name: 'Updated' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await PUT(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(404)
      expect(data).toEqual({ error: 'Project not found' })
    })

    it('should return 400 for invalid domain URL', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockReturnValue({
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
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123', {
        method: 'PUT',
        body: JSON.stringify({ domain: 'not-a-valid-url' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await PUT(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(400)
      expect(data).toEqual({ error: 'Invalid domain URL' })
    })

    it('should handle domain without protocol', async () => {
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
            })),
            update: jest.fn((data) => {
              expect(data.domain).toBe('https://example.com')
              return {
                eq: jest.fn(() => ({
                  data: null,
                  error: null
                }))
              }
            })
          }
        }
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123', {
        method: 'PUT',
        body: JSON.stringify({ domain: 'example.com' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await PUT(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({ success: true })
    })

    it('should return 500 on project update error', async () => {
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
            })),
            update: jest.fn(() => ({
              eq: jest.fn(() => ({
                data: null,
                error: new Error('Update failed')
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123', {
        method: 'PUT',
        body: JSON.stringify({ name: 'Updated' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await PUT(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to update project' })
    })

    it('should return 500 on config update error', async () => {
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
            })),
            update: jest.fn(() => ({
              eq: jest.fn(() => ({
                data: null,
                error: null
              }))
            }))
          }
        }
        if (table === 'project_configs') {
          return {
            update: jest.fn(() => ({
              eq: jest.fn(() => ({
                data: null,
                error: new Error('Config update failed')
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123', {
        method: 'PUT',
        body: JSON.stringify({ crawl_depth: 3 }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await PUT(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to update project configuration' })
    })
  })

  describe('DELETE /api/projects/[id]', () => {
    it('should delete project and associated tasks', async () => {
      const mockQueuedRuns = [
        { id: 'run-1' },
        { id: 'run-2' }
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
            })),
            delete: jest.fn(() => ({
              eq: jest.fn(() => ({
                data: null,
                error: null
              }))
            }))
          }
        }
        if (table === 'runs') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                in: jest.fn(() => ({
                  data: mockQueuedRuns,
                  error: null
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      mockDeleteTasks.mockResolvedValue([
        { runId: 'run-1', success: true },
        { runId: 'run-2', success: true }
      ])

      const request = new NextRequest('http://localhost:3000/api/projects/project-123', {
        method: 'DELETE'
      })

      const response = await DELETE(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({ success: true })
      expect(mockDeleteTasks).toHaveBeenCalledWith(['run-1', 'run-2'])
    })

    it('should return 401 for unauthenticated user', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: null },
        error: new Error('Not authenticated')
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123', {
        method: 'DELETE'
      })

      const response = await DELETE(request, { params: Promise.resolve(mockParams) })
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

      const request = new NextRequest('http://localhost:3000/api/projects/project-123', {
        method: 'DELETE'
      })

      const response = await DELETE(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(404)
      expect(data).toEqual({ error: 'Project not found' })
    })

    it('should handle task deletion failures gracefully', async () => {
      const mockQueuedRuns = [
        { id: 'run-1' },
        { id: 'run-2' }
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
            })),
            delete: jest.fn(() => ({
              eq: jest.fn(() => ({
                data: null,
                error: null
              }))
            }))
          }
        }
        if (table === 'runs') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                in: jest.fn(() => ({
                  data: mockQueuedRuns,
                  error: null
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      mockDeleteTasks.mockResolvedValue([
        { runId: 'run-1', success: true },
        { runId: 'run-2', success: false, error: 'Task deletion failed' }
      ])

      const request = new NextRequest('http://localhost:3000/api/projects/project-123', {
        method: 'DELETE'
      })

      const response = await DELETE(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      // Should still succeed even if some tasks fail to delete
      expect(response.status).toBe(200)
      expect(data).toEqual({ success: true })
    })

    it('should return 500 on project deletion error', async () => {
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
            })),
            delete: jest.fn(() => ({
              eq: jest.fn(() => ({
                data: null,
                error: new Error('Delete failed')
              }))
            }))
          }
        }
        if (table === 'runs') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                in: jest.fn(() => ({
                  data: [],
                  error: null
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123', {
        method: 'DELETE'
      })

      const response = await DELETE(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to delete project' })
    })

    it('should return 500 on runs fetch error', async () => {
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
                in: jest.fn(() => ({
                  data: null,
                  error: new Error('Runs fetch failed')
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123', {
        method: 'DELETE'
      })

      const response = await DELETE(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to fetch queued runs' })
    })
  })
})
