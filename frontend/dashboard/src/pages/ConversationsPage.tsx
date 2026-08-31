import { useEffect, useState, useRef, useCallback } from 'react'
import {
  Send,
  Clock,
  CreditCard,
  CheckCircle,
  Loader,
  Sparkles,
  MessageSquare,
  DollarSign,
  Calendar,
  Gift,
  Zap,
} from 'lucide-react'
import { useAppStore } from '../store'
import {
  listConversations,
  getConversation,
  sendConversationMessage,
  initiatePayment,
  checkPaymentStatus,
  generateDemoMatches,
  type Conversation,
  type ConversationMessage,
  type PaymentStatus,
} from '../api'

// ---------------------------------------------------------------------------
// Demo conversations data (fallback when API is unreachable)
// ---------------------------------------------------------------------------

interface DemoConversation {
  id: string
  match_id: string
  buyer_id: string
  seller_id: string
  status: string
  topic: string
  subscription_details: Record<string, any> | null
  message_count: number
  messages: DemoMessage[]
  created_at: string
}

interface DemoMessage {
  id: string
  sender_id: string
  role: string
  content: string
  message_type: string
  is_read: boolean
  meta?: Record<string, any>
  created_at: string
}

function generateDemoConversations(): DemoConversation[] {
  const now = new Date()
  const matches = generateDemoMatches()
  const accepted = matches.filter((m) => m.status === 'accepted')

  return accepted.map((m, i) => ({
    id: `conv-${i}`,
    match_id: m.id,
    buyer_id: 'demo-buyer',
    seller_id: 'demo-seller',
    status: 'active',
    topic: 'subscription_pricing',
    subscription_details: {
      service_name: m.serviceName,
      price: m.proposedPrice,
      seats: 1,
      billing_cycle: 'monthly',
    },
    message_count: 5,
    messages: [
      {
        id: 'msg-1',
        sender_id: 'demo-seller',
        role: 'agent',
        content:
          `🎉 Welcome! Your match for ${m.serviceName} (Family plan) has been accepted.\n\n` +
          `**Your share price:** $${m.proposedPrice.toFixed(2)}/month\n` +
          `**Total subscription cost:** $16.99/month\n` +
          `**Your seat:** 1 of family plan\n\n` +
          'Below are the available subscription tiers and pricing details.',
        message_type: 'pricing_welcome',
        is_read: true,
        meta: { action: 'show_pricing', match_id: m.id, proposed_price: m.proposedPrice },
        created_at: new Date(now.getTime() - 300000).toISOString(),
      },
      {
        id: 'msg-2',
        sender_id: 'demo-seller',
        role: 'agent',
        content:
          `📋 **${m.serviceName} — Available Subscription Tiers**\n\n` +
          '  • **Individual** — $10.99/mo (1 seat) — Ad-free music, Offline downloads, Unlimited skips\n' +
          '  • **Duo** — $14.99/mo (2 seats) — Two accounts, Duo Mix playlist, Ad-free music\n' +
          '  • **Family** — $16.99/mo (6 seats) — Up to 6 accounts, Family Mix playlist, Spotify Kids\n' +
          '  • **Student** — $5.99/mo (1 seat) — Ad-free music, Hulu included\n\n' +
          `💡 **Your seat** is on the **Family** plan at **$${m.proposedPrice.toFixed(2)}/month**.`,
        message_type: 'pricing_tiers',
        is_read: true,
        meta: {
          tiers: {
            individual: { price: 10.99, seats: 1 },
            family: { price: 16.99, seats: 6 },
          },
          selected_tier: 'family',
        },
        created_at: new Date(now.getTime() - 240000).toISOString(),
      },
      {
        id: 'msg-3',
        sender_id: 'demo-seller',
        role: 'agent',
        content:
          '📅 **Billing Information**\n\n' +
          '• **Billing cycle:** Monthly (recurring)\n' +
          `• **Your payment:** $${m.proposedPrice.toFixed(2)} due each billing cycle\n` +
          '• **Platform fee:** 12% service fee included\n' +
          '• **Billing note:** Billed monthly. Cancel anytime.\n\n' +
          'Your payment is secured through our escrow system until the seat is confirmed active.',
        message_type: 'billing_info',
        is_read: true,
        meta: { billing_cycle: 'monthly', platform_fee_pct: 12 },
        created_at: new Date(now.getTime() - 180000).toISOString(),
      },
      {
        id: 'msg-4',
        sender_id: 'demo-seller',
        role: 'agent',
        content:
          '🎁 **Available Promotions & Discounts**\n\n' +
          '  🎵 Get 3 months of Premium for free if you\'re a new user!\n' +
          '  🎁 Refer a friend and both get 1 month free.\n\n' +
          'Some promotions may apply to you as a new subscriber.',
        message_type: 'promotions',
        is_read: true,
        meta: { promotions: ['Get 3 months free', 'Refer a friend'] },
        created_at: new Date(now.getTime() - 120000).toISOString(),
      },
      {
        id: 'msg-5',
        sender_id: 'demo-seller',
        role: 'agent',
        content:
          '💳 **Ready to proceed with payment?**\n\n' +
          'When you\'re ready, click the payment button below to fund the escrow and secure your seat.\n\n' +
          '• ✅ Secure escrow payment\n' +
          '• ✅ Instant access upon confirmation\n' +
          '• ✅ Full refund if seat is not delivered\n\n' +
          'Type **"pay now"** or click the button below to proceed.',
        message_type: 'payment_prompt',
        is_read: true,
        meta: { action: 'create_escrow', match_id: m.id, amount: m.proposedPrice },
        created_at: new Date(now.getTime() - 60000).toISOString(),
      },
    ],
    created_at: new Date(now.getTime() - 300000).toISOString(),
  }))
}

