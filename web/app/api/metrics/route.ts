import { NextResponse } from 'next/server'

const BASELINE_MS = new Date('2026-01-10').getTime()
const YC_DEADLINE_MS = new Date('2026-07-27').getTime()

export async function GET() {
  const now = Date.now()

  const day_number = Math.floor((now - BASELINE_MS) / 86_400_000) + 1
  const yc_days_remaining = Math.max(0, Math.ceil((YC_DEADLINE_MS - now) / 86_400_000))

  // Leads — query Supabase REST API with service role key (server-side only)
  let leads: { drafted: number; approved: number; sent: number } | null = null
  const supabaseUrl = process.env.SUPABASE_URL
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

  if (supabaseUrl && serviceKey) {
    try {
      const res = await fetch(
        `${supabaseUrl}/rest/v1/outreach_leads?select=status`,
        {
          headers: {
            apikey: serviceKey,
            Authorization: `Bearer ${serviceKey}`,
          },
          next: { revalidate: 60 },
        },
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
  }

  return NextResponse.json({
    day_number,
    yc_days_remaining,
    // Verified ₹0: STATE.md line 522, zero paying customers through Day 175
    mrr_inr: 0,
    leads,
    agent_status: {
      // ContractForge is deployed and live at contractforge.co.in
      contractforge: 'live' as const,
      // OutreachForge has drafted leads but none sent — human approval required
      outreach: 'queued_awaiting_approval' as const,
    },
    // agent_logs table does not exist yet — no real activity to show
    recent_activity: [] as unknown[],
  })
}
