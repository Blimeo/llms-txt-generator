require('@testing-library/jest-dom')

// Global test utilities
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}))

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})

// Mock Next.js components
jest.mock('next/server', () => ({
  NextRequest: class NextRequest {
    constructor(input, init = {}) {
      this.url = typeof input === 'string' ? input : input.url
      this.method = init.method || 'GET'
      this.headers = new Headers(init.headers)
      this.body = init.body
    }

    async json() {
      return JSON.parse(this.body)
    }
  },
  NextResponse: class NextResponse {
    constructor(body, init = {}) {
      this.body = body
      this.status = init.status || 200
      this.statusText = init.statusText || 'OK'
      this.headers = new Headers(init.headers)
    }

    async json() {
      return JSON.parse(this.body)
    }

    async text() {
      return this.body
    }

    static json(data, init = {}) {
      return new NextResponse(JSON.stringify(data), {
        status: init.status || 200,
        statusText: init.statusText || 'OK',
        headers: {
          'Content-Type': 'application/json',
          ...init.headers
        }
      })
    }

    static redirect(url, status = 302) {
      return new NextResponse(null, {
        status,
        headers: { location: url }
      })
    }
  }
}))

// Mock Headers
global.Headers = global.Headers || class Headers {
  constructor(init = {}) {
    this.map = new Map()
    if (init) {
      Object.entries(init).forEach(([key, value]) => {
        this.map.set(key.toLowerCase(), value)
      })
    }
  }

  get(name) {
    return this.map.get(name.toLowerCase())
  }

  set(name, value) {
    this.map.set(name.toLowerCase(), value)
  }

  has(name) {
    return this.map.has(name.toLowerCase())
  }

  delete(name) {
    this.map.delete(name.toLowerCase())
  }

  forEach(callback) {
    this.map.forEach(callback)
  }
}
