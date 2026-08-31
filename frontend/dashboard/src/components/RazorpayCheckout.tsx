import { useState, useCallback, useEffect } from 'react'
import {
  CreditCard,
  Smartphone,
  Building2,
  Wallet,
  Shield,
  CheckCircle2,
  XCircle,
  Loader2,
  ArrowLeft,
  Lock,
} from 'lucide-react'
import { api } from '../api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RazorpayOrderResponse {
  order_id: string
  amount: number
  currency: string
  key_id: string
  receipt: string | null
  escrow_id: string | null
}

export interface VerifyPaymentResponse {
  verified: boolean
  order_id: string
  payment_id: string
  amount: number
  currency: string
  status: string
  method: string
  message: string
}

type PaymentMethod = 'card' | 'upi' | 'netbanking' | 'wallet' | 'emi'
type PaymentStatus = 'idle' | 'processing' | 'success' | 'failed'

interface RazorpayCheckoutProps {
  amount: number
  matchId?: string
  currency?: string
  onSuccess?: (result: VerifyPaymentResponse) => void
  onFailure?: (error: string) => void
  onCancel?: () => void
}

interface RazorpayWindow {
  Razorpay: new (options: Record<string, unknown>) => {
    open: () => void
    on: (event: string, handler: (response: Record<string, unknown>) => void) => void
  }
}

// ---------------------------------------------------------------------------
// Payment method icons
// ---------------------------------------------------------------------------

const PAYMENT_METHODS: { id: PaymentMethod; label: string; icon: typeof CreditCard; description: string }[] = [
  { id: 'card', label: 'Credit / Debit Card', icon: CreditCard, description: 'Visa, Mastercard, Rupay' },
  { id: 'upi', label: 'UPI', icon: Smartphone, description: 'GPay, PhonePe, Paytm, BHIM' },
  { id: 'netbanking', label: 'Net Banking', icon: Building2, description: 'All major banks' },
  { id: 'wallet', label: 'Wallets', icon: Wallet, description: 'Paytm, Amazon Pay, Mobikwik' },
  { id: 'emi', label: 'EMI', icon: CreditCard, description: 'Easy monthly installments' },
]

// ---------------------------------------------------------------------------
// Razorpay script loader
// ---------------------------------------------------------------------------

