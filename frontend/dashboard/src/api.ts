import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || ''

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('vault_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 errors — reject but don't force-redirect
// (The app routes handle redirect logic; a hard redirect causes loops)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear the stale token so it doesn't keep causing 401s
      localStorage.removeItem('vault_token')

      // Only force redirect if we're NOT on the login page already
      // and there are no saved accounts (truly unauthenticated)
      const savedRaw = localStorage.getItem('vault_saved_accounts')
      const savedAccounts: { token: string }[] = savedRaw ? JSON.parse(savedRaw) : []
      // Remove the expired account from saved accounts
      if (savedAccounts.length > 0) {
        // Keep accounts that have different (valid) tokens
        const validAccounts = savedAccounts.filter((a) => {
          try {
            const parts = a.token.split('.')
            if (parts.length !== 3) return false
            const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
            const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
            const payload = JSON.parse(atob(padded))
            const nowSec = Math.floor(Date.now() / 1000)
            return typeof payload.exp === 'number' && nowSec <= payload.exp
          } catch {
            return false
          }
        })
        localStorage.setItem('vault_saved_accounts', JSON.stringify(validAccounts))
        if (validAccounts.length === 0 && window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      } else if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// ---------------------------------------------------------------------------
// Demo Data Generators (for hackathon demo without real API)
// ---------------------------------------------------------------------------

export interface DemoSubscription {
  id: string
  serviceName: string
  serviceCategory: string
  serviceLogo: string
  tier: string
  status: string
  monthlyCost: number
  maxSeats: number
  usedSeats: number
  usagePercentage: number
}

export interface DemoListing {
  id: string
  sellerId: string
  sellerName: string
  sellerReputation: number
  serviceName: string
  serviceCategory: string
  askingPrice: number
  dynamicPrice: number
  seatsAvailable: number
  description: string
  distanceKm: number
  matchScore: number
  matchReasons: string[]
}

export interface DemoMatch {
  id: string
  listingId: string
  serviceName: string
  sellerName: string
  status: string
  matchScore: number
  proposedPrice: number
  createdAt: string
}

export interface DemoTransaction {
  id: string
  matchId: string
  serviceName: string
  amount: number
  platformFee: number
  sellerPayout: number
  status: string
  createdAt: string
}

export interface DemoDashboardData {
  totalSubscriptions: number
  totalMonthlyCost: number
  totalSavings: number
  activeMatches: number
  completedTransactions: number
  reputationScore: number
  usageChart: { name: string; usage: number; savings: number }[]
  recentActivity: { id: string; type: string; message: string; time: string }[]
}

const SERVICES = [
  { name: 'Spotify', category: 'music', logo: '🎵', tier: 'Family', cost: 16.99, maxSeats: 6 },
  { name: 'Google One', category: 'cloud_storage', logo: '☁️', tier: 'Family', cost: 22.99, maxSeats: 5 },
  { name: 'YouTube Premium', category: 'streaming', logo: '📺', tier: 'Family', cost: 22.99, maxSeats: 5 },
  { name: 'Headspace', category: 'wellness', logo: '🧘', tier: 'Family', cost: 9.99, maxSeats: 6 },
  { name: 'Duolingo', category: 'education', logo: '🦉', tier: 'Super', cost: 7.99, maxSeats: 6 },
]

const SELLERS = [
  { name: 'Alex Chen', reputation: 0.92 },
  { name: 'Maria Santos', reputation: 0.88 },
  { name: 'James Wilson', reputation: 0.85 },
  { name: 'Sarah Kim', reputation: 0.95 },
  { name: 'David Park', reputation: 0.78 },
]

export function generateDemoSubscriptions(): DemoSubscription[] {
  return SERVICES.map((s, i) => ({
    id: `sub-${i}`,
    serviceName: s.name,
    serviceCategory: s.category,
    serviceLogo: s.logo,
    tier: s.tier,
    status: 'active',
    monthlyCost: s.cost,
    maxSeats: s.maxSeats,
    usedSeats: Math.floor(Math.random() * s.maxSeats),
    usagePercentage: Math.round(Math.random() * 80 + 10),
  }))
}

export function generateDemoListings(): DemoListing[] {
  return SERVICES.slice(0, 3).map((s, i) => ({
    id: `list-${i}`,
    sellerId: `user-${i}`,
    sellerName: SELLERS[i].name,
    sellerReputation: SELLERS[i].reputation,
    serviceName: s.name,
    serviceCategory: s.category,
    askingPrice: Math.round(s.cost / s.maxSeats * 100) / 100,
    dynamicPrice: Math.round((s.cost / s.maxSeats * 0.9) * 100) / 100,
    seatsAvailable: Math.floor(Math.random() * 3) + 1,
    description: `${s.tier} plan — ${Math.floor(Math.random() * 3) + 1} seats available.`,
    distanceKm: Math.round((Math.random() * 15 + 0.5) * 10) / 10,
    matchScore: Math.round((Math.random() * 0.4 + 0.6) * 1000) / 1000,
    matchReasons: ['High trust', 'Nearby', 'Good price'],
  }))
}

export function generateDemoMatches(): DemoMatch[] {
  return [
    { id: 'match-1', listingId: 'list-0', serviceName: 'Spotify', sellerName: 'Alex Chen', status: 'accepted', matchScore: 0.847, proposedPrice: 4.50, createdAt: new Date(Date.now() - 3600000).toISOString() },
    { id: 'match-2', listingId: 'list-1', serviceName: 'Google One', sellerName: 'Maria Santos', status: 'proposed', matchScore: 0.792, proposedPrice: 5.75, createdAt: new Date(Date.now() - 7200000).toISOString() },
    { id: 'match-3', listingId: 'list-2', serviceName: 'YouTube Premium', sellerName: 'James Wilson', status: 'proposed', matchScore: 0.756, proposedPrice: 5.00, createdAt: new Date(Date.now() - 10800000).toISOString() },
  ]
}

export function generateDemoTransactions(): DemoTransaction[] {
  return [
    { id: 'esc-1', matchId: 'match-1', serviceName: 'Spotify', amount: 4.50, platformFee: 0.54, sellerPayout: 3.96, status: 'released', createdAt: new Date(Date.now() - 86400000).toISOString() },
    { id: 'esc-2', matchId: 'match-0', serviceName: 'Headspace', amount: 2.50, platformFee: 0.30, sellerPayout: 2.20, status: 'funded', createdAt: new Date(Date.now() - 43200000).toISOString() },
  ]
}

// ---------------------------------------------------------------------------
// Agent Chat API
// ---------------------------------------------------------------------------

export interface AgentResultCard {
  type: 'subscription' | 'listing' | 'match' | 'escrow' | 'stats' | 'action'
  title: string
  subtitle?: string
  data: Record<string, unknown>
  actions?: { label: string; variant?: string }[]
}

export interface AgentChatResponse {
  reply: string
  cards: AgentResultCard[]
  suggestions: string[]
  conversation_id: string
}

export interface AgentChatRequest {
  message: string
  conversation_history?: { role: string; content: string; timestamp: string }[]
  context?: Record<string, unknown>
}

export async function sendAgentChat(req: AgentChatRequest): Promise<AgentChatResponse> {
  try {
    const { data } = await api.post<AgentChatResponse>('/agent/chat', req)
    return data
  } catch {
    // Fallback to client-side demo agent if backend is unreachable
    return generateDemoAgentResponse(req.message)
  }
}

export async function getAgentSuggestions(): Promise<string[]> {
  try {
    const { data } = await api.get<{ suggestions: string[] }>('/agent/suggestions')
    return data.suggestions
  } catch {
    return [
      'Show my subscriptions',
      'Find marketplace matches',
      'Optimize my spending',
      'View dashboard',
    ]
  }
}

// ---------------------------------------------------------------------------
// Streaming Agent Chat
// ---------------------------------------------------------------------------

export interface StreamCallbacks {
  onToken: (token: string) => void
  onCards: (cards: AgentResultCard[], suggestions: string[]) => void
  onDone: () => void
  onError: (message: string) => void
}

export async function streamAgentChat(
  req: AgentChatRequest,
  callbacks: StreamCallbacks,
): Promise<void> {
  try {
    const token = localStorage.getItem('vault_token')
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    const response = await fetch(`${API_BASE}/agent/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify(req),
    })

    if (!response.ok) {
      // Fall back to non-streaming
      const fallback = await sendAgentChat(req)
      callbacks.onToken(fallback.reply)
      callbacks.onCards(fallback.cards, fallback.suggestions)
      callbacks.onDone()
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      callbacks.onError('No response stream')
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const jsonStr = line.slice(6)
        if (!jsonStr) continue

        try {
          const event = JSON.parse(jsonStr)
          switch (event.type) {
            case 'token':
              callbacks.onToken(event.content)
              break
            case 'cards':
              callbacks.onCards(event.cards || [], event.suggestions || [])
              break
            case 'done':
              callbacks.onDone()
              return
            case 'error':
              callbacks.onError(event.message || 'Unknown error')
              return
          }
        } catch {
          // Skip malformed JSON lines
        }
      }
    }

    // If stream ends without explicit 'done' event
    callbacks.onDone()
  } catch (err) {
    // Network error — fall back to non-streaming
    try {
      const fallback = await sendAgentChat(req)
      callbacks.onToken(fallback.reply)
      callbacks.onCards(fallback.cards, fallback.suggestions)
      callbacks.onDone()
    } catch {
      callbacks.onError('Failed to connect to agent')
    }
  }
}

// ---------------------------------------------------------------------------
// Client-Side Demo Agent (fallback when backend is unreachable)
// ---------------------------------------------------------------------------

function generateDemoAgentResponse(message: string): AgentChatResponse {
  const lower = message.toLowerCase()
  const cards: AgentResultCard[] = []
  const suggestions: string[] = []
  let reply = ''

  const totalCost = SERVICES.reduce((sum, s) => sum + s.cost, 0)
  const totalMaxSeats = SERVICES.reduce((sum, s) => sum + s.maxSeats, 0)
  const totalUsedSeats = 8 // demo
  const unusedSeats = totalMaxSeats - totalUsedSeats
  const savingsPotential = SERVICES.reduce(
    (sum, s) => sum + (s.maxSeats - Math.floor(s.maxSeats * 0.4)) * (s.cost / s.maxSeats * 0.5),
    0
  )

  if (/subscri|my sub|what do i have|services/i.test(lower)) {
    SERVICES.forEach((s) => {
      const used = Math.floor(s.maxSeats * 0.4)
      cards.push({
        type: 'subscription',
        title: `${s.logo || '📦'} ${s.name}`,
        subtitle: `${s.tier} — ${used}/${s.maxSeats} seats`,
        data: { name: s.name, tier: s.tier, cost: s.cost, max_seats: s.maxSeats, used_seats: used, status: 'active' },
      })
    })
    reply = `You have ${SERVICES.length} active subscriptions totaling $${totalCost.toFixed(2)}/mo. You're using ${totalUsedSeats} out of ${totalMaxSeats} total seats. You have ${unusedSeats} unused seats that could save you ~$${savingsPotential.toFixed(2)}/mo!`
    suggestions.push('Show savings opportunities', 'Find matches for unused seats', 'Optimize my spending')
  } else if (/market|find|search|listing|listings|available/i.test(lower)) {
    generateDemoListings().forEach((l) => {
      cards.push({
        type: 'listing',
        title: `${l.serviceName}`,
        subtitle: `by ${l.sellerName}`,
        data: l as unknown as Record<string, unknown>,
      })
    })
    reply = `I found ${cards.length} marketplace listings near you. Here are the best matches based on your preferences — high trust scores, competitive prices, and nearby sellers.`
    suggestions.push('Accept the best match', 'Show more details', 'Filter by category')
  } else if (/match|matches|paired|connected/i.test(lower)) {
    generateDemoMatches().forEach((m) => {
      cards.push({
        type: 'match',
        title: `${m.serviceName}`,
        subtitle: `with ${m.sellerName}`,
        data: m as unknown as Record<string, unknown>,
      })
    })
    reply = `You have ${cards.length} active matches. 1 has been accepted and is ready for escrow.`
    suggestions.push('Fund the escrow', 'View match details', 'Find more matches')
  } else if (/escrow|payment|pay|transaction|transactions/i.test(lower)) {
    generateDemoTransactions().forEach((t) => {
      cards.push({
        type: 'escrow',
        title: `${t.serviceName}`,
        subtitle: `Amount: $${t.amount.toFixed(2)}`,
        data: t as unknown as Record<string, unknown>,
      })
    })
    reply = `Here's your escrow overview: $3.96 earned from completed transactions, $2.50 currently in escrow. You have ${cards.length} total transactions.`
    suggestions.push('View payout history', 'Release funds', 'Dispute a transaction')
  } else if (/sav|optimi|waste|low usage/i.test(lower)) {
    const lowUsage = [
      { name: 'YouTube Premium', logo: '📺', usage: 18, seats: 4, savings: 9.20 },
      { name: 'Duolingo', logo: '🦉', usage: 28, seats: 4, savings: 5.33 },
      { name: 'Spotify', logo: '🎵', usage: 35, seats: 4, savings: 5.66 },
    ]
    lowUsage.forEach((u) => {
      cards.push({
        type: 'subscription',
        title: `${u.logo} ${u.name}`,
        subtitle: `Only ${u.usage}% used — ${u.seats} unused seats`,
        data: { name: u.name, usage_pct: u.usage, potential_savings: u.savings },
      })
    })
    reply = `I found 3 subscriptions with low usage. By sharing ${unusedSeats} unused seats, you could save ~$${savingsPotential.toFixed(2)}/mo. Want me to create marketplace listings for these?`
    suggestions.push('Create listings for unused seats', 'Find matches for unused seats', 'Show all subscriptions')
  } else if (/dashboard|overview|summary|stats|how am i/i.test(lower)) {
    cards.push(
      { type: 'stats', title: 'Active Subscriptions', subtitle: '5', data: { value: '5', label: 'services' } },
      { type: 'stats', title: 'Monthly Cost', subtitle: `$${totalCost.toFixed(2)}`, data: { value: `$${totalCost.toFixed(2)}` } },
      { type: 'stats', title: 'Potential Savings', subtitle: `~$${savingsPotential.toFixed(2)}/mo`, data: { value: `~$${savingsPotential.toFixed(2)}` } },
      { type: 'stats', title: 'Trust Score', subtitle: '87%', data: { value: '87%', label: 'Gold tier' } },
    )
    reply = `Here's your Vault overview! You're doing well with a Gold-tier trust score. You're spending $${totalCost.toFixed(2)}/mo across ${SERVICES.length} subscriptions but have ~$${savingsPotential.toFixed(2)}/mo in potential savings from unused seats.`
    suggestions.push('Show savings opportunities', 'Find marketplace matches', 'View escrow status')
  } else if (/creat|list|sell|share/i.test(lower)) {
    reply = `I can create marketplace listings for your unused subscription seats. Based on your usage analysis, here are the best candidates:\n\n• 🎵 Spotify — 4 unused seats (~$5.66/mo potential)\n• 📺 YouTube Premium — 4 unused seats (~$9.20/mo potential)\n• 🦉 Duolingo — 4 unused seats (~$5.33/mo potential)\n\nI'll set competitive prices and match with verified sellers nearby. Shall I create these listings?`
    suggestions.push('Yes, create all listings', 'Let me customize prices', 'Show me the match algorithm')
  } else if (/accept|confirm|yes|go ahead|do it/i.test(lower)) {
    reply = "✅ Done! I've processed that for you. The changes are reflected in your account. You'll receive notifications as things progress."
    suggestions.push('Show me my updated overview', 'Check notifications', 'Find more opportunities')
  } else {
    reply = (
      "I'm Vault Agent — your AI assistant for subscription management. I can help you with:\n\n" +
      '• 📋 **View subscriptions** — See all your active services\n' +
      '• 🔍 **Find matches** — Discover marketplace listings\n' +
      '• 💰 **Optimize spending** — Find savings from unused seats\n' +
      '• 🤝 **Manage matches** — Accept/reject proposals\n' +
      '• 💳 **Escrow & payments** — Track transactions\n' +
      '• 📊 **Dashboard** — See your overview stats\n\n' +
      'What would you like to do?'
    )
    suggestions.push('Show my subscriptions', 'Find marketplace matches', 'Optimize my spending', 'View dashboard')
  }

  return { reply, cards, suggestions, conversation_id: `conv-${Date.now()}` }
}

export function generateDemoDashboard(): DemoDashboardData {
  const usageData = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day) => ({
    name: day,
    usage: Math.round(Math.random() * 120 + 30),
    savings: Math.round(Math.random() * 15 + 3),
  }))

  const activity = [
    { id: 'a1', type: 'match', message: 'New match with Alex Chen for Spotify', time: '2 hours ago' },
    { id: 'a2', type: 'payment', message: 'Escrow funded for $4.50', time: '5 hours ago' },
    { id: 'a3', type: 'usage', message: 'Spotify usage report generated', time: '1 day ago' },
    { id: 'a4', type: 'match', message: 'Match accepted — Google One seat secured', time: '2 days ago' },
    { id: 'a5', type: 'payout', message: '$3.96 payout processed to bank account', time: '3 days ago' },
  ]

  return {
    totalSubscriptions: 5,
    totalMonthlyCost: 80.95,
    totalSavings: 27.50,
    activeMatches: 2,
    completedTransactions: 8,
    reputationScore: 0.87,
    usageChart: usageData,
    recentActivity: activity,
  }
}

// ---------------------------------------------------------------------------
// Payment & Conversation API
// ---------------------------------------------------------------------------

export interface PaymentResult {
  escrow_id: string
  client_secret: string
  payment_intent_id: string
  amount: number
  platform_fee: number
  seller_payout: string
  status: string
  access_granted: boolean
  message: string
}

export interface PaymentStatus {
  escrow_id: string
  status: string
  amount: number
  funded: boolean
  access_granted: boolean
  subscription_active: boolean
  message: string
}

export interface ConversationMessage {
  id: string
  sender_id: string
  role: string
  content: string
  message_type: string
  is_read: boolean
  meta?: Record<string, unknown>
  created_at: string
}

export interface Conversation {
  id: string
  match_id: string
  buyer_id: string
  seller_id: string
  status: string
  topic: string
  subscription_details?: Record<string, unknown>
  message_count: number
  messages: ConversationMessage[]
  created_at: string
}

/** Initiate payment from a conversation. */
export async function initiatePayment(
  conversationId: string,
  paymentMethod: string = 'demo',
): Promise<PaymentResult> {
  try {
    const { data } = await api.post<PaymentResult>(
      `/api/v1/conversations/${conversationId}/pay`,
      { conversation_id: conversationId, payment_method: paymentMethod },
    )
    return data
  } catch (err: any) {
    // In demo mode, simulate successful payment
    return {
      escrow_id: `esc_${Date.now()}`,
      client_secret: `demo_secret_${Date.now()}`,
      payment_intent_id: `pi_demo_${Date.now()}`,
      amount: 4.50,
      platform_fee: 0.54,
      seller_payout: '3.96',
      status: 'funded',
      access_granted: true,
      message: 'Payment complete! Access granted.',
    }
  }
}

/** Check payment/access status for a conversation. */
export async function checkPaymentStatus(conversationId: string): Promise<PaymentStatus> {
  try {
    const { data } = await api.get<PaymentStatus>(
      `/api/v1/conversations/${conversationId}/payment-status`,
    )
    return data
  } catch {
    return {
      escrow_id: '',
      status: 'unknown',
      amount: 0,
      funded: false,
      access_granted: false,
      subscription_active: false,
      message: 'Could not check payment status.',
    }
  }
}

/** List conversations for the current user. */
export async function listConversations(): Promise<Conversation[]> {
  try {
    const { data } = await api.get<Conversation[]>('/api/v1/conversations')
    return data
  } catch {
    return []
  }
}

/** Get a conversation with messages. */
export async function getConversation(conversationId: string): Promise<Conversation | null> {
  try {
    const { data } = await api.get<Conversation>(
      `/api/v1/conversations/${conversationId}`,
    )
    return data
  } catch {
    return null
  }
}

/** Send a message in a conversation. */
export async function sendConversationMessage(
  conversationId: string,
  content: string,
  messageType: string = 'text',
): Promise<ConversationMessage | null> {
  try {
    const { data } = await api.post<ConversationMessage>(
      `/api/v1/conversations/${conversationId}/messages`,
      { content, message_type: messageType },
    )
    return data
  } catch {
    return null
  }
}

/** Accept a match (triggers conversation creation with pricing agent). */
export async function acceptMatch(matchId: string): Promise<{ message: string; match_id: string; status: string }> {
  try {
    const { data } = await api.post(`/api/v1/matches/${matchId}/accept`)
    return data
  } catch {
    return { message: 'Match accepted (demo)', match_id: matchId, status: 'accepted' }
  }
}

/** Reject a match. */
export async function rejectMatch(matchId: string): Promise<{ message: string; match_id: string; status: string }> {
  try {
    const { data } = await api.post(`/api/v1/matches/${matchId}/reject`)
    return data
  } catch {
    return { message: 'Match rejected (demo)', match_id: matchId, status: 'rejected' }
  }
}

/** Propose a match for a listing. */
export async function proposeMatch(listingId: string): Promise<{ message: string; match_id: string; status: string }> {
  try {
    const { data } = await api.post(`/api/v1/matches/propose/${listingId}`)
    return data
  } catch {
    return { message: 'Match proposed (demo)', match_id: `match_${Date.now()}`, status: 'proposed' }
  }
}

// ---------------------------------------------------------------------------
// Subscription CRUD API
// ---------------------------------------------------------------------------

export interface SubscriptionData {
  id: string
  service_name: string
  service_category: string
  tier: string
  status: string
  monthly_cost: number
  max_seats: number
  used_seats: number
  billing_cycle_day: number
  usage_percentage?: number
  created_at: string
}

/** Fetch all subscriptions from the API. */
export async function fetchSubscriptions(): Promise<SubscriptionData[]> {
  try {
    const { data } = await api.get<SubscriptionData[]>('/api/v1/subscriptions')
    return data
  } catch {
    return []
  }
}

/** Create a new subscription. */
export async function createSubscription(payload: {
  service_name: string
  tier: string
  monthly_cost: number
  max_seats: number
  billing_cycle_day: number
}): Promise<SubscriptionData | null> {
  try {
    const { data } = await api.post<SubscriptionData>('/api/v1/subscriptions', payload)
    return data
  } catch {
    return null
  }
}
