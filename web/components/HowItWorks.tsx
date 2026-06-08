'use client'

import { motion } from 'framer-motion'

const steps = [
  {
    num: '01',
    title: 'You type one sentence.',
    desc: 'A product idea in plain English. No spec doc, no wireframes, no tech decisions required.',
  },
  {
    num: '02',
    title: 'The forge runs.',
    desc: '18 specialized agents execute autonomously — PM, architect, coder, security, QA, deploy.',
  },
  {
    num: '03',
    title: 'You get a deployed URL.',
    desc: 'GBrain learns. The next build is smarter, faster, and cheaper than the last.',
  },
]

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.10 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
}

export default function HowItWorks() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      style={{ padding: '56px 40px' }}
    >
      <span className="label" style={{ display: 'block', marginBottom: '40px' }}>
        How it works
      </span>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true }}
        className="grid grid-cols-1 md:grid-cols-3"
        style={{ gap: '40px' }}
      >
        {steps.map((step) => (
          <motion.div key={step.num} variants={itemVariants}>
            {/* Step number */}
            <div
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '48px',
                fontStyle: 'italic',
                fontWeight: 400,
                color: 'var(--bd2)',
                lineHeight: 1,
                marginBottom: '12px',
              }}
            >
              {step.num}
            </div>

            {/* Title */}
            <div
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '24px',
                fontWeight: 400,
                color: 'var(--w)',
                lineHeight: 1.2,
                marginBottom: '12px',
              }}
            >
              {step.title}
            </div>

            {/* Description */}
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '10px',
                color: 'var(--m)',
                lineHeight: 1.9,
                letterSpacing: '0.04em',
              }}
            >
              {step.desc}
            </div>
          </motion.div>
        ))}
      </motion.div>
    </motion.section>
  )
}
