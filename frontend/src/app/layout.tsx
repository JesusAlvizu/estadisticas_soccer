import type { Metadata } from 'next'
import './globals.css'

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
      <body>
        <main>
          {children}
        </main>
      </body>
    </html>
  )
}
