import { useMemo, useState } from 'react'
import {
  CreditCard,
  ArrowDownLeft,
  Clock,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  Wallet,
  RefreshCw,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

// ---------------------------------------------------------------------------
// Types & Demo Data
// ---------------------------------------------------------------------------

interface EscrowTransaction {
  id: string
  matchId: string
  serviceName: string
  serviceLogo: string
  sellerName: string
  amount: number
  platformFee: number
  sellerPayout: number
  status: 'created' | 'funded' | 'held' | 'released' | 'refunded' | 'disputed'
  createdAt: string
  releasedAt: string | null
}

interface Payout {
  id: string
  amount: number
  currency: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  payoutMethod: string
  createdAt: string
  processedAt: string | null
  failureReason: string | null
}

const DEMO_ESCROWS: EscrowTransaction[] = [
  { id: 'esc-1', matchId: 'm1', serviceName: 'Spotify', serviceLogo: '🎵', sellerName: 'Alex Chen', amount: 4.50, platformFee: 0.54, sellerPayout: 3.96, status: 'released', createdAt: new Date(Date.now() - 86400000).toISOString(), releasedAt: new Date(Date.now() - 43200000).toISOString() },
  { id: 'esc-2', matchId: 'm2', serviceName: 'Google One', serviceLogo: '☁️', sellerName: 'Maria Santos', amount: 5.75, platformFee: 0.69, sellerPayout: 5.06, status: 'funded', createdAt: new Date(Date.now() - 172800000).toISOString(), releasedAt: null },
  { id: 'esc-3', matchId: 'm3', serviceName: 'YouTube Premium', serviceLogo: '📺', sellerName: 'James Wilson', amount: 5.00, platformFee: 0.60, sellerPayout: 4.40, status: 'held', createdAt: new Date(Date.now() - 259200000).toISOString(), releasedAt: null },
  { id: 'esc-4', matchId: 'm4', serviceName: 'Headspace', serviceLogo: '🧘', sellerName: 'Sarah Kim', amount: 2.50, platformFee: 0.30, sellerPayout: 2.20, status: 'disputed', createdAt: new Date(Date.now() - 345600000).toISOString(), releasedAt: null },
  { id: 'esc-5', matchId: 'm5', serviceName: 'Duolingo', serviceLogo: '🦉', sellerName: 'David Park', amount: 2.00, platformFee: 0.24, sellerPayout: 1.76, status: 'released', createdAt: new Date(Date.now() - 604800000).toISOString(), releasedAt: new Date(Date.now() - 518400000).toISOString() },
  { id: 'esc-6', matchId: 'm6', serviceName: 'Spotify', serviceLogo: '🎵', sellerName: 'Alex Chen', amount: 4.50, platformFee: 0.54, sellerPayout: 3.96, status: 'refunded', createdAt: new Date(Date.now() - 691200000).toISOString(), releasedAt: null },
]

const DEMO_PAYOUTS: Payout[] = [
  { id: 'pay-1', amount: 3.96, currency: 'USD', status: 'completed', payoutMethod: 'bank_transfer', createdAt: new Date(Date.now() - 43200000).toISOString(), processedAt: new Date(Date.now() - 36000000).toISOString(), failureReason: null },
  { id: 'pay-2', amount: 1.76, currency: 'USD', status: 'completed', payoutMethod: 'bank_transfer', createdAt: new Date(Date.now() - 518400000).toISOString(), processedAt: new Date(Date.now() - 432000000).toISOString(), failureReason: null },
  { id: 'pay-3', amount: 5.06, currency: 'USD', status: 'pending', payoutMethod: 'bank_transfer', createdAt: new Date(Date.now() - 172800000).toISOString(), processedAt: null, failureReason: null },
  { id: 'pay-4', amount: 12.50, currency: 'USD', status: 'failed', payoutMethod: 'bank_transfer', createdAt: new Date(Date.now() - 777600000).toISOString(), processedAt: null, failureReason: 'Bank account not verified' },
]

const CHART_DATA = [
  { name: 'Week 1', income: 12.50, fees: 1.50 },
  { name: 'Week 2', income: 18.75, fees: 2.25 },
  { name: 'Week 3', income: 15.00, fees: 1.80 },
  { name: 'Week 4', income: 22.25, fees: 2.67 },
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusIcon(status: string) {
  switch (status) {
    case 'released': return <CheckCircle className="h-4 w-4 text-emerald-400" />
    case 'funded': return <CreditCard className="h-4 w-4 text-blue-400" />
    case 'held': return <Clock className="h-4 w-4 text-yellow-400" />
    case 'disputed': return <AlertTriangle className="h-4 w-4 text-red-400" />
    case 'refunded': return <RefreshCw className="h-4 w-4 text-orange-400" />
    default: return <Clock className="h-4 w-4 text-gray-400" />
  }
}

function statusColor(status: string) {
  switch (status) {
    case 'released': case 'completed': return 'badge-green'
    case 'funded': case 'processing': return 'badge-blue'
    case 'held': case 'pending': return 'badge-yellow'
    case 'disputed': case 'failed': return 'badge-red'
    case 'refunded': return 'bg-orange-900/30 text-orange-400 rounded-full px-2.5 py-0.5 text-xs font-medium'
    default: return 'badge-blue'
  }
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function EscrowPage() {
  const [activeTab, setActiveTab] = useState<'escrows' | 'payouts'>('escrows')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const filteredEscrows = useMemo(
    () => statusFilter === 'all' ? DEMO_ESCROWS : DEMO_ESCROWS.filter((e) => e.status === statusFilter),
    [statusFilter]
  )

  const totalEarned = DEMO_ESCROWS
    .filter((e) => e.status === 'released')
    .reduce((sum, e) => sum + e.sellerPayout, 0)

  const totalPending = DEMO_ESCROWS
    .filter((e) => ['funded', 'held'].includes(e.status))
    .reduce((sum, e) => sum + e.amount, 0)

  const totalFees = DEMO_ESCROWS
    .filter((e) => e.status === 'released')
    .reduce((sum, e) => sum + e.platformFee, 0)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Escrow & Transactions</h2>
        <p className="text-sm text-gray-400">Track payments, escrow status, and payouts</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-emerald-900/50 p-2.5 text-emerald-400">
              <ArrowDownLeft className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Total Earned</p>
              <p className="text-xl font-bold">${totalEarned.toFixed(2)}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-yellow-900/50 p-2.5 text-yellow-400">
              <Clock className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-gray-400">In Escrow</p>
              <p className="text-xl font-bold">${totalPending.toFixed(2)}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-vault-900/50 p-2.5 text-vault-400">
              <TrendingUp className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Platform Fees</p>
              <p className="text-xl font-bold">${totalFees.toFixed(2)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-gray-800 p-1">
        <button
          onClick={() => setActiveTab('escrows')}
          className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'escrows' ? 'bg-vault-600 text-white' : 'text-gray-400 hover:text-white'
          }`}
        >
          Escrow Transactions
        </button>
        <button
          onClick={() => setActiveTab('payouts')}
          className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'payouts' ? 'bg-vault-600 text-white' : 'text-gray-400 hover:text-white'
          }`}
        >
          Payouts
        </button>
      </div>

      {/* Escrow Tab */}
      {activeTab === 'escrows' && (
        <>
          <div className="flex items-center gap-3">
            <select
              className="input w-auto"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Status</option>
              <option value="created">Created</option>
              <option value="funded">Funded</option>
              <option value="held">Held</option>
              <option value="released">Released</option>
              <option value="refunded">Refunded</option>
              <option value="disputed">Disputed</option>
            </select>
          </div>

          <div className="space-y-3">
            {filteredEscrows.map((escrow) => (
              <div key={escrow.id} className="card">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <span className="text-2xl">{escrow.serviceLogo}</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium">{escrow.serviceName}</h4>
                        <span className={statusColor(escrow.status)}>{escrow.status}</span>
                      </div>
                      <p className="text-sm text-gray-400">with {escrow.sellerName}</p>
                      <p className="text-xs text-gray-500">{timeAgo(escrow.createdAt)}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-1">
                      {statusIcon(escrow.status)}
                      <span className="text-lg font-bold">${escrow.amount.toFixed(2)}</span>
                    </div>
                    <div className="text-xs text-gray-500">
                      Fee: ${escrow.platformFee.toFixed(2)} · Payout: ${escrow.sellerPayout.toFixed(2)}
                    </div>
                  </div>
                </div>
                {escrow.status === 'disputed' && (
                  <div className="mt-3 flex items-center gap-2 rounded-lg bg-red-900/20 p-2 text-xs text-red-400">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    <span>Funds on hold due to dispute. Awaiting resolution.</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {/* Payouts Tab */}
      {activeTab === 'payouts' && (
        <>
          {/* Revenue Chart */}
          <div className="card">
            <h3 className="mb-4 text-lg font-semibold">Revenue Over Time</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={CHART_DATA}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" fontSize={12} />
                <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }} />
                <Bar dataKey="income" fill="#10B981" name="Income" radius={[4, 4, 0, 0]} />
                <Bar dataKey="fees" fill="#6366F1" name="Fees" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-3">
            {DEMO_PAYOUTS.map((payout) => (
              <div key={payout.id} className="card">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-800">
                      <Wallet className="h-5 w-5 text-gray-400" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium">${payout.amount.toFixed(2)} {payout.currency}</h4>
                        <span className={statusColor(payout.status)}>{payout.status}</span>
                      </div>
                      <p className="text-sm text-gray-400">{payout.payoutMethod.replace('_', ' ')}</p>
                      <p className="text-xs text-gray-500">{timeAgo(payout.createdAt)}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    {payout.processedAt && (
                      <p className="text-xs text-gray-500">
                        Processed {timeAgo(payout.processedAt)}
                      </p>
                    )}
                    {payout.failureReason && (
                      <p className="text-xs text-red-400">{payout.failureReason}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
