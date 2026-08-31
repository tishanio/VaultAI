import { useMemo, useState } from 'react'
import {
  Users,
  DollarSign,
  AlertTriangle,
  Shield,
  Activity,
  Search,
  Ban,
  CheckCircle,
  UserPlus,
  CreditCard,
  Eye,
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
// Demo Data
// ---------------------------------------------------------------------------

interface PlatformStats {
  totalUsers: number
  activeUsers7d: number
  totalSubscriptions: number
  activeSubscriptions: number
  totalListings: number
  activeListings: number
  totalMatches: number
  activeMatches: number
  completedMatches: number
  totalEscrowAmount: number
  totalPayouts: number
  platformFeesCollected: number
  openDisputes: number
  complianceEvents: number
  newUsers30d: number
  revenue30d: number
}

interface AdminUser {
  id: string
  email: string
  username: string
  displayName: string
  isActive: boolean
  isVerified: boolean
  createdAt: string
  lastLoginAt: string | null
  subscriptionCount: number
  matchCount: number
}

interface Dispute {
  id: string
  matchId: string
  filedById: string
  status: string
  reason: string
  description: string
  createdAt: string
  resolvedAt: string | null
}

interface ActivityItem {
  id: string
  type: string
  title: string
  description: string
  severity: string
  createdAt: string
}

const DEMO_STATS: PlatformStats = {
  totalUsers: 1247,
  activeUsers7d: 438,
  totalSubscriptions: 3891,
  activeSubscriptions: 3204,
  totalListings: 856,
  activeListings: 623,
  totalMatches: 2134,
  activeMatches: 187,
  completedMatches: 1845,
  totalEscrowAmount: 48750.0,
  totalPayouts: 42900.0,
  platformFeesCollected: 5850.0,
  openDisputes: 12,
  complianceEvents: 89,
  newUsers30d: 312,
  revenue30d: 5850.0,
}

const DEMO_USERS: AdminUser[] = [
  { id: 'u1', email: 'alex@example.com', username: 'alexchen', displayName: 'Alex Chen', isActive: true, isVerified: true, createdAt: '2024-01-15T00:00:00Z', lastLoginAt: '2024-08-28T10:00:00Z', subscriptionCount: 3, matchCount: 8 },
  { id: 'u2', email: 'maria@example.com', username: 'mariasantos', displayName: 'Maria Santos', isActive: true, isVerified: true, createdAt: '2024-02-20T00:00:00Z', lastLoginAt: '2024-08-27T15:00:00Z', subscriptionCount: 2, matchCount: 5 },
  { id: 'u3', email: 'james@example.com', username: 'jameswilson', displayName: 'James Wilson', isActive: true, isVerified: false, createdAt: '2024-03-10T00:00:00Z', lastLoginAt: '2024-08-26T08:00:00Z', subscriptionCount: 4, matchCount: 12 },
  { id: 'u4', email: 'spam@fake.com', username: 'suspicioususer', displayName: 'Suspicious User', isActive: false, isVerified: false, createdAt: '2024-08-01T00:00:00Z', lastLoginAt: null, subscriptionCount: 0, matchCount: 0 },
  { id: 'u5', email: 'sarah@example.com', username: 'sarahkim', displayName: 'Sarah Kim', isActive: true, isVerified: true, createdAt: '2024-04-05T00:00:00Z', lastLoginAt: '2024-08-28T12:00:00Z', subscriptionCount: 5, matchCount: 15 },
]

const DEMO_DISPUTES: Dispute[] = [
  { id: 'd1', matchId: 'm1', filedById: 'u2', status: 'open', reason: 'No access provided', description: 'Seller did not provide Spotify access after payment.', createdAt: new Date(Date.now() - 86400000).toISOString(), resolvedAt: null },
  { id: 'd2', matchId: 'm3', filedById: 'u1', status: 'under_review', reason: 'Service down', description: 'Google One storage was full and inaccessible.', createdAt: new Date(Date.now() - 172800000).toISOString(), resolvedAt: null },
  { id: 'd3', matchId: 'm5', filedById: 'u3', status: 'resolved', reason: 'Refund requested', description: 'Buyer no longer needs the subscription seat.', createdAt: new Date(Date.now() - 604800000).toISOString(), resolvedAt: new Date(Date.now() - 518400000).toISOString() },
]

const DEMO_ACTIVITY: ActivityItem[] = [
  { id: 'a1', type: 'risk_alert', title: 'High risk user detected', description: 'User suspicioususer scored 0.92 risk score', severity: 'critical', createdAt: new Date(Date.now() - 3600000).toISOString() },
  { id: 'a2', type: 'circuit_breaker', title: 'Transaction velocity breaker triggered', description: '15 transactions in 30 minutes from user jameswilson', severity: 'high', createdAt: new Date(Date.now() - 7200000).toISOString() },
  { id: 'a3', type: 'tos_violation', title: 'Netflix listing blocked', description: 'User attempted to list Netflix seat sharing', severity: 'medium', createdAt: new Date(Date.now() - 14400000).toISOString() },
  { id: 'a4', type: 'audit_log', title: 'Admin user activated account', description: 'Admin reactivated user sarahkim', severity: 'low', createdAt: new Date(Date.now() - 28800000).toISOString() },
  { id: 'a5', type: 'risk_alert', title: 'Low reputation alert', description: 'User bobsmith dropped below 0.3 reputation score', severity: 'high', createdAt: new Date(Date.now() - 43200000).toISOString() },
]

const REVENUE_DATA = [
  { name: 'Mon', revenue: 420, fees: 50 },
  { name: 'Tue', revenue: 380, fees: 46 },
  { name: 'Wed', revenue: 510, fees: 61 },
  { name: 'Thu', revenue: 470, fees: 56 },
  { name: 'Fri', revenue: 620, fees: 74 },
  { name: 'Sat', revenue: 550, fees: 66 },
  { name: 'Sun', revenue: 390, fees: 47 },
]

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function StatCard({ label, value, change, icon: Icon, color }: {
  label: string; value: string; change?: string; icon: React.ElementType; color: string
}) {
  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-400">{label}</p>
          <p className="mt-1 text-2xl font-bold">{value}</p>
          {change && <p className="mt-1 text-xs text-gray-500">{change}</p>}
        </div>
        <div className={`rounded-lg p-2.5 ${color}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  )
}

function severityColor(severity: string) {
  switch (severity) {
    case 'critical': return 'bg-red-900/30 text-red-400'
    case 'high': return 'bg-orange-900/30 text-orange-400'
    case 'medium': return 'bg-yellow-900/30 text-yellow-400'
    default: return 'bg-gray-800 text-gray-400'
  }
}

function statusColor(status: string) {
  switch (status) {
    case 'open': return 'badge-yellow'
    case 'under_review': return 'badge-blue'
    case 'resolved': return 'badge-green'
    default: return 'badge-blue'
  }
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'disputes' | 'activity'>('overview')
  const [userSearch, setUserSearch] = useState('')
  const stats = DEMO_STATS

  const filteredUsers = useMemo(
    () => DEMO_USERS.filter(
      (u) => u.username.toLowerCase().includes(userSearch.toLowerCase()) ||
             u.email.toLowerCase().includes(userSearch.toLowerCase()) ||
             u.displayName.toLowerCase().includes(userSearch.toLowerCase())
    ),
    [userSearch]
  )

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Admin Dashboard</h2>
        <p className="text-sm text-gray-400">Platform monitoring and management</p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 rounded-lg bg-gray-800 p-1">
        {(['overview', 'users', 'disputes', 'activity'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-vault-600 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total Users" value={stats.totalUsers.toLocaleString()} change={`+${stats.newUsers30d} this month`} icon={Users} color="bg-vault-900/50 text-vault-400" />
            <StatCard label="Revenue (30d)" value={`$${stats.revenue30d.toLocaleString()}`} icon={DollarSign} color="bg-emerald-900/50 text-emerald-400" />
            <StatCard label="Active Matches" value={String(stats.activeMatches)} change={`${stats.completedMatches} completed`} icon={UserPlus} color="bg-purple-900/50 text-purple-400" />
            <StatCard label="Open Disputes" value={String(stats.openDisputes)} icon={AlertTriangle} color="bg-yellow-900/50 text-yellow-400" />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Active Users (7d)" value={String(stats.activeUsers7d)} icon={Activity} color="bg-blue-900/50 text-blue-400" />
            <StatCard label="Active Listings" value={String(stats.activeListings)} icon={Eye} color="bg-cyan-900/50 text-cyan-400" />
            <StatCard label="Platform Fees" value={`$${stats.platformFeesCollected.toLocaleString()}`} icon={CreditCard} color="bg-green-900/50 text-green-400" />
            <StatCard label="Compliance Events" value={String(stats.complianceEvents)} icon={Shield} color="bg-red-900/50 text-red-400" />
          </div>

          {/* Revenue Chart */}
          <div className="card">
            <h3 className="mb-4 text-lg font-semibold">Weekly Revenue</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={REVENUE_DATA}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" fontSize={12} />
                <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }} />
                <Bar dataKey="revenue" fill="#0EA5E9" name="Revenue" radius={[4, 4, 0, 0]} />
                <Bar dataKey="fees" fill="#10B981" name="Fees" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              placeholder="Search users by name or email..."
              className="input pl-10"
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            {filteredUsers.map((user) => (
              <div key={user.id} className="card flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-800 text-sm font-bold">
                    {user.displayName.charAt(0)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium">{user.displayName}</h4>
                      {user.isVerified && <Shield className="h-3.5 w-3.5 text-emerald-400" />}
                    </div>
                    <p className="text-xs text-gray-400">{user.email} · @{user.username}</p>
                    <p className="text-xs text-gray-500">
                      {user.subscriptionCount} subscriptions · {user.matchCount} matches
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs ${user.isActive ? 'text-emerald-400' : 'text-red-400'}`}>
                    {user.isActive ? 'Active' : 'Inactive'}
                  </span>
                  {user.isActive ? (
                    <button className="flex items-center gap-1 rounded-lg bg-red-900/30 px-2.5 py-1 text-xs text-red-400 hover:bg-red-900/50">
                      <Ban className="h-3 w-3" /> Deactivate
                    </button>
                  ) : (
                    <button className="flex items-center gap-1 rounded-lg bg-emerald-900/30 px-2.5 py-1 text-xs text-emerald-400 hover:bg-emerald-900/50">
                      <CheckCircle className="h-3 w-3" /> Activate
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Disputes Tab */}
      {activeTab === 'disputes' && (
        <div className="space-y-4">
          {DEMO_DISPUTES.map((dispute) => (
            <div key={dispute.id} className="card">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium">{dispute.reason}</h4>
                    <span className={statusColor(dispute.status)}>{dispute.status}</span>
                  </div>
                  <p className="mt-1 text-sm text-gray-400">{dispute.description}</p>
                  <p className="mt-2 text-xs text-gray-500">
                    Filed {new Date(dispute.createdAt).toLocaleDateString()}
                    {dispute.resolvedAt && ` · Resolved ${new Date(dispute.resolvedAt).toLocaleDateString()}`}
                  </p>
                </div>
                {dispute.status !== 'resolved' && (
                  <div className="flex gap-2">
                    <button className="btn-secondary text-xs">Review</button>
                    <button className="btn-primary text-xs">Resolve</button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Activity Tab */}
      {activeTab === 'activity' && (
        <div className="space-y-2">
          {DEMO_ACTIVITY.map((item) => (
            <div key={item.id} className="card flex items-start gap-3">
              <span className={`mt-1 inline-block rounded px-2 py-0.5 text-xs font-medium ${severityColor(item.severity)}`}>
                {item.severity}
              </span>
              <div className="flex-1">
                <h4 className="font-medium">{item.title}</h4>
                <p className="text-sm text-gray-400">{item.description}</p>
                <p className="mt-1 text-xs text-gray-500">{timeAgo(item.createdAt)}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
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
