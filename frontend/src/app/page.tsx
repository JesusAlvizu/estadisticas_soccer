export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800">
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-5xl font-bold text-white mb-4">
            Estadísticas Soccer
          </h1>
          <p className="text-xl text-gray-300 mb-8">
            Plataforma de análisis estadístico deportivo con IA
          </p>
          <div className="space-y-2">
            <p className="text-gray-400">Inicializando...</p>
            <p className="text-sm text-gray-500">
              Backend: http://localhost:8000
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