function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if ((window as unknown as RazorpayWindow).Razorpay) {
      resolve(true)
      return
    }
    const script = document.createElement('script')
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.onload = () => resolve(true)
    script.onerror = () => resolve(false)
    document.body.appendChild(script)
  })
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function RazorpayCheckout({
  amount,
  matchId,
  currency = 'INR',
  onSuccess,
  onFailure,
  onCancel,
}: RazorpayCheckoutProps) {
  const [selectedMethod, setSelectedMethod] = useState<PaymentMethod>('card')
  const [status, setStatus] = useState<PaymentStatus>('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const [, setOrderId] = useState<string | null>(null)
  const [, setEscrowId] = useState<string | null>(null)
  const [, setKeyId] = useState<string>('')

  // Load Razorpay script on mount
  useEffect(() => {
    loadRazorpayScript()
  }, [])

  // Step 1: Create order
  const handleCreateOrder = useCallback(async () => {
    setStatus('processing')
    setErrorMessage('')

    try {
      const { data } = await api.post<RazorpayOrderResponse>('/api/v1/razorpay/create-order', {
        amount,
        currency,
        match_id: matchId,
        notes: { payment_method: selectedMethod },
      })

      setOrderId(data.order_id)
      setEscrowId(data.escrow_id)
      setKeyId(data.key_id)

      // Step 2: Open Razorpay checkout
      openRazorpayCheckout(data)
    } catch (err: unknown) {
      setStatus('failed')
      const msg = err instanceof Error ? err.message : 'Failed to create payment order'
      setErrorMessage(msg)
      onFailure?.(msg)
    }
  }, [amount, currency, matchId, selectedMethod, onFailure])

  // Step 2: Open Razorpay checkout popup
  const openRazorpayCheckout = useCallback(
    (order: RazorpayOrderResponse) => {
      const razorpay = new (window as unknown as RazorpayWindow).Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: 'Vault',
        description: 'Subscription access payment',
        order_id: order.order_id,
        handler: async (response: Record<string, unknown>) => {
          // Step 3: Verify payment
          const paymentId = response.razorpay_payment_id as string
          const signature = response.razorpay_signature as string

          try {
            const { data: verifyResult } = await api.post<VerifyPaymentResponse>(
              '/api/v1/razorpay/verify',
              {
                razorpay_order_id: order.order_id,
                razorpay_payment_id: paymentId,
                razorpay_signature: signature,
                escrow_id: order.escrow_id,
              },
            )

            if (verifyResult.verified) {
              setStatus('success')
              onSuccess?.(verifyResult)
            } else {
              setStatus('failed')
              setErrorMessage('Payment verification failed')
              onFailure?.('Payment verification failed')
            }
          } catch (err: unknown) {
            setStatus('failed')
            const msg = err instanceof Error ? err.message : 'Payment verification error'
            setErrorMessage(msg)
            onFailure?.(msg)
          }
        },
        prefill: {
          contact: '',
          email: '',
        },
        notes: {
          vault_order_id: order.order_id,
        },
        theme: {
          color: '#7c3aed', // vault violet
        },
        method: {
          netbanking: selectedMethod === 'netbanking' ? undefined : false,
          card: selectedMethod === 'card' ? undefined : false,
          upi: selectedMethod === 'upi' ? undefined : false,
          wallet: selectedMethod === 'wallet' ? undefined : false,
          emi: selectedMethod === 'emi' ? undefined : false,
        },
      })

      razorpay.on('payment.failed', (response: Record<string, unknown>) => {
        const error = response.error as { description?: string } | undefined
        setStatus('failed')
        setErrorMessage(error?.description || 'Payment failed')
        onFailure?.(error?.description || 'Payment failed')
      })

      razorpay.open()
    },
    [selectedMethod, onSuccess, onFailure],
  )

  // ---------------------------------------------------------------------------
  // Render: Payment method selection
  // ---------------------------------------------------------------------------

  if (status === 'success') {
    return (
      <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-6 text-center">
        <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-400" />
        <h3 className="mt-3 text-lg font-semibold text-white">Payment Successful!</h3>
        <p className="mt-1 text-sm text-emerald-300">
          Your subscription access has been activated.
        </p>
        <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3">
          <p className="text-xs text-emerald-400">
            Amount: ₹{amount.toFixed(2)} • Verified ✓
          </p>
        </div>
      </div>
    )
  }

  if (status === 'failed') {
    return (
      <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-6 text-center">
        <XCircle className="mx-auto h-12 w-12 text-red-400" />
        <h3 className="mt-3 text-lg font-semibold text-white">Payment Failed</h3>
        <p className="mt-1 text-sm text-red-300">{errorMessage}</p>
        <div className="mt-4 flex gap-3 justify-center">
          <button
            onClick={() => { setStatus('idle'); setErrorMessage('') }}
            className="rounded-xl border border-slate-600 bg-slate-800 px-4 py-2 text-sm text-slate-200 hover:bg-slate-700 transition"
          >
            Try Again
          </button>
          <button
            onClick={onCancel}
            className="rounded-xl px-4 py-2 text-sm text-slate-400 hover:text-white transition"
          >
            Cancel
          </button>
        </div>
      </div>
    )
  }

  // Idle / Processing
  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Select Payment Method</h3>
          <p className="text-sm text-slate-400">Choose how you'd like to pay</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-white">₹{amount.toFixed(2)}</div>
          <div className="text-xs text-slate-400">Total amount</div>
        </div>
      </div>

      {/* Payment method cards */}
      <div className="space-y-2">
        {PAYMENT_METHODS.map((method) => {
          const Icon = method.icon
          const isSelected = selectedMethod === method.id
          return (
            <button
              key={method.id}
              onClick={() => setSelectedMethod(method.id)}
              disabled={status === 'processing'}
              className={`w-full flex items-center gap-3 rounded-xl border p-3 text-left transition ${
                isSelected
                  ? 'border-vault-500/50 bg-vault-500/10 ring-1 ring-vault-500/20'
                  : 'border-slate-700 bg-slate-900/50 hover:border-slate-500 hover:bg-slate-800/80'
              } ${status === 'processing' ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                isSelected ? 'bg-vault-500/20 text-vault-300' : 'bg-slate-800 text-slate-400'
              }`}>
                <Icon className="h-5 w-5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-white">{method.label}</div>
                <div className="text-xs text-slate-400">{method.description}</div>
              </div>
              <div className={`h-4 w-4 rounded-full border-2 ${
                isSelected
                  ? 'border-vault-500 bg-vault-500'
                  : 'border-slate-600'
              }`}>
                {isSelected && <div className="h-full w-full rounded-full bg-white scale-[0.4]" />}
              </div>
            </button>
          )
        })}
      </div>

      {/* Security badge */}
      <div className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/50 p-3">
        <Shield className="h-4 w-4 text-emerald-400 shrink-0" />
        <p className="text-xs text-slate-400">
          Payments are secured by Razorpay. Your card details are never stored on our servers.
        </p>
        <Lock className="h-3 w-3 text-slate-500 shrink-0" />
      </div>

      {/* Pay button */}
      <button
        onClick={handleCreateOrder}
        disabled={status === 'processing'}
        className="w-full flex items-center justify-center gap-2 rounded-xl bg-vault-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-vault-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {status === 'processing' ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <Lock className="h-4 w-4" />
            Pay ₹{amount.toFixed(2)}
          </>
        )}
      </button>

      {/* Cancel */}
      {onCancel && (
        <button
          onClick={onCancel}
          disabled={status === 'processing'}
          className="w-full flex items-center justify-center gap-1 text-sm text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="h-3 w-3" />
          Cancel and go back
        </button>
      )}
    </div>
  )
}
