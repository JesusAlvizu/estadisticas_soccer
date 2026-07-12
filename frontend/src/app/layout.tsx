import type { Metadata } from 'next'
import { DM_Sans, Space_Grotesk } from 'next/font/google'
import './globals.css'

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-display',
})

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-body',
})

export const metadata: Metadata = {
  title: 'Estadísticas Soccer - Análisis Deportivo IA',
  description: 'Plataforma de análisis estadístico deportivo con Machine Learning',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="es">
      <body className={`${spaceGrotesk.variable} ${dmSans.variable}`}>
        <main>
          {children}
        </main>
      </body>
    </html>
  )
}
