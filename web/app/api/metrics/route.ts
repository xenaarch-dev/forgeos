import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const BASELINE_MS = new Date('2026-01-10').getTime()
const YC_DEADLINE_MS = new Date('2026-07-27').getTime()

type ActivityEvent = {
  id: string
  agent: string
  event_type: 'info' | 'action' | 'gate' | 'error'
  message: string
  created_at: string
}

export async function GET() {
  const now = Date.now()

  const day_number = Math.floor((now - BASELINE_MS) / 86_400_000) + 1
  const yc_days_remaining = Math.max(0, Math.ceil((YC_DEADLINE_MS - now) / 86_400_000))

  const supabaseUrl = process.env.SUPABASE_URL
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

  let leads: { drafted: number; approved: number; sent: number } | null = null
  let recent_activity: ActivityEvent[] = []
  // Verified ₹0 as of STATE.md Day 175 (zero paying customers); overwritten
  // below by the latest real product_metrics row if one exists.
  let mrr_inr = 0

  if (supabaseUrl && serviceKey) {
    const headers = {
      apikey: serviceKey,
      Authorization: `Bearer ${serviceKey}`,
    }

    // Leads — query Supabase REST API with service role key (server-side only)
    try {
      const res = await fetch(
        `${supabaseUrl}/rest/v1/outreach_leads?select=status`,
        { headers, next: { revalidate: 60 } },
      )
      if (res.ok) {
        const rows: { status: string }[] = await res.json()
        leads = { drafted: 0, approved: 0, sent: 0 }
        for (const { status } of rows) {
          if (status === 'drafted') leads.drafted++
          else if (status === 'approved') leads.approved++
          else if (status === 'sent') leads.sent++
        }
      }
    } catch {
      // Supabase unavailable — leads stays null, shown as "pending"
    }

    // Recent activity — dashboard_events is the real table the Python
    // pipeline writes to (see supabase/migrations/20260707000000_app_foundations.sql).
    // `agent_logs` is a legacy table with no application code reading/writing
    // it (see 20260707000002_agent_logs_as_built_reference.sql) — deliberately not used.
    try {
      const res = await fetch(
        `${supabaseUrl}/rest/v1/dashboard_events?select=id,agent,event_type,message,created_at&order=created_at.desc&limit=5`,
        { headers, next: { revalidate: 60 } },
      )
      if (res.ok) {
        recent_activity = await res.json()
      }
    } catch {
      // Supabase unavailable — recent_activity stays [], shown as an honest empty state
    }

    // MRR — latest recorded snapshot per product from product_metrics, summed
    try {
      const res = await fetch(
        `${supabaseUrl}/rest/v1/product_metrics?select=product_slug,mrr_inr,recorded_at&order=recorded_at.desc`,
        { headers, next: { revalidate: 60 } },
      )
      if (res.ok) {
        const rows: { product_slug: string; mrr_inr: number; recorded_at: string }[] = await res.json()
        const latestByProduct = new Map<string, number>()
        for (const row of rows) {
          if (!latestByProduct.has(row.product_slug)) latestByProduct.set(row.product_slug, row.mrr_inr)
        }
        if (latestByProduct.size > 0) {
          mrr_inr = Array.from(latestByProduct.values()).reduce((sum, v) => sum + v, 0)
        }
      }
    } catch {
      // Supabase unavailable — mrr_inr stays at the verified-real 0 above
    }
  }

  return NextResponse.json({
    day_number,
    yc_days_remaining,
    mrr_inr,
    leads,
    agent_status: {
      // ContractForge is deployed and live at contractforge.co.in
      contractforge: 'live' as const,
      // OutreachForge has drafted leads but none sent — human approval required
      outreach: 'queued_awaiting_approval' as const,
    },
    recent_activity,
  })
}
