// web/app/app/page.tsx
import { AgentRoster } from '@/components/dashboard/AgentRoster'
import { ActivityStream } from '@/components/dashboard/ActivityStream'
import { ArtifactPreview } from '@/components/dashboard/ArtifactPreview'
import { MetricsBar } from '@/components/dashboard/MetricsBar'

export default function DashboardPage() {
  return (
    <div style={{ height: '100vh', display: 'grid', gridTemplateRows: '1fr auto' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr 300px', gap: 14, padding: '14px 14px 0', minHeight: 0 }}>
        <AgentRoster />
        <ActivityStream />
        <ArtifactPreview />
      </div>
      <div style={{ padding: 14 }}>
        <MetricsBar />
      </div>
    </div>
  )
}