// ---------------------------------------------------------------------------
// Message rendering helpers
// ---------------------------------------------------------------------------

function getMessageIcon(type: string): React.ReactNode {
  switch (type) {
    case 'pricing_welcome':
      return <Sparkles className="h-4 w-4 text-vault-300" />
    case 'pricing_tiers':
      return <DollarSign className="h-4 w-4 text-emerald-400" />
    case 'billing_info':
      return <Calendar className="h-4 w-4 text-blue-400" />
    case 'promotions':
      return <Gift className="h-4 w-4 text-amber-400" />
    case 'payment_prompt':
      return <CreditCard className="h-4 w-4 text-violet-400" />
    case 'payment_confirmation':
      return <CheckCircle className="h-4 w-4 text-emerald-400" />
    case 'payment_initiated':
      return <Loader className="h-4 w-4 text-blue-400" />
    default:
      return <MessageSquare className="h-4 w-4 text-slate-400" />
  }
}

function getMessageLabel(type: string): string {
  switch (type) {
    case 'pricing_welcome': return 'Pricing Overview'
    case 'pricing_tiers': return 'Subscription Tiers'
    case 'billing_info': return 'Billing Details'
    case 'promotions': return 'Promotions'
    case 'payment_prompt': return 'Payment'
    case 'payment_confirmation': return 'Payment Confirmed'
    case 'payment_initiated': return 'Payment Initiated'
    default: return 'Message'
  }
}

function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split('\n')
  return lines.map((line, i) => {
    const boldRegex = /\*\*(.*?)\*\*/g
    const parts: React.ReactNode[] = []
    let lastIndex = 0
    let match: RegExpExecArray | null
    while ((match = boldRegex.exec(line)) !== null) {
      if (match.index > lastIndex) {
        parts.push(line.slice(lastIndex, match.index))
      }
      parts.push(<strong key={`b-${i}-${match.index}`} className="font-semibold text-white">{match[1]}</strong>)
      lastIndex = match.index + match[0].length
    }
    let processed: React.ReactNode
    if (parts.length > 0) {
      if (lastIndex < line.length) parts.push(line.slice(lastIndex))
      processed = <>{parts}</>
    } else {
      processed = line
    }

    if (line.startsWith('📋') || line.startsWith('📅') || line.startsWith('🎁') || line.startsWith('💳') || line.startsWith('✅')) {
      return (
        <div key={i} className="mt-3 first:mt-0">
          {processed}
        </div>
      )
    }

    if (line.startsWith('  •') || line.startsWith('•')) {
      return (
        <div key={i} className="flex gap-2 ml-1">
          <span className="text-slate-500 mt-0.5">•</span>
          <span>{processed}</span>
        </div>
      )
    }

    return (
      <div key={i} className={line.trim() === '' ? 'h-2' : ''}>
        {processed}
      </div>
    )
  })
}

// ---------------------------------------------------------------------------
// Payment Status Banner
// ---------------------------------------------------------------------------

