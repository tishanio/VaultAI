import { useState, useEffect } from 'react'
import {
  Search,
  MapPin,
  Star,
  Clock,
  Loader,
  Zap,
} from 'lucide-react'
import { useAppStore } from '../store'
import { api, proposeMatch } from '../api'

interface Listing {
  id: string
  seller_id: string
  subscription_id: string
  status: string
  asking_price: number
  dynamic_price: number
  seats_available: number
  description: string
  geo_radius_km: number
  min_trust_score: number
  meta?: Record<string, any>
  created_at: string
  seller?: {
    id: string
    display_name: string
    username: string
  }
  subscription?: {
    service_name: string
    service_category: string
    tier: string
    monthly_cost: number
  }
}

const LOGOS: Record<string, string> = {
  Spotify: '🎵', 'Google One': '☁️', 'YouTube Premium': '📺', Netflix: '🎬',
  'Microsoft 365': '💼', Canva: '🎨', Duolingo: '🦉', Headspace: '🧘',
  Calm: '🧘', 'Apple Music': '🎵',
}

export default function MarketplacePage() {
  const demoMode = useAppStore((s) => s.demoMode)
  const [listings, setListings] = useState<Listing[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [proposing, setProposing] = useState<string | null>(null)
  const [proposedIds, setProposedIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const { data } = await api.get('/api/v1/marketplace/listings')
        if (Array.isArray(data)) {
          setListings(data)
        }
      } catch {
        setListings([])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [demoMode])

  const handlePropose = async (listingId: string) => {
    setProposing(listingId)
    try {
      await proposeMatch(listingId)
      setProposedIds((prev) => new Set([...prev, listingId]))
    } catch {
      // ignore
    } finally {
      setProposing(null)
    }
  }

  const filtered = listings.filter((l) => {
    if (!search.trim()) return true
    const q = search.toLowerCase()
    const name = l.subscription?.service_name?.toLowerCase() || ''
    const desc = (l.description || '').toLowerCase()
    return name.includes(q) || desc.includes(q)
  })

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Marketplace</h1>
          <p className="text-sm text-slate-400">Find subscription seats near you</p>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search services..."
          className="w-full pl-10 pr-4 py-2.5 bg-slate-800/60 border border-slate-700/40 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-vault-500/50 transition"
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader className="h-6 w-6 animate-spin text-vault-400" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-slate-400">
          <Zap className="h-10 w-10 mx-auto opacity-30 mb-3" />
          <p className="font-medium">No listings found</p>
          <p className="text-sm mt-1">Try a different search or check back later</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((listing) => {
            const svcName = listing.subscription?.service_name || 'Unknown'
            const logo = LOGOS[svcName] || '📦'
            const isProposed = proposedIds.has(listing.id)

            return (
              <div
                key={listing.id}
                className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 hover:border-slate-700 transition-all"
              >
                <div className="flex items-start gap-3 mb-3">
                  <span className="text-3xl">{logo}</span>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-white truncate">{svcName}</h3>
                    <p className="text-xs text-slate-400">
                      {listing.subscription?.tier || 'Standard'} plan
                    </p>
                  </div>
                </div>

                <p className="text-sm text-slate-300 mb-3 line-clamp-2">{listing.description}</p>

                <div className="grid grid-cols-2 gap-2 mb-3">
                  <div className="rounded-lg bg-slate-800/50 px-3 py-2">
                    <p className="text-[10px] text-slate-500 uppercase">Price</p>
                    <p className="text-sm font-bold text-vault-300">
                      ${listing.dynamic_price.toFixed(2)}/mo
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-800/50 px-3 py-2">
                    <p className="text-[10px] text-slate-500 uppercase">Seats</p>
                    <p className="text-sm font-bold text-white">{listing.seats_available}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-[10px] text-slate-500 mb-3">
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    {listing.geo_radius_km}km
                  </span>
                  <span className="flex items-center gap-1">
                    <Star className="h-3 w-3" />
                    Min {Math.round(listing.min_trust_score * 100)}%
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Active
                  </span>
                </div>

                <button
                  onClick={() => handlePropose(listing.id)}
                  disabled={isProposed || proposing === listing.id}
                  className={`w-full py-2.5 rounded-xl text-sm font-semibold transition ${
                    isProposed
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                      : 'bg-vault-600 hover:bg-vault-500 text-white shadow-lg shadow-vault-500/20 disabled:opacity-50'
                  }`}
                >
                  {isProposed ? '✓ Proposed' : proposing === listing.id ? 'Proposing...' : 'Propose Match'}
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
