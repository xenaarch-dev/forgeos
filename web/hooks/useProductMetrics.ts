// web/hooks/useProductMetrics.ts
'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'

export type ProductMetricRow = {
  product_slug: string
  mrr_inr: number
  signups: number
  conversions: number
  recorded_at: string
}

export function useProductMetrics(): ProductMetricRow[] {
  const [rows, setRows] = useState<ProductMetricRow[]>([])

  useEffect(() => {
    const supabase = createClient()
    supabase
      .from('product_metrics')
      .select('product_slug, mrr_inr, signups, conversions, recorded_at')
      .order('recorded_at', { ascending: false })
      .then(({ data, error }) => {
        if (error) {
          console.error('useProductMetrics: fetch failed', error)
          return
        }
        if (data) setRows(data)
      })
  }, [])

  return rows
}
