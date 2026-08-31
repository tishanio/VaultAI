import { useState, useRef, useEffect } from 'react'
import {
  Send,
  Bot,
  User,
  Sparkles,
  Loader2,
  CreditCard,
  Store,
  Wallet,
  BarChart3,
  ArrowUpRight,
  Star,
  MapPin,
  Shield,
  Zap,
  MessageSquare,
  ChevronRight,
} from 'lucide-react'
import { useAppStore, type ChatMessage, type ResultCard } from '../store'
import { streamAgentChat } from '../api'

// ---------------------------------------------------------------------------
// Result Card Renderer
// ---------------------------------------------------------------------------

function SubscriptionCard({ card }: { card: ResultCard }) {
  const d = card.data
  const usagePct = (d.usage_pct as number) ?? 30
  return (
    <div className="rounded-xl border border-gray-700/50 bg-gray-800/60 p-4 transition-all hover:border-vault-600/50">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gray-700/50 text-xl">
            {(d.logo as string) || '📦'}
          </div>
          <div>
            <h4 className="font-semibold text-gray-100">{card.title}</h4>
            <p className="text-xs text-gray-400">{card.subtitle}</p>
          </div>
        </div>
        {d.cost !== undefined && (
          <span className="text-sm font-bold text-emerald-400">
            ${(d.cost as number).toFixed(2)}/mo
          </span>
        )}
      </div>
      {d.potential_savings !== undefined && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-emerald-900/20 px-3 py-2 text-xs text-emerald-400">
          <TrendingUpIcon className="h-3.5 w-3.5" />
          Potential savings: ${(d.potential_savings as number).toFixed(2)}/mo
        </div>
      )}
      {usagePct > 0 && (
        <div className="mt-3">
          <div className="mb-1 flex justify-between text-[11px] text-gray-500">
            <span>Usage</span>
            <span>{usagePct}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-gray-700">
            <div
              className={`h-full rounded-full transition-all ${
                usagePct < 30 ? 'bg-emerald-500' : usagePct < 60 ? 'bg-yellow-500' : 'bg-red-500'
              }`}
              style={{ width: `${usagePct}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

function ListingCard({ card }: { card: ResultCard }) {
  const d = card.data
  const score = (d.match_score as number) ?? 0
  return (
    <div className="rounded-xl border border-gray-700/50 bg-gray-800/60 p-4 transition-all hover:border-vault-600/50">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gray-700/50 text-xl">
            {(d.logo as string) || '📦'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-semibold text-gray-100">{card.title}</h4>
              {score > 0 && (
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${
                    score >= 0.8
                      ? 'bg-emerald-900/50 text-emerald-400'
                      : score >= 0.6
                      ? 'bg-yellow-900/50 text-yellow-400'
                      : 'bg-gray-800 text-gray-400'
                  }`}
                >
                  {(score * 100).toFixed(0)}% match
                </span>
              )}
            </div>
            <p className="text-xs text-gray-400">{card.subtitle}</p>
          </div>
        </div>
        {d.price !== undefined && (
          <span className="text-sm font-bold text-emerald-400">
            ${(d.price as number).toFixed(2)}
            <span className="text-xs text-gray-500">/mo</span>
          </span>
        )}
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        {d.reputation !== undefined && (
          <span className="flex items-center gap-1 rounded-full bg-gray-700/50 px-2 py-1 text-gray-300">
            <Star className="h-3 w-3 text-yellow-400" />
            {((d.reputation as number) * 100).toFixed(0)}%
          </span>
        )}
        {d.distance_km !== undefined && (
          <span className="flex items-center gap-1 rounded-full bg-gray-700/50 px-2 py-1 text-gray-300">
            <MapPin className="h-3 w-3" />
            {String(d.distance_km)} km
          </span>
        )}
        {d.seats !== undefined && (
          <span className="rounded-full bg-gray-700/50 px-2 py-1 text-gray-300">
            {String(d.seats)} seat(s)
          </span>
        )}
      </div>
    </div>
  )
}

