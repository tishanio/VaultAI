import { useState, useEffect } from 'react'
import { Search, Loader, Zap } from 'lucide-react'
import { useAppStore } from '../store'
import { api } from '../api'

interface Listing {
  id: string
  asking_price: number
  dynamic_price: number
  seats_available: number
  description: string
  geo_radius_km: number
  meta?: Record<string, any>
  subscription?: {
    service_name: string
    tier: string
    monthly_cost: number
  }
}

interface Subscription {
  id: string
  service_name: string
  service_category: string
  tier: string
  monthly_cost: number
  max_seats: number
  used_seats: number
}

const LOGOS: Record<string, string> = {
  Spotify: '🎵', 'Google One': '☁️', 'YouTube Premium': '📺', Netflix: '🎬',
  'Microsoft 365': '💼', Canva: '🎨', Duolingo: '🦉', Headspace: '🧘',
  Calm: '🧘', 'Apple Music': '🎵',
}

export default function SearchPage() {
  const demoMode = useAppStore((s) => s.demoMode)
  const [query, setQuery] = useState('')
  const [listings, setListings] = useState<Listing[]>([])
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [listingsRes, subsRes] = await Promise.all([
          api.get('/api/v1/marketplace/listings').catch(() => ({ data: [] })),
          api.get('/api/v1/subscriptions').catch(() => ({ data: [] })),
        ])
        if (Array.isArray(listingsRes.data)) setListings(listingsRes.data)
        if (Array.isArray(subsRes.data)) setSubscriptions(subsRes.data)
      } catch {
        // ignore
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [demoMode])

  const q = query.toLowerCase()
  const filteredListings = listings.filter((l) => {
    if (!q) return true
    const name = l.subscription?.service_name?.toLowerCase() || ''
    const desc = (l.description || '').toLowerCase()
    return name.includes(q) || desc.includes(q)
  })

  const filteredSubs = subscriptions.filter((s) => {
    if (!q) return true
    return s.service_name.toLowerCase().includes(q) || s.service_category.toLowerCase().includes(q)
  })

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Search</h1>
        <p className="text-sm text-slate-400">Search subscriptions and marketplace listings</p>
      </div>

      <div className="relative max-w-lg">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search services..."
          className="w-full pl-10 pr-4 py-3 bg-slate-800/60 border border-slate-700/40 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-vault-500/50 transition"
          autoFocus
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader className="h-6 w-6 animate-spin text-vault-400" />
        </div>
      ) : (
        <>
          {/* Marketplace Listings */}
          {filteredListings.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-white mb-3">Marketplace Listings ({filteredListings.length})</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {filteredListings.map((l) => (
                  <div key={l.id} className="rounded-xl border border-slate-800 bg-slate-900/70 p-3 flex items-center gap-3">
                    <span className="text-2xl">{LOGOS[l.subscription?.service_name || ''] || '📦'}</span>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-white text-sm">{l.subscription?.service_name || 'Unknown'}</p>
                      <p className="text-xs text-slate-400 truncate">{l.description}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm font-bold text-vault-300">${l.dynamic_price.toFixed(2)}/mo</p>
                      <p className="text-[10px] text-slate-500">{l.seats_available} seats</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Subscriptions */}
          {filteredSubs.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-white mb-3">Subscriptions ({filteredSubs.length})</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {filteredSubs.map((s) => (
                  <div key={s.id} className="rounded-xl border border-slate-800 bg-slate-900/70 p-3 flex items-center gap-3">
                    <span className="text-2xl">{LOGOS[s.service_name] || '📦'}</span>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-white text-sm">{s.service_name}</p>
                      <p className="text-xs text-slate-400">{s.tier} • {s.used_seats}/{s.max_seats} seats</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm font-bold text-white">${s.monthly_cost}/mo</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {filteredListings.length === 0 && filteredSubs.length === 0 && query && (
            <div className="text-center py-12 text-slate-400">
              <Zap className="h-10 w-10 mx-auto opacity-30 mb-3" />
              <p className="font-medium">No results found</p>
              <p className="text-sm mt-1">Try a different search term</p>
            </div>
          )}

          {!query && filteredListings.length === 0 && filteredSubs.length === 0 && (
            <div className="text-center py-12 text-slate-400">
              <Search className="h-10 w-10 opacity-30 mb-3 mx-auto" />
              <p className="font-medium">Start typing to search</p>
              <p className="text-sm mt-1">Search for services, subscriptions, or listings</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
