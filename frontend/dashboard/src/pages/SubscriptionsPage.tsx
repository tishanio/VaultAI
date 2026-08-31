import { useEffect, useState } from 'react'
import { Plus, TrendingUp, Clock, BarChart3, AlertTriangle, Loader } from 'lucide-react'
import { useAppStore } from '../store'
import { api, generateDemoSubscriptions, type DemoSubscription } from '../api'
import SubscriptionModal from '../components/SubscriptionModal'

export default function SubscriptionsPage() {
  const demoMode = useAppStore((s) => s.demoMode)
  const [subscriptions, setSubscriptions] = useState<DemoSubscription[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedSub, setSelectedSub] = useState<DemoSubscription | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Fetch subscriptions from API or generate demo data
  const fetchSubscriptions = async () => {
    if (demoMode) {
      setSubscriptions(generateDemoSubscriptions())
      return
    }

    setLoading(true)
    try {
      const { data } = await api.get('/api/v1/subscriptions')
      const mapped: DemoSubscription[] = data.map((s: any) => ({
        id: s.id,
        serviceName: s.service_name,
        serviceCategory: s.service_category,
        serviceLogo: getServiceLogo(s.service_name),
        tier: s.tier,
        status: s.status,
        monthlyCost: s.monthly_cost,
        maxSeats: s.max_seats,
        usedSeats: s.used_seats,
        usagePercentage: s.usage_percentage ?? 0,
      }))
      setSubscriptions(mapped)
    } catch {
      // Fallback to demo data if API is unreachable
      setSubscriptions(generateDemoSubscriptions())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSubscriptions()
  }, [demoMode])

  function getServiceLogo(name: string): string {
    const logos: Record<string, string> = {
      'Spotify': '🎵', 'Google One': '☁️', 'YouTube Premium': '📺',
      'YouTube Music': '🎵', 'Apple Music': '🎵', 'Headspace': '🧘',
      'Calm': '🧘', 'Duolingo': '🦉', 'Microsoft 365': '💼', 'Canva': '🎨',
    }
    return logos[name] || '📦'
  }

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-vault-200">Usage</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">Subscriptions</h2>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Add subscription
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader className="h-6 w-6 animate-spin text-vault-400" />
          <span className="ml-3 text-sm text-slate-400">Loading subscriptions...</span>
        </div>
      )}

      {!loading && subscriptions.length === 0 && (
        <div className="card text-center py-12">
          <p className="text-slate-400 text-lg">No subscriptions yet</p>
          <p className="text-slate-500 text-sm mt-1">Add your first subscription to start sharing unused seats</p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn-primary mt-4"
          >
            <Plus className="h-4 w-4 mr-2 inline" />
            Add your first subscription
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {subscriptions.map((sub) => (
          <div
            key={sub.id}
            onClick={() => setSelectedSub(sub)}
            className={`card cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:border-vault-500/40 ${
              selectedSub?.id === sub.id ? 'border-vault-500/40 ring-1 ring-vault-500/30' : ''
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="text-3xl">{sub.serviceLogo}</span>
                <div>
                  <h3 className="font-semibold text-white">{sub.serviceName}</h3>
                  <p className="text-sm text-slate-400">{sub.tier}</p>
                </div>
              </div>
              <span className="badge-green">{sub.status}</span>
            </div>

            <div className="mt-4 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Monthly cost</span>
                <span className="font-medium text-white">${sub.monthlyCost}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Seats</span>
                <span className="font-medium text-white">
                  {sub.usedSeats}/{sub.maxSeats}
                </span>
              </div>

              <div className="mt-2">
                <div className="mb-1 flex justify-between text-xs text-slate-400">
                  <span>Usage</span>
                  <span>{sub.usagePercentage}%</span>
                </div>
                <div className="h-2.5 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className={`h-full rounded-full transition-all ${
                      sub.usagePercentage < 30
                        ? 'bg-emerald-400'
                        : sub.usagePercentage < 60
                        ? 'bg-amber-400'
                        : 'bg-red-400'
                    }`}
                    style={{ width: `${sub.usagePercentage}%` }}
                  />
                </div>
              </div>
            </div>

            {sub.usagePercentage < 30 && (
              <div className="mt-4 flex items-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-2 text-xs text-emerald-200">
                <TrendingUp className="h-3.5 w-3.5" />
                <span>Shareable — potential savings: ${(sub.monthlyCost * 0.5).toFixed(2)}/mo</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {selectedSub && (
        <div className="card">
          <h3 className="mb-4 text-lg font-semibold text-white">
            {selectedSub.serviceLogo} {selectedSub.serviceName} — Usage analytics
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Clock className="h-4 w-4" /> Avg daily usage
              </div>
              <p className="mt-1 text-2xl font-bold text-white">
                {Math.round(selectedSub.usagePercentage * 24 * 0.3)}min
              </p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <BarChart3 className="h-4 w-4" /> Optimization score
              </div>
              <p className="mt-1 text-2xl font-bold text-white">
                {selectedSub.usagePercentage < 30
                  ? 'Low'
                  : selectedSub.usagePercentage < 60
                  ? 'Medium'
                  : 'High'}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <TrendingUp className="h-4 w-4" /> Potential savings
              </div>
              <p className="mt-1 text-2xl font-bold text-emerald-300">
                ${(selectedSub.monthlyCost * (selectedSub.maxSeats - selectedSub.usedSeats) * 0.15).toFixed(2)}/mo
              </p>
            </div>
          </div>

          {selectedSub.usagePercentage < 25 && (
            <div className="mt-4 flex items-center gap-2 rounded-2xl border border-amber-400/20 bg-amber-500/10 p-3 text-sm text-amber-200">
              <AlertTriangle className="h-4 w-4" />
              <span>
                Low usage detected. You could save{' '}
                <strong>${(selectedSub.monthlyCost * 0.4).toFixed(2)}/mo</strong>{' '}
                by sharing {selectedSub.maxSeats - selectedSub.usedSeats} unused seat(s).
                <button className="ml-2 text-vault-200 underline">Create listing →</button>
              </span>
            </div>
          )}
        </div>
      )}

      <SubscriptionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={(newSub) => {
          // Immediately show the new subscription in the list
          if (newSub) {
            setSubscriptions((prev) => [
              {
                id: newSub.id,
                serviceName: newSub.service_name,
                serviceCategory: newSub.service_category,
                serviceLogo: getServiceLogo(newSub.service_name),
                tier: newSub.tier,
                status: newSub.status,
                monthlyCost: newSub.monthly_cost,
                maxSeats: newSub.max_seats,
                usedSeats: newSub.used_seats,
                usagePercentage: 0,
              },
              ...prev,
            ])
          } else {
            // In demo mode or if no data returned, refresh from source
            fetchSubscriptions()
          }
        }}
      />
    </div>
  )
}
