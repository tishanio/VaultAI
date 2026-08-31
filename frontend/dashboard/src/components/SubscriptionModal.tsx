import { useState } from 'react'
import { X, Loader } from 'lucide-react'
import { api } from '../api'
import { useAppStore } from '../store'

interface SubscriptionModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: (createdSub?: any) => void
}

const SERVICES = [
  { name: 'Spotify', category: 'music', maxSeats: 6, logo: '🎵' },
  { name: 'Google One', category: 'cloud_storage', maxSeats: 5, logo: '☁️' },
  { name: 'YouTube Premium', category: 'streaming', maxSeats: 5, logo: '📺' },
  { name: 'YouTube Music', category: 'music', maxSeats: 5, logo: '🎵' },
  { name: 'Apple Music', category: 'music', maxSeats: 6, logo: '🎵' },
  { name: 'Headspace', category: 'wellness', maxSeats: 6, logo: '🧘' },
  { name: 'Calm', category: 'wellness', maxSeats: 6, logo: '🧘' },
  { name: 'Duolingo', category: 'education', maxSeats: 6, logo: '🦉' },
  { name: 'Microsoft 365', category: 'productivity', maxSeats: 6, logo: '💼' },
  { name: 'Canva', category: 'design', maxSeats: 5, logo: '🎨' },
]

const TIERS = ['premium', 'family']

export default function SubscriptionModal({ isOpen, onClose, onSuccess }: SubscriptionModalProps) {
  const [serviceName, setServiceName] = useState('')
  const [tier, setTier] = useState('family')
  const [monthlyCost, setMonthlyCost] = useState('')
  const [maxSeats, setMaxSeats] = useState('2')
  const [billingCycleDay, setBillingCycleDay] = useState('1')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const demoMode = useAppStore((s) => s.demoMode)

  if (!isOpen) return null

  const selectedService = SERVICES.find((s) => s.name === serviceName)
  const maxSeatsLimit = selectedService?.maxSeats || 6

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (!serviceName || !monthlyCost || !maxSeats) {
        throw new Error('Please fill in all required fields')
      }

      const seatsNum = parseInt(maxSeats, 10)
      if (seatsNum < 2 || seatsNum > maxSeatsLimit) {
        throw new Error(`Seats must be between 2 and ${maxSeatsLimit}`)
      }

      const costNum = parseFloat(monthlyCost)
      if (costNum <= 0) {
        throw new Error('Monthly cost must be greater than 0')
      }

      const billingDayNum = parseInt(billingCycleDay, 10)
      if (billingDayNum < 1 || billingDayNum > 28) {
        throw new Error('Billing day must be between 1 and 28')
      }

      // In demo mode, create locally without hitting the API
      if (demoMode) {
        const localSub = {
          id: `sub_${Date.now()}`,
          service_name: serviceName,
          service_category: selectedService?.category || 'other',
          tier,
          status: 'active',
          monthly_cost: costNum,
          max_seats: seatsNum,
          used_seats: 0,
          billing_cycle_day: billingDayNum,
        }
        resetForm()
        onClose()
        onSuccess?.(localSub)
        return
      }

      // Real API call
      const response = await api.post('/api/v1/subscriptions', {
        service_name: serviceName,
        tier,
        monthly_cost: costNum,
        max_seats: seatsNum,
        billing_cycle_day: billingDayNum,
      })

      if (response.status === 201) {
        resetForm()
        onClose()
        onSuccess?.(response.data)
      }
    } catch (err: any) {
      // If API is unreachable in non-demo mode, fall back to local creation
      if (!demoMode && (err.code === 'ERR_NETWORK' || err.code === 'ECONNABORTED' || !err.response)) {
        const localSub = {
          id: `sub_${Date.now()}`,
          service_name: serviceName,
          service_category: selectedService?.category || 'other',
          tier,
          status: 'active',
          monthly_cost: parseFloat(monthlyCost),
          max_seats: parseInt(maxSeats, 10),
          used_seats: 0,
          billing_cycle_day: parseInt(billingCycleDay, 10),
        }
        resetForm()
        onClose()
        onSuccess?.(localSub)
        return
      }
      setError(err.response?.data?.detail || err.message || 'Failed to create subscription')
    } finally {
      setLoading(false)
    }
  }

  function resetForm() {
    setServiceName('')
    setTier('family')
    setMonthlyCost('')
    setMaxSeats('2')
    setBillingCycleDay('1')
    setError('')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center">
      <div className="panel w-full max-w-md transform rounded-t-3xl border-0 sm:rounded-3xl">
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Add Subscription</h2>
            <p className="text-sm text-slate-400">Track a subscription you own</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 hover:bg-slate-800 transition-colors"
            disabled={loading}
          >
            <X className="h-5 w-5 text-slate-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-4">
          {/* Service Selection */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">Service *</label>
            <select
              value={serviceName}
              onChange={(e) => setServiceName(e.target.value)}
              className="input w-full"
              required
              disabled={loading}
            >
              <option value="">Select a service</option>
              {SERVICES.map((s) => (
                <option key={s.name} value={s.name}>
                  {s.logo} {s.name}
                </option>
              ))}
            </select>
          </div>

          {/* Tier Selection */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">Plan Tier *</label>
            <div className="grid grid-cols-2 gap-3">
              {TIERS.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTier(t)}
                  disabled={loading}
                  className={`rounded-xl border-2 px-3 py-2 text-sm font-medium transition-colors ${
                    tier === t
                      ? 'border-vault-500/40 bg-vault-500/10 text-vault-200'
                      : 'border-slate-700 bg-slate-900 text-slate-400 hover:border-slate-600'
                  }`}
                >
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Monthly Cost */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">Monthly Cost $ *</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={monthlyCost}
              onChange={(e) => setMonthlyCost(e.target.value)}
              className="input w-full"
              placeholder="e.g., 16.99"
              required
              disabled={loading}
            />
          </div>

          {/* Max Seats */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Total Seats (2-{maxSeatsLimit}) *
            </label>
            <input
              type="number"
              min="2"
              max={maxSeatsLimit}
              value={maxSeats}
              onChange={(e) => setMaxSeats(e.target.value)}
              className="input w-full"
              placeholder="e.g., 4"
              required
              disabled={loading}
            />
          </div>

          {/* Billing Cycle Day */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Billing Day (1-28) *
            </label>
            <input
              type="number"
              min="1"
              max="28"
              value={billingCycleDay}
              onChange={(e) => setBillingCycleDay(e.target.value)}
              className="input w-full"
              placeholder="e.g., 15"
              required
              disabled={loading}
            />
          </div>

          {/* Error Message */}
          {error && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !serviceName}
              className="btn-primary flex flex-1 items-center justify-center gap-2"
            >
              {loading && <Loader className="h-4 w-4 animate-spin" />}
              {loading ? 'Adding...' : 'Add Subscription'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
