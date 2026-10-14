// Agent Builder client: the spec shape (mirrors agent_builder/spec.py), local
// validation for instant feedback, and the API calls. The server re-validates
// everything; this file only exists so the form can say what's wrong early.

import staticCatalog from './builderCatalog.json'
import type { SpriteProp } from '@/components/agents/AgentSprite'

export type ModelTier = 'fast' | 'balanced' | 'deep'

export type McpServerSpec = {
  name: string
  transport: 'stdio' | 'http'
  command?: string | null
  args?: string[]
  url?: string | null
  env?: string[]
}

export type AgentSpec = {
  slug: string
  name: string
  role: string
  instructions: string
  phase: string
  model_tier: ModelTier
  skills: string[]
  tools: string[]
  plugins: string[]
  mcp_servers: McpServerSpec[]
  budget_usd: number
  suit_color: string
  prop: SpriteProp
}

export type Catalog = typeof staticCatalog

export const STATIC_CATALOG: Catalog = staticCatalog

export const SLUG_RE = /^[a-z][a-z0-9-]{1,40}$/
const HEX_RE = /^#[0-9A-Fa-f]{6}$/
const ENV_RE = /^[A-Z][A-Z0-9_]{0,63}$/

export function slugify(name: string): string {
  const s = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/^[0-9-]+/, '')
    .slice(0, 41)
  return s.replace(/-+$/, '')
}

export function emptySpec(): AgentSpec {
  return {
    slug: '',
    name: '',
    role: '',
    instructions: '',
    phase: 'custom',
    model_tier: 'balanced',
    skills: [],
    tools: ['workspace'],
    plugins: [],
    mcp_servers: [],
    budget_usd: 0.25,
    suit_color: '#A4D8FF',
    prop: 'wrench',
  }
}

/** Problems keyed by field. Empty object = ready to save. */
export function validateSpec(spec: AgentSpec, catalog: Catalog = STATIC_CATALOG): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!SLUG_RE.test(spec.slug)) errors.slug = 'Lowercase letters, digits and -, starting with a letter.'
  if (spec.name.trim().length < 2 || spec.name.length > 40) errors.name = 'Name needs 2 to 40 characters.'
  if (spec.role.trim().length < 4 || spec.role.length > 160) errors.role = 'One line, 4 to 160 characters.'
  if (spec.instructions.length > 8000) errors.instructions = 'Keep instructions under 8,000 characters.'
  if (!HEX_RE.test(spec.suit_color)) errors.suit_color = 'Use a #RRGGBB colour.'
  if (spec.budget_usd < 0 || spec.budget_usd > 20) errors.budget_usd = 'Budget must be between $0 and $20.'

  const known = {
    skills: new Set(catalog.skills.map((s) => s.id)),
    tools: new Set(catalog.tools.map((t) => t.id)),
    plugins: new Set(catalog.plugins.map((p) => p.id)),
  }
  for (const key of ['skills', 'tools', 'plugins'] as const) {
    const unknown = spec[key].filter((id) => !known[key].has(id))
    if (unknown.length) errors[key] = `Unknown: ${unknown.join(', ')}`
  }

  const names = new Set<string>()
  spec.mcp_servers.forEach((m, i) => {
    const at = `mcp_servers.${i}`
    if (!/^[a-zA-Z0-9_-]+$/.test(m.name)) errors[at] = 'Server name: letters, digits, - and _ only.'
    else if (names.has(m.name)) errors[at] = `Duplicate server name "${m.name}".`
    else if (m.transport === 'stdio' && !m.command?.trim()) errors[at] = 'A stdio server needs a command.'
    else if (m.transport === 'http' && !m.url?.startsWith('https://')) errors[at] = 'An http server needs an https:// URL.'
    else if ((m.env ?? []).some((k) => !ENV_RE.test(k))) errors[at] = 'Env entries are VARIABLE_NAMES, never secret values.'
    names.add(m.name)
  })
  return errors
}

/** Everything a spec ends up with once its plugins are expanded. */
export function resolveSpec(spec: AgentSpec, catalog: Catalog = STATIC_CATALOG) {
  const skills = [...spec.skills]
  const tools = [...spec.tools]
  const mcp = spec.mcp_servers.map((m) => m.name)
  for (const id of spec.plugins) {
    const plugin = catalog.plugins.find((p) => p.id === id)
    if (!plugin) continue
    skills.push(...plugin.skills)
    tools.push(...plugin.tools)
    mcp.push(...plugin.mcp)
  }
  const uniq = (xs: string[]) => Array.from(new Set(xs))
  return { skills: uniq(skills), tools: uniq(tools), mcp: uniq(mcp) }
}

// ---------------------------------------------------------------------------
// API — only when NEXT_PUBLIC_FORGEOS_API_URL points at the FastAPI service.
// ---------------------------------------------------------------------------

export const API_URL = (process.env.NEXT_PUBLIC_FORGEOS_API_URL ?? '').replace(/\/+$/, '')

async function authHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  try {
    const { createClient } = await import('@/lib/supabase/client')
    const { data } = await createClient().auth.getSession()
    if (data.session?.access_token) headers.Authorization = `Bearer ${data.session.access_token}`
  } catch {
    // No Supabase in this environment: the API decides whether that's allowed.
  }
  return headers
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_URL) throw new Error('NEXT_PUBLIC_FORGEOS_API_URL is not set')
  const res = await fetch(`${API_URL}${path}`, { ...init, headers: { ...(await authHeaders()), ...init?.headers } })
  if (!res.ok) {
    let detail = `${res.status}`
    try { detail = (await res.json()).detail ?? detail } catch { /* not JSON */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

export const builderApi = {
  catalog: () => call<Catalog>('/agent-builder/catalog'),
  list: () => call<AgentSpec[]>('/agents/custom'),
  create: (spec: AgentSpec) => call<AgentSpec>('/agents/custom', { method: 'POST', body: JSON.stringify(spec) }),
  update: (spec: AgentSpec) => call<AgentSpec>(`/agents/custom/${spec.slug}`, { method: 'POST', body: JSON.stringify(spec) }),
  remove: (slug: string) => call<void>(`/agents/custom/${slug}/delete`, { method: 'POST' }),
  run: (slug: string, task: string) =>
    call<{ status: string; output: string | null; error: string | null; model: string | null }>(
      `/agents/custom/${slug}/run`, { method: 'POST', body: JSON.stringify({ task }) },
    ),
  exportBundle: (slug: string) =>
    call<{ files: Record<string, string>; mcp: unknown }>(`/agents/custom/${slug}/export`),
}