function MatchCard({ card }: { card: ResultCard }) {
  const d = card.data
  const score = (d.match_score as number) ?? (d.score as number) ?? 0
  const status = (d.status as string) ?? 'proposed'
  const statusColor =
    status === 'accepted'
      ? 'bg-emerald-900/50 text-emerald-400'
      : status === 'proposed'
      ? 'bg-yellow-900/50 text-yellow-400'
      : 'bg-gray-800 text-gray-400'

  return (
    <div className="rounded-xl border border-gray-700/50 bg-gray-800/60 p-4 transition-all hover:border-vault-600/50">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gray-700/50 text-xl">
            {(d.logo as string) || '🤝'}
          </div>
          <div>
            <h4 className="font-semibold text-gray-100">{card.title}</h4>
            <p className="text-xs text-gray-400">{card.subtitle}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-medium ${statusColor}`}>
            {status}
          </span>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        {score > 0 && (
          <span className="flex items-center gap-1 rounded-full bg-gray-700/50 px-2 py-1 text-gray-300">
            <Shield className="h-3 w-3 text-vault-400" />
            {(score * 100).toFixed(0)}% match
          </span>
        )}
        {(d.price as number) !== undefined && (
          <span className="flex items-center gap-1 rounded-full bg-gray-700/50 px-2 py-1 text-gray-300">
            ${(d.price as number).toFixed(2)}/mo
          </span>
        )}
      </div>
    </div>
  )
}

function EscrowCard({ card }: { card: ResultCard }) {
  const d = card.data
  const status = (d.status as string) ?? 'created'
  const statusColor =
    status === 'released'
      ? 'bg-emerald-900/50 text-emerald-400'
      : status === 'funded'
      ? 'bg-blue-900/50 text-blue-400'
      : status === 'held'
      ? 'bg-yellow-900/50 text-yellow-400'
      : status === 'disputed'
      ? 'bg-red-900/50 text-red-400'
      : 'bg-gray-800 text-gray-400'

  return (
    <div className="rounded-xl border border-gray-700/50 bg-gray-800/60 p-4 transition-all hover:border-vault-600/50">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gray-700/50 text-xl">
            {(d.logo as string) || '💳'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-semibold text-gray-100">{card.title}</h4>
              <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-medium ${statusColor}`}>
                {status}
              </span>
            </div>
            <p className="text-xs text-gray-400">{card.subtitle}</p>
          </div>
        </div>
        {(d.amount as number) !== undefined && (
          <span className="text-sm font-bold text-gray-100">
            ${(d.amount as number).toFixed(2)}
          </span>
        )}
      </div>
    </div>
  )
}

function StatsCard({ card }: { card: ResultCard }) {
  const d = card.data
  return (
    <div className="rounded-xl border border-gray-700/50 bg-gray-800/60 p-4 transition-all hover:border-vault-600/50">
      <p className="text-xs text-gray-400">{card.title}</p>
      <p className="mt-1 text-2xl font-bold text-gray-100">{card.subtitle ?? ''}</p>
      {typeof d.label === 'string' && <p className="mt-1 text-xs text-gray-500">{d.label}</p>}
    </div>
  )
}

function ResultCardComponent({ card }: { card: ResultCard }) {
  switch (card.type) {
    case 'subscription':
      return <SubscriptionCard card={card} />
    case 'listing':
      return <ListingCard card={card} />
    case 'match':
      return <MatchCard card={card} />
    case 'escrow':
      return <EscrowCard card={card} />
    case 'stats':
      return <StatsCard card={card} />
    default:
      return null
  }
}

// ---------------------------------------------------------------------------
// Message Bubble
// ---------------------------------------------------------------------------

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {/* Avatar */}
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-vault-600/20 text-vault-400">
          <Bot className="h-4 w-4" />
        </div>
      )}

      <div className={`flex max-w-[80%] flex-col gap-2 ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Text */}
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? 'bg-vault-600 text-white'
              : 'bg-gray-800 text-gray-200'
          }`}
        >
          {message.loading && !message.content ? (
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-vault-400" />
              <span className="text-gray-400">Thinking...</span>
            </div>
          ) : (
            <div className="whitespace-pre-wrap">
              <span dangerouslySetInnerHTML={{ __html: formatMessage(message.content) }} />
              {message.loading && message.content && (
                <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-vault-400 align-text-bottom" />
              )}
            </div>
          )}
        </div>

        {/* Cards */}
        {message.cards && message.cards.length > 0 && (
          <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
            {message.cards.slice(0, 6).map((card, i) => (
              <ResultCardComponent key={i} card={card} />
            ))}
          </div>
        )}

        {/* Suggestions */}
        {message.suggestions && message.suggestions.length > 0 && !message.loading && (
          <div className="flex flex-wrap gap-1.5">
            {message.suggestions.map((s, i) => (
              <SuggestionChip key={i} text={s} />
            ))}
          </div>
        )}
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-700 text-gray-300">
          <User className="h-4 w-4" />
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Suggestion Chip
// ---------------------------------------------------------------------------

