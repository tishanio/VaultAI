import { useState } from 'react'
import {
  User,
  Shield,
  Star,
  MapPin,
  Clock,
  CheckCircle,
  Camera,
  Edit3,
  Save,
  X,
  Award,
  TrendingUp,
  MessageSquare,
  FileText,
} from 'lucide-react'

// ---------------------------------------------------------------------------
// Demo Data
// ---------------------------------------------------------------------------

interface UserProfile {
  id: string
  email: string
  username: string
  displayName: string
  avatarUrl: string | null
  latitude: number | null
  longitude: number | null
  timezone: string
  locale: string
  isVerified: boolean
  createdAt: string
  lastLoginAt: string
}

interface ReputationData {
  overallScore: number
  reliabilityScore: number
  communicationScore: number
  paymentScore: number
  totalTransactions: number
  positiveReviews: number
  negativeReviews: number
  trustTier: string
}

interface KYCStatus {
  status: 'not_started' | 'pending' | 'verified' | 'rejected'
  documentType: string | null
  verifiedAt: string | null
  expiresAt: string | null
}

const DEMO_PROFILE: UserProfile = {
  id: 'u1',
  email: 'alex@example.com',
  username: 'alexchen',
  displayName: 'Alex Chen',
  avatarUrl: null,
  latitude: 37.7749,
  longitude: -122.4194,
  timezone: 'America/Los_Angeles',
  locale: 'en-US',
  isVerified: true,
  createdAt: '2024-01-15T00:00:00Z',
  lastLoginAt: new Date(Date.now() - 3600000).toISOString(),
}

const DEMO_REPUTATION: ReputationData = {
  overallScore: 0.87,
  reliabilityScore: 0.92,
  communicationScore: 0.85,
  paymentScore: 0.88,
  totalTransactions: 23,
  positiveReviews: 21,
  negativeReviews: 2,
  trustTier: 'gold',
}

