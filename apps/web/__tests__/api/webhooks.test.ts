import { NextRequest } from 'next/server'
import { GET, POST } from '../../app/api/projects/[id]/webhooks/route'
import { PUT, DELETE } from '../../app/api/projects/[id]/webhooks/[webhookId]/route'
import { GET as GET_EVENTS } from '../../app/api/projects/[id]/webhooks/events/route'
import { createClient } from '../../utils/supabase/server'

// Mock dependencies
jest.mock('../../utils/supabase/server')
jest.mock('next/headers', () => ({
  cookies: jest.fn(() => Promise.resolve([]))
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

describe('/api/projects/[id]/webhooks', () => {
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
            })),
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
            select: jest.fn(() => ({
              single: jest.fn(() => ({
                data: null,
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
      }))
    }

    mockCreateClient.mockResolvedValue(mockSupabase)
  })

  describe('GET /api/projects/[id]/webhooks', () => {
    it('should return webhooks for authenticated user', async () => {
      const mockWebhooks = [
        {
          id: 'webhook-1',
          project_id: 'project-123',
          url: 'https://example.com/webhook',
          event_types: ['run.complete'],
          secret: 'secret-key',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
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
        if (table === 'webhooks') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                order: jest.fn(() => ({
                  data: mockWebhooks,
                  error: null
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/webhooks'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({ webhooks: mockWebhooks })
    })

    it('should return 401 for unauthenticated user', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: null },
        error: new Error('Not authenticated')
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/webhooks'), { params: Promise.resolve(mockParams) })
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

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/webhooks'), { params: Promise.resolve(mockParams) })
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
        if (table === 'webhooks') {
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

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/webhooks'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to fetch webhooks' })
    })
  })

  describe('POST /api/projects/[id]/webhooks', () => {
    it('should create a new webhook with valid data', async () => {
      const webhookData = {
        url: 'https://example.com/webhook',
        event_types: ['run.complete', 'run.failed'],
        secret: 'secret-key',
        is_active: true
      }

      const mockWebhook = {
        id: 'webhook-123',
        project_id: 'project-123',
        url: webhookData.url,
        event_types: webhookData.event_types,
        secret: webhookData.secret,
        is_active: webhookData.is_active,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
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
            }))
          }
        }
        if (table === 'webhooks') {
          return {
            insert: jest.fn(() => ({
              select: jest.fn(() => ({
                single: jest.fn(() => ({
                  data: mockWebhook,
                  error: null
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks', {
        method: 'POST',
        body: JSON.stringify(webhookData),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({ webhook: mockWebhook })
    })

    it('should return 401 for unauthenticated user', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: null },
        error: new Error('Not authenticated')
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks', {
        method: 'POST',
        body: JSON.stringify({ url: 'https://example.com/webhook' }),
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

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks', {
        method: 'POST',
        body: JSON.stringify({ event_types: ['run.complete'] }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(400)
      expect(data).toEqual({ error: 'URL is required' })
    })

    it('should return 400 for invalid URL format', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks', {
        method: 'POST',
        body: JSON.stringify({ url: 'not-a-valid-url' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(400)
      expect(data).toEqual({ error: 'Invalid URL format' })
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

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks', {
        method: 'POST',
        body: JSON.stringify({ url: 'https://example.com/webhook' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(404)
      expect(data).toEqual({ error: 'Project not found' })
    })

    it('should return 500 on webhook creation error', async () => {
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
        if (table === 'webhooks') {
          return {
            insert: jest.fn(() => ({
              select: jest.fn(() => ({
                single: jest.fn(() => ({
                  data: null,
                  error: new Error('Webhook creation failed')
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks', {
        method: 'POST',
        body: JSON.stringify({ url: 'https://example.com/webhook' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to create webhook' })
    })

    it('should use default values for optional parameters', async () => {
      const webhookData = {
        url: 'https://example.com/webhook'
        // No event_types, secret, or is_active
      }

      const mockWebhook = {
        id: 'webhook-123',
        project_id: 'project-123',
        url: webhookData.url,
        event_types: ['run.complete'], // Default value
        secret: null, // Default value
        is_active: true, // Default value
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
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
            }))
          }
        }
        if (table === 'webhooks') {
          return {
            insert: jest.fn((data) => {
              expect(data.event_types).toEqual(['run.complete'])
              expect(data.secret).toBeNull()
              expect(data.is_active).toBe(true)
              return {
                select: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: mockWebhook,
                    error: null
                  }))
                }))
              }
            })
          }
        }
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks', {
        method: 'POST',
        body: JSON.stringify(webhookData),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await POST(request, { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({ webhook: mockWebhook })
    })
  })

  describe('PUT /api/projects/[id]/webhooks/[webhookId]', () => {
    let webhookParams: any

    beforeEach(() => {
      webhookParams = {
        id: 'project-123',
        webhookId: 'webhook-123'
      }
    })

    it('should update webhook with valid data', async () => {
      const updateData = {
        url: 'https://updated.com/webhook',
        event_types: ['run.complete', 'run.failed'],
        secret: 'new-secret',
        is_active: false
      }

      const mockWebhook = {
        id: 'webhook-123',
        project_id: 'project-123',
        projects: { created_by: 'user-123' }
      }

      const mockUpdatedWebhook = {
        id: 'webhook-123',
        project_id: 'project-123',
        url: updateData.url,
        event_types: updateData.event_types,
        secret: updateData.secret,
        is_active: updateData.is_active,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T01:00:00Z'
      }

      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockImplementation((table) => {
        if (table === 'webhooks') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  eq: jest.fn(() => ({
                    single: jest.fn(() => ({
                      data: mockWebhook,
                      error: null
                    }))
                  }))
                }))
              }))
            })),
            update: jest.fn(() => ({
              eq: jest.fn(() => ({
                select: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: mockUpdatedWebhook,
                    error: null
                  }))
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks/webhook-123', {
        method: 'PUT',
        body: JSON.stringify(updateData),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await PUT(request, { params: Promise.resolve(webhookParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({ webhook: mockUpdatedWebhook })
    })

    it('should return 401 for unauthenticated user', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: null },
        error: new Error('Not authenticated')
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks/webhook-123', {
        method: 'PUT',
        body: JSON.stringify({ url: 'https://updated.com/webhook' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await PUT(request, { params: Promise.resolve(webhookParams) })
      const data = await response.json()

      expect(response.status).toBe(401)
      expect(data).toEqual({ error: 'Unauthorized' })
    })

    it('should return 400 for invalid URL format', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks/webhook-123', {
        method: 'PUT',
        body: JSON.stringify({ url: 'not-a-valid-url' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await PUT(request, { params: Promise.resolve(webhookParams) })
      const data = await response.json()

      expect(response.status).toBe(400)
      expect(data).toEqual({ error: 'Invalid URL format' })
    })

    it('should return 404 for non-existent webhook', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockReturnValue({
        select: jest.fn(() => ({
          eq: jest.fn(() => ({
            eq: jest.fn(() => ({
              eq: jest.fn(() => ({
                single: jest.fn(() => ({
                  data: null,
                  error: new Error('Not found')
                }))
              }))
            }))
          }))
        }))
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks/webhook-123', {
        method: 'PUT',
        body: JSON.stringify({ url: 'https://updated.com/webhook' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await PUT(request, { params: Promise.resolve(webhookParams) })
      const data = await response.json()

      expect(response.status).toBe(404)
      expect(data).toEqual({ error: 'Webhook not found' })
    })

    it('should return 500 on webhook update error', async () => {
      const mockWebhook = {
        id: 'webhook-123',
        project_id: 'project-123',
        projects: { created_by: 'user-123' }
      }

      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockImplementation((table) => {
        if (table === 'webhooks') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  eq: jest.fn(() => ({
                    single: jest.fn(() => ({
                      data: mockWebhook,
                      error: null
                    }))
                  }))
                }))
              }))
            })),
            update: jest.fn(() => ({
              eq: jest.fn(() => ({
                select: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: null,
                    error: new Error('Update failed')
                  }))
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks/webhook-123', {
        method: 'PUT',
        body: JSON.stringify({ url: 'https://updated.com/webhook' }),
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const response = await PUT(request, { params: Promise.resolve(webhookParams) })
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to update webhook' })
    })
  })

  describe('DELETE /api/projects/[id]/webhooks/[webhookId]', () => {
    let webhookParams: any

    beforeEach(() => {
      webhookParams = {
        id: 'project-123',
        webhookId: 'webhook-123'
      }
    })

    it('should delete webhook', async () => {
      const mockWebhook = {
        id: 'webhook-123',
        project_id: 'project-123',
        projects: { created_by: 'user-123' }
      }

      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockImplementation((table) => {
        if (table === 'webhooks') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  eq: jest.fn(() => ({
                    single: jest.fn(() => ({
                      data: mockWebhook,
                      error: null
                    }))
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
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks/webhook-123', {
        method: 'DELETE'
      })

      const response = await DELETE(request, { params: Promise.resolve(webhookParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({ success: true })
    })

    it('should return 401 for unauthenticated user', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: null },
        error: new Error('Not authenticated')
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks/webhook-123', {
        method: 'DELETE'
      })

      const response = await DELETE(request, { params: Promise.resolve(webhookParams) })
      const data = await response.json()

      expect(response.status).toBe(401)
      expect(data).toEqual({ error: 'Unauthorized' })
    })

    it('should return 404 for non-existent webhook', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockReturnValue({
        select: jest.fn(() => ({
          eq: jest.fn(() => ({
            eq: jest.fn(() => ({
              eq: jest.fn(() => ({
                single: jest.fn(() => ({
                  data: null,
                  error: new Error('Not found')
                }))
              }))
            }))
          }))
        }))
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks/webhook-123', {
        method: 'DELETE'
      })

      const response = await DELETE(request, { params: Promise.resolve(webhookParams) })
      const data = await response.json()

      expect(response.status).toBe(404)
      expect(data).toEqual({ error: 'Webhook not found' })
    })

    it('should return 500 on webhook deletion error', async () => {
      const mockWebhook = {
        id: 'webhook-123',
        project_id: 'project-123',
        projects: { created_by: 'user-123' }
      }

      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: mockUser },
        error: null
      })

      mockSupabase.from.mockImplementation((table) => {
        if (table === 'webhooks') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  eq: jest.fn(() => ({
                    single: jest.fn(() => ({
                      data: mockWebhook,
                      error: null
                    }))
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
        return mockSupabase.from(table)
      })

      const request = new NextRequest('http://localhost:3000/api/projects/project-123/webhooks/webhook-123', {
        method: 'DELETE'
      })

      const response = await DELETE(request, { params: Promise.resolve(webhookParams) })
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to delete webhook' })
    })
  })

  describe('GET /api/projects/[id]/webhooks/events', () => {
    it('should return webhook events for authenticated user', async () => {
      const mockWebhooks = [
        { id: 'webhook-1' },
        { id: 'webhook-2' }
      ]

      const mockEvents = [
        {
          webhook_id: 'webhook-1',
          attempted_at: '2024-01-01T00:00:00Z',
          status_code: 200
        },
        {
          webhook_id: 'webhook-2',
          attempted_at: '2024-01-01T01:00:00Z',
          status_code: 404
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
        if (table === 'webhooks') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                data: mockWebhooks,
                error: null
              }))
            }))
          }
        }
        if (table === 'webhook_events') {
          return {
            select: jest.fn(() => ({
              in: jest.fn(() => ({
                order: jest.fn(() => ({
                  data: mockEvents,
                  error: null
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET_EVENTS(new NextRequest('http://localhost:3000/api/projects/project-123/webhooks/events'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({
        events: {
          'webhook-1': mockEvents[0],
          'webhook-2': mockEvents[1]
        }
      })
    })

    it('should return empty events when no webhooks exist', async () => {
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
        if (table === 'webhooks') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                data: [],
                error: null
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET_EVENTS(new NextRequest('http://localhost:3000/api/projects/project-123/webhooks/events'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({ events: {} })
    })

    it('should return 401 for unauthenticated user', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: null },
        error: new Error('Not authenticated')
      })

      const response = await GET_EVENTS(new NextRequest('http://localhost:3000/api/projects/project-123/webhooks/events'), { params: Promise.resolve(mockParams) })
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

      const response = await GET_EVENTS(new NextRequest('http://localhost:3000/api/projects/project-123/webhooks/events'), { params: Promise.resolve(mockParams) })
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
        if (table === 'webhooks') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                data: null,
                error: new Error('Database error')
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET_EVENTS(new NextRequest('http://localhost:3000/api/projects/project-123/webhooks/events'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to fetch webhooks' })
    })
  })
})
