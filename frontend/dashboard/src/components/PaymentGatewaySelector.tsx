import { useState } from 'react'
import { CreditCard, Smartphone, Shield, CheckCircle2, ArrowLeft } from 'lucide-react'
import RazorpayCheckout from './RazorpayCheckout'
import type { VerifyPaymentResponse } from './RazorpayCheckout'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Gateway = 'razorpay' | 'stripe'

interface PaymentGatewaySelectorProps {
  amount: number
  matchId?: string
  currency?: string
  onSuccess?: (result: VerifyPaymentResponse, gateway: Gateway) => void
  onFailure?: (error: string, gateway: Gateway) => void
  onCancel?: () => void
}

// ---------------------------------------------------------------------------
// Stripe Checkout (lightweight wrapper)
// ---------------------------------------------------------------------------

function StripeCheckout({
  amount,
  matchId,
  onSuccess,
  onFailure,
}: {
  amount: number
  matchId?: string
  onSuccess?: (result: VerifyPaymentResponse) => void
  onFailure?: (error: string) => void
}) {
  const [processing, setProcessing] = useState(false)

  const handlePay = async () => {
    setProcessing(true)
    try {
      // Use existing Stripe payment flow
      const { initiatePayment } = await import('../api')
      const result = await initiatePayment(matchId || '', 'card')
      if (result.access_granted) {
        onSuccess?.({
          verified: true,
          order_id: '',
          payment_id: result.payment_intent_id,
          amount: result.amount,
          currency: 'USD',
          status: 'captured',
          method: 'card',
          message: 'Payment successful',
        })
      } else {
        onFailure?.(result.message || 'Payment failed')
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Payment failed'
      onFailure?.(msg)
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="text-center">
        <CreditCard className="mx-auto h-10 w-10 text-blue-400" />
        <h3 className="mt-2 text-lg font-semibold text-white">Pay with Stripe</h3>
        <p className="text-sm text-slate-400">Credit card, debit card, or Apple Pay</p>
      </div>
      <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4 text-center">
        <div className="text-2xl font-bold text-white">${amount.toFixed(2)}</div>
        <div className="text-xs text-slate-400">USD • Stripe</div>
      </div>
      <button
        onClick={handlePay}
        disabled={processing}
        className="w-full flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50"
      >
        {processing ? 'Processing...' : `Pay $${amount.toFixed(2)}`}
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function PaymentGatewaySelector({
  amount,
  matchId,
  currency = 'INR',
  onSuccess,
  onFailure,
  onCancel,
}: PaymentGatewaySelectorProps) {
  const [selectedGateway, setSelectedGateway] = useState<Gateway | null>(null)

  // If a gateway is selected, show its checkout
  if (selectedGateway === 'razorpay') {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setSelectedGateway(null)}
          className="flex items-center gap-1 text-sm text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="h-3 w-3" />
          Back to payment methods
        </button>
        <RazorpayCheckout
          amount={amount}
          matchId={matchId}
          currency={currency}
          onSuccess={(result) => onSuccess?.(result, 'razorpay')}
          onFailure={(error) => onFailure?.(error, 'razorpay')}
          onCancel={() => setSelectedGateway(null)}
        />
      </div>
    )
  }

  if (selectedGateway === 'stripe') {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setSelectedGateway(null)}
          className="flex items-center gap-1 text-sm text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="h-3 w-3" />
          Back to payment methods
        </button>
        <StripeCheckout
          amount={amount}
          matchId={matchId}
          onSuccess={(result) => onSuccess?.(result, 'stripe')}
          onFailure={(error) => onFailure?.(error, 'stripe')}
        />
      </div>
    )
  }

  // Gateway selection screen
  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-lg font-semibold text-white">Choose Payment Gateway</h3>
        <p className="text-sm text-slate-400">Select your preferred payment provider</p>
      </div>

      <div className="space-y-3">
        {/* Razorpay */}
        <button
          onClick={() => setSelectedGateway('razorpay')}
          className="w-full flex items-center gap-4 rounded-xl border border-slate-700 bg-slate-900/50 p-4 text-left transition hover:border-vault-500/40 hover:bg-vault-500/5"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-500/15 text-violet-300">
            <Smartphone className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold text-white">Razorpay</div>
            <div className="text-xs text-slate-400">
              UPI • Cards • Net Banking • Wallets • EMI
            </div>
            <div className="mt-1 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
              <span className="text-[10px] text-emerald-400">Recommended for INR</span>
            </div>
          </div>
          <div className="text-xs text-slate-500">₹{amount.toFixed(2)}</div>
        </button>

        {/* Stripe */}
        <button
          onClick={() => setSelectedGateway('stripe')}
          className="w-full flex items-center gap-4 rounded-xl border border-slate-700 bg-slate-900/50 p-4 text-left transition hover:border-blue-500/40 hover:bg-blue-500/5"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/15 text-blue-300">
            <CreditCard className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold text-white">Stripe</div>
            <div className="text-xs text-slate-400">
              Credit Card • Debit Card • Apple Pay
            </div>
            <div className="mt-1 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-blue-400" />
              <span className="text-[10px] text-blue-400">Best for USD / International</span>
            </div>
          </div>
          <div className="text-xs text-slate-500">
            ${currency === 'INR' ? (amount / 83).toFixed(2) : amount.toFixed(2)}
          </div>
        </button>
      </div>

      {/* Security */}
      <div className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/50 p-3">
        <Shield className="h-4 w-4 text-emerald-400 shrink-0" />
        <p className="text-xs text-slate-400">
          Both gateways use PCI-DSS compliant tokenization. No card details touch our servers.
        </p>
      </div>

      {onCancel && (
        <button
          onClick={onCancel}
          className="w-full text-center text-sm text-slate-400 hover:text-white transition"
        >
          Cancel
        </button>
      )}
    </div>
  )
}