const DEMO_KYC: KYCStatus = {
  status: 'verified',
  documentType: 'passport',
  verifiedAt: '2024-02-01T00:00:00Z',
  expiresAt: '2025-02-01T00:00:00Z',
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function tierColor(tier: string) {
  switch (tier) {
    case 'platinum': return 'text-gray-300 bg-gray-700/50'
    case 'gold': return 'text-yellow-400 bg-yellow-900/30'
    case 'silver': return 'text-gray-400 bg-gray-700/50'
    default: return 'text-amber-600 bg-amber-900/30'
  }
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  const percentage = Math.round(score * 100)
  const color = score >= 0.8 ? 'bg-emerald-500' : score >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="text-gray-400">{label}</span>
        <span className="font-medium">{percentage}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-gray-800">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ProfilePage() {
  const [isEditing, setIsEditing] = useState(false)
  const [profile, setProfile] = useState(DEMO_PROFILE)
  const [editForm, setEditForm] = useState({
    displayName: DEMO_PROFILE.displayName,
    timezone: DEMO_PROFILE.timezone,
    locale: DEMO_PROFILE.locale,
  })

  const reputation = DEMO_REPUTATION
  const kyc = DEMO_KYC

  const handleSave = () => {
    setProfile((prev) => ({
      ...prev,
      displayName: editForm.displayName,
      timezone: editForm.timezone,
      locale: editForm.locale,
    }))
    setIsEditing(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Profile</h2>
        <p className="text-sm text-gray-400">Manage your account and verification status</p>
      </div>

      {/* Profile Header */}
      <div className="card">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-5">
            <div className="relative">
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-vault-900/50 text-3xl font-bold text-vault-400">
                {profile.displayName.charAt(0)}
              </div>
              {isEditing && (
                <button className="absolute bottom-0 right-0 rounded-full bg-gray-700 p-1.5 text-gray-300 hover:bg-gray-600">
                  <Camera className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
            <div>
              {isEditing ? (
                <input
                  className="input mb-2"
                  value={editForm.displayName}
                  onChange={(e) => setEditForm((f) => ({ ...f, displayName: e.target.value }))}
                />
              ) : (
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-bold">{profile.displayName}</h3>
                  {profile.isVerified && (
                    <span className="flex items-center gap-1 rounded-full bg-emerald-900/30 px-2 py-0.5 text-xs text-emerald-400">
                      <CheckCircle className="h-3 w-3" /> Verified
                    </span>
                  )}
                </div>
              )}
              <p className="text-sm text-gray-400">@{profile.username}</p>
              <p className="text-xs text-gray-500">{profile.email}</p>
            </div>
          </div>
          <div className="flex gap-2">
            {isEditing ? (
              <>
                <button onClick={handleSave} className="btn-primary flex items-center gap-1.5">
                  <Save className="h-4 w-4" /> Save
                </button>
                <button onClick={() => setIsEditing(false)} className="btn-secondary flex items-center gap-1.5">
                  <X className="h-4 w-4" /> Cancel
                </button>
              </>
            ) : (
              <button onClick={() => setIsEditing(true)} className="btn-secondary flex items-center gap-1.5">
                <Edit3 className="h-4 w-4" /> Edit Profile
              </button>
            )}
          </div>
        </div>

        {/* Account Info */}
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="flex items-center gap-2 rounded-lg bg-gray-800/50 p-3 text-sm">
            <MapPin className="h-4 w-4 text-gray-400" />
            <div>
              <p className="text-gray-400">Location</p>
              <p className="font-medium">San Francisco, CA</p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-lg bg-gray-800/50 p-3 text-sm">
            <Clock className="h-4 w-4 text-gray-400" />
            <div>
              <p className="text-gray-400">Timezone</p>
              {isEditing ? (
                <select
                  className="input mt-1 py-1 text-xs"
                  value={editForm.timezone}
                  onChange={(e) => setEditForm((f) => ({ ...f, timezone: e.target.value }))}
                >
                  <option value="America/Los_Angeles">Pacific Time</option>
                  <option value="America/New_York">Eastern Time</option>
                  <option value="UTC">UTC</option>
                  <option value="Europe/London">London</option>
                </select>
              ) : (
                <p className="font-medium">{profile.timezone}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-lg bg-gray-800/50 p-3 text-sm">
            <User className="h-4 w-4 text-gray-400" />
            <div>
              <p className="text-gray-400">Member Since</p>
              <p className="font-medium">{new Date(profile.createdAt).toLocaleDateString()}</p>
            </div>
          </div>
        </div>
      </div>

      {/* KYC Verification */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="h-5 w-5 text-vault-400" />
            <h3 className="text-lg font-semibold">Identity Verification (KYC)</h3>
          </div>
          <span className={
            kyc.status === 'verified'
              ? 'badge-green'
              : kyc.status === 'pending'
              ? 'badge-yellow'
              : 'badge-red'
          }>
            {kyc.status === 'verified' && <CheckCircle className="mr-1 inline h-3 w-3" />}
            {kyc.status}
          </span>
        </div>
        <div className="mt-4 rounded-lg bg-gray-800/50 p-4">
          {kyc.status === 'verified' ? (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Document Type</span>
                <span className="capitalize">{kyc.documentType}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Verified On</span>
                <span>{kyc.verifiedAt ? new Date(kyc.verifiedAt).toLocaleDateString() : '—'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Expires</span>
                <span>{kyc.expiresAt ? new Date(kyc.expiresAt).toLocaleDateString() : '—'}</span>
              </div>
            </div>
          ) : kyc.status === 'not_started' ? (
            <div className="text-center">
              <FileText className="mx-auto h-8 w-8 text-gray-500" />
              <p className="mt-2 text-sm text-gray-400">
                Verify your identity to unlock higher trust tiers and transaction limits.
              </p>
              <button className="btn-primary mt-3">Start Verification</button>
            </div>
          ) : (
            <div className="text-center">
              <Clock className="mx-auto h-8 w-8 text-yellow-400" />
              <p className="mt-2 text-sm text-gray-400">
                Your verification is being reviewed. This usually takes 1-2 business days.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Reputation Score */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Star className="h-5 w-5 text-yellow-400" />
            <h3 className="text-lg font-semibold">Reputation Score</h3>
          </div>
          <span className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${tierColor(reputation.trustTier)}`}>
            <Award className="h-4 w-4" />
            {reputation.trustTier.charAt(0).toUpperCase() + reputation.trustTier.slice(1)} Tier
          </span>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <div className="mb-4 text-center">
              <p className="text-4xl font-bold text-vault-400">
                {Math.round(reputation.overallScore * 100)}%
              </p>
              <p className="text-sm text-gray-400">Overall Score</p>
            </div>
            <div className="space-y-3">
              <ScoreBar label="Reliability" score={reputation.reliabilityScore} />
              <ScoreBar label="Communication" score={reputation.communicationScore} />
              <ScoreBar label="Payment" score={reputation.paymentScore} />
            </div>
          </div>
          <div className="space-y-3">
            <div className="rounded-lg bg-gray-800/50 p-4">
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <MessageSquare className="h-4 w-4" /> Reviews
              </div>
              <div className="mt-2 flex items-center gap-4">
                <span className="text-emerald-400">👍 {reputation.positiveReviews}</span>
                <span className="text-red-400">👎 {reputation.negativeReviews}</span>
              </div>
            </div>
            <div className="rounded-lg bg-gray-800/50 p-4">
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <TrendingUp className="h-4 w-4" /> Transactions
              </div>
              <p className="mt-1 text-xl font-bold">{reputation.totalTransactions}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
