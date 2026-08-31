import { useMemo, useState } from 'react'
import { Check, X, Clock, Shield, DollarSign, MessageSquare } from 'lucide-react'
import { useAppStore } from '../store'
import { generateDemoMatches } from '../api'

export default function MatchesPage() {
  const demoMode = useAppStore((s) => s.demoMode)
  const matches = useMemo(
    () => (demoMode ? generateDemoMatches() : []),
    [demoMode]
  )
  const [filter, setFilter] = useState<'all' | 'proposed' | 'accepted' | 'completed'>('all')

  const filteredMatches = matches.filter(
    (m) => filter === 'all' || m.status === filter
  )

  const statusColor = (status: string) => {
    switch (status) {
      case 'proposed': return 'badge-yellow'
      case 'accepted': return 'badge-green'
      case 'completed': return 'badge-blue'
      case 'rejected': return 'badge-red'
      default: return 'badge-blue'
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Matches</h2>
        <p className="text-sm text-gray-400">
          View and manage your subscription matches
        </p>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2">
        {(['all', 'proposed', 'accepted', 'completed'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              filter === tab
                ? 'bg-vault-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            {tab !== 'all' && (
              <span className="ml-1.5 text-xs opacity-60">
                ({matches.filter((m) => m.status === tab).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Matches List */}
      <div className="space-y-4">
        {filteredMatches.map((match) => (
          <div key={match.id} className="card">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gray-800 text-2xl">
                  {match.serviceName === 'Spotify'
                    ? '🎵'
                    : match.serviceName === 'Google One'
                    ? '☁️'
                    : '📺'}
                </div>
                <div>
                  <h3 className="font-semibold">{match.serviceName}</h3>
                  <p className="text-sm text-gray-400">with {match.sellerName}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <span className={statusColor(match.status)}>
                      {match.status}
                    </span>
                    <span className="badge-blue">
                      <Shield className="mr-1 h-3 w-3" />
                      Match Score: {(match.matchScore * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              {match.status === 'proposed' && (
                <div className="flex gap-2">
                  <button className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700">
                    <Check className="h-4 w-4" /> Accept
                  </button>
                  <button className="flex items-center gap-1.5 rounded-lg bg-gray-700 px-3 py-1.5 text-sm font-medium text-gray-300 hover:bg-gray-600">
                    <X className="h-4 w-4" /> Reject
                  </button>
                </div>
              )}
            </div>

            {/* Match Details */}
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="flex items-center gap-2 rounded-lg bg-gray-800/50 p-3 text-sm">
                <DollarSign className="h-4 w-4 text-emerald-400" />
                <div>
                  <p className="text-gray-400">Monthly Price</p>
                  <p className="font-medium">${match.proposedPrice.toFixed(2)}/mo</p>
                </div>
              </div>
              <div className="flex items-center gap-2 rounded-lg bg-gray-800/50 p-3 text-sm">
                <Clock className="h-4 w-4 text-yellow-400" />
                <div>
                  <p className="text-gray-400">Proposed</p>
                  <p className="font-medium">
                    {new Date(match.createdAt).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 rounded-lg bg-gray-800/50 p-3 text-sm">
                <MessageSquare className="h-4 w-4 text-vault-400" />
                <div>
                  <p className="text-gray-400">Communication</p>
                  <p className="font-medium">In-app chat</p>
                </div>
              </div>
            </div>

            {match.status === 'accepted' && (
              <div className="mt-4 rounded-lg border border-emerald-800 bg-emerald-900/20 p-3 text-sm text-emerald-300">
                ✅ Match accepted! Escrow will be created to secure the transaction. 
                You'll receive access details once payment is confirmed.
              </div>
            )}
          </div>
        ))}
      </div>

      {filteredMatches.length === 0 && (
        <div className="card text-center">
          <Clock className="mx-auto h-12 w-12 text-gray-600" />
          <h3 className="mt-3 text-lg font-medium text-gray-400">No matches found</h3>
          <p className="mt-1 text-sm text-gray-500">
            Browse the marketplace to find subscription matches
          </p>
        </div>
      )}
    </div>
  )
}
