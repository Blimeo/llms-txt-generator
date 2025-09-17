import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '../../../../../utils/supabase/server'
import { cookies } from 'next/headers'

// GET /api/projects/[id]/webhooks - Get all webhooks for a project
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

    // Verify project ownership
    const { data: project, error: projectError } = await supabase
      .from('projects')
      .select('id')
      .eq('id', projectId)
      .eq('created_by', user.id)
      .single()

    if (projectError || !project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Fetch webhooks for the project
    const { data: webhooks, error: webhooksError } = await supabase
      .from('webhooks')
      .select('*')
      .eq('project_id', projectId)
      .order('created_at', { ascending: false })

    if (webhooksError) {
      console.error('Error fetching webhooks:', webhooksError)
      return NextResponse.json({ error: 'Failed to fetch webhooks' }, { status: 500 })
    }

    return NextResponse.json({ webhooks })
  } catch (err: any) {
    console.error('Error in GET /api/projects/[id]/webhooks:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal server error' }, { status: 500 })
  }
}

// POST /api/projects/[id]/webhooks - Create a new webhook
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
    const { url, event_types, secret, is_active } = body

    // Validate required fields
    if (!url) {
      return NextResponse.json({ error: 'URL is required' }, { status: 400 })
    }

    // Validate URL format
    try {
      new URL(url)
    } catch {
      return NextResponse.json({ error: 'Invalid URL format' }, { status: 400 })
    }

    // Verify project ownership
    const { data: project, error: projectError } = await supabase
      .from('projects')
      .select('id')
      .eq('id', projectId)
      .eq('created_by', user.id)
      .single()

    if (projectError || !project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Create webhook
    const webhookData = {
      project_id: projectId,
      url,
      event_types: event_types || ['run.complete'],
      secret: secret || null,
      is_active: is_active !== undefined ? is_active : true
    }

    const { data: webhook, error: webhookError } = await supabase
      .from('webhooks')
      .insert(webhookData)
      .select()
      .single()

    if (webhookError) {
      console.error('Error creating webhook:', webhookError)
      return NextResponse.json({ error: 'Failed to create webhook' }, { status: 500 })
    }

    return NextResponse.json({ webhook })
  } catch (err: any) {
    console.error('Error in POST /api/projects/[id]/webhooks:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal server error' }, { status: 500 })
  }
}
