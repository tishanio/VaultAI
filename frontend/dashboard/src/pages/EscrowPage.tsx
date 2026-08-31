import { useState, useEffect } from 'react'
import {
  Loader,
  Zap,
} from 'lucide-react'
import { useAppStore } from '../store'
import { api } from '../api'

interface Escrow {
  id: string
  match_id: string
  status: string
  amount: number
  platform_fee: number
  seller_payout: number
  fee_percentage: number
  currency: string
  funded_at: string | null
  released_at: string | null
  created_at: string
}

const STATUS_COLORS: Record<string, string> = {
  created: 'bg-blue-500/15 text-blue-400',
  funded: 'bg-amber-500/15 text-amber-400',
  held: 'bg-violet-500/15 text-violet-400',
  released: 'bg-emerald-500/15 text-emerald-400',
  refunded: 'bg-red-500/15 text-red-400',
}

const STATUS_ICONS: Record<string, string> = {
  created: 'Created',
  funded: 'Funded',
  held: 'Held in Escrow',
  released: 'Released',
  refunded: 'Refunded',
}

export default function EscrowPage() {
  const demoMode = useAppStore((s) => s.demoMode)
  const [escrows, setEscrows] = useState<Escrow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        // Try to fetch escrows - may not exist as a standalone endpoint
        const { data } = await api.get('/api/v1/escrow').catch(() => ({ data: [] }))
        if (Array.isArray(data)) {
          setEscrows(data)
        }
      } catch {
        setEscrows([])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [demoMode])

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Escrow & Payments</h1>
        <p className="text-sm text-slate-400">Track your payment transactions</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader className="h-6 w-6 animate-spin text-vault-400" />
        </div>
      ) : escrows.length === 0 ? (
        <div className="text-center py-12 text-slate-400">
          <Zap className="h-10 w-10 mx-auto opacity-30 mb-3" />
          <p className="font-medium">No transactions yet</p>
          <p className="text-sm mt-1">Accept a match and complete payment to see transactions here</p>
        </div>
      ) : (
        <div className="space-y-3">
          {escrows.map((escrow) => (
            <div
              key={escrow.id}
              className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <span className={`px-2 py-0.5 rounded-md text-[10px] font-medium ${STATUS_COLORS[escrow.status] || 'bg-slate-700/30 text-slate-400'}`}>
                  {STATUS_ICONS[escrow.status] || escrow.status}
                </span>
                <span className="text-xs text-slate-500">
                  {new Date(escrow.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-4 mt-3">
                <div>
                  <p className="text-[10px] text-slate-500 uppercase">Amount</p>
                  <p className="text-sm font-bold text-white">${escrow.amount.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 uppercase">Platform Fee</p>
                  <p className="text-sm font-bold text-slate-300">${escrow.platform_fee.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 uppercase">Seller Payout</p>
                  <p className="text-sm font-bold text-emerald-400">${escrow.seller_payout.toFixed(2)}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
