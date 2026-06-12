'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import Ember from '@/components/fx/Ember'

const EASE = [0.22, 1, 0.36, 1] as const
const REPO = 'https://github.com/xenaarch-dev/forgeos'

/* The return to nothing — pure void, maximum negative space.
   The page exhales. One input. One instruction. */
export default function S13_CTA() {
  const [focused, setFocused] = useState(false)

  return (
    <section
      id="cta"
      className="relative flex min-h-screen flex-col items-center justify-center"
      style={{ background: 'var(--void)' }}
    >
      <motion.form
        className="relative w-full max-w-[680px] px-6"
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
          className="glass relative flex h-[80px] items-center transition-shadow duration-500"
          style={{
            borderRadius: 32,
            boxShadow: focused
              ? '0 40px 100px rgba(0,0,5,0.7), 0 0 42px rgba(0,229,204,0.25), inset 0 1px 0 rgba(255,255,255,0.10)'
              : undefined,
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
            className="relative z-10 h-full flex-1 bg-transparent pl-7 pr-2 text-[15px] outline-none placeholder:text-[15px]"
            style={{ color: 'var(--w)', caretColor: 'var(--gold)' }}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
          />
          {/* the ember from the hero reappears at the input's right edge */}
          {focused && (
            <motion.span
              className="relative z-10 mr-4 hidden sm:block"
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, ease: EASE }}
            >
              <Ember />
            </motion.span>
          )}
          <button
            type="submit"
            className="relative z-10 mr-3 flex h-12 shrink-0 items-center px-6 text-[14px] font-bold transition-transform duration-300 hover:scale-[1.02]"
            style={{
              background:
                'linear-gradient(135deg, #F2A93C 0%, var(--gold) 55%, #C97A12 100%)',
              color: 'var(--void)',
              borderRadius: 20,
              boxShadow: '0 0 32px rgba(232,150,31,0.45)',
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
