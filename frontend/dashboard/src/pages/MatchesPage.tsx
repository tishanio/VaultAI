import { useState, useEffect } from 'react'
import {
  Check,
  X,
  Clock,
  Loader,
  Zap,
  Star,
  DollarSign,
} from 'lucide-react'
import { useAppStore } from '../store'
import { api, acceptMatch, rejectMatch } from '../api'

interface Match {
  id: string
  listing_id: string
  buyer_id: string
  seller_id: string
  status: string
  match_score: number
  trust_score: number
  proximity_score: number
  schedule_score: number
  proposed_price: number
  expires_at: string
  accepted_at: string | null
  created_at: string
  listing?: {
    id: string
    description: string
    subscription?: {
      service_name: string
      tier: string
      monthly_cost: number
    }
  }
  buyer?: {
    display_name: string
    username: string
  }
  seller?: {
    display_name: string
    username: string
  }
}

const LOGOS: Record<string, string> = {
  Spotify: '🎵', 'Google One': '☁️', 'YouTube Premium': '📺', Netflix: '🎬',
  'Microsoft 365': '💼', Canva: '🎨', Duolingo: '🦉', Headspace: '🧘',
  Calm: '🧘', 'Apple Music': '🎵',
}

export default function MatchesPage() {
  const demoMode = useAppStore((s) => s.demoMode)
  const [matches, setMatches] = useState<Match[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'proposed' | 'accepted' | 'rejected'>('all')

  useEffect(() => {
    loadMatches()
  }, [demoMode])

  async function loadMatches() {
    setLoading(true)
    try {
      const { data } = await api.get('/api/v1/matches')
      if (Array.isArray(data)) {
        setMatches(data)
      }
    } catch {
      setMatches([])
    } finally {
      setLoading(false)
    }
  }

  async function handleAccept(matchId: string) {
    setActionLoading(matchId)
    try {
      await acceptMatch(matchId)
      await loadMatches() // Refresh
    } catch {
      // ignore
    } finally {
      setActionLoading(null)
    }
  }

  async function handleReject(matchId: string) {
    setActionLoading(matchId)
    try {
      await rejectMatch(matchId)
      await loadMatches() // Refresh
    } catch {
      // ignore
    } finally {
      setActionLoading(null)
    }
  }

  const filtered = matches.filter((m) => filter === 'all' || m.status === filter)

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Matches</h1>
          <p className="text-sm text-slate-400">Your subscription matches</p>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {(['all', 'proposed', 'accepted', 'rejected'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              filter === f
                ? 'bg-vault-600 text-white'
                : 'bg-slate-800/50 text-slate-400 hover:text-white'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {f !== 'all' && (
              <span className="ml-1.5 text-[10px] opacity-70">
                {matches.filter((m) => m.status === f).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader className="h-6 w-6 animate-spin text-vault-400" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-slate-400">
          <Zap className="h-10 w-10 mx-auto opacity-30 mb-3" />
          <p className="font-medium">No matches found</p>
          <p className="text-sm mt-1">
            {filter === 'all'
              ? 'Browse the marketplace to find matches'
              : `No ${filter} matches`}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((match) => {
            const svcName = match.listing?.subscription?.service_name || 'Unknown'
            const logo = LOGOS[svcName] || '📦'
            const isActioning = actionLoading === match.id

            return (
              <div
                key={match.id}
                className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 hover:border-slate-700 transition-all"
              >
                <div className="flex items-start gap-4">
                  <span className="text-3xl">{logo}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="font-semibold text-white">{svcName}</h3>
                      <span
                        className={`px-2 py-0.5 rounded-md text-[10px] font-medium ${
                          match.status === 'accepted'
                            ? 'bg-emerald-500/15 text-emerald-400'
                            : match.status === 'proposed'
                            ? 'bg-blue-500/15 text-blue-400'
                            : 'bg-red-500/15 text-red-400'
                        }`}
                      >
                        {match.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {match.listing?.subscription?.tier || 'Standard'} plan
                    </p>

                    <div className="flex items-center gap-4 mt-3 text-xs text-slate-400">
                      <span className="flex items-center gap-1">
                        <DollarSign className="h-3 w-3 text-vault-400" />
                        ${match.proposed_price.toFixed(2)}/mo
                      </span>
                      <span className="flex items-center gap-1">
                        <Star className="h-3 w-3 text-amber-400" />
                        {Math.round(match.match_score * 100)}% match
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(match.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    {match.listing?.description && (
                      <p className="text-sm text-slate-300 mt-2 line-clamp-1">
                        {match.listing.description}
                      </p>
                    )}
                  </div>
                </div>

                {/* Action buttons for proposed matches */}
                {match.status === 'proposed' && (
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={() => handleAccept(match.id)}
                      disabled={isActioning}
                      className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold transition disabled:opacity-50"
                    >
                      {isActioning ? (
                        <Loader className="h-4 w-4 animate-spin" />
                      ) : (
                        <Check className="h-4 w-4" />
                      )}
                      Accept
                    </button>
                    <button
                      onClick={() => handleReject(match.id)}
                      disabled={isActioning}
                      className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-slate-700 hover:bg-slate-600 text-white text-sm font-semibold transition disabled:opacity-50"
                    >
                      {isActioning ? (
                        <Loader className="h-4 w-4 animate-spin" />
                      ) : (
                        <X className="h-4 w-4" />
                      )}
                      Reject
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
