'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { AgentSprite, type SpriteMode, type SpriteProp } from '@/components/agents/AgentSprite'
import {
  API_URL,
  STATIC_CATALOG,
  builderApi,
  emptySpec,
  resolveSpec,
  slugify,
  validateSpec,
  type AgentSpec,
  type Catalog,
  type McpServerSpec,
  type ModelTier,
} from '@/lib/agents/builder'

const SUITS = ['#A4D8FF', '#E0A96D', '#8FD3B8', '#B9A8F0', '#E89BB8', '#CDBF9C', '#E38B7E', '#9FB4C7']
const TIERS: { id: ModelTier; label: string; hint: string }[] = [
  { id: 'fast', label: 'FAST', hint: 'Cheapest tier. Formatting, triage, drafts.' },
  { id: 'balanced', label: 'BALANCED', hint: 'Default. Code, reviews, most work.' },
  { id: 'deep', label: 'DEEP', hint: 'Architecture and security grade.' },
]

const label: React.CSSProperties = { font: '400 8px var(--font-mono)', letterSpacing: '0.16em', color: 'rgba(164,216,255,0.6)', marginBottom: 8, display: 'block' }
const input: React.CSSProperties = { width: '100%', background: 'rgba(12,14,16,0.7)', border: '0.5px solid rgba(164,216,255,0.18)', borderRadius: 3, padding: '10px 12px', color: '#ECEBE6', font: '400 14px var(--font-body)' }
const errText: React.CSSProperties = { font: '400 11px var(--font-body)', color: '#E38B7E', marginTop: 6 }

