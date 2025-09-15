import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '../../../../../utils/supabase/server'
import { cookies } from 'next/headers'
import { v4 as uuidv4 } from 'uuid'
import { enqueueImmediateJob, scheduleJob } from '../../../../../utils/cloud-tasks/scheduler'

// GET /api/projects/[id]/runs - List all runs for a project
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const cookieStore = cookies()
    const supabase = await createClient(cookieStore)
    
    // Get the authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id: projectId } = await params

    // Check if project exists and user owns it
    const { data: project, error: projectError } = await supabase
      .from('projects')
      .select('id')
      .eq('id', projectId)
      .eq('created_by', user.id)
      .single()

    if (projectError || !project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Fetch runs for the project
    const { data: runs, error } = await supabase
      .from('runs')
      .select(`
        id,
        project_id,
        initiated_by,
        started_at,
        finished_at,
        summary,
        status,
        created_at,
        updated_at,
        metrics
      `)
      .eq('project_id', projectId)
      .order('created_at', { ascending: false })

    if (error) {
      console.error('Error fetching runs:', error)
      return NextResponse.json({ error: 'Failed to fetch runs' }, { status: 500 })
    }

    return NextResponse.json({ runs })
  } catch (err: any) {
    console.error('Error in GET /api/projects/[id]/runs:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal server error' }, { status: 500 })
  }
}

// POST /api/projects/[id]/runs - Create a new run for a project
export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const cookieStore = cookies()
    const supabase = await createClient(cookieStore)
    
    // Get the authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id: projectId } = await params
    const body = await req.json()
    const { 
      url, 
      priority = 'NORMAL',
      render_mode = 'STATIC',
      metadata = {}
    } = body

    // Validate URL
    if (!url) {
      return NextResponse.json({ error: 'URL is required' }, { status: 400 })
    }

    try {
      new URL(url)
    } catch {
      return NextResponse.json({ error: 'Invalid URL' }, { status: 400 })
    }

    // Check if project exists and user owns it
    const { data: project, error: projectError } = await supabase
      .from('projects')
      .select(`
        id,
        domain,
        project_configs (
          crawl_depth
        )
      `)
      .eq('id', projectId)
      .eq('created_by', user.id)
      .single()

    if (projectError || !project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Create a new run for this generation
    const { data: run, error: runError } = await supabase
      .from('runs')
      .insert({
        project_id: projectId,
        initiated_by: user.id,
        status: 'QUEUED',
        summary: `Generation run for ${url}`,
        metrics: {}
      })
      .select()
      .single()

    if (runError) {
      console.error('Error creating run:', runError)
      return NextResponse.json({ error: 'Failed to create run' }, { status: 500 })
    }

    // Generate job ID for Cloud Tasks
    const jobId = uuidv4()

    // Enqueue job via Cloud Tasks with run_id for immediate execution
    await enqueueImmediateJob({ 
      id: jobId, 
      url, 
      projectId,
      runId: run.id,
      priority,
      render_mode
    })

    return NextResponse.json({ 
      run: { 
        id: run.id,
        project_id: run.project_id,
        status: run.status,
        summary: run.summary,
        created_at: run.created_at
      },
      job: { 
        id: jobId, 
        status: 'queued',
        url,
        projectId
      } 
    })
  } catch (err: any) {
    console.error('Error in POST /api/projects/[id]/runs:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal server error' }, { status: 500 })
  }
}
