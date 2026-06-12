'use client'

import { RefObject, useEffect } from 'react'
import { MotionValue, useMotionValueEvent } from 'framer-motion'

/**
 * Binds a scroll-driven MotionValue to an element's opacity with a
 * direct DOM write. Components that re-render while scrolling (state
 * updates from typewriters, sim triggers) lose framer's style-prop
 * opacity subscription — transforms survive, opacity freezes. This
 * hook is immune: the subscription lives on the MotionValue itself.
 */
export default function useScrollOpacity(
  value: MotionValue<number>,
  ref: RefObject<HTMLElement | null>,
  disabled = false
) {
  useMotionValueEvent(value, 'change', (v) => {
    if (!disabled && ref.current) ref.current.style.opacity = String(v)
  })
  useEffect(() => {
    if (!disabled && ref.current) {
      ref.current.style.opacity = String(value.get())
    }
  }, [value, ref, disabled])
}
