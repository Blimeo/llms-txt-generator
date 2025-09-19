# Testing Guide

This directory contains comprehensive tests for the Next.js web application.

## Test Structure

```
__tests__/
├── api/                    # API route tests
│   ├── projects.test.ts
│   └── project-runs.test.ts
├── components/             # React component tests
│   ├── CreateProjectModal.test.tsx
│   ├── LoadingSpinner.test.tsx
│   ├── MessageAlert.test.tsx
│   ├── Navigation.test.tsx
│   └── ProjectCard.test.tsx
├── utils/                  # Utility function tests
│   ├── helpers.test.ts
│   └── test-utils.tsx      # Test utilities and mock data
├── setup.ts               # Global test setup
└── README.md              # This file
```

## Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

## Test Configuration

- **Jest**: Testing framework
- **React Testing Library**: Component testing utilities
- **jsdom**: DOM environment for tests
- **Coverage**: 70% threshold for branches, functions, lines, and statements

## Writing Tests

### Component Tests

Use React Testing Library for component tests:

```tsx
import { render, screen, fireEvent } from '../utils/test-utils'
import MyComponent from '@/app/components/MyComponent'

describe('MyComponent', () => {
  it('should render correctly', () => {
    render(<MyComponent />)
    expect(screen.getByText('Expected text')).toBeInTheDocument()
  })
})
```

### API Route Tests

Test API routes by mocking dependencies:

```tsx
import { GET, POST } from '@/app/api/my-route/route'
import { createClient } from '@/app/utils/supabase/server'

jest.mock('@/app/utils/supabase/server')

describe('/api/my-route', () => {
  it('should handle GET requests', async () => {
    // Mock setup
    const response = await GET()
    expect(response.status).toBe(200)
  })
})
```

### Utility Function Tests

Test pure functions directly:

```tsx
import { myUtilityFunction } from '@/app/utils/helpers'

describe('myUtilityFunction', () => {
  it('should return expected result', () => {
    expect(myUtilityFunction('input')).toBe('expected output')
  })
})
```

## Mock Data

Use the test utilities for consistent mock data:

```tsx
import { createMockProject, createMockRun } from '../utils/test-utils'

const mockProject = createMockProject({ name: 'Custom Name' })
const mockRun = createMockRun({ status: 'COMPLETE' })
```

## Best Practices

1. **Test Behavior, Not Implementation**: Focus on what the component does, not how it does it
2. **Use Semantic Queries**: Prefer `getByRole`, `getByLabelText`, `getByText` over `getByTestId`
3. **Mock External Dependencies**: Mock Supabase, Cloud Tasks, and other external services
4. **Test Edge Cases**: Include tests for error states, loading states, and edge cases
5. **Keep Tests Simple**: Each test should focus on one specific behavior
6. **Use Descriptive Names**: Test names should clearly describe what is being tested

## Coverage

The test suite aims for 70% coverage across:
- Branches (conditional logic)
- Functions (all functions called)
- Lines (all lines executed)
- Statements (all statements executed)

Run `npm run test:coverage` to see detailed coverage reports.

## Debugging Tests

1. Use `screen.debug()` to see the current DOM state
2. Use `console.log()` for debugging (will be filtered in CI)
3. Use `--verbose` flag for detailed test output
4. Use `--no-coverage` flag to speed up test runs during development

## Common Patterns

### Testing Form Submissions

```tsx
const user = userEvent.setup()
await user.type(screen.getByLabelText('Name'), 'Test Name')
await user.click(screen.getByText('Submit'))
expect(mockOnSubmit).toHaveBeenCalledWith({ name: 'Test Name' })
```

### Testing Async Operations

```tsx
await waitFor(() => {
  expect(screen.getByText('Loading complete')).toBeInTheDocument()
})
```

### Testing Error States

```tsx
render(<Component error="Something went wrong" />)
expect(screen.getByText('Something went wrong')).toBeInTheDocument()
```

### Testing Loading States

```tsx
render(<Component loading={true} />)
expect(screen.getByText('Loading...')).toBeInTheDocument()
expect(screen.getByText('Submit')).toBeDisabled()
```
