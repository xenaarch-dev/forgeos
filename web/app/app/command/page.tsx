'use client'

import { useState } from 'react'

type Message = { id: string; from: 'user' | 'core' | 'contract'; text: string; bullets?: string[] }

const INITIAL: Message[] = [
  { id: 'm1', from: 'user', text: 'Generate an NDA and service agreement for a new fintech client.' },
  { id: 'm2', from: 'core', text: 'Routing to ContractForge. Generating NDA + Service Agreement...' },
  {
    id: 'm3', from: 'contract', text: '',
    bullets: [
      'NDA loaded — Indian Contract Act 1872',
      'Service agreement drafted — SaaS / CA context',
      'Running DPDP 2023 compliance check...',
    ],
  },
]

const QUICK_ACTIONS = ['GENERATE NDA', 'DRAFT OUTREACH FOR CA FIRMS', 'RUN MORNING METRICS']

export default function CommandPage() {
  const [messages, setMessages] = useState<Message[]>(INITIAL)
  const [input, setInput] = useState('')

  function send(text: string) {
    if (!text.trim()) return
    const userMsg: Message = { id: crypto.randomUUID(), from: 'user', text }
    const routingMsg: Message = { id: crypto.randomUUID(), from: 'core', text: `Routing "${text.slice(0, 40)}${text.length > 40 ? '…' : ''}" to the mesh...` }
    setMessages((prev) => [...prev, userMsg, routingMsg])
    setInput('')
  }

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', padding: '14px 20px', borderBottom: '0.5px solid rgba(164,216,255,0.10)' }}>
          <div style={{ display: 'flex', gap: 6 }}>
            {['#5a4a3a', '#4a5a3a', '#3a4a5a'].map((c) => (
              <span key={c} style={{ width: 8, height: 8, borderRadius: '50%', background: c }} />
            ))}
          </div>
          <span style={{ flex: 1, textAlign: 'center', font: '400 9px var(--font-mono)', color: 'rgba(236,235,230,0.40)', letterSpacing: '0.14em' }}>
            FORGEOS COMMAND INTERFACE
          </span>
          <span style={{ font: '400 8px var(--font-mono)', color: '#A4D8FF', letterSpacing: '0.10em' }}>CORE ACTIVE</span>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {messages.map((m) => (
            <div
              key={m.id}
              className="glass"
              style={{
                maxWidth: m.from === 'user' ? '70%' : '80%', alignSelf: m.from === 'user' ? 'flex-end' : 'flex-start',
                borderRadius: 4, padding: '12px 16px',
              }}
            >
              {m.bullets ? (
                <ul style={{ margin: 0, paddingLeft: 16, font: '400 9.5px var(--font-mono)', color: 'rgba(236,235,230,0.65)', lineHeight: 1.8 }}>
                  {m.bullets.map((b) => <li key={b}>{b}</li>)}
                </ul>
              ) : (
                <span style={{ font: m.from === 'user' ? '400 14px var(--font-body)' : '400 10px var(--font-mono)', color: '#ECEBE6' }}>
                  {m.text}
                </span>
              )}
            </div>
          ))}
        </div>

        <div style={{ padding: 16 }}>
          <form
            onSubmit={(e) => { e.preventDefault(); send(input) }}
            className="glass"
            style={{ display: 'flex', alignItems: 'center', height: 52, borderRadius: 4, padding: '0 16px' }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="▸ Send a command to ForgeOS..."
              style={{ flex: 1, background: 'transparent', border: 'none', color: '#ECEBE6', font: '400 13px var(--font-mono)' }}
            />
            <span style={{ font: '400 8px var(--font-mono)', color: 'rgba(236,235,230,0.30)' }}>→ ⌘↵</span>
          </form>
          <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
            {QUICK_ACTIONS.map((qa) => (
              <button
                key={qa}
                onClick={() => send(qa)}
                className="glass"
                style={{ padding: '8px 14px', borderRadius: 20, font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.70)', letterSpacing: '0.06em' }}
              >
                → {qa}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ width: 280, flexShrink: 0, borderLeft: '0.5px solid rgba(164,216,255,0.10)', padding: 20, overflowY: 'auto' }}>
        <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.20em', marginBottom: 14 }}>
          LIVE ARTIFACT
        </div>
        <div className="glass" style={{ borderRadius: 4, padding: 14, marginBottom: 20 }}>
          <div style={{ font: '400 8px var(--font-mono)', color: '#A4D8FF', marginBottom: 8 }}>SERVICE AGREEMENT</div>
          <div style={{ font: '400 7px var(--font-mono)', color: 'rgba(236,235,230,0.50)', lineHeight: 1.7 }}>
            This Service Agreement is entered into between the parties named below, governed by the laws of India, GST 18% applicable...
          </div>
        </div>
        <button style={{ width: '100%', background: '#A4D8FF', color: '#0C0E10', font: '400 9px var(--font-mono)', letterSpacing: '0.08em', padding: '12px 0', marginBottom: 8 }}>
          APPROVE ARTIFACT →
        </button>
        <button style={{ width: '100%', border: '0.5px solid rgba(236,235,230,0.20)', color: 'rgba(236,235,230,0.55)', font: '400 9px var(--font-mono)', padding: '12px 0', marginBottom: 24 }}>
          REQUEST REVISION
        </button>

        <div style={{ font: '400 8px var(--font-mono)', color: 'rgba(164,216,255,0.55)', letterSpacing: '0.20em', marginBottom: 12 }}>
          AGENT STATUS
        </div>
        {[
          { name: 'ContractForge', status: 'ACTIVE' },
          { name: 'OutreachForge', status: 'IDLE' },
          { name: 'GBrain', status: 'RUNNING' },
        ].map((a) => (
          <div key={a.name} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: a.status === 'IDLE' ? 'rgba(236,235,230,0.25)' : '#A4D8FF' }} />
            <span style={{ font: '400 9px var(--font-mono)', color: '#ECEBE6', flex: 1 }}>{a.name}</span>
            <span style={{ font: '400 7px var(--font-mono)', color: a.status === 'IDLE' ? 'rgba(236,235,230,0.30)' : '#A4D8FF' }}>{a.status}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