function Section({ title, kicker, children }: { title: string; kicker: string; children: React.ReactNode }) {
  return (
    <section className="glass" style={{ borderRadius: 4, padding: 22, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <div style={{ font: '400 7.5px var(--font-mono)', letterSpacing: '0.2em', color: 'rgba(164,216,255,0.45)' }}>{kicker}</div>
        <h2 style={{ font: '700 22px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', marginTop: 4 }}>{title}</h2>
      </div>
      {children}
    </section>
  )
}

function Chip({ on, onClick, title, sub }: { on: boolean; onClick: () => void; title: string; sub?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={on}
      style={{
        textAlign: 'left', padding: '10px 12px', borderRadius: 3, minWidth: 0,
        background: on ? 'rgba(164,216,255,0.12)' : 'rgba(12,14,16,0.5)',
        border: on ? '0.5px solid rgba(164,216,255,0.6)' : '0.5px solid rgba(164,216,255,0.12)',
        transition: 'background 0.2s var(--ease), border-color 0.2s var(--ease)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ width: 8, height: 8, borderRadius: 2, border: '0.5px solid #A4D8FF', background: on ? '#A4D8FF' : 'transparent', flexShrink: 0 }} />
        <span style={{ font: '400 11px var(--font-mono)', color: on ? '#A4D8FF' : '#ECEBE6' }}>{title}</span>
      </div>
      {sub && <div style={{ font: '300 12px/1.45 var(--font-body)', color: 'rgba(236,235,230,0.45)', marginTop: 6 }}>{sub}</div>}
    </button>
  )
}

function toggle(list: string[], id: string) {
  return list.includes(id) ? list.filter((x) => x !== id) : [...list, id]
}

export default function AgentBuilderPage() {
  const [catalog, setCatalog] = useState<Catalog>(STATIC_CATALOG)
  const [spec, setSpec] = useState<AgentSpec>(emptySpec)
  const [slugTouched, setSlugTouched] = useState(false)
  const [previewMode, setPreviewMode] = useState<SpriteMode>('working')
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null)
  const [saved, setSaved] = useState(false)
  const [task, setTask] = useState('')
  const [runOut, setRunOut] = useState<string | null>(null)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    if (!API_URL) return
    builderApi.catalog().then(setCatalog).catch(() => { /* keep the static copy */ })
  }, [])

  const errors = useMemo(() => validateSpec(spec, catalog), [spec, catalog])
  const resolved = useMemo(() => resolveSpec(spec, catalog), [spec, catalog])
  const ready = Object.keys(errors).length === 0
  const set = <K extends keyof AgentSpec>(key: K, value: AgentSpec[K]) => {
    setSpec((s) => ({ ...s, [key]: value }))
    setSaved(false)
  }

  function setName(name: string) {
    setSpec((s) => ({ ...s, name, slug: slugTouched ? s.slug : slugify(name) }))
    setSaved(false)
  }

  function addMcp(server: McpServerSpec) {
    if (spec.mcp_servers.some((m) => m.name === server.name)) return
    set('mcp_servers', [...spec.mcp_servers, server])
  }

  async function save() {
    setNotice(null)
    if (!ready) return
    if (!API_URL) {
      download()
      setNotice({ kind: 'ok', text: 'No API configured, so the spec was downloaded. POST it to /agents/custom on your ForgeOS API.' })
      return
    }
    setSaving(true)
    try {
      await (saved ? builderApi.update(spec) : builderApi.create(spec))
      setSaved(true)
      setNotice({ kind: 'ok', text: `${spec.name} has clocked in on the factory floor.` })
    } catch (e) {
      setNotice({ kind: 'err', text: (e as Error).message })
    } finally {
      setSaving(false)
    }
  }

  function download() {
    const blob = new Blob([JSON.stringify(spec, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${spec.slug || 'agent'}.agent.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function exportClaude() {
    try {
      const bundle = await builderApi.exportBundle(spec.slug)
      const text = Object.entries(bundle.files).map(([p, c]) => `# ${p}\n${c}`).join('\n') +
        `\n# .mcp.json\n${JSON.stringify(bundle.mcp, null, 2)}\n`
      await navigator.clipboard.writeText(text)
      setNotice({ kind: 'ok', text: 'Claude Code subagent and .mcp.json copied to your clipboard.' })
    } catch (e) {
      setNotice({ kind: 'err', text: (e as Error).message })
    }
  }

  async function testRun() {
    if (!task.trim()) return
    setRunning(true)
    setRunOut(null)
    setPreviewMode('working')
    try {
      const res = await builderApi.run(spec.slug, task)
      setRunOut(res.output ?? res.error ?? `Run finished: ${res.status}`)
    } catch (e) {
      setRunOut((e as Error).message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div style={{ padding: 32, display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 360px', gap: 24, alignItems: 'start' }}>
      {/* -------------------------------------------------------------- form */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, minWidth: 0 }}>
        <div>
          <Link href="/app/agents" style={{ font: '400 9px var(--font-mono)', color: 'rgba(164,216,255,0.6)', letterSpacing: '0.1em' }}>← AGENTS</Link>
          <h1 style={{ font: '900 42px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal', letterSpacing: '-0.03em', marginTop: 10 }}>Agent Builder</h1>
          <p style={{ font: '300 14px var(--font-body)', color: 'rgba(236,235,230,0.5)', marginTop: 6, maxWidth: 620 }}>
            Hire a new agent for the factory: give it a job, a brain, skills, tools and MCP servers. It runs on the same
            pipeline as the built-in crew and exports to Claude Code.
          </p>
        </div>

        <Section kicker="01 · IDENTITY" title="Who is this agent?">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <label>
              <span style={label}>NAME</span>
              <input style={input} value={spec.name} onChange={(e) => setName(e.target.value)} placeholder="Test Pilot" maxLength={40} />
              {errors.name && spec.name && <div style={errText}>{errors.name}</div>}
            </label>
            <label>
              <span style={label}>SLUG</span>
              <input
                style={{ ...input, fontFamily: 'var(--font-mono)', fontSize: 12 }}
                value={spec.slug}
                onChange={(e) => { setSlugTouched(true); set('slug', e.target.value) }}
                placeholder="test-pilot"
              />
              {errors.slug && spec.slug && <div style={errText}>{errors.slug}</div>}
            </label>
          </div>
          <label>
            <span style={label}>ROLE (ONE LINE)</span>
            <input style={input} value={spec.role} onChange={(e) => set('role', e.target.value)} placeholder="Writes and runs end-to-end tests for every feature." maxLength={160} />
            {errors.role && spec.role && <div style={errText}>{errors.role}</div>}
          </label>
        </Section>

        <Section kicker="02 · LOOK" title="Suit and kit">
          <div>
            <span style={label}>SUIT COLOUR</span>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
              {SUITS.map((c) => (
                <button
                  key={c}
                  type="button"
                  aria-label={`Suit colour ${c}`}
                  aria-pressed={spec.suit_color === c}
                  onClick={() => set('suit_color', c)}
                  style={{ width: 28, height: 28, borderRadius: '50%', background: c, outline: spec.suit_color === c ? '2px solid #ECEBE6' : 'none', outlineOffset: 3 }}
                />
              ))}
              <input type="color" aria-label="Custom suit colour" value={spec.suit_color} onChange={(e) => set('suit_color', e.target.value.toUpperCase())} style={{ width: 34, height: 28, background: 'none', border: 'none' }} />
            </div>
          </div>
          <div>
            <span style={label}>CARRIES</span>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
              {(catalog.props as SpriteProp[]).map((p) => (
                <button
                  key={p}
                  type="button"
                  aria-pressed={spec.prop === p}
                  onClick={() => set('prop', p)}
                  style={{
                    padding: '8px 4px 6px', borderRadius: 3, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
                    background: spec.prop === p ? 'rgba(164,216,255,0.12)' : 'rgba(12,14,16,0.5)',
                    border: spec.prop === p ? '0.5px solid rgba(164,216,255,0.6)' : '0.5px solid rgba(164,216,255,0.12)',
                  }}
                >
                  <AgentSprite color={spec.suit_color} prop={p} mode="idle" size={30} />
                  <span style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.6)' }}>{p}</span>
                </button>
              ))}
            </div>
          </div>
        </Section>

        <Section kicker="03 · BRAIN" title="Model, budget, instructions">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
            {TIERS.map((t) => (
              <Chip key={t.id} on={spec.model_tier === t.id} onClick={() => set('model_tier', t.id)} title={t.label} sub={t.hint} />
            ))}
          </div>
          <label>
            <span style={label}>BUDGET PER BUILD · ${spec.budget_usd.toFixed(2)}</span>
            <input type="range" min={0} max={5} step={0.05} value={spec.budget_usd} onChange={(e) => set('budget_usd', Number(e.target.value))} style={{ width: '100%', accentColor: '#A4D8FF' }} />
          </label>
          <label>
            <span style={label}>INSTRUCTIONS</span>
            <textarea
              style={{ ...input, minHeight: 120, resize: 'vertical', lineHeight: 1.5 }}
              value={spec.instructions}
              onChange={(e) => set('instructions', e.target.value)}
              placeholder="How should it work? What should it never do? What does a good result look like?"
            />
            <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.3)', marginTop: 4 }}>{spec.instructions.length} / 8000</div>
          </label>
        </Section>

        <Section kicker="04 · SKILLS" title="What it knows how to do">
          <p style={{ font: '300 13px var(--font-body)', color: 'rgba(236,235,230,0.45)' }}>
            Skills are SKILL.md folders. Drop any skill from a GitHub skills repo into <code style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>skills/</code> and it shows up here.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
            {catalog.skills.map((s) => (
              <Chip key={s.id} on={spec.skills.includes(s.id)} onClick={() => set('skills', toggle(spec.skills, s.id))} title={s.name} sub={s.description.length > 150 ? `${s.description.slice(0, 150)}…` : s.description} />
            ))}
          </div>
        </Section>

        <Section kicker="05 · TOOLS" title="What it can touch">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
            {catalog.tools.map((t) => (
              <Chip
                key={t.id}
                on={spec.tools.includes(t.id)}
                onClick={() => set('tools', toggle(spec.tools, t.id))}
                title={t.name}
                sub={t.env.length ? `${t.description} Needs ${t.env.join(', ')}.` : t.description}
              />
            ))}
          </div>
        </Section>

        <Section kicker="06 · PLUGINS" title="Bundles">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
            {catalog.plugins.map((p) => (
              <Chip
                key={p.id}
                on={spec.plugins.includes(p.id)}
                onClick={() => set('plugins', toggle(spec.plugins, p.id))}
                title={p.name}
                sub={`${p.description} ${[...p.skills, ...p.tools, ...p.mcp].join(' · ')}`}
              />
            ))}
          </div>
        </Section>

        <Section kicker="07 · MCP" title="MCP servers">
          <p style={{ font: '300 13px var(--font-body)', color: 'rgba(236,235,230,0.45)' }}>
            MCP servers run on your machine when the agent runs in Claude Code. ForgeOS stores the config and never launches them itself.
            Env lists variable <em>names</em>; secrets stay in your environment.
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {catalog.mcp_presets.map((m) => {
              const on = spec.mcp_servers.some((s) => s.name === m.name)
              return (
                <Chip
                  key={m.name}
                  on={on}
                  title={`+ ${m.name}`}
                  onClick={() =>
                    on
                      ? set('mcp_servers', spec.mcp_servers.filter((s) => s.name !== m.name))
                      : addMcp('url' in m
                        ? { name: m.name, transport: 'http', url: m.url as string }
                        : { name: m.name, transport: 'stdio', command: (m as { command: string }).command, args: (m as { args?: string[] }).args ?? [], env: Object.keys((m as { env?: Record<string, string> }).env ?? {}) })
                  }
                />
              )
            })}
            <Chip on={false} title="+ custom server" onClick={() => addMcp({ name: `server-${spec.mcp_servers.length + 1}`, transport: 'stdio', command: 'npx', args: [], env: [] })} />
          </div>
          {spec.mcp_servers.map((m, i) => (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '140px 90px minmax(0,1fr) 150px 30px', gap: 8, alignItems: 'start' }}>
              <input aria-label="Server name" style={{ ...input, fontFamily: 'var(--font-mono)', fontSize: 11 }} value={m.name} onChange={(e) => set('mcp_servers', spec.mcp_servers.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} />
              <select aria-label="Transport" style={{ ...input, fontSize: 12 }} value={m.transport} onChange={(e) => set('mcp_servers', spec.mcp_servers.map((x, j) => (j === i ? { ...x, transport: e.target.value as 'stdio' | 'http' } : x)))}>
                <option value="stdio">stdio</option>
                <option value="http">http</option>
              </select>
              {m.transport === 'stdio' ? (
                <input
                  aria-label="Command and arguments"
                  style={{ ...input, fontFamily: 'var(--font-mono)', fontSize: 11 }}
                  value={[m.command ?? '', ...(m.args ?? [])].join(' ').trim()}
                  onChange={(e) => {
                    const [command, ...args] = e.target.value.split(/\s+/)
                    set('mcp_servers', spec.mcp_servers.map((x, j) => (j === i ? { ...x, command, args } : x)))
                  }}
                  placeholder="npx -y @scope/mcp-server"
                />
              ) : (
                <input aria-label="Server URL" style={{ ...input, fontFamily: 'var(--font-mono)', fontSize: 11 }} value={m.url ?? ''} onChange={(e) => set('mcp_servers', spec.mcp_servers.map((x, j) => (j === i ? { ...x, url: e.target.value } : x)))} placeholder="https://…" />
              )}
              <input
                aria-label="Environment variable names"
                style={{ ...input, fontFamily: 'var(--font-mono)', fontSize: 11 }}
                value={(m.env ?? []).join(',')}
                onChange={(e) => set('mcp_servers', spec.mcp_servers.map((x, j) => (j === i ? { ...x, env: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) } : x)))}
                placeholder="ENV_NAMES"
              />
              <button type="button" aria-label={`Remove ${m.name}`} onClick={() => set('mcp_servers', spec.mcp_servers.filter((_, j) => j !== i))} style={{ color: 'rgba(236,235,230,0.5)', font: '400 16px var(--font-mono)', paddingTop: 8 }}>×</button>
              {errors[`mcp_servers.${i}`] && <div style={{ ...errText, gridColumn: '1 / -1', marginTop: -2 }}>{errors[`mcp_servers.${i}`]}</div>}
            </div>
          ))}
        </Section>
      </div>

      {/* -------------------------------------------------------------- preview */}
      <aside style={{ position: 'sticky', top: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div className="glass" style={{ borderRadius: 4, overflow: 'hidden' }}>
          <div
            onMouseEnter={() => setPreviewMode('walking')}
            onMouseLeave={() => setPreviewMode('working')}
            style={{
              height: 230, position: 'relative', display: 'grid', placeItems: 'center',
              background: 'radial-gradient(ellipse at 50% 20%, rgba(164,216,255,0.14), transparent 65%), linear-gradient(180deg, #101317, #0A0C0E)',
              backgroundSize: 'auto, auto',
            }}
          >
            <div aria-hidden style={{ position: 'absolute', inset: 0, backgroundImage: 'linear-gradient(rgba(164,216,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(164,216,255,0.05) 1px, transparent 1px)', backgroundSize: '32px 32px', maskImage: 'linear-gradient(180deg, transparent, black 40%)' }} />
            <div style={{ position: 'absolute', top: 12, left: 14, font: '400 7.5px var(--font-mono)', letterSpacing: '0.18em', color: 'rgba(164,216,255,0.5)' }}>TEST BAY · LIVE PREVIEW</div>
            <div style={{ position: 'relative', textAlign: 'center' }}>
              <AgentSprite color={spec.suit_color} prop={spec.prop} mode={running ? 'working' : previewMode} size={96} title={`${spec.name || 'New agent'} preview`} />
              <div style={{ marginTop: 6, display: 'inline-block', font: '400 9px var(--font-mono)', letterSpacing: '0.08em', color: spec.suit_color, padding: '2px 8px', background: 'rgba(12,14,16,0.85)', border: `0.5px solid ${spec.suit_color}55`, borderRadius: 2 }}>
                {spec.name || 'NEW AGENT'}
              </div>
            </div>
          </div>
          <div style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <p style={{ font: '300 13px/1.5 var(--font-body)', color: 'rgba(236,235,230,0.65)', minHeight: 20 }}>{spec.role || 'Give it a one-line job to see it here.'}</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
              {[
                { v: resolved.skills.length, l: 'SKILLS' },
                { v: resolved.tools.length, l: 'TOOLS' },
                { v: resolved.mcp.length, l: 'MCP' },
              ].map((s) => (
                <div key={s.l} style={{ textAlign: 'center', padding: '8px 0', border: '0.5px solid rgba(164,216,255,0.12)', borderRadius: 3 }}>
                  <div style={{ font: '700 22px var(--font-display)', color: '#ECEBE6', fontStyle: 'normal' }}>{s.v}</div>
                  <div style={{ font: '400 7px var(--font-mono)', letterSpacing: '0.12em', color: 'rgba(236,235,230,0.35)' }}>{s.l}</div>
                </div>
              ))}
            </div>
            {[...resolved.skills, ...resolved.tools, ...resolved.mcp].length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {[...resolved.skills, ...resolved.tools, ...resolved.mcp].map((x) => (
                  <span key={x} style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.8)', border: '0.5px solid rgba(164,216,255,0.25)', padding: '2px 6px', borderRadius: 2 }}>{x}</span>
                ))}
              </div>
            )}

            <button
              type="button"
              onClick={save}
              disabled={!ready || saving}
              data-magnetic
              style={{ background: ready ? '#A4D8FF' : 'rgba(164,216,255,0.2)', color: '#0C0E10', font: '700 9.5px var(--font-mono)', letterSpacing: '0.08em', padding: '14px 0', cursor: ready ? 'pointer' : 'not-allowed' }}
            >
              {saving ? 'CLOCKING IN…' : API_URL ? (saved ? 'SAVE CHANGES' : 'HIRE AGENT →') : 'DOWNLOAD SPEC →'}
            </button>
            {!ready && (spec.name || spec.role) && (
              <ul style={{ paddingLeft: 16, font: '300 12px/1.5 var(--font-body)', color: 'rgba(236,235,230,0.5)' }}>
                {Object.values(errors).map((e) => <li key={e}>{e}</li>)}
              </ul>
            )}
            {notice && (
              <div role="status" style={{ font: '300 12px/1.5 var(--font-body)', color: notice.kind === 'ok' ? '#8FD3B8' : '#E38B7E' }}>{notice.text}</div>
            )}
            {saved && API_URL && (
              <>
                <button type="button" onClick={exportClaude} className="glass" style={{ padding: '10px 0', borderRadius: 2, font: '400 9px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.08em' }}>
                  COPY FOR CLAUDE CODE
                </button>
                <div style={{ borderTop: '0.5px solid rgba(164,216,255,0.1)', paddingTop: 12 }}>
                  <span style={label}>TEST RUN</span>
                  <textarea style={{ ...input, minHeight: 64, fontSize: 13 }} value={task} onChange={(e) => setTask(e.target.value)} placeholder="Give it a task…" />
                  <button type="button" onClick={testRun} disabled={running || !task.trim()} className="glass" style={{ marginTop: 8, width: '100%', padding: '10px 0', borderRadius: 2, font: '400 9px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.08em' }}>
                    {running ? 'WORKING…' : 'RUN'}
                  </button>
                  {runOut && <pre style={{ marginTop: 10, maxHeight: 220, overflow: 'auto', whiteSpace: 'pre-wrap', font: '400 11px/1.5 var(--font-mono)', color: 'rgba(236,235,230,0.75)' }}>{runOut}</pre>}
                </div>
              </>
            )}
          </div>
        </div>
      </aside>
    </div>
  )
}
