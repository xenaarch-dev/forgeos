// web/app/app/page.tsx
import { AgentRoster } from '@/components/dashboard/AgentRoster'
import { ActivityStream } from '@/components/dashboard/ActivityStream'
import { ArtifactPreview } from '@/components/dashboard/ArtifactPreview'

export default function DashboardPage() {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr 280px', gap: 0, height: '100%' }}>
      <AgentRoster />
      <ActivityStream />
      <ArtifactPreview />
    </div>
  )
}
