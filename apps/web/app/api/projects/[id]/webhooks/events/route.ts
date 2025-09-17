import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '../../../../../../utils/supabase/server'
import { cookies } from 'next/headers'

// GET /api/projects/[id]/webhooks/events - Get webhook events for all webhooks in a project
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

    // Get all webhook IDs for this project
    const { data: webhooks, error: webhooksError } = await supabase
      .from('webhooks')
      .select('id')
      .eq('project_id', projectId)

    if (webhooksError) {
      console.error('Error fetching webhooks:', webhooksError)
      return NextResponse.json({ error: 'Failed to fetch webhooks' }, { status: 500 })
    }

    if (!webhooks || webhooks.length === 0) {
      return NextResponse.json({ events: {} })
    }

    const webhookIds = webhooks.map(w => w.id)

    // Get the most recent event for each webhook
    const { data: events, error: eventsError } = await supabase
      .from('webhook_events')
      .select('webhook_id, attempted_at, status_code')
      .in('webhook_id', webhookIds)
      .order('attempted_at', { ascending: false })

    if (eventsError) {
      console.error('Error fetching webhook events:', eventsError)
      return NextResponse.json({ error: 'Failed to fetch webhook events' }, { status: 500 })
    }

    // Group events by webhook_id and get the most recent for each
    const eventsByWebhook: Record<string, any> = {}
    
    if (events) {
      for (const event of events) {
        if (!eventsByWebhook[event.webhook_id]) {
          eventsByWebhook[event.webhook_id] = event
        }
      }
    }

    return NextResponse.json({ events: eventsByWebhook })
  } catch (err: any) {
    console.error('Error in GET /api/projects/[id]/webhooks/events:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal server error' }, { status: 500 })
  }
}
