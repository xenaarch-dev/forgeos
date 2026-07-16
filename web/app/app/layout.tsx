// web/app/app/layout.tsx
'use client'

import { usePathname } from 'next/navigation'
import { MissionBar } from '@/components/global/MissionBar'
import { Topbar } from '@/components/app-shell/Topbar'
import { Sidebar } from '@/components/app-shell/Sidebar'
import { MetricsBar } from '@/components/dashboard/MetricsBar'
import { chapterFromRoute } from '@/lib/forge/chapters'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const collapsed = pathname.endsWith('/pipeline')

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', paddingTop: 26, background: '#0C0E10' }}>
      <MissionBar chapter={chapterFromRoute(pathname)} />
      <Topbar />
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <Sidebar collapsed={collapsed} />
        <main style={{ flex: 1, minWidth: 0, overflowY: 'auto' }}>{children}</main>
      </div>
      <MetricsBar />
    </div>
  )
}
