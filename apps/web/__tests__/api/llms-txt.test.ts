import { NextRequest } from 'next/server'
import { GET } from '../../app/api/projects/[id]/runs/[runId]/llms.txt/route'
import { createClient } from '../../utils/supabase/server'

// Mock dependencies
jest.mock('../../utils/supabase/server')
jest.mock('next/headers', () => ({
  cookies: jest.fn(() => Promise.resolve([]))
}))

const mockCreateClient = createClient as jest.MockedFunction<typeof createClient>

describe('/api/projects/[id]/runs/[runId]/llms.txt', () => {
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
      id: 'project-123',
      runId: 'run-123'
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
        }))
      }))
    }

    mockCreateClient.mockResolvedValue(mockSupabase)
  })

  describe('GET /api/projects/[id]/runs/[runId]/llms.txt', () => {
    it('should redirect to public URL when artifact has public_url', async () => {
      const mockProject = {
        id: 'project-123'
      }

      const mockRun = {
        id: 'run-123',
        status: 'COMPLETE_WITH_DIFFS',
        project_id: 'project-123'
      }

      const mockArtifact = {
        id: 'artifact-123',
        type: 'LLMS_TXT',
        storage_path: 's3://bucket/llms.txt',
        file_name: 'llms.txt',
        metadata: {
          public_url: 'https://cdn.example.com/llms.txt'
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
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: mockRun,
                    error: null
                  }))
                }))
              }))
            }))
          }
        }
        if (table === 'artifacts') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  order: jest.fn(() => ({
                    limit: jest.fn(() => ({
                      data: [mockArtifact],
                      error: null
                    }))
                  }))
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs/run-123/llms.txt'), { params: Promise.resolve(mockParams) })

      expect(response.status).toBe(302)
      expect(response.headers.get('location')).toBe('https://cdn.example.com/llms.txt')
    })

    it('should return storage path info when artifact has storage_path but no public_url', async () => {
      const mockProject = {
        id: 'project-123'
      }

      const mockRun = {
        id: 'run-123',
        status: 'COMPLETE_WITH_DIFFS',
        project_id: 'project-123'
      }

      const mockArtifact = {
        id: 'artifact-123',
        type: 'LLMS_TXT',
        storage_path: 's3://bucket/llms.txt',
        file_name: 'llms.txt',
        metadata: {}
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
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: mockRun,
                    error: null
                  }))
                }))
              }))
            }))
          }
        }
        if (table === 'artifacts') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  order: jest.fn(() => ({
                    limit: jest.fn(() => ({
                      data: [mockArtifact],
                      error: null
                    }))
                  }))
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs/run-123/llms.txt'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual({
        message: 'File available at storage path',
        storage_path: 's3://bucket/llms.txt',
        file_name: 'llms.txt'
      })
    })

    it('should return content directly when artifact has content in metadata', async () => {
      const mockProject = {
        id: 'project-123'
      }

      const mockRun = {
        id: 'run-123',
        status: 'COMPLETE_WITH_DIFFS',
        project_id: 'project-123'
      }

      const mockArtifact = {
        id: 'artifact-123',
        type: 'LLMS_TXT',
        storage_path: null,
        file_name: 'llms.txt',
        metadata: {
          content: 'Site: example.com\nGenerated-At: 2024-01-01T00:00:00Z\nStatus: COMPLETE_WITH_DIFFS'
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
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: mockRun,
                    error: null
                  }))
                }))
              }))
            }))
          }
        }
        if (table === 'artifacts') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  order: jest.fn(() => ({
                    limit: jest.fn(() => ({
                      data: [mockArtifact],
                      error: null
                    }))
                  }))
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs/run-123/llms.txt'), { params: Promise.resolve(mockParams) })

      expect(response.status).toBe(200)
      expect(response.headers.get('content-type')).toBe('text/plain')
      expect(response.headers.get('content-disposition')).toBe('attachment; filename="llms.txt"')
      
      const content = await response.text()
      expect(content).toBe('Site: example.com\nGenerated-At: 2024-01-01T00:00:00Z\nStatus: COMPLETE_WITH_DIFFS')
    })

    it('should return placeholder content when artifact has no content or storage path', async () => {
      const mockProject = {
        id: 'project-123'
      }

      const mockRun = {
        id: 'run-123',
        status: 'COMPLETE_WITH_DIFFS',
        project_id: 'project-123'
      }

      const mockArtifact = {
        id: 'artifact-123',
        type: 'LLMS_TXT',
        storage_path: null,
        file_name: 'llms.txt',
        metadata: {}
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
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: mockRun,
                    error: null
                  }))
                }))
              }))
            }))
          }
        }
        if (table === 'artifacts') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  order: jest.fn(() => ({
                    limit: jest.fn(() => ({
                      data: [mockArtifact],
                      error: null
                    }))
                  }))
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs/run-123/llms.txt'), { params: Promise.resolve(mockParams) })

      expect(response.status).toBe(200)
      expect(response.headers.get('content-type')).toBe('text/plain')
      expect(response.headers.get('content-disposition')).toBe('attachment; filename="llms.txt"')
      
      const content = await response.text()
      expect(content).toContain('Site: project-123')
      expect(content).toContain('Status: COMPLETE_WITH_DIFFS')
      expect(content).toContain('Run ID: run-123')
      expect(content).toContain('Project ID: project-123')
    })

    it('should return 401 for unauthenticated user', async () => {
      mockSupabase.auth.getUser.mockResolvedValue({
        data: { user: null },
        error: new Error('Not authenticated')
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs/run-123/llms.txt'), { params: Promise.resolve(mockParams) })
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

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs/run-123/llms.txt'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(404)
      expect(data).toEqual({ error: 'Project not found' })
    })

    it('should return 404 for non-existent run', async () => {
      const mockProject = {
        id: 'project-123'
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
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs/run-123/llms.txt'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(404)
      expect(data).toEqual({ error: 'Run not found' })
    })

    it('should return 400 for incomplete run', async () => {
      const mockProject = {
        id: 'project-123'
      }

      const mockRun = {
        id: 'run-123',
        status: 'IN_PROGRESS',
        project_id: 'project-123'
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
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: mockRun,
                    error: null
                  }))
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs/run-123/llms.txt'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(400)
      expect(data).toEqual({ error: 'Run is not complete yet' })
    })

    it('should return 404 when no llms.txt file found', async () => {
      const mockProject = {
        id: 'project-123'
      }

      const mockRun = {
        id: 'run-123',
        status: 'COMPLETE_WITH_DIFFS',
        project_id: 'project-123'
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
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: mockRun,
                    error: null
                  }))
                }))
              }))
            }))
          }
        }
        if (table === 'artifacts') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  order: jest.fn(() => ({
                    limit: jest.fn(() => ({
                      data: null,
                      error: null
                    }))
                  }))
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs/run-123/llms.txt'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(404)
      expect(data).toEqual({ error: 'No llms.txt file found for this run' })
    })

    it('should return 404 when project fetch fails', async () => {
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
                    data: null,
                    error: new Error('Database error')
                  }))
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs/run-123/llms.txt'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(404)
      expect(data).toEqual({ error: 'Project not found' })
    })

    it('should return 500 on artifacts fetch error', async () => {
      const mockProject = {
        id: 'project-123'
      }

      const mockRun = {
        id: 'run-123',
        status: 'COMPLETE_WITH_DIFFS',
        project_id: 'project-123'
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
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: mockRun,
                    error: null
                  }))
                }))
              }))
            }))
          }
        }
        if (table === 'artifacts') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  order: jest.fn(() => ({
                    limit: jest.fn(() => ({
                      data: null,
                      error: new Error('Artifacts fetch failed')
                    }))
                  }))
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs/run-123/llms.txt'), { params: Promise.resolve(mockParams) })
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data).toEqual({ error: 'Failed to fetch artifacts' })
    })

    it('should handle COMPLETE_NO_DIFFS status', async () => {
      const mockProject = {
        id: 'project-123'
      }

      const mockRun = {
        id: 'run-123',
        status: 'COMPLETE_NO_DIFFS',
        project_id: 'project-123'
      }

      const mockArtifact = {
        id: 'artifact-123',
        type: 'LLMS_TXT',
        storage_path: null,
        file_name: 'llms.txt',
        metadata: {
          content: 'Site: example.com\nGenerated-At: 2024-01-01T00:00:00Z\nStatus: COMPLETE_NO_DIFFS'
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
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  single: jest.fn(() => ({
                    data: mockRun,
                    error: null
                  }))
                }))
              }))
            }))
          }
        }
        if (table === 'artifacts') {
          return {
            select: jest.fn(() => ({
              eq: jest.fn(() => ({
                eq: jest.fn(() => ({
                  order: jest.fn(() => ({
                    limit: jest.fn(() => ({
                      data: [mockArtifact],
                      error: null
                    }))
                  }))
                }))
              }))
            }))
          }
        }
        return mockSupabase.from(table)
      })

      const response = await GET(new NextRequest('http://localhost:3000/api/projects/project-123/runs/run-123/llms.txt'), { params: Promise.resolve(mockParams) })

      expect(response.status).toBe(200)
      expect(response.headers.get('content-type')).toBe('text/plain')
      
      const content = await response.text()
      expect(content).toContain('Status: COMPLETE_NO_DIFFS')
    })
  })
})