function SuggestionChip({ text }: { text: string }) {
  const { addMessage, setChatLoading, messages } = useAppStore()

  const handleClick = async () => {
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    }
    addMessage(userMsg)
    setChatLoading(true)

    const msgId = `msg-${Date.now() + 1}`
    const loadingMsg: ChatMessage = {
      id: msgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      loading: true,
    }
    addMessage(loadingMsg)

    const history = messages.map((m) => ({
      role: m.role,
      content: m.content,
      timestamp: m.timestamp,
    }))

    let accumulated = ''
    streamAgentChat(
      { message: text, conversation_history: history },
      {
        onToken: (token) => {
          accumulated += token
          useAppStore.getState().updateMessage(msgId, {
            content: accumulated,
            loading: false,
          })
        },
        onCards: (cards, suggestions) => {
          useAppStore.getState().updateMessage(msgId, { cards, suggestions })
        },
        onDone: () => {
          setChatLoading(false)
        },
        onError: () => {
          useAppStore.getState().updateMessage(msgId, {
            content: "Sorry, I couldn't process that. Please try again.",
            loading: false,
          })
          setChatLoading(false)
        },
      },
    )
  }

  return (
    <button
      onClick={handleClick}
      className="flex items-center gap-1.5 rounded-full border border-gray-700 bg-gray-800/60 px-3 py-1.5 text-xs font-medium text-gray-300 transition-all hover:border-vault-600/50 hover:bg-gray-800 hover:text-vault-400"
    >
      <ChevronRight className="h-3 w-3" />
      {text}
    </button>
  )
}

// ---------------------------------------------------------------------------
// Formatting Helpers
// ---------------------------------------------------------------------------

function formatMessage(content: string): string {
  // Basic markdown-like formatting
  return content
    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-gray-100 font-semibold">$1</strong>')
    .replace(/`(.*?)`/g, '<code class="rounded bg-gray-700/50 px-1.5 py-0.5 text-xs text-vault-300">$1</code>')
    .replace(/\n/g, '<br />')
}

// ---------------------------------------------------------------------------
// Welcome Screen
// ---------------------------------------------------------------------------

function WelcomeScreen() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4">
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-vault-600/20">
        <Sparkles className="h-10 w-10 text-vault-400" />
      </div>
      <h2 className="text-2xl font-bold text-gray-100">Welcome to Vault Agent</h2>
      <p className="mt-2 max-w-md text-center text-sm text-gray-400">
        Your AI-powered subscription assistant. Tell me what you need — I'll handle
        the rest.
      </p>
      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {[
          { icon: CreditCard, text: 'Show my subscriptions', color: 'text-vault-400' },
          { icon: Store, text: 'Find marketplace matches', color: 'text-blue-400' },
          { icon: Zap, text: 'Optimize my spending', color: 'text-emerald-400' },
          { icon: BarChart3, text: 'View dashboard', color: 'text-purple-400' },
          { icon: Wallet, text: 'Check escrow status', color: 'text-yellow-400' },
          { icon: MessageSquare, text: 'Create a listing', color: 'text-pink-400' },
        ].map(({ text }) => (
          <SuggestionChip key={text} text={text} />
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main ChatPage
// ---------------------------------------------------------------------------

export default function ChatPage() {
  const { messages, chatLoading, addMessage, setChatLoading } = useAppStore()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const showWelcome = messages.length === 0

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || chatLoading) return

    setInput('')

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    }
    addMessage(userMsg)
    setChatLoading(true)

    const msgId = `msg-${Date.now() + 1}`
    const loadingMsg: ChatMessage = {
      id: msgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      loading: true,
    }
    addMessage(loadingMsg)

    const history = messages.map((m) => ({
      role: m.role,
      content: m.content,
      timestamp: m.timestamp,
    }))

    let accumulated = ''
    streamAgentChat(
      { message: text, conversation_history: history },
      {
        onToken: (token) => {
          accumulated += token
          useAppStore.getState().updateMessage(msgId, {
            content: accumulated,
            loading: false,
          })
        },
        onCards: (cards, suggestions) => {
          useAppStore.getState().updateMessage(msgId, { cards, suggestions })
        },
        onDone: () => {
          setChatLoading(false)
        },
        onError: () => {
          useAppStore.getState().updateMessage(msgId, {
            content: "Sorry, something went wrong. Please try again.",
            loading: false,
          })
          setChatLoading(false)
        },
      },
    )
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        {showWelcome ? (
          <WelcomeScreen />
        ) : (
          <div className="mx-auto max-w-3xl space-y-6 px-4 py-6">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-800 bg-gray-900/80 px-4 py-4 backdrop-blur">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-center gap-3 rounded-2xl border border-gray-700 bg-gray-800 px-4 py-2 transition-all focus-within:border-vault-600/50">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask Vault Agent anything..."
              className="flex-1 bg-transparent text-sm text-gray-100 placeholder-gray-500 focus:outline-none"
              disabled={chatLoading}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || chatLoading}
              className="flex h-9 w-9 items-center justify-center rounded-xl bg-vault-600 text-white transition-all hover:bg-vault-500 disabled:opacity-40 disabled:hover:bg-vault-600"
            >
              {chatLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </div>
          <p className="mt-2 text-center text-[11px] text-gray-600">
            Vault Agent — AI-powered subscription management
          </p>
        </div>
      </div>
    </div>
  )
}

// Small helper icon component
function TrendingUpIcon({ className }: { className?: string }) {
  return <ArrowUpRight className={className} />
}
