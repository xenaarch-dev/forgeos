// web/hooks/useDashboardEvents.ts
'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'

export type DashboardEvent = {
  id: string
  agent: string
  event_type: 'info' | 'action' | 'gate' | 'error'
  message: string
  created_at: string
}

export function useDashboardEvents(limit = 14): DashboardEvent[] {
  const [logs, setLogs] = useState<DashboardEvent[]>([])

  useEffect(() => {
    const supabase = createClient()

    supabase
      .from('dashboard_events')
      .select('id, agent, event_type, message, created_at')
      .order('created_at', { ascending: false })
      .limit(limit)
      .then(({ data }) => {
        if (data) setLogs([...data].reverse())
      })

    const channel = supabase
      .channel('dashboard_events_stream')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'dashboard_events' },
        (payload) => {
          setLogs((prev) => [...prev, payload.new as DashboardEvent].slice(-limit))
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [limit])

  return logs
}
