import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'FarmTrust — Land Intelligence Portal',
  description: 'Satellite-based land assessment and evidence review portal',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
