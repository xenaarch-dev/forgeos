'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import Ember from '@/components/fx/Ember'

const EASE = [0.22, 1, 0.36, 1] as const
const REPO = 'https://github.com/xenaarch-dev/forgeos'

export default function S13_CTA() {
  const [focused, setFocused] = useState(false)

  return (
    <section
      id="cta"
      className="relative flex min-h-screen flex-col items-center justify-center"
      style={{ background: 'var(--bg)' }}
    >
      <motion.form
        className="relative w-full max-w-[640px] px-6"
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '0px 0px -20% 0px' }}
        transition={{ duration: 1, ease: EASE }}
        onSubmit={(e) => {
          e.preventDefault()
          window.open(REPO, '_blank', 'noopener,noreferrer')
        }}
      >
        <div
          className="relative flex h-[72px] items-center transition-shadow duration-500"
          style={{
            background: 'var(--glass)',
            backdropFilter: 'blur(24px) saturate(1.2)',
            WebkitBackdropFilter: 'blur(24px) saturate(1.2)',
            border: `1px solid ${focused ? 'rgba(217,131,42,0.55)' : 'var(--glass-border)'}`,
            borderTopColor: focused
              ? 'rgba(217,131,42,0.55)'
              : 'var(--glass-highlight)',
            borderRadius: 24,
            boxShadow: focused
              ? '0 24px 64px rgba(0,0,0,0.45), 0 0 42px rgba(217,131,42,0.22), inset 0 1px 0 var(--glass-highlight)'
              : '0 24px 64px rgba(0,0,0,0.45), inset 0 1px 0 var(--glass-highlight)',
          }}
        >
          <label htmlFor="idea" className="sr-only">
            Your idea. One sentence.
          </label>
          <input
            id="idea"
            name="idea"
            type="text"
            placeholder="Your idea. One sentence."
            autoComplete="off"
            className="h-full flex-1 bg-transparent pl-7 pr-2 text-[15px] outline-none placeholder:text-[15px]"
            style={{ color: 'var(--w)', caretColor: 'var(--fire)' }}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
          />
          {/* the ember from the hero reappears at the input's right edge */}
          {focused && (
            <motion.span
              className="mr-4 hidden sm:block"
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, ease: EASE }}
            >
              <Ember />
            </motion.span>
          )}
          <button
            type="submit"
            className="mr-3 flex h-12 shrink-0 items-center rounded-2xl px-6 text-[14px] font-bold transition-transform duration-300 hover:scale-[1.02]"
            style={{
              background: 'var(--fire)',
              color: 'var(--bg)',
              boxShadow: '0 0 32px rgba(217,131,42,0.45)',
            }}
          >
            Build it →
          </button>
        </div>
      </motion.form>

      <footer className="absolute bottom-8 left-0 right-0 px-6">
        <p
          className="text-center text-[12px]"
          style={{ color: 'var(--w-dim)', letterSpacing: '0.06em' }}
        >
          ForgeOS — built in Mumbai by xenarch ·{' '}
          <a
            href={REPO}
            target="_blank"
            rel="noopener noreferrer"
            className="underline-offset-4 transition-colors duration-300 hover:underline"
          >
            GitHub
          </a>
          {' · '}
          <a
            href="https://x.com/xenaarch"
            target="_blank"
            rel="noopener noreferrer"
            className="underline-offset-4 transition-colors duration-300 hover:underline"
          >
            X
          </a>
        </p>
      </footer>
    </section>
  )
}
