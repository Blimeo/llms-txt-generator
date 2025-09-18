import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '../../../../utils/supabase/server'
import { cookies } from 'next/headers'
import { deleteTasks } from '../../../../utils/cloud-tasks/scheduler'

// GET /api/projects/[id] - Get a specific project
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

    // Fetch project with configuration
    const { data: project, error: projectError } = await supabase
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
      .eq('id', projectId)
      .eq('created_by', user.id)
      .single()

    if (projectError) {
      if (projectError.code === 'PGRST116') {
        return NextResponse.json({ error: 'Project not found' }, { status: 404 })
      }
      console.error('Error fetching project:', projectError)
      return NextResponse.json({ error: 'Failed to fetch project' }, { status: 500 })
    }

    return NextResponse.json({ project })
  } catch (err: any) {
    console.error('Error in GET /api/projects/[id]:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal server error' }, { status: 500 })
  }
}

// PUT /api/projects/[id] - Update a project
export async function PUT(
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
      name, 
      domain, 
      description, 
      crawl_depth
    } = body

    // Check if project exists and user owns it
    const { data: existingProject, error: checkError } = await supabase
      .from('projects')
      .select('id')
      .eq('id', projectId)
      .eq('created_by', user.id)
      .single()

    if (checkError || !existingProject) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Update project
    const projectUpdateData: any = {}
    if (name !== undefined) projectUpdateData.name = name
    if (domain !== undefined) {
      try {
        new URL(domain.startsWith('http') ? domain : `https://${domain}`)
        projectUpdateData.domain = domain.startsWith('http') ? domain : `https://${domain}`
      } catch {
        return NextResponse.json({ error: 'Invalid domain URL' }, { status: 400 })
      }
    }
    if (description !== undefined) projectUpdateData.description = description

    if (Object.keys(projectUpdateData).length > 0) {
      const { error: projectError } = await supabase
        .from('projects')
        .update(projectUpdateData)
        .eq('id', projectId)

      if (projectError) {
        console.error('Error updating project:', projectError)
        return NextResponse.json({ error: 'Failed to update project' }, { status: 500 })
      }
    }

    // Update project configuration if provided
    const configUpdateData: any = {}
    if (crawl_depth !== undefined) configUpdateData.crawl_depth = crawl_depth

    if (Object.keys(configUpdateData).length > 0) {
      const { error: configError } = await supabase
        .from('project_configs')
        .update(configUpdateData)
        .eq('project_id', projectId)

      if (configError) {
        console.error('Error updating project config:', configError)
        return NextResponse.json({ error: 'Failed to update project configuration' }, { status: 500 })
      }
    }

    return NextResponse.json({ success: true })
  } catch (err: any) {
    console.error('Error in PUT /api/projects/[id]:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal server error' }, { status: 500 })
  }
}

// DELETE /api/projects/[id] - Delete a project
export async function DELETE(
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
    const { data: existingProject, error: checkError } = await supabase
      .from('projects')
      .select('id')
      .eq('id', projectId)
      .eq('created_by', user.id)
      .single()

    if (checkError || !existingProject) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Get all queued runs for this project
    const { data: queuedRuns, error: runsError } = await supabase
      .from('runs')
      .select('id')
      .eq('project_id', projectId)
      .in('status', ['QUEUED', 'IN_PROGRESS'])

    if (runsError) {
      console.error('Error fetching queued runs:', runsError)
      return NextResponse.json({ error: 'Failed to fetch queued runs' }, { status: 500 })
    }

    // Delete queued runs from Cloud Tasks if any exist
    if (queuedRuns && queuedRuns.length > 0) {
      const runIds = queuedRuns.map(run => run.id)
      console.log(`Deleting ${runIds.length} queued tasks from Cloud Tasks for project ${projectId}`)
      
      try {
        const deleteResults = await deleteTasks(runIds)
        const failedDeletes = deleteResults.filter(result => !result.success)
        
        if (failedDeletes.length > 0) {
          console.warn(`Failed to delete ${failedDeletes.length} tasks from Cloud Tasks:`, failedDeletes)
          // Continue with project deletion even if some tasks couldn't be deleted
        } else {
          console.log(`Successfully deleted all ${runIds.length} queued tasks from Cloud Tasks`)
        }
      } catch (error) {
        console.error('Error deleting tasks from Cloud Tasks:', error)
        // Continue with project deletion even if Cloud Tasks deletion fails
      }
    }

    // Delete project (cascade will handle related records)
    const { error: deleteError } = await supabase
      .from('projects')
      .delete()
      .eq('id', projectId)

    if (deleteError) {
      console.error('Error deleting project:', deleteError)
      return NextResponse.json({ error: 'Failed to delete project' }, { status: 500 })
    }

    return NextResponse.json({ success: true })
  } catch (err: any) {
    console.error('Error in DELETE /api/projects/[id]:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal server error' }, { status: 500 })
  }
}
