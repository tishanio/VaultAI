import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import {
  TrendingUp,
  DollarSign,
  Users,
  Zap,
  ArrowUpRight,
  Shield,
} from 'lucide-react'
import { useAppStore } from '../store'
import {
  generateDemoDashboard,
  generateDemoSubscriptions,
  type DemoDashboardData,
  type DemoSubscription,
} from '../api'

function StatCard({
  label,
  value,
  change,
  icon: Icon,
  color,
}: {
  label: string
  value: string
  change?: string
  icon: React.ElementType
  color: string
}) {
  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-400">{label}</p>
          <p className="mt-1 text-2xl font-bold">{value}</p>
          {change && (
            <p className="mt-1 flex items-center text-xs text-emerald-400">
              <ArrowUpRight className="mr-0.5 h-3 w-3" />
              {change}
            </p>
          )}
        </div>
        <div className={`rounded-lg p-2.5 ${color}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const demoMode = useAppStore((s) => s.demoMode)

  const data: DemoDashboardData = useMemo(
    () => (demoMode ? generateDemoDashboard() : generateDemoDashboard()),
    [demoMode]
  )

  const subscriptions: DemoSubscription[] = useMemo(
    () => (demoMode ? generateDemoSubscriptions() : []),
    [demoMode]
  )

  return (
    <div className="space-y-6 p-4 sm:p-6">
      {demoMode && (
        <div className="panel border-emerald-500/20 bg-emerald-500/10 p-4">
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-emerald-300" />
            <p className="text-sm text-emerald-200">
              <strong>Demo Mode Active</strong> — Showing simulated data. Toggle in the header to switch to live data.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Active Subscriptions"
          value={String(data.totalSubscriptions)}
          change="+1 this month"
          icon={Users}
          color="bg-vault-500/15 text-vault-200"
        />
        <StatCard
          label="Monthly Cost"
          value={`$${data.totalMonthlyCost.toFixed(2)}`}
          icon={DollarSign}
          color="bg-violet-500/15 text-violet-200"
        />
        <StatCard
          label="Monthly Savings"
          value={`$${data.totalSavings.toFixed(2)}`}
          change="+12% vs last month"
          icon={TrendingUp}
          color="bg-emerald-500/15 text-emerald-200"
        />
        <StatCard
          label="Trust Score"
          value={`${(data.reputationScore * 100).toFixed(0)}%`}
          change="Gold tier"
          icon={Shield}
          color="bg-amber-500/15 text-amber-200"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="card">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Weekly usage</h3>
            <span className="rounded-full border border-vault-500/20 bg-vault-500/10 px-2.5 py-1 text-[10px] uppercase tracking-[0.2em] text-vault-200">
              Minutes
            </span>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.usageChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94A3B8" fontSize={12} />
              <YAxis stroke="#94A3B8" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  borderRadius: '12px',
                  color: '#e2e8f0',
                }}
              />
              <Bar dataKey="usage" fill="#38bdf8" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Savings by day</h3>
            <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2.5 py-1 text-[10px] uppercase tracking-[0.2em] text-emerald-200">
              $ value
            </span>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.usageChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94A3B8" fontSize={12} />
              <YAxis stroke="#94A3B8" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  borderRadius: '12px',
                  color: '#e2e8f0',
                }}
              />
              <Bar dataKey="savings" fill="#34d399" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="card">
          <h3 className="mb-4 text-lg font-semibold text-white">Your subscriptions</h3>
          <div className="space-y-3">
            {subscriptions.map((sub) => (
              <div
                key={sub.id}
                className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-900/70 p-3"
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{sub.serviceLogo}</span>
                  <div>
                    <p className="font-medium text-white">{sub.serviceName}</p>
                    <p className="text-xs text-slate-400">
                      {sub.tier} • {sub.usedSeats}/{sub.maxSeats} seats
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-medium text-white">${sub.monthlyCost}/mo</p>
                  <p className="text-xs text-slate-400">{sub.usagePercentage}% used</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3 className="mb-4 text-lg font-semibold text-white">Recent activity</h3>
          <div className="space-y-3">
            {data.recentActivity.map((activity) => (
              <div
                key={activity.id}
                className="flex items-start gap-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-3"
              >
                <div
                  className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${
                    activity.type === 'match'
                      ? 'bg-vault-400'
                      : activity.type === 'payment'
                      ? 'bg-emerald-400'
                      : activity.type === 'payout'
                      ? 'bg-amber-400'
                      : 'bg-violet-400'
                  }`}
                />
                <div className="flex-1">
                  <p className="text-sm text-slate-200">{activity.message}</p>
                  <p className="mt-1 text-xs text-slate-500">{activity.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
