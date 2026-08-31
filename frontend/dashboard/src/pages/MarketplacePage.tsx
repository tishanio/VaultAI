import { useMemo, useState } from 'react'
import {
  Search,
  MapPin,
  Star,
  UserPlus,
} from 'lucide-react'
import { useAppStore } from '../store'
import { generateDemoListings } from '../api'

export default function MarketplacePage() {
  const demoMode = useAppStore((s) => s.demoMode)
  const listings = useMemo(
    () => (demoMode ? generateDemoListings() : []),
    [demoMode]
  )
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'price' | 'score' | 'distance'>('score')
  const [matchAnimation, setMatchAnimation] = useState<string | null>(null)

  const filteredListings = useMemo(() => {
    let filtered = listings
    if (searchQuery) {
      filtered = filtered.filter(
        (l) =>
          l.serviceName.toLowerCase().includes(searchQuery.toLowerCase()) ||
          l.sellerName.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }
    if (selectedCategory !== 'all') {
      filtered = filtered.filter((l) => l.serviceCategory === selectedCategory)
    }
    if (sortBy === 'price') {
      filtered = [...filtered].sort((a, b) => a.dynamicPrice - b.dynamicPrice)
    } else if (sortBy === 'score') {
      filtered = [...filtered].sort((a, b) => b.matchScore - a.matchScore)
    } else if (sortBy === 'distance') {
      filtered = [...filtered].sort((a, b) => a.distanceKm - b.distanceKm)
    }
    return filtered
  }, [listings, searchQuery, selectedCategory, sortBy])

  const handleMatch = (listingId: string) => {
    setMatchAnimation(listingId)
    setTimeout(() => setMatchAnimation(null), 1500)
  }

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-vault-200">Discovery</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">Marketplace</h2>
        </div>
        <div className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.2em] text-emerald-200">
          {filteredListings.length} live listings
        </div>
      </div>

      <div className="panel p-3 sm:p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search services, sellers..."
              className="input pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <select
            className="input w-auto min-w-[160px]"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
          >
            <option value="all">All Categories</option>
            <option value="music">Music</option>
            <option value="cloud_storage">Cloud Storage</option>
            <option value="streaming">Streaming</option>
            <option value="wellness">Wellness</option>
            <option value="education">Education</option>
          </select>

          <select
            className="input w-auto min-w-[150px]"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'price' | 'score' | 'distance')}
          >
            <option value="score">Best Match</option>
            <option value="price">Lowest Price</option>
            <option value="distance">Nearest</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filteredListings.map((listing) => (
          <div
            key={listing.id}
            className={`card relative overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:border-vault-500/40 ${
              matchAnimation === listing.id ? 'ring-2 ring-emerald-500/60 shadow-[0_0_0_1px_rgba(16,185,129,0.5)]' : ''
            }`}
          >
            <div className="absolute right-3 top-3">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-full text-xs font-bold ${
                  listing.matchScore >= 0.8
                    ? 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/25'
                    : listing.matchScore >= 0.6
                    ? 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-400/25'
                    : 'bg-slate-800 text-slate-300 ring-1 ring-slate-700'
                }`}
              >
                {(listing.matchScore * 100).toFixed(0)}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-vault-500/10 text-2xl ring-1 ring-vault-500/20">
                {listing.serviceName === 'Spotify'
                  ? '🎵'
                  : listing.serviceName === 'Google One'
                  ? '☁️'
                  : '📺'}
              </div>
              <div>
                <h3 className="font-semibold text-white">{listing.serviceName}</h3>
                <p className="text-sm text-slate-400">by {listing.sellerName}</p>
              </div>
            </div>

            <p className="mt-4 text-sm leading-6 text-slate-300">{listing.description}</p>

            <div className="mt-4 flex flex-wrap gap-1.5">
              {listing.matchReasons.map((reason, i) => (
                <span key={i} className="badge-blue">{reason}</span>
              ))}
            </div>

            <div className="mt-4 flex items-center justify-between text-sm">
              <div className="flex items-center gap-3 text-slate-400">
                <span className="flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5" />
                  {listing.distanceKm} km
                </span>
                <span className="flex items-center gap-1">
                  <Star className="h-3.5 w-3.5 text-amber-400" />
                  {(listing.sellerReputation * 100).toFixed(0)}%
                </span>
              </div>
              <span className="text-sm font-medium text-slate-300">
                {listing.seatsAvailable} seat(s)
              </span>
            </div>

            <div className="mt-4 flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
              <div>
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Dynamic Price</p>
                <p className="mt-1 text-lg font-bold text-emerald-300">
                  ${listing.dynamicPrice.toFixed(2)}
                  <span className="text-xs text-slate-500">/mo</span>
                </p>
              </div>
              <button
                onClick={() => handleMatch(listing.id)}
                className="btn-primary flex items-center gap-2"
              >
                <UserPlus className="h-4 w-4" />
                {matchAnimation === listing.id ? 'Matched!' : 'Match'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {filteredListings.length === 0 && (
        <div className="card text-center">
          <Search className="mx-auto h-12 w-12 text-slate-600" />
          <h3 className="mt-3 text-lg font-medium text-slate-200">No listings found</h3>
          <p className="mt-1 text-sm text-slate-500">Try adjusting your filters or search query.</p>
        </div>
      )}
    </div>
  )
}
