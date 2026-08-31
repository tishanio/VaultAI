import { useMemo, useState } from 'react'
import {
  Bell,
  BellOff,
  CheckCheck,
  MessageSquare,
  CreditCard,
  Shield,
  Trash2,
} from 'lucide-react'

interface Notification {
  id: string
  channel: string
  title: string
  body: string
  is_read: boolean
  created_at: string
  type: 'match' | 'payment' | 'compliance' | 'system'
}

const DEMO_NOTIFICATIONS: Notification[] = [
  {
    id: 'n1',
    channel: 'in_app',
    title: 'New Match Proposal',
    body: 'Alex Chen wants to share their Spotify Family seat with you for $4.50/mo.',
    is_read: false,
    created_at: new Date(Date.now() - 1800000).toISOString(),
    type: 'match',
  },
  {
    id: 'n2',
    channel: 'in_app',
    title: 'Escrow Funded',
    body: 'Payment of $4.50 has been secured in escrow for your Spotify match.',
    is_read: false,
    created_at: new Date(Date.now() - 7200000).toISOString(),
    type: 'payment',
  },
  {
    id: 'n3',
    channel: 'in_app',
    title: 'Match Accepted',
    body: 'Your match with Maria Santos for Google One has been accepted! Access details will follow.',
    is_read: true,
    created_at: new Date(Date.now() - 86400000).toISOString(),
    type: 'match',
  },
  {
    id: 'n4',
    channel: 'in_app',
    title: 'Compliance Alert',
    body: 'Netflix is not supported on Vault due to Terms of Service restrictions. Your listing has been removed.',
    is_read: true,
    created_at: new Date(Date.now() - 172800000).toISOString(),
    type: 'compliance',
  },
  {
    id: 'n5',
    channel: 'in_app',
    title: 'Payout Processed',
    body: '$3.96 has been transferred to your bank account.',
    is_read: true,
    created_at: new Date(Date.now() - 259200000).toISOString(),
    type: 'payment',
  },
  {
    id: 'n6',
    channel: 'in_app',
    title: 'Usage Report Ready',
    body: 'Your monthly usage report for Spotify is ready. You used 32% of your capacity — consider sharing.',
    is_read: true,
    created_at: new Date(Date.now() - 345600000).toISOString(),
    type: 'system',
  },
]

function NotificationIcon({ type }: { type: string }) {
  switch (type) {
    case 'match':
      return <MessageSquare className="h-4 w-4 text-vault-400" />
    case 'payment':
      return <CreditCard className="h-4 w-4 text-emerald-400" />
    case 'compliance':
      return <Shield className="h-4 w-4 text-yellow-400" />
    default:
      return <Bell className="h-4 w-4 text-gray-400" />
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

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>(DEMO_NOTIFICATIONS)
  const [filter, setFilter] = useState<'all' | 'unread'>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')

  const filtered = useMemo(() => {
    let result = notifications
    if (filter === 'unread') result = result.filter((n) => !n.is_read)
    if (typeFilter !== 'all') result = result.filter((n) => n.type === typeFilter)
    return result
  }, [notifications, filter, typeFilter])

  const unreadCount = notifications.filter((n) => !n.is_read).length

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
  }

  const markRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
    )
  }

  const deleteNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Notifications</h2>
          <p className="text-sm text-gray-400">
            {unreadCount > 0 ? `You have ${unreadCount} unread notification${unreadCount > 1 ? 's' : ''}` : 'All caught up!'}
          </p>
        </div>
        <button
          onClick={markAllRead}
          className="btn-secondary flex items-center gap-2"
          disabled={unreadCount === 0}
        >
          <CheckCheck className="h-4 w-4" />
          Mark all read
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-1 rounded-lg bg-gray-800 p-1">
          <button
            onClick={() => setFilter('all')}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              filter === 'all' ? 'bg-vault-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            All ({notifications.length})
          </button>
          <button
            onClick={() => setFilter('unread')}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              filter === 'unread' ? 'bg-vault-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            Unread ({unreadCount})
          </button>
        </div>

        <select
          className="input w-auto"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        >
          <option value="all">All Types</option>
          <option value="match">Matches</option>
          <option value="payment">Payments</option>
          <option value="compliance">Compliance</option>
          <option value="system">System</option>
        </select>
      </div>

      {/* Notifications List */}
      <div className="space-y-2">
        {filtered.map((notification) => (
          <div
            key={notification.id}
            className={`card flex items-start gap-4 transition-all ${
              !notification.is_read ? 'border-l-2 border-l-vault-500 bg-gray-900/50' : ''
            }`}
          >
            <div className={`mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
              !notification.is_read ? 'bg-vault-900/50' : 'bg-gray-800'
            }`}>
              <NotificationIcon type={notification.type} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <h4 className={`font-medium ${!notification.is_read ? 'text-white' : 'text-gray-300'}`}>
                  {notification.title}
                </h4>
                <span className="text-xs text-gray-500 shrink-0">
                  {timeAgo(notification.created_at)}
                </span>
              </div>
              <p className="mt-1 text-sm text-gray-400">{notification.body}</p>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              {!notification.is_read && (
                <button
                  onClick={() => markRead(notification.id)}
                  className="rounded p-1 text-gray-500 hover:bg-gray-800 hover:text-gray-300"
                  title="Mark as read"
                >
                  <CheckCheck className="h-4 w-4" />
                </button>
              )}
              <button
                onClick={() => deleteNotification(notification.id)}
                className="rounded p-1 text-gray-500 hover:bg-gray-800 hover:text-red-400"
                title="Delete"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="card text-center">
          <BellOff className="mx-auto h-12 w-12 text-gray-600" />
          <h3 className="mt-3 text-lg font-medium text-gray-400">
            {filter === 'unread' ? 'No unread notifications' : 'No notifications'}
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            {filter === 'unread'
              ? "You're all caught up!"
              : "You'll see notifications about matches, payments, and compliance here."}
          </p>
        </div>
      )}
    </div>
  )
}
