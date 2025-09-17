import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '../../../../../../utils/supabase/server'
import { cookies } from 'next/headers'

// PUT /api/projects/[id]/webhooks/[webhookId] - Update a webhook
export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ id: string; webhookId: string }> }
) {
  try {
    const cookieStore = cookies()
    const supabase = await createClient(cookieStore)
    
    // Get the authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id: projectId, webhookId } = await params
    const body = await req.json()
    const { url, event_types, secret, is_active } = body

    // Validate URL format if provided
    if (url) {
      try {
        new URL(url)
      } catch {
        return NextResponse.json({ error: 'Invalid URL format' }, { status: 400 })
      }
    }

    // Verify webhook exists and user owns the project
    const { data: webhook, error: webhookError } = await supabase
      .from('webhooks')
      .select(`
        id,
        project_id,
        projects!inner(created_by)
      `)
      .eq('id', webhookId)
      .eq('project_id', projectId)
      .eq('projects.created_by', user.id)
      .single()

    if (webhookError || !webhook) {
      return NextResponse.json({ error: 'Webhook not found' }, { status: 404 })
    }

    // Update webhook
    const updateData: any = {}
    if (url !== undefined) updateData.url = url
    if (event_types !== undefined) updateData.event_types = event_types
    if (secret !== undefined) updateData.secret = secret
    if (is_active !== undefined) updateData.is_active = is_active

    const { data: updatedWebhook, error: updateError } = await supabase
      .from('webhooks')
      .update(updateData)
      .eq('id', webhookId)
      .select()
      .single()

    if (updateError) {
      console.error('Error updating webhook:', updateError)
      return NextResponse.json({ error: 'Failed to update webhook' }, { status: 500 })
    }

    return NextResponse.json({ webhook: updatedWebhook })
  } catch (err: any) {
    console.error('Error in PUT /api/projects/[id]/webhooks/[webhookId]:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal server error' }, { status: 500 })
  }
}

// DELETE /api/projects/[id]/webhooks/[webhookId] - Delete a webhook
export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string; webhookId: string }> }
) {
  try {
    const cookieStore = cookies()
    const supabase = await createClient(cookieStore)
    
    // Get the authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id: projectId, webhookId } = await params

    // Verify webhook exists and user owns the project
    const { data: webhook, error: webhookError } = await supabase
      .from('webhooks')
      .select(`
        id,
        project_id,
        projects!inner(created_by)
      `)
      .eq('id', webhookId)
      .eq('project_id', projectId)
      .eq('projects.created_by', user.id)
      .single()

    if (webhookError || !webhook) {
      return NextResponse.json({ error: 'Webhook not found' }, { status: 404 })
    }

    // Delete webhook
    const { error: deleteError } = await supabase
      .from('webhooks')
      .delete()
      .eq('id', webhookId)

    if (deleteError) {
      console.error('Error deleting webhook:', deleteError)
      return NextResponse.json({ error: 'Failed to delete webhook' }, { status: 500 })
    }

    return NextResponse.json({ success: true })
  } catch (err: any) {
    console.error('Error in DELETE /api/projects/[id]/webhooks/[webhookId]:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal server error' }, { status: 500 })
  }
}
