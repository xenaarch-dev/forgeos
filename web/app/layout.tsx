import type { Metadata, Viewport } from 'next'
import './globals.css'
import { ForgeCursor } from '@/components/global/ForgeCursor'
import { Scanline } from '@/components/global/Scanline'

export const metadata: Metadata = {
  title: 'ForgeOS — The autonomous business OS for solo founders',
  description:
    'One indie developer and seven agents — researching, building, testing, shipping, and selling while the founder sleeps. Proof: contractforge.co.in — live.',
  openGraph: {
    title: 'ForgeOS — The autonomous business OS for solo founders',
    description:
      'One indie developer and seven agents — researching, building, testing, shipping, and selling while the founder sleeps. Proof: contractforge.co.in — live.',
    siteName: 'ForgeOS',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'ForgeOS — The autonomous business OS for solo founders',
    description:
      'One indie developer and seven agents — researching, building, testing, shipping, and selling while the founder sleeps. Proof: contractforge.co.in — live.',
    creator: '@xenaarch',
  },
}

export const viewport: Viewport = {
  themeColor: '#0C0E10',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        {children}
        <ForgeCursor />
        <Scanline />
      </body>
    </html>
  )
}
