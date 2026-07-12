"use client"

import { useEffect, useState } from "react"


const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"


type HealthState = "checking" | "online" | "offline"

type LeagueItem = {
  id: number
  name: string
  code: string
  country: string | null
  teams: number
  matches: number
  current_season: number | null
}

type TeamItem = {
  id: number
  name: string
  code: string
  country: string | null
  logo_url: string | null
}

type PredictionItem = {
  id: number
  market: string
  outcome: string
  probability: number
  confidence: number
  model: string
  match?: {
    id: number | null
    home_team: string
    away_team: string
    date: string | null
  }
}

type MatchOdd = {
  id: number
  bookmaker: string | null
  market: string | null
  outcome: string
  odd: number
  implied_probability: number
}

type MatchItem = {
  id: number
  match_date: string | null
  status: string
  home_team: { id: number | null; name: string }
  away_team: { id: number | null; name: string }
  score: { home: number | null; away: number | null }
  odds: MatchOdd[]
  predictions: PredictionItem[]
}

type BetTicket = {
  id: number
  match_id: number
  sportsbook: string
  market: string
  outcome: string
  odd_value: number
  stake: number
  expected_probability: number | null
  status: string
  potential_payout: number
  actual_payout: number
  placed_at: string | null
  settled_at: string | null
  notes: string | null
  match: {
    id: number | null
    date: string | null
    status: string | null
    home_team: string
    away_team: string
    score_home: number | null
    score_away: number | null
  }
}

type SectionKey = "overview" | "leagues" | "teams" | "bets" | "probabilities"

type ManualProbabilityBet = {
  market: string
  selection: string
  probability: number
}

type ManualProbabilityResponse = {
  input: {
    home_team: string
    away_team: string
    stadium: string | null
    simulations: number
  }
  resolved: {
    home_team_id: number
    home_team_name: string
    away_team_id: number
    away_team_name: string
  }
  model_context: {
    home_expected_goals: number
    away_expected_goals: number
    expected_corners: number
    expected_cards: number
    h2h_matches_used: number
    home_recent_matches_used: number
    away_recent_matches_used: number
    confidence: number
  }
  recommended_bets_top5: ManualProbabilityBet[]
  exact_score_top5: Array<{
    score: string
    probability: number
  }>
}

type ManualMatchOptionsResponse = {
  league: string | null
  teams: string[]
  stadiums: string[]
}


