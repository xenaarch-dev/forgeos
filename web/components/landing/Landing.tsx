'use client'

import { useEffect, useState } from 'react'
import { MissionBar } from '@/components/global/MissionBar'
import { BootSequence } from '@/components/global/BootSequence'
import { Nav } from './Nav'
import { Hero } from './Hero'
import { FactoryFloor } from './FactoryFloor'
import { HowItWorks } from './HowItWorks'
import { Proof } from './Proof'
import { Mission } from './Mission'
import { CTA } from './CTA'
import { Footer } from './Footer'

const CHAPTERS: Record<string, string> = {
  hero: 'CH.01 // HERO',
  agents: 'CH.02 // FACTORY FLOOR',
  how: 'CH.03 // HOW IT WORKS',
  proof: 'CH.04 // PROOF',
  mission: 'CH.05 // MISSION',
  cta: 'CH.06 // START',
}

export default function Landing() {
  const [chapter, setChapter] = useState(CHAPTERS.hero)

  useEffect(() => {
    const sections = Object.keys(CHAPTERS)
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null)

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setChapter(CHAPTERS[entry.target.id] ?? CHAPTERS.hero)
          }
        }
      },
      { threshold: 0.5 }
    )

    sections.forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [])

  return (
    <>
      <BootSequence />
      <MissionBar chapter={chapter} />
      <Nav />
      <main>
        <Hero />
        <FactoryFloor />
        <HowItWorks />
        <Proof />
        <Mission />
        <CTA />
      </main>
      <Footer />
    </>
  )
}
