import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '../../../utils/supabase/server'
import { cookies } from 'next/headers'
import { v4 as uuidv4 } from 'uuid'
import { enqueueImmediateJob } from '../../../utils/cloud-tasks/scheduler'

// Helper function to convert schedule to cron expression and calculate next run
function getCronAndNextRun(schedule: string): { cron_expression: string | null, next_run_at: string | null } {
  const now = new Date()
  
  switch (schedule) {
    case 'daily':
      // Run daily at 2 AM
      const daily = new Date(now)
      daily.setHours(2, 0, 0, 0)
      if (daily <= now) {
        daily.setDate(daily.getDate() + 1)
      }
      return {
        cron_expression: '0 2 * * *',
        next_run_at: daily.toISOString()
      }
    case 'weekly':
      // Run weekly on Sunday at 2 AM
      const weekly = new Date(now)
      weekly.setHours(2, 0, 0, 0)
      const daysUntilSunday = (7 - weekly.getDay()) % 7
      weekly.setDate(weekly.getDate() + (daysUntilSunday === 0 ? 7 : daysUntilSunday))
      return {
        cron_expression: '0 2 * * 0',
        next_run_at: weekly.toISOString()
      }
    case 'custom':
      return {
        cron_expression: null,
        next_run_at: null
      }
    default:
      return {
        cron_expression: null,
        next_run_at: null
      }
  }
}

// GET /api/projects - List all projects for the authenticated user
export async function GET() {
  try {
    const cookieStore = cookies()
    const supabase = await createClient(cookieStore)
    
    // Get the authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Fetch projects for the user
    const { data: projects, error } = await supabase
      .from('projects')
      .select(`
        id,
        name,
        domain,
        description,
        created_at,
        updated_at,
        metadata,
        project_configs (
          crawl_depth,
          cron_expression,
          last_run_at,
          next_run_at,
          is_enabled,
          config
        )
      `)
      .eq('created_by', user.id)
      .order('created_at', { ascending: false })

    if (error) {
      console.error('Error fetching projects:', error)
      return NextResponse.json({ error: 'Failed to fetch projects' }, { status: 500 })
    }

    return NextResponse.json({ projects })
  } catch (err: any) {
    console.error('Error in GET /api/projects:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal server error' }, { status: 500 })
  }
}

// POST /api/projects - Create a new project
export async function POST(req: NextRequest) {
  try {
    const cookieStore = cookies()
    const supabase = await createClient(cookieStore)
    
    // Get the authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await req.json()
    const { 
      name, 
      domain, 
      description, 
      crawl_depth = 2,
      cron_expression = 'daily',
      is_enabled = true
    } = body

    // Validate required fields
    if (!name || !domain) {
      return NextResponse.json({ error: 'Name and domain are required' }, { status: 400 })
    }

    // Validate URL
    try {
      new URL(domain.startsWith('http') ? domain : `https://${domain}`)
    } catch {
      return NextResponse.json({ error: 'Invalid domain URL' }, { status: 400 })
    }


    // Create project
    const { data: project, error: projectError } = await supabase
      .from('projects')
      .insert({
        created_by: user.id,
        name,
        domain: domain.startsWith('http') ? domain : `https://${domain}`,
        description,
        metadata: {}
      })
      .select()
      .single()

    if (projectError) {
      console.error('Error creating project:', projectError)
      return NextResponse.json({ error: 'Failed to create project' }, { status: 500 })
    }

    // Get cron expression and next run time
    const { cron_expression: cronExpr, next_run_at } = getCronAndNextRun(cron_expression)

    // Create project configuration
    const { error: configError } = await supabase
      .from('project_configs')
      .insert({
        project_id: project.id,
        crawl_depth,
        cron_expression: cronExpr,
        next_run_at,
        is_enabled,
        config: {}
      })

    if (configError) {
      console.error('Error creating project config:', configError)
      // Clean up the project if config creation fails
      await supabase.from('projects').delete().eq('id', project.id)
      return NextResponse.json({ error: 'Failed to create project configuration' }, { status: 500 })
    }

    // Create an initial run and enqueue it immediately
    if (is_enabled) {
      try {
        // Create a new run for initial generation
        const { data: run, error: runError } = await supabase
          .from('runs')
          .insert({
            project_id: project.id,
            initiated_by: user.id,
            status: 'QUEUED',
            metrics: {}
          })
          .select()
          .single()

        if (runError) {
          console.error('Error creating initial run:', runError)
        } else {
          // Generate job ID for Cloud Tasks
          const jobId = uuidv4()
          
          // Enqueue job for immediate execution via Cloud Tasks
          await enqueueImmediateJob({
            id: jobId,
            url: project.domain,  
            projectId: project.id,
            runId: run.id,
            priority: 'NORMAL',
            render_mode: 'STATIC',
            isScheduled: false,
            isInitialRun: true
          })
        }
      } catch (error) {
        console.error('Error setting up initial run:', error)
        // Don't fail the project creation, just log the error
      }
    }

    return NextResponse.json({ project }, { status: 201 })
  } catch (err: any) {
    console.error('Error in POST /api/projects:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal server error' }, { status: 500 })
  }
}
