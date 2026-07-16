export function ArtifactPreview() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto', padding: '18px 16px' }}>
      <span style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.20em', marginBottom: 18 }}>
        LATEST ARTIFACT
      </span>
      <div style={{ flex: 1, display: 'grid', placeItems: 'center', textAlign: 'center', padding: 16 }}>
        <span style={{ font: '300 12px var(--font-body)', color: 'rgba(236,235,230,0.30)', lineHeight: 1.6 }}>
          No artifact is currently being drafted.
          <br />
          This panel lights up when an agent starts writing.
        </span>
      </div>
      <div style={{ borderTop: '0.5px solid rgba(164,216,255,0.10)', paddingTop: 12, marginTop: 12 }}>
        <div style={{ font: '400 7px var(--font-mono)', color: 'rgba(164,216,255,0.45)', letterSpacing: '0.10em' }}>NIGHTLY LOOP</div>
        <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.35)', marginTop: 4 }}>NEXT RUN: 02:00 IST</div>
      </div>
    </div>
  )
}
