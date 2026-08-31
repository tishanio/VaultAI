import { useState, useEffect } from 'react'
import {
  Loader,
  Zap,
} from 'lucide-react'
import { useAppStore } from '../store'
import { api } from '../api'

interface Notification {
  id: string
  channel: string
  title: string
  body: string
  is_read: boolean
  created_at: string
}

export default function NotificationsPage() {
  const demoMode = useAppStore((s) => s.demoMode)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const { data } = await api.get('/api/v1/notifications').catch(() => ({ data: [] }))
        if (Array.isArray(data)) {
          setNotifications(data)
        }
      } catch {
        setNotifications([])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [demoMode])

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Notifications</h1>
        <p className="text-sm text-slate-400">Stay updated on matches and payments</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader className="h-6 w-6 animate-spin text-vault-400" />
        </div>
      ) : notifications.length === 0 ? (
        <div className="text-center py-12 text-slate-400">
          <Zap className="h-10 w-10 mx-auto opacity-30 mb-3" />
          <p className="font-medium">No notifications</p>
          <p className="text-sm mt-1">You're all caught up!</p>
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map((notif) => (
            <div
              key={notif.id}
              className={`rounded-xl border p-3 flex items-start gap-3 ${
                notif.is_read
                  ? 'border-slate-800/50 bg-slate-900/30'
                  : 'border-vault-500/20 bg-vault-500/5'
              }`}
            >
              <div className={`mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full ${notif.is_read ? 'bg-slate-600' : 'bg-vault-400'}`} />
              <div className="flex-1">
                <p className="text-sm font-medium text-white">{notif.title}</p>
                <p className="text-xs text-slate-400 mt-0.5">{notif.body}</p>
                <p className="text-[10px] text-slate-500 mt-1">
                  {notif.channel} • {new Date(notif.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
