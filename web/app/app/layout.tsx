// web/app/app/layout.tsx
import { Nav } from '@/components/app-shell/Nav'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', background: 'var(--void)' }}>
      <Nav />
      <div style={{ flex: 1, minWidth: 0 }}>{children}</div>
    </div>
  )
}
