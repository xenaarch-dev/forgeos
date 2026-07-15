// web/components/dashboard/ArtifactPreview.tsx
export function ArtifactPreview() {
  return (
    <div style={{ border: '0.5px solid rgba(0,229,204,0.14)', borderRadius: 6, background: '#07080A', display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '12px 18px', borderBottom: '0.5px solid rgba(0,229,204,0.1)' }}>
        <span style={{ font: '400 8.5px var(--font-body)', color: 'var(--hud)', letterSpacing: '0.18em' }}>LIVE ARTIFACT</span>
      </div>
      <div style={{ flex: 1, display: 'grid', placeItems: 'center', padding: 16 }}>
        <span style={{ font: '400 11px var(--font-body)', color: 'var(--w-ghost)', textAlign: 'center' }}>
          No artifact is currently being drafted.
          <br />
          This panel lights up when an agent starts writing.
        </span>
      </div>
    </div>
  )
}
