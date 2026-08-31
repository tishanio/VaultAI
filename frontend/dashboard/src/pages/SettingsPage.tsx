import { useState } from 'react'
import {
  User,
  Bell,
  Shield,
  Zap,
  Mail,
  MessageCircle,
  Smartphone,
} from 'lucide-react'
import { useAppStore } from '../store'

export default function SettingsPage() {
  const { demoMode, toggleDemoMode } = useAppStore()
  const [notifications, setNotifications] = useState({
    email: true,
    push: true,
    telegram: false,
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Settings</h2>
        <p className="text-sm text-gray-400">Manage your account and preferences</p>
      </div>

      {/* Profile */}
      <div className="card">
        <div className="mb-4 flex items-center gap-2">
          <User className="h-5 w-5 text-vault-400" />
          <h3 className="text-lg font-semibold">Profile</h3>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm text-gray-400">Display Name</label>
            <input className="input" defaultValue="Demo User" />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-400">Email</label>
            <input className="input" defaultValue="demo@vault.app" />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-400">Username</label>
            <input className="input" defaultValue="demo_user" />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-400">Timezone</label>
            <select className="input" defaultValue="UTC">
              <option>UTC</option>
              <option>America/New_York</option>
              <option>America/Chicago</option>
              <option>America/Los_Angeles</option>
              <option>Europe/London</option>
              <option>Asia/Tokyo</option>
            </select>
          </div>
        </div>
        <button className="btn-primary mt-4">Save Changes</button>
      </div>

      {/* Demo Mode */}
      <div className="card">
        <div className="mb-4 flex items-center gap-2">
          <Zap className="h-5 w-5 text-emerald-400" />
          <h3 className="text-lg font-semibold">Demo Mode</h3>
        </div>
        <p className="mb-4 text-sm text-gray-400">
          Toggle demo mode to show simulated data for hackathon presentations.
          This fills the dashboard with realistic mock data for judges.
        </p>
        <div className="flex items-center gap-4">
          <button
            onClick={toggleDemoMode}
            className={`relative h-8 w-14 rounded-full transition-colors ${
              demoMode ? 'bg-emerald-600' : 'bg-gray-700'
            }`}
          >
            <div
              className={`absolute top-1 h-6 w-6 rounded-full bg-white transition-transform ${
                demoMode ? 'translate-x-7' : 'translate-x-1'
              }`}
            />
          </button>
          <div>
            <p className="font-medium">{demoMode ? 'Demo Mode ON' : 'Demo Mode OFF'}</p>
            <p className="text-xs text-gray-500">
              {demoMode ? 'Showing simulated data' : 'Using live data from API'}
            </p>
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className="card">
        <div className="mb-4 flex items-center gap-2">
          <Bell className="h-5 w-5 text-yellow-400" />
          <h3 className="text-lg font-semibold">Notifications</h3>
        </div>
        <div className="space-y-3">
          {[
            { key: 'email' as const, icon: Mail, label: 'Email Notifications', desc: 'Receive updates via email' },
            { key: 'push' as const, icon: Smartphone, label: 'Push Notifications', desc: 'Browser/mobile push alerts' },
            { key: 'telegram' as const, icon: MessageCircle, label: 'Telegram Bot', desc: 'Get alerts via Telegram' },
          ].map(({ key, icon: Icon, label, desc }) => (
            <div key={key} className="flex items-center justify-between rounded-lg bg-gray-800/50 p-3">
              <div className="flex items-center gap-3">
                <Icon className="h-5 w-5 text-gray-400" />
                <div>
                  <p className="text-sm font-medium">{label}</p>
                  <p className="text-xs text-gray-500">{desc}</p>
                </div>
              </div>
              <button
                onClick={() =>
                  setNotifications((prev) => ({ ...prev, [key]: !prev[key] }))
                }
                className={`relative h-6 w-11 rounded-full transition-colors ${
                  notifications[key] ? 'bg-vault-600' : 'bg-gray-700'
                }`}
              >
                <div
                  className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                    notifications[key] ? 'translate-x-5' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Security */}
      <div className="card">
        <div className="mb-4 flex items-center gap-2">
          <Shield className="h-5 w-5 text-purple-400" />
          <h3 className="text-lg font-semibold">Security</h3>
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between rounded-lg bg-gray-800/50 p-3">
            <div>
              <p className="text-sm font-medium">Two-Factor Authentication</p>
              <p className="text-xs text-gray-500">Add an extra layer of security</p>
            </div>
            <button className="btn-secondary text-sm">Enable</button>
          </div>
          <div className="flex items-center justify-between rounded-lg bg-gray-800/50 p-3">
            <div>
              <p className="text-sm font-medium">KYC Verification</p>
              <p className="text-xs text-gray-500">Verify your identity to build trust</p>
            </div>
            <span className="badge-green">Verified ✓</span>
          </div>
          <div className="flex items-center justify-between rounded-lg bg-gray-800/50 p-3">
            <div>
              <p className="text-sm font-medium">Change Password</p>
              <p className="text-xs text-gray-500">Update your account password</p>
            </div>
            <button className="btn-secondary text-sm">Change</button>
          </div>
        </div>
      </div>
    </div>
  )
}
