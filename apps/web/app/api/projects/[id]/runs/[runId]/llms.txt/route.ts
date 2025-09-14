import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'
import { cookies } from 'next/headers'

// GET /api/projects/[id]/runs/[runId]/llms.txt - Serve generated llms.txt file
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string; runId: string }> }
) {
  try {
    const cookieStore = cookies()
    const supabase = await createClient(cookieStore)

    // Get the authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id: projectId, runId } = await params

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

    // Check if run exists and belongs to the project
    const { data: run, error: runError } = await supabase
      .from('runs')
      .select('id, status, project_id')
      .eq('id', runId)
      .eq('project_id', projectId)
      .single()

    if (runError || !run) {
      return NextResponse.json({ error: 'Run not found' }, { status: 404 })
    }

    // Check if run is complete
    if (run.status !== 'COMPLETE_WITH_DIFFS' && run.status !== 'COMPLETE_NO_DIFFS') {
      return NextResponse.json({ error: 'Run is not complete yet' }, { status: 400 })
    }

    // Look for artifacts associated with this run
    const { data: artifacts, error: artifactError } = await supabase
      .from('artifacts')
      .select('id, type, storage_path, file_name, metadata')
      .eq('run_id', runId)
      .eq('type', 'LLMS_TXT')
      .order('created_at', { ascending: false })
      .limit(1)

    if (artifactError) {
      console.error('Error fetching artifacts:', artifactError)
      return NextResponse.json({ error: 'Failed to fetch artifacts' }, { status: 500 })
    }

    if (!artifacts || artifacts.length === 0) {
      return NextResponse.json({ error: 'No llms.txt file found for this run' }, { status: 404 })
    }

    const artifact = artifacts[0]
    if (!artifact) {
      return NextResponse.json({ error: 'No llms.txt file found for this run' }, { status: 404 })
    }

    // If we have a public URL in metadata, redirect to it
    if (artifact.metadata?.public_url) {
      return NextResponse.redirect(artifact.metadata.public_url)
    }

    // If we have a storage path, redirect to it (for S3/Supabase Storage)
    if (artifact.storage_path) {
      // For now, we'll return a placeholder response
      // In a real implementation, you'd generate a presigned URL or serve from storage
      return NextResponse.json({
        message: 'File available at storage path',
        storage_path: artifact.storage_path,
        file_name: artifact.file_name
      })
    }

    // If the content is stored in the database metadata, serve it directly
    if (artifact.metadata?.content) {
      return new NextResponse(artifact.metadata.content, {
        headers: {
          'Content-Type': 'text/plain',
          'Content-Disposition': `attachment; filename="${artifact.file_name || 'llms.txt'}"`
        }
      })
    }

    // Fallback: return a placeholder llms.txt content
    const placeholderContent = `Site: ${projectId}
Generated-At: ${new Date().toISOString()}
Status: ${run.status}

[Note]
This is a placeholder llms.txt file. The actual generated content will be available once the worker processes this run.

Run ID: ${runId}
Project ID: ${projectId}
`

    return new NextResponse(placeholderContent, {
      headers: {
        'Content-Type': 'text/plain',
        'Content-Disposition': 'attachment; filename="llms.txt"'
      }
    })

  } catch (err: any) {
    console.error('Error in GET /api/projects/[id]/runs/[runId]/llms.txt:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal server error' }, { status: 500 })
  }
}