function PaymentStatusBanner({
  status,
  onPay,
  paying,
}: {
  status: PaymentStatus | null
  onPay: () => void
  paying: boolean
}) {
  if (!status || status.status === 'not_initiated') {
    return (
      <div className="border-t border-slate-800 bg-slate-900/80 p-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/15 text-violet-300">
              <CreditCard className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-white">Ready to subscribe?</p>
              <p className="text-xs text-slate-400">Secure your seat with escrow payment</p>
            </div>
          </div>
          <button
            onClick={onPay}
            disabled={paying}
            className="flex items-center gap-2 rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-500/25 transition hover:bg-violet-500 disabled:opacity-50"
          >
            {paying ? (
              <>
                <Loader className="h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <CreditCard className="h-4 w-4" />
                Pay Now
              </>
            )}
          </button>
        </div>
      </div>
    )
  }

  if (status.access_granted) {
    return (
      <div className="border-t border-emerald-800/50 bg-emerald-900/20 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/15">
            <CheckCircle className="h-5 w-5 text-emerald-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-emerald-300">✅ Access Granted</p>
            <p className="text-xs text-emerald-400/70">
              Your subscription seat is active. ${status.amount.toFixed(2)}/month
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (status.status === 'created' || status.status === 'funded') {
    return (
      <div className="border-t border-blue-800/50 bg-blue-900/20 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/15">
            <Loader className="h-5 w-5 text-blue-400 animate-spin" />
          </div>
          <div>
            <p className="text-sm font-semibold text-blue-300">Payment {status.status}</p>
            <p className="text-xs text-blue-400/70">{status.message}</p>
          </div>
        </div>
      </div>
    )
  }

  return null
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function ConversationsPage() {
  const demoMode = useAppStore((s) => s.demoMode)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selected, setSelected] = useState<Conversation | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [paying, setPaying] = useState(false)
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus | null>(null)
  const [messageInput, setMessageInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load conversations
  const loadConversations = useCallback(async () => {
    setLoading(true)
    try {
      const convs = await listConversations()
      if (convs.length > 0) {
        setConversations(convs)
      } else if (demoMode) {
        // Fallback to demo data
        setConversations(generateDemoConversations() as unknown as Conversation[])
      }
    } catch {
      if (demoMode) {
        setConversations(generateDemoConversations() as unknown as Conversation[])
      }
    } finally {
      setLoading(false)
    }
  }, [demoMode])

  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  // Load a conversation with messages
  const selectConversation = useCallback(async (convId: string) => {
    const conv = await getConversation(convId)
    if (conv) {
      setSelected(conv)
      // Check payment status
      const ps = await checkPaymentStatus(convId)
      setPaymentStatus(ps)
    } else {
      // Demo fallback
      const demo = generateDemoConversations().find((c) => c.id === convId)
      if (demo) {
        setSelected(demo as unknown as Conversation)
        setPaymentStatus({
          escrow_id: '',
          status: 'not_initiated',
          amount: demo.subscription_details?.price || 0,
          funded: false,
          access_granted: false,
          subscription_active: true,
          message: 'Demo mode — payment available.',
        })
      }
    }
    setMessageInput('')
  }, [])

  // Send a message
  const handleSend = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selected || !messageInput.trim()) return

    setSending(true)
    try {
      const msg = await sendConversationMessage(selected.id, messageInput.trim())
      if (msg) {
        setSelected((prev) =>
          prev
            ? { ...prev, messages: [...prev.messages, msg], message_count: prev.message_count + 1 }
            : prev
        )

        // If payment keyword, refresh conversation and payment status
        const lower = messageInput.trim().toLowerCase()
        if (['pay now', 'pay', 'confirm payment', 'proceed to payment', 'buy now'].includes(lower)) {
          const [refreshed, ps] = await Promise.all([
            getConversation(selected.id),
            checkPaymentStatus(selected.id),
          ])
          if (refreshed) setSelected(refreshed)
          if (ps) setPaymentStatus(ps)
        }
      }
      setMessageInput('')
    } catch {
      // In demo mode, simulate a response
      if (demoMode) {
        const demoMsg: ConversationMessage = {
          id: `msg-${Date.now()}`,
          sender_id: 'demo-buyer',
          role: 'buyer',
          content: messageInput.trim(),
          message_type: 'text',
          is_read: true,
          created_at: new Date().toISOString(),
        }
        setSelected((prev) =>
          prev ? { ...prev, messages: [...prev.messages, demoMsg] } : prev
        )
        setMessageInput('')
      }
    } finally {
      setSending(false)
    }
  }, [selected, messageInput, demoMode])

  // Handle payment
  const handlePay = useCallback(async () => {
    if (!selected) return
    setPaying(true)
    try {
      const result = await initiatePayment(selected.id, 'demo')
      if (result) {
        setPaymentStatus({
          escrow_id: result.escrow_id,
          status: result.status,
          amount: result.amount,
          funded: result.access_granted,
          access_granted: result.access_granted,
          subscription_active: true,
          message: result.message,
        })
        // Refresh conversation to get agent confirmation message
        const refreshed = await getConversation(selected.id)
        if (refreshed) setSelected(refreshed)
      }
    } catch {
      // Demo fallback
      setPaymentStatus({
        escrow_id: `esc_${Date.now()}`,
        status: 'funded',
        amount: servicePrice(selected) || 4.50,
        funded: true,
        access_granted: true,
        subscription_active: true,
        message: 'Payment complete! Access granted.',
      })
    } finally {
      setPaying(false)
    }
  }, [selected])

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [selected?.messages?.length])

  // Helpers
  const formatTime = (iso: string) => {
    const d = new Date(iso)
    const mins = Math.floor((Date.now() - d.getTime()) / 60000)
    if (mins < 1) return 'now'
    if (mins < 60) return `${mins}m`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h`
    return `${Math.floor(hrs / 24)}d`
  }

  const getDetails = (conv: Conversation) => (conv.subscription_details || {}) as Record<string, any>
  const serviceName = (conv: Conversation) =>
    getDetails(conv).service_name || conv.topic.replace(/_/g, ' ')
  const servicePrice = (conv: Conversation) => {
    const p = getDetails(conv).price
    return typeof p === 'number' ? p : 0
  }

  const serviceLogo = (name: string) => {
    const logos: Record<string, string> = {
      Spotify: '🎵', 'Google One': '☁️', 'YouTube Premium': '📺',
      'Apple Music': '🎵', Duolingo: '🦉', Headspace: '🧘',
      Calm: '🧘', 'Microsoft 365': '💼', Canva: '🎨',
    }
    return logos[name] || '📦'
  }

  return (
    <div className="h-full flex flex-col bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50 p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-vault-500/15 text-vault-300">
            <MessageSquare className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Conversations</h1>
            <p className="text-sm text-slate-400">
              Pricing negotiation, payment, and subscription access
            </p>
          </div>
        </div>
      </div>

      {/* Main split view */}
      <div className="flex-1 flex overflow-hidden">
        {/* Conversation list sidebar */}
        <div className="w-80 border-r border-slate-800 overflow-y-auto bg-slate-900/30 shrink-0">
          {loading ? (
            <div className="p-6 text-center text-slate-400">
              <Loader className="h-5 w-5 animate-spin mx-auto mb-2" />
              <p className="text-sm">Loading conversations...</p>
            </div>
          ) : conversations.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <Clock className="h-10 w-10 mx-auto opacity-40 mb-3" />
              <p className="font-medium">No conversations yet</p>
              <p className="text-xs mt-1 text-slate-500">Accept a match to start negotiating pricing</p>
            </div>
          ) : (
            <div className="space-y-1 p-2">
              {conversations.map((conv) => {
                const svc = serviceName(conv)
                const isActive = selected?.id === conv.id
                return (
                  <button
                    key={conv.id}
                    onClick={() => selectConversation(conv.id)}
                    className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                      isActive
                        ? 'bg-vault-500/10 border-vault-500/30 shadow-lg shadow-vault-500/5'
                        : 'bg-slate-800/20 border-slate-800/50 hover:bg-slate-800/40 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-2xl mt-0.5">{serviceLogo(svc)}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <p className={`font-semibold text-sm truncate ${isActive ? 'text-white' : 'text-slate-200'}`}>
                            {svc}
                          </p>
                          <span className="text-[10px] text-slate-500 shrink-0">
                            {formatTime(conv.created_at)}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 mt-0.5 truncate">
                          ${servicePrice(conv).toFixed(2) || '—'}/mo · {conv.message_count} messages
                        </p>
                        <div className="flex items-center gap-1.5 mt-1.5">
                          <span className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-medium ${
                            conv.status === 'active'
                              ? 'bg-emerald-500/10 text-emerald-400'
                              : 'bg-slate-700/30 text-slate-400'
                          }`}>
                            {conv.status === 'active' ? '● Active' : conv.status}
                          </span>
                        </div>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Chat area */}
        {selected ? (
          <div className="flex-1 flex flex-col bg-slate-950 min-w-0">
            {/* Chat header */}
            <div className="border-b border-slate-800 bg-slate-900/50 px-6 py-3 shrink-0">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{serviceLogo(serviceName(selected))}</span>
                <div>
                  <h2 className="font-semibold text-white">{serviceName(selected)}</h2>
                  <p className="text-xs text-slate-400">
                    {servicePrice(selected) > 0
                      ? `$${servicePrice(selected).toFixed(2)}/month`
                      : 'Pricing negotiation'}
                    {' · '}#{selected.id.slice(0, 8)}
                  </p>
                </div>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              {selected.messages?.length ? (
                <div className="space-y-4 max-w-3xl mx-auto">
                  {selected.messages.map((msg) => {
                    const isAgent = msg.role === 'agent'

                    return (
                      <div key={msg.id} className={`flex ${isAgent ? 'justify-start' : 'justify-end'}`}>
                        <div className={`max-w-lg ${isAgent ? 'order-1' : 'order-1'}`}>
                          {isAgent && (
                            <div className="flex items-center gap-1.5 mb-1.5 ml-1">
                              {getMessageIcon(msg.message_type)}
                              <span className="text-[10px] font-medium uppercase tracking-wider text-slate-500">
                                {getMessageLabel(msg.message_type)}
                              </span>
                            </div>
                          )}
                          <div
                            className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                              isAgent
                                ? 'bg-slate-800/70 text-slate-200 border border-slate-700/50'
                                : 'bg-vault-600 text-white'
                            }`}
                          >
                            <div className={isAgent ? 'space-y-0.5' : ''}>
                              {isAgent ? renderMarkdown(msg.content) : msg.content}
                            </div>
                          </div>
                          <p className={`text-[10px] text-slate-600 mt-1 ${isAgent ? 'ml-1' : 'text-right mr-1'}`}>
                            {formatTime(msg.created_at)}
                          </p>
                        </div>
                      </div>
                    )
                  })}
                  <div ref={messagesEndRef} />
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-slate-400">
                  <MessageSquare className="h-10 w-10 opacity-30 mb-3" />
                  <p className="text-sm">No messages yet</p>
                </div>
              )}
            </div>

            {/* Payment status banner */}
            <PaymentStatusBanner
              status={paymentStatus}
              onPay={handlePay}
              paying={paying}
            />

            {/* Message input */}
            {selected.status === 'active' ? (
              <form onSubmit={handleSend} className="border-t border-slate-800 p-4 bg-slate-900/50 shrink-0">
                <div className="flex gap-3 max-w-3xl mx-auto">
                  <input
                    type="text"
                    value={messageInput}
                    onChange={(e) => setMessageInput(e.target.value)}
                    placeholder='Type a message or "pay now" to proceed...'
                    disabled={sending}
                    className="flex-1 px-4 py-2.5 bg-slate-800/80 border border-slate-700/50 rounded-xl text-white text-sm placeholder-slate-500 focus:outline-none focus:border-vault-500/50 focus:ring-1 focus:ring-vault-500/25 disabled:opacity-50 transition"
                  />
                  <button
                    type="submit"
                    disabled={sending || !messageInput.trim()}
                    className="px-4 py-2.5 bg-vault-600 hover:bg-vault-500 disabled:opacity-30 text-white rounded-xl font-medium flex items-center gap-2 transition shadow-lg shadow-vault-500/20"
                  >
                    {sending ? <Loader className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  </button>
                </div>
              </form>
            ) : (
              <div className="border-t border-slate-800 p-4 bg-slate-900/50 text-center text-sm text-slate-400 shrink-0">
                This conversation is {selected.status}
              </div>
            )}
          </div>
        ) : (
          /* Empty state */
          <div className="flex-1 flex items-center justify-center bg-slate-950">
            <div className="text-center text-slate-400">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-800/50 mx-auto mb-4">
                <Zap className="h-7 w-7 opacity-40" />
              </div>
              <p className="font-medium text-slate-300">Select a conversation</p>
              <p className="text-sm mt-1 max-w-xs">
                Choose an accepted match to view pricing details, negotiate, and complete payment
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
