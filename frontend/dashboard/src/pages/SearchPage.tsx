import { useMemo, useState } from 'react'
import {
  Search,
  Star,
  MapPin,
  X,
  UserPlus,
  CreditCard,
  Store,
  SlidersHorizontal,
} from 'lucide-react'
import { useAppStore } from '../store'
import {
  generateDemoListings,
  generateDemoSubscriptions,
  type DemoListing,
  type DemoSubscription,
} from '../api'

type SearchTab = 'all' | 'listings' | 'subscriptions'

interface SearchResult {
  id: string
  type: 'listing' | 'subscription'
  icon: string
  title: string
  subtitle: string
  price?: number
  priceLabel?: string
  reputation?: number
  distance?: number
  seats?: string
  category: string
  matchScore?: number
  tags: string[]
}

export default function SearchPage() {
  const demoMode = useAppStore((s) => s.demoMode)
  const [query, setQuery] = useState('')
  const [activeTab, setActiveTab] = useState<SearchTab>('all')
  const [sortBy, setSortBy] = useState<'relevance' | 'price' | 'distance' | 'score'>('relevance')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [priceRange, setPriceRange] = useState<[number, number]>([0, 50])
  const [minReputation, setMinReputation] = useState(0)
  const [showFilters, setShowFilters] = useState(false)

  const listings: DemoListing[] = useMemo(
    () => (demoMode ? generateDemoListings() : []),
    [demoMode]
  )
  const subscriptions: DemoSubscription[] = useMemo(
    () => (demoMode ? generateDemoSubscriptions() : []),
    [demoMode]
  )

  // Build unified search results
  const results = useMemo<SearchResult[]>(() => {
    const items: SearchResult[] = []

    // Listings
    listings.forEach((l) => {
      items.push({
        id: l.id,
        type: 'listing',
        icon:
          l.serviceName === 'Spotify'
            ? '🎵'
            : l.serviceName === 'Google One'
            ? '☁️'
            : l.serviceName === 'YouTube Premium'
            ? '📺'
            : '🔧',
        title: l.serviceName,
        subtitle: `by ${l.sellerName}`,
        price: l.dynamicPrice,
        priceLabel: '/mo',
        reputation: l.sellerReputation,
        distance: l.distanceKm,
        seats: `${l.seatsAvailable} seat(s) available`,
        category: l.serviceCategory,
        matchScore: l.matchScore,
        tags: l.matchReasons,
      })
    })

    // Subscriptions (user's own)
    subscriptions.forEach((s) => {
      items.push({
        id: s.id,
        type: 'subscription',
        icon: s.serviceLogo,
        title: s.serviceName,
        subtitle: `${s.tier} — ${s.usedSeats}/${s.maxSeats} seats`,
        price: s.monthlyCost,
        priceLabel: '/mo',
        seats: `${s.maxSeats - s.usedSeats} unused seat(s)`,
        category: s.serviceCategory,
        tags: [s.status, `${s.usagePercentage}% used`],
      })
    })

    return items
  }, [listings, subscriptions])

  // Filter
  const filtered = useMemo(() => {
    let out = results

    // Tab filter
    if (activeTab === 'listings') out = out.filter((r) => r.type === 'listing')
    if (activeTab === 'subscriptions') out = out.filter((r) => r.type === 'subscription')

    // Search query
    if (query.trim()) {
      const q = query.toLowerCase()
      out = out.filter(
        (r) =>
          r.title.toLowerCase().includes(q) ||
          r.subtitle.toLowerCase().includes(q) ||
          r.category.toLowerCase().includes(q) ||
          r.tags.some((t) => t.toLowerCase().includes(q))
      )
    }

    // Category
    if (categoryFilter !== 'all') {
      out = out.filter((r) => r.category === categoryFilter)
    }

    // Price range
    out = out.filter((r) => {
      if (r.price === undefined) return true
      return r.price >= priceRange[0] && r.price <= priceRange[1]
    })

    // Min reputation
    if (minReputation > 0) {
      out = out.filter((r) => (r.reputation ?? 1) >= minReputation / 100)
    }

    // Sort
    if (sortBy === 'price') {
      out = [...out].sort((a, b) => (a.price ?? 0) - (b.price ?? 0))
    } else if (sortBy === 'distance') {
      out = [...out].sort((a, b) => (a.distance ?? 999) - (b.distance ?? 999))
    } else if (sortBy === 'score') {
      out = [...out].sort((a, b) => (b.matchScore ?? 0) - (a.matchScore ?? 0))
    }

    return out
  }, [results, query, activeTab, categoryFilter, priceRange, minReputation, sortBy])

  const categories = useMemo(() => {
    const cats = new Set(results.map((r) => r.category))
    return Array.from(cats).sort()
  }, [results])

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div>
        <p className="text-xs uppercase tracking-[0.24em] text-vault-200">Search</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">Find what matters</h2>
      </div>

      <div className="panel p-0">
        <div className="flex items-center gap-3 px-4 py-3">
          <Search className="h-5 w-5 text-slate-500" />
          <input
            type="text"
            placeholder="Search services, sellers, categories..."
            className="flex-1 bg-transparent text-slate-100 placeholder-slate-500 focus:outline-none"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          {query && (
            <button onClick={() => setQuery('')} className="rounded p-1 text-slate-500 hover:text-slate-300">
              <X className="h-4 w-4" />
            </button>
          )}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-sm font-medium transition-colors ${
              showFilters
                ? 'bg-vault-500/10 text-vault-200 ring-1 ring-vault-500/20'
                : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            <SlidersHorizontal className="h-4 w-4" />
            Filters
          </button>
        </div>

        {showFilters && (
          <div className="border-t border-slate-800 px-4 py-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">Category</label>
                <select
                  className="input py-2 text-sm"
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                >
                  <option value="all">All Categories</option>
                  {categories.map((c) => (
                    <option key={c} value={c}>
                      {c.replace(/_/g, ' ').replace(/\b\w/g, (ch) => ch.toUpperCase())}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">Sort by</label>
                <select
                  className="input py-2 text-sm"
                  value={sortBy}
                  onChange={(e) =>
                    setSortBy(e.target.value as 'relevance' | 'price' | 'distance' | 'score')
                  }
                >
                  <option value="relevance">Relevance</option>
                  <option value="price">Price: Low → High</option>
                  <option value="distance">Distance: Near → Far</option>
                  <option value="score">Match Score: High → Low</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">
                  Max Price: ${priceRange[1]}/mo
                </label>
                <input
                  type="range"
                  min={0}
                  max={50}
                  step={1}
                  value={priceRange[1]}
                  onChange={(e) => setPriceRange([0, Number(e.target.value)])}
                  className="mt-2 w-full accent-vault-500"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">
                  Min Reputation: {minReputation}%
                </label>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={minReputation}
                  onChange={(e) => setMinReputation(Number(e.target.value))}
                  className="mt-2 w-full accent-vault-500"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-1 rounded-2xl border border-slate-800 bg-slate-950/80 p-1">
        {(
          [
            { key: 'all', label: 'All', icon: Search },
            { key: 'listings', label: 'Marketplace', icon: Store },
            { key: 'subscriptions', label: 'My Subscriptions', icon: CreditCard },
          ] as const
        ).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === key
                ? 'bg-vault-500/10 text-vault-200 ring-1 ring-vault-500/20'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">
          {filtered.length} result{filtered.length !== 1 ? 's' : ''}
          {query && (
            <span>
              {' '}
              for "<span className="text-slate-200">{query}</span>"
            </span>
          )}
        </p>
      </div>

      <div className="space-y-3">
        {filtered.map((result) => (
          <div
            key={result.id}
            className="card flex flex-col gap-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-vault-500/40 sm:flex-row sm:items-center"
          >
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-vault-500/10 text-2xl ring-1 ring-vault-500/20">
              {result.icon}
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="truncate font-semibold text-white">{result.title}</h3>
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${
                    result.type === 'listing'
                      ? 'bg-vault-500/10 text-vault-200 ring-1 ring-vault-500/20'
                      : 'bg-violet-500/10 text-violet-200 ring-1 ring-violet-500/20'
                  }`}
                >
                  {result.type === 'listing' ? 'Marketplace' : 'Your Subscription'}
                </span>
                {result.matchScore !== undefined && result.matchScore > 0 && (
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      result.matchScore >= 0.8
                        ? 'bg-emerald-500/10 text-emerald-200 ring-1 ring-emerald-500/20'
                        : result.matchScore >= 0.6
                        ? 'bg-amber-500/10 text-amber-200 ring-1 ring-amber-500/20'
                        : 'bg-slate-800 text-slate-300 ring-1 ring-slate-700'
                    }`}
                  >
                    {(result.matchScore * 100).toFixed(0)}% match
                  </span>
                )}
              </div>
              <p className="mt-1 truncate text-sm text-slate-400">{result.subtitle}</p>

              <div className="mt-2 flex flex-wrap gap-1.5">
                {result.tags.map((tag, i) => (
                  <span key={i} className="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] text-slate-300">
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-4 text-sm">
              {result.reputation !== undefined && (
                <span className="flex items-center gap-1 text-slate-400">
                  <Star className="h-3.5 w-3.5 text-amber-400" />
                  {(result.reputation * 100).toFixed(0)}%
                </span>
              )}
              {result.distance !== undefined && (
                <span className="flex items-center gap-1 text-slate-400">
                  <MapPin className="h-3.5 w-3.5" />
                  {result.distance} km
                </span>
              )}
              {result.seats && <span className="text-slate-500">{result.seats}</span>}
              {result.price !== undefined && (
                <div className="text-right">
                  <p className="font-bold text-emerald-300">
                    ${result.price.toFixed(2)}
                    <span className="text-xs text-slate-500">{result.priceLabel}</span>
                  </p>
                </div>
              )}
              {result.type === 'listing' && (
                <button className="btn-primary flex items-center gap-1.5 text-sm">
                  <UserPlus className="h-3.5 w-3.5" />
                  Match
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="card text-center">
          <Search className="mx-auto h-12 w-12 text-slate-600" />
          <h3 className="mt-3 text-lg font-medium text-slate-200">No results found</h3>
          <p className="mt-1 text-sm text-slate-500">
            {query ? `No matches for "${query}". Try a different search term.` : 'Try adjusting your filters.'}
          </p>
          <button
            onClick={() => {
              setQuery('')
              setCategoryFilter('all')
              setPriceRange([0, 50])
              setMinReputation(0)
            }}
            className="btn-secondary mt-4"
          >
            Clear all filters
          </button>
        </div>
      )}
    </div>
  )
}
