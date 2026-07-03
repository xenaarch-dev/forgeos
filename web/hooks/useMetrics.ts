import { useEffect, useState } from 'react'

export type Metrics = {
  day_number: number
  yc_days_remaining: number
  mrr_inr: number
  leads: { drafted: number; approved: number; sent: number } | null
  agent_status: {
    contractforge: 'live' | 'offline'
    outreach: 'live' | 'queued_awaiting_approval' | 'idle'
  }
  recent_activity: unknown[]
}

export function useMetrics(): Metrics | null {
  const [metrics, setMetrics] = useState<Metrics | null>(null)

  useEffect(() => {
    fetch('/api/metrics')
      .then((r) => r.json())
      .then(setMetrics)
      .catch(() => {})
  }, [])

  return metrics
}
