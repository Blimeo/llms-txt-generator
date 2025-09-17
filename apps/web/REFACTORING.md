# NextJS App Refactoring

This document outlines the refactoring changes made to improve code organization and maintainability.

## Structure Changes

### 1. Types and Interfaces (`/types/index.ts`)
- Centralized all TypeScript interfaces and types
- Includes project, run, webhook, and form data types
- Component prop types for better type safety

### 2. Reusable Components (`/components/`)
- **ProjectCard**: Displays project information with actions
- **CreateProjectModal**: Modal form for creating new projects
- **WebhookCard**: Displays webhook information and controls
- **WebhookForm**: Form for creating/editing webhooks
- **RunCard**: Displays run information and download links
- **ProjectDetails**: Project information display component
- **MessageAlert**: Reusable alert component for messages
- **LoadingSpinner**: Loading state component
- **UnauthorizedAlert**: Authentication required alert
- **NotFoundAlert**: Resource not found alert

### 3. Utility Functions (`/utils/helpers.ts`)
- **getScheduleDisplayText**: Converts cron expressions to readable text
- **getProjectConfig**: Safely extracts project configuration
- **getStatusColor**: Returns CSS classes for status colors
- **getStatusDisplayText**: Converts status codes to readable text
- **formatDate**: Formats date strings consistently
- **getWebhookEventStatus**: Gets webhook event status information

### 4. Component Index (`/components/index.ts`)
- Barrel export for cleaner imports
- Allows importing multiple components from a single path

## Benefits

1. **Code Reusability**: Common UI patterns extracted into reusable components
2. **Type Safety**: Centralized type definitions prevent inconsistencies
3. **Maintainability**: Smaller, focused components are easier to maintain
4. **Consistency**: Shared utility functions ensure consistent behavior
5. **Cleaner Imports**: Barrel exports reduce import clutter
6. **Separation of Concerns**: Logic separated from presentation

## Usage Examples

### Before (Old Structure)
```tsx
// Inline interfaces and helper functions
interface Project {
  id: string
  name: string
  // ...
}

function getScheduleDisplayText(cronExpression: string | null): string {
  // Helper function repeated in multiple files
}

// Large component with mixed concerns
export default function ProjectsPage() {
  // 300+ lines of mixed UI and logic
}
```

### After (New Structure)
```tsx
// Clean imports
import { ProjectCard, CreateProjectModal, MessageAlert } from '../components'
import type { Project, CreateProjectFormData } from '@/types'
import { getScheduleDisplayText } from '../utils/helpers'

// Focused component
export default function ProjectsPage() {
  // Clean, focused component logic
  return (
    <>
      <MessageAlert message={message} />
      <CreateProjectModal {...modalProps} />
      {projects.map(project => (
        <ProjectCard key={project.id} {...projectProps} />
      ))}
    </>
  )
}
```

## File Organization

```
apps/web/
├── app/
│   ├── components/
│   │   ├── index.ts          # Barrel exports
│   │   ├── ProjectCard.tsx
│   │   ├── CreateProjectModal.tsx
│   │   ├── WebhookCard.tsx
│   │   ├── WebhookForm.tsx
│   │   ├── RunCard.tsx
│   │   ├── ProjectDetails.tsx
│   │   ├── MessageAlert.tsx
│   │   ├── LoadingSpinner.tsx
│   │   ├── UnauthorizedAlert.tsx
│   │   ├── NotFoundAlert.tsx
│   │   └── Navigation.tsx
│   ├── utils/
│   │   └── helpers.ts        # Shared utility functions
│   ├── page.tsx              # Refactored home page
│   └── projects/
│       ├── page.tsx          # Refactored projects list
│       └── [id]/
│           └── page.tsx      # Refactored project detail
├── types/
│   └── index.ts              # Centralized type definitions
└── REFACTORING.md            # This documentation
```

This refactoring maintains all existing functionality while significantly improving code organization and maintainability.
