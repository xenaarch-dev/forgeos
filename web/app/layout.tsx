import type { Metadata, Viewport } from 'next'
import { Cormorant_Garamond, Space_Mono } from 'next/font/google'
import './globals.css'

const cormorant = Cormorant_Garamond({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  style: ['normal', 'italic'],
  variable: '--font-display',
})

const spaceMono = Space_Mono({
  subsets: ['latin'],
  weight: ['400', '700'],
  style: ['normal', 'italic'],
  variable: '--font-mono',
})

export const metadata: Metadata = {
  title: 'ForgeOS — One sentence in. Full SaaS out.',
  description:
    'ForgeOS builds, deploys, and operates complete software businesses — autonomously. Proof: contractforge.co.in — live, real, built by ForgeOS.',
  openGraph: {
    title: 'ForgeOS — One sentence in. Full SaaS out.',
    description:
      'ForgeOS builds, deploys, and operates complete software businesses — autonomously. Proof: contractforge.co.in — live, real, built by ForgeOS.',
    siteName: 'ForgeOS',
    type: 'website',
  },
}

export const viewport: Viewport = {
  themeColor: '#000008',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`${cormorant.variable} ${spaceMono.variable}`}>
      <body>{children}</body>
    </html>
  )
}
