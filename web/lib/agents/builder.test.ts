import { describe, expect, it } from 'vitest'
import { emptySpec, resolveSpec, slugify, validateSpec, type AgentSpec } from './builder'

const good = (over: Partial<AgentSpec> = {}): AgentSpec => ({
  ...emptySpec(),
  slug: 'test-pilot',
  name: 'Test Pilot',
  role: 'Writes tests for every feature.',
  ...over,
})

describe('slugify', () => {
  it('makes a valid slug from a display name', () => {
    expect(slugify('Test Pilot 3000!')).toBe('test-pilot-3000')
    expect(slugify('  99 Problems ')).toBe('problems')
  })
})

describe('validateSpec', () => {
  it('accepts a good spec', () => {
    expect(validateSpec(good())).toEqual({})
  })

  it('flags bad slug, colour and unknown catalog ids', () => {
    const errors = validateSpec(good({ slug: 'Bad Slug', suit_color: 'blue', skills: ['nope'] }))
    expect(Object.keys(errors).sort()).toEqual(['skills', 'slug', 'suit_color'])
  })

  it('rejects secret values in MCP env', () => {
    const errors = validateSpec(good({ mcp_servers: [{ name: 'x', transport: 'stdio', command: 'npx', env: ['sk-ant-123'] }] }))
    expect(errors['mcp_servers.0']).toMatch(/VARIABLE_NAMES/)
  })

  it('requires https for http MCP servers', () => {
    const errors = validateSpec(good({ mcp_servers: [{ name: 'x', transport: 'http', url: 'http://a' }] }))
    expect(errors['mcp_servers.0']).toMatch(/https/)
  })
})

describe('resolveSpec', () => {
  it('expands plugins into skills, tools and MCP without duplicates', () => {
    const r = resolveSpec(good({ skills: ['test-writer'], tools: ['workspace'], plugins: ['qa-kit'] }))
    expect(r.skills).toEqual(['test-writer', 'code-reviewer'])
    expect(r.tools).toEqual(['workspace', 'browser'])
    expect(r.mcp).toEqual(['playwright'])
  })
})
