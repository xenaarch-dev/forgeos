import type { Metadata, Viewport } from 'next'
import './globals.css'

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
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400;1,700&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  )
}
