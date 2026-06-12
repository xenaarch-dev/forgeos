'use client'

import { CSSProperties, useEffect, useRef, useState } from 'react'

/**
 * Char-by-char typewriter. Resets and replays whenever `active`
 * flips back to true. Multi-line values render with preserved breaks.
 */
export default function Typewriter({
  text,
  active,
  speed = 30,
  startDelay = 0,
  onDone,
  className = '',
  style,
}: {
  text: string
  active: boolean
  speed?: number
  startDelay?: number
  onDone?: () => void
  className?: string
  style?: CSSProperties
}) {
  const [count, setCount] = useState(0)
  const doneRef = useRef(false)

  useEffect(() => {
    if (!active) {
      setCount(0)
      doneRef.current = false
      return
    }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setCount(text.length)
      if (!doneRef.current) {
        doneRef.current = true
        onDone?.()
      }
      return
    }
    let i = 0
    let iv: ReturnType<typeof setInterval>
    const t0 = setTimeout(() => {
      iv = setInterval(() => {
        i += 1
        setCount(i)
        if (i >= text.length) {
          clearInterval(iv)
          if (!doneRef.current) {
            doneRef.current = true
            onDone?.()
          }
        }
      }, speed)
    }, startDelay)
    return () => {
      clearTimeout(t0)
      clearInterval(iv)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, text, speed, startDelay])

  return (
    <span className={className} style={{ whiteSpace: 'pre-wrap', ...style }}>
      {text.slice(0, count)}
    </span>
  )
}