export default function Home() {
  const [health, setHealth] = useState<HealthState>("checking")
  const [activeSection, setActiveSection] = useState<SectionKey>("overview")
  const [loadingData, setLoadingData] = useState(true)
  const [leagues, setLeagues] = useState<LeagueItem[]>([])
  const [teams, setTeams] = useState<TeamItem[]>([])
  const [matches, setMatches] = useState<MatchItem[]>([])
  const [predictions, setPredictions] = useState<PredictionItem[]>([])
  const [bets, setBets] = useState<BetTicket[]>([])
  const [settling, setSettling] = useState(false)
  const [savingBet, setSavingBet] = useState(false)
  const [betMessage, setBetMessage] = useState<string | null>(null)
  const [predictingManual, setPredictingManual] = useState(false)
  const [manualProbabilityMessage, setManualProbabilityMessage] = useState<string | null>(null)
  const [manualProbability, setManualProbability] = useState<ManualProbabilityResponse | null>(null)
  const [manualOptions, setManualOptions] = useState<ManualMatchOptionsResponse>({
    league: null,
    teams: [],
    stadiums: [],
  })

  const [manualForm, setManualForm] = useState({
    homeTeam: "",
    awayTeam: "",
    stadium: "",
    simulations: "5000",
  })

  const [betForm, setBetForm] = useState({
    matchId: "",
    sportsbook: "Caliente",
    market: "1X2",
    outcome: "HOME",
    oddValue: "1.90",
    stake: "100",
    expectedProbability: "",
    notes: "",
  })

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const healthResponse = await fetch(`${backendUrl}/health`, { cache: "no-store" })
        if (!healthResponse.ok) {
          setHealth("offline")
          setLoadingData(false)
          return
        }

        setHealth("online")

        const settled = await Promise.allSettled([
          fetch(`${backendUrl}/api/v1/leagues/`, { cache: "no-store" }),
          fetch(`${backendUrl}/api/v1/teams/?skip=0&limit=100`, { cache: "no-store" }),
          fetch(`${backendUrl}/api/v1/matches/?skip=0&limit=50`, { cache: "no-store" }),
          fetch(`${backendUrl}/api/v1/predictions/?skip=0&limit=100`, { cache: "no-store" }),
          fetch(`${backendUrl}/api/v1/bets/?skip=0&limit=100`, { cache: "no-store" }),
          fetch(`${backendUrl}/api/v1/predictions/manual-match-options`, { cache: "no-store" }),
        ])

        const parseList = async (index: number) => {
          const item = settled[index]
          if (item.status !== "fulfilled") {
            return []
          }
          if (!item.value.ok) {
            return []
          }
          return item.value.json()
        }

        setLeagues(await parseList(0))
        const teamsData = await parseList(1)
        setTeams(teamsData)
        setMatches(await parseList(2))
        setPredictions(await parseList(3))
        setBets(await parseList(4))
        const optionsData = await parseList(5)
        if (optionsData && Array.isArray(optionsData.teams) && Array.isArray(optionsData.stadiums)) {
          setManualOptions({
            league: optionsData.league || null,
            teams: optionsData.teams,
            stadiums: optionsData.stadiums,
          })
        }
      } catch {
        setHealth("offline")
      } finally {
        setLoadingData(false)
      }
    }

    loadDashboard()
  }, [])

  const statusText =
    health === "checking"
      ? "Verificando backend..."
      : health === "online"
      ? "Backend conectado"
      : "Backend sin conexión"

  const statusColor =
    health === "checking"
      ? "text-amber-300"
      : health === "online"
      ? "text-emerald-300"
      : "text-rose-300"

  const menuItems: Array<{ key: SectionKey; label: string }> = [
    { key: "overview", label: "Resumen" },
    { key: "leagues", label: "Ligas" },
    { key: "teams", label: "Equipos" },
    { key: "bets", label: "Apuestas" },
    { key: "probabilities", label: "Probabilidades" },
  ]

  const allOdds = matches.flatMap((m) => m.odds || [])
  const availableMarkets = Array.from(
    new Set(allOdds.map((o) => o.market || "Sin mercado"))
  )

  const openBets = bets.filter((b) => b.status === "open")
  const wonBets = bets.filter((b) => b.status === "won")
  const pnl = bets.reduce((acc, b) => acc + (b.actual_payout - b.stake), 0)

  const upcomingMatchOptions = matches
    .filter((m) => ["NS", "TBD", "SCHEDULED"].includes((m.status || "").toUpperCase()))
    .slice(0, 20)
  const betMatchOptions = upcomingMatchOptions.length > 0 ? upcomingMatchOptions : matches.slice(0, 20)

  const refreshBets = async () => {
    const res = await fetch(`${backendUrl}/api/v1/bets/?skip=0&limit=100`, { cache: "no-store" })
    if (!res.ok) {
      return
    }
    const data = await res.json()
    setBets(data)
  }

  const submitBet = async () => {
    if (!betForm.matchId) {
      setBetMessage("Selecciona un partido para registrar la apuesta")
      return
    }

    setSavingBet(true)
    setBetMessage(null)
    try {
      const payload = {
        match_id: Number(betForm.matchId),
        sportsbook: betForm.sportsbook,
        market: betForm.market,
        outcome: betForm.outcome,
        odd_value: Number(betForm.oddValue),
        stake: Number(betForm.stake),
        expected_probability: betForm.expectedProbability ? Number(betForm.expectedProbability) : null,
        notes: betForm.notes || null,
      }

      const res = await fetch(`${backendUrl}/api/v1/bets/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const detail = await res.text()
        setBetMessage(`No se pudo registrar la apuesta: ${detail}`)
        return
      }

      setBetMessage("Apuesta registrada correctamente")
      setBetForm((prev) => ({ ...prev, notes: "", expectedProbability: "" }))
      await refreshBets()
    } catch {
      setBetMessage("Error de red al registrar apuesta")
    } finally {
      setSavingBet(false)
    }
  }

  const runAutoSettlement = async () => {
    setSettling(true)
    setBetMessage(null)
    try {
      const res = await fetch(`${backendUrl}/api/v1/bets/settle/auto`, { method: "POST" })
      if (!res.ok) {
        setBetMessage("No se pudo ejecutar la liquidacion automatica")
        return
      }
      const data = await res.json()
      setBetMessage(`Liquidacion completada: ${data.settled} apuestas`)
      await refreshBets()
    } catch {
      setBetMessage("Error de red al liquidar apuestas")
    } finally {
      setSettling(false)
    }
  }

  const runManualProbability = async () => {
    if (!manualForm.homeTeam || !manualForm.awayTeam) {
      setManualProbabilityMessage("Captura equipo local y visitante")
      return
    }

    if (manualForm.homeTeam.trim().toLowerCase() === manualForm.awayTeam.trim().toLowerCase()) {
      setManualProbabilityMessage("Local y visitante deben ser diferentes")
      return
    }

    setPredictingManual(true)
    setManualProbabilityMessage(null)

    try {
      const payload = {
        home_team: manualForm.homeTeam,
        away_team: manualForm.awayTeam,
        stadium: manualForm.stadium || null,
        simulations: Number(manualForm.simulations || "5000"),
      }

      const res = await fetch(`${backendUrl}/api/v1/predictions/manual-match-probabilities`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const detail = await res.text()
        setManualProbabilityMessage(`No se pudo calcular: ${detail}`)
        return
      }

      const data: ManualProbabilityResponse = await res.json()
      setManualProbability(data)
      setManualProbabilityMessage("Probabilidades calculadas correctamente")
    } catch {
      setManualProbabilityMessage("Error de red al calcular probabilidades")
    } finally {
      setPredictingManual(false)
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_20%_0%,#16315d_0%,#0f172a_45%,#090f1d_100%)] text-slate-100">
      <div className="mx-auto flex max-w-[1500px] gap-4 px-4 py-4 md:gap-6 md:px-6 md:py-6">
        <aside className="sticky top-4 hidden h-[calc(100vh-2rem)] w-64 shrink-0 rounded-2xl border border-slate-700/70 bg-slate-950/70 p-4 backdrop-blur md:block">
          <h1 className="mb-2 text-2xl font-bold tracking-tight">Estadísticas Soccer</h1>
          <p className="mb-6 text-xs text-slate-400">Centro de control Liga MX</p>

          <nav className="space-y-2">
            {menuItems.map((item) => (
              <button
                key={item.key}
                onClick={() => setActiveSection(item.key)}
                className={`w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition ${
                  activeSection === item.key
                    ? "bg-cyan-400 text-slate-900"
                    : "bg-slate-900/40 text-slate-200 hover:bg-slate-800"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="mt-6 rounded-lg border border-slate-700 bg-slate-900/60 p-3 text-xs">
            <p className={`font-semibold ${statusColor}`}>{statusText}</p>
            <p className="mt-1 text-slate-400">Backend: {backendUrl}</p>
          </div>
        </aside>

        <main className="min-w-0 flex-1 rounded-2xl border border-slate-700/70 bg-slate-950/60 p-4 backdrop-blur md:p-6">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-3xl font-semibold tracking-tight">Dashboard Deportivo</h2>
              <p className="text-sm text-slate-400">Ligas, equipos, apuestas y probabilidades en un solo lugar</p>
            </div>
            <div className="flex gap-2">
              <a
                href={`${backendUrl}/docs`}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg bg-cyan-400 px-3 py-2 text-xs font-bold text-slate-900"
              >
                API Docs
              </a>
              <a
                href={`${backendUrl}/health`}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg border border-slate-600 px-3 py-2 text-xs font-bold text-slate-200"
              >
                Health
              </a>
            </div>
          </div>

          <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            <MetricCard label="Ligas" value={leagues.length} />
            <MetricCard label="Equipos" value={teams.length} />
            <MetricCard label="Partidos" value={matches.length} />
            <MetricCard label="Predicciones" value={predictions.length} />
          </div>

          {loadingData ? (
            <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-6 text-center text-slate-300">
              Cargando datos del dashboard...
            </div>
          ) : (
            <>
              {activeSection === "overview" && (
                <div className="grid gap-4 lg:grid-cols-2">
                  <Panel title="Partidos recientes">
                    <div className="space-y-2">
                      {matches.slice(0, 8).map((m) => (
                        <div key={m.id} className="rounded-lg bg-slate-900/70 p-3 text-sm">
                          <div className="flex items-center justify-between">
                            <p className="font-semibold">
                              {m.home_team.name} vs {m.away_team.name}
                            </p>
                            <span className="text-xs text-slate-400">{m.status}</span>
                          </div>
                          <p className="text-xs text-slate-400">
                            {m.score.home ?? "-"} : {m.score.away ?? "-"}
                          </p>
                        </div>
                      ))}
                      {matches.length === 0 && <EmptyState text="Sin partidos cargados por ahora" />}
                    </div>
                  </Panel>

                  <Panel title="Mercados disponibles">
                    <div className="flex flex-wrap gap-2">
                      {availableMarkets.slice(0, 20).map((market) => (
                        <span key={market} className="rounded-full bg-slate-800 px-3 py-1 text-xs">
                          {market}
                        </span>
                      ))}
                      {availableMarkets.length === 0 && <EmptyState text="Sin mercados cargados" />}
                    </div>
                  </Panel>
                </div>
              )}

              {activeSection === "leagues" && (
                <Panel title="Ligas">
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {leagues.map((league) => (
                      <div key={league.id} className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
                        <p className="text-lg font-semibold">{league.name}</p>
                        <p className="text-xs text-slate-400">{league.country || "N/A"}</p>
                        <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                          <div className="rounded bg-slate-800 p-2">
                            <p className="font-bold">{league.seasons}</p>
                            <p className="text-slate-400">Temporadas</p>
                          </div>
                          <div className="rounded bg-slate-800 p-2">
                            <p className="font-bold">{league.teams}</p>
                            <p className="text-slate-400">Equipos</p>
                          </div>
                          <div className="rounded bg-slate-800 p-2">
                            <p className="font-bold">{league.matches}</p>
                            <p className="text-slate-400">Partidos</p>
                          </div>
                        </div>
                      </div>
                    ))}
                    {leagues.length === 0 && <EmptyState text="Sin ligas registradas aún" />}
                  </div>
                </Panel>
              )}

              {activeSection === "teams" && (
                <Panel title="Equipos">
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {teams.map((team) => (
                      <div key={team.id} className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
                        <p className="font-semibold">{team.name}</p>
                        <p className="text-xs text-slate-400">
                          {team.code} · {team.country || "N/A"}
                        </p>
                      </div>
                    ))}
                    {teams.length === 0 && <EmptyState text="Sin equipos cargados aún" />}
                  </div>
                </Panel>
              )}

              {activeSection === "bets" && (
                <div className="grid gap-4 xl:grid-cols-2">
                  <Panel title="Registro de apuesta">
                    <div className="grid gap-3">
                      <label className="grid gap-1 text-xs text-slate-300">
                        Partido
                        <select
                          value={betForm.matchId}
                          onChange={(e) => setBetForm((prev) => ({ ...prev, matchId: e.target.value }))}
                          className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm"
                        >
                          <option value="">Selecciona un partido</option>
                          {betMatchOptions.map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.home_team.name} vs {m.away_team.name} ({m.status})
                            </option>
                          ))}
                        </select>
                      </label>

                      <div className="grid gap-3 sm:grid-cols-2">
                        <label className="grid gap-1 text-xs text-slate-300">
                          Casa
                          <input
                            value={betForm.sportsbook}
                            onChange={(e) => setBetForm((prev) => ({ ...prev, sportsbook: e.target.value }))}
                            className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm"
                          />
                        </label>
                        <label className="grid gap-1 text-xs text-slate-300">
                          Mercado
                          <input
                            value={betForm.market}
                            onChange={(e) => setBetForm((prev) => ({ ...prev, market: e.target.value }))}
                            className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm"
                            placeholder="1X2 / BTTS / TOTAL_GOALS_OU"
                          />
                        </label>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-2">
                        <label className="grid gap-1 text-xs text-slate-300">
                          Seleccion
                          <input
                            value={betForm.outcome}
                            onChange={(e) => setBetForm((prev) => ({ ...prev, outcome: e.target.value }))}
                            className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm"
                            placeholder="HOME / DRAW / AWAY / OVER_2.5"
                          />
                        </label>
                        <label className="grid gap-1 text-xs text-slate-300">
                          Cuota
                          <input
                            type="number"
                            step="0.01"
                            min="1.01"
                            value={betForm.oddValue}
                            onChange={(e) => setBetForm((prev) => ({ ...prev, oddValue: e.target.value }))}
                            className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm"
                          />
                        </label>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-2">
                        <label className="grid gap-1 text-xs text-slate-300">
                          Stake
                          <input
                            type="number"
                            step="0.01"
                            min="1"
                            value={betForm.stake}
                            onChange={(e) => setBetForm((prev) => ({ ...prev, stake: e.target.value }))}
                            className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm"
                          />
                        </label>
                        <label className="grid gap-1 text-xs text-slate-300">
                          Probabilidad esperada (0-1)
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="1"
                            value={betForm.expectedProbability}
                            onChange={(e) => setBetForm((prev) => ({ ...prev, expectedProbability: e.target.value }))}
                            className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm"
                          />
                        </label>
                      </div>

                      <label className="grid gap-1 text-xs text-slate-300">
                        Notas
                        <textarea
                          value={betForm.notes}
                          onChange={(e) => setBetForm((prev) => ({ ...prev, notes: e.target.value }))}
                          className="min-h-20 rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm"
                          placeholder="Contexto de la apuesta"
                        />
                      </label>

                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={submitBet}
                          disabled={savingBet}
                          className="rounded-lg bg-cyan-400 px-4 py-2 text-sm font-bold text-slate-900 disabled:opacity-60"
                        >
                          {savingBet ? "Guardando..." : "Registrar Apuesta"}
                        </button>
                        <button
                          onClick={runAutoSettlement}
                          disabled={settling}
                          className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-bold text-slate-200 disabled:opacity-60"
                        >
                          {settling ? "Liquidando..." : "Liquidacion Automatica"}
                        </button>
                      </div>

                      {betMessage && <p className="text-xs text-emerald-300">{betMessage}</p>}
                    </div>
                  </Panel>

                  <Panel title="Apuestas registradas">
                    <div className="mb-3 grid grid-cols-3 gap-2 text-xs">
                      <div className="rounded bg-slate-900/70 p-2">
                        <p className="text-slate-400">Abiertas</p>
                        <p className="text-lg font-semibold">{openBets.length}</p>
                      </div>
                      <div className="rounded bg-slate-900/70 p-2">
                        <p className="text-slate-400">Ganadas</p>
                        <p className="text-lg font-semibold">{wonBets.length}</p>
                      </div>
                      <div className="rounded bg-slate-900/70 p-2">
                        <p className="text-slate-400">PnL</p>
                        <p className={`text-lg font-semibold ${pnl >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                          {pnl.toFixed(2)}
                        </p>
                      </div>
                    </div>

                    <div className="space-y-2">
                      {bets.slice(0, 30).map((bet) => (
                        <div key={bet.id} className="rounded-lg bg-slate-900/70 p-3 text-sm">
                          <div className="flex items-center justify-between gap-2">
                            <p className="font-semibold">
                              {bet.match.home_team} vs {bet.match.away_team}
                            </p>
                            <span className={`rounded px-2 py-0.5 text-xs ${
                              bet.status === "won"
                                ? "bg-emerald-400/20 text-emerald-300"
                                : bet.status === "lost"
                                ? "bg-rose-400/20 text-rose-300"
                                : "bg-amber-400/20 text-amber-300"
                            }`}>
                              {bet.status}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400">
                            {bet.sportsbook} · {bet.market} · {bet.outcome}
                          </p>
                          <p className="text-xs text-slate-300">
                            Stake: {bet.stake.toFixed(2)} · Cuota: {bet.odd_value.toFixed(2)} · Pago Potencial: {bet.potential_payout.toFixed(2)}
                          </p>
                          <p className="text-xs text-slate-400">
                            Marcador: {bet.match.score_home ?? "-"} - {bet.match.score_away ?? "-"} ({bet.match.status || "N/A"})
                          </p>
                        </div>
                      ))}
                      {bets.length === 0 && <EmptyState text="No hay apuestas registradas" />}
                    </div>
                  </Panel>

                  <Panel title="Cuotas disponibles (referencia)">
                    <div className="space-y-2">
                      {allOdds.slice(0, 20).map((odd) => (
                        <div key={odd.id} className="grid grid-cols-4 gap-3 rounded-lg bg-slate-900/70 p-3 text-sm">
                          <span className="truncate">{odd.bookmaker || "Bookmaker"}</span>
                          <span className="truncate text-slate-300">{odd.market || "Mercado"}</span>
                          <span>{odd.outcome}</span>
                          <span className="text-right font-semibold text-cyan-300">{odd.odd.toFixed(2)}</span>
                        </div>
                      ))}
                      {allOdds.length === 0 && <EmptyState text="Aun no hay cuotas disponibles" />}
                    </div>
                  </Panel>
                </div>
              )}

              {activeSection === "probabilities" && (
                <div className="grid gap-4 xl:grid-cols-2">
                  <Panel title="Calculadora manual de probabilidades">
                    <div className="grid gap-3">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <label className="grid gap-1 text-xs text-slate-300">
                          Equipo local
                          <select
                            value={manualForm.homeTeam}
                            onChange={(e) => setManualForm((prev) => ({ ...prev, homeTeam: e.target.value }))}
                            className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm"
                          >
                            <option value="">Selecciona equipo local</option>
                            {manualOptions.teams.map((team) => (
                              <option key={`manual-home-${team}`} value={team}>{team}</option>
                            ))}
                          </select>
                        </label>
                        <label className="grid gap-1 text-xs text-slate-300">
                          Equipo visitante
                          <select
                            value={manualForm.awayTeam}
                            onChange={(e) => setManualForm((prev) => ({ ...prev, awayTeam: e.target.value }))}
                            className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm"
                          >
                            <option value="">Selecciona equipo visitante</option>
                            {manualOptions.teams.map((team) => (
                              <option key={`manual-away-${team}`} value={team}>{team}</option>
                            ))}
                          </select>
                        </label>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-2">
                        <label className="grid gap-1 text-xs text-slate-300">
                          Estadio {manualOptions.league ? `(${manualOptions.league})` : ""}
                          <select
                            value={manualForm.stadium}
                            onChange={(e) => setManualForm((prev) => ({ ...prev, stadium: e.target.value }))}
                            className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm"
                          >
                            <option value="">Selecciona estadio</option>
                            {manualOptions.stadiums.map((stadium) => (
                              <option key={`manual-stadium-${stadium}`} value={stadium}>{stadium}</option>
                            ))}
                          </select>
                        </label>
                        <label className="grid gap-1 text-xs text-slate-300">
                          Simulaciones
                          <input
                            type="number"
                            min="1000"
                            max="10000"
                            step="500"
                            value={manualForm.simulations}
                            onChange={(e) => setManualForm((prev) => ({ ...prev, simulations: e.target.value }))}
                            className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm"
                          />
                        </label>
                      </div>

                      <button
                        onClick={runManualProbability}
                        disabled={predictingManual}
                        className="w-fit rounded-lg bg-cyan-400 px-4 py-2 text-sm font-bold text-slate-900 disabled:opacity-60"
                      >
                        {predictingManual ? "Calculando..." : "Calcular Top 5 Apuestas"}
                      </button>

                      {manualProbabilityMessage && (
                        <p className="text-xs text-emerald-300">{manualProbabilityMessage}</p>
                      )}

                      {manualProbability && (
                        <div className="rounded-lg border border-slate-700 bg-slate-900/70 p-3 text-xs text-slate-300">
                          <p>
                            Contexto: xG local {manualProbability.model_context.home_expected_goals} · xG visitante {manualProbability.model_context.away_expected_goals}
                          </p>
                          <p>
                            Corners esperados {manualProbability.model_context.expected_corners} · Tarjetas esperadas {manualProbability.model_context.expected_cards}
                          </p>
                          <p>
                            Muestras usadas: H2H {manualProbability.model_context.h2h_matches_used} · Home {manualProbability.model_context.home_recent_matches_used} · Away {manualProbability.model_context.away_recent_matches_used}
                          </p>
                        </div>
                      )}
                    </div>
                  </Panel>

                  <Panel title="Top 5 apuestas recomendadas">
                    <div className="space-y-3">
                      {manualProbability?.recommended_bets_top5.map((item) => {
                        const percentage = Math.max(0, Math.min(100, Math.round(item.probability * 100)))
                        return (
                          <div key={`${item.market}-${item.selection}`} className="rounded-lg bg-slate-900/70 p-3">
                            <div className="mb-1 flex items-center justify-between text-sm">
                              <span className="font-semibold">{item.market}</span>
                              <span className="text-cyan-300">{percentage}%</span>
                            </div>
                            <p className="mb-2 text-xs text-slate-400">{item.selection}</p>
                            <div className="h-2 rounded-full bg-slate-800">
                              <div className="h-2 rounded-full bg-gradient-to-r from-cyan-400 to-emerald-400" style={{ width: `${percentage}%` }} />
                            </div>
                          </div>
                        )
                      })}

                      {!manualProbability && <EmptyState text="Calcula un partido para ver las 5 apuestas sugeridas" />}

                      {manualProbability && (
                        <div className="rounded-lg border border-slate-700 bg-slate-900/70 p-3">
                          <p className="mb-2 text-xs font-semibold text-slate-200">Ranking exact score (Top 5)</p>
                          <div className="space-y-1 text-xs">
                            {manualProbability.exact_score_top5.map((item, index) => (
                              <div key={`${item.score}-${index}`} className="flex items-center justify-between rounded bg-slate-950/70 px-2 py-1">
                                <span className="text-slate-300">{index + 1}. {item.score}</span>
                                <span className="font-semibold text-cyan-300">{Math.round(item.probability * 100)}%</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </Panel>

                  <Panel title="Historial de predicciones guardadas">
                    <div className="space-y-3">
                      {predictions.slice(0, 20).map((p) => {
                        const percentage = Math.max(0, Math.min(100, Math.round((p.probability || 0) * 100)))
                        return (
                          <div key={p.id} className="rounded-lg bg-slate-900/70 p-3">
                            <div className="mb-1 flex items-center justify-between text-sm">
                              <span className="font-semibold">
                                {p.match?.home_team || "Equipo A"} vs {p.match?.away_team || "Equipo B"}
                              </span>
                              <span className="text-cyan-300">{percentage}%</span>
                            </div>
                            <p className="mb-2 text-xs text-slate-400">
                              {p.market} · {p.outcome} · {p.model}
                            </p>
                          </div>
                        )
                      })}
                      {predictions.length === 0 && <EmptyState text="Sin predicciones generadas aún" />}
                    </div>
                  </Panel>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  )
}


function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-3">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-2xl font-bold text-cyan-300">{value}</p>
    </div>
  )
}


function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
      <h3 className="mb-3 text-lg font-semibold">{title}</h3>
      {children}
    </section>
  )
}


function EmptyState({ text }: { text: string }) {
  return <p className="rounded-lg bg-slate-900/50 p-3 text-sm text-slate-400">{text}</p>
}
