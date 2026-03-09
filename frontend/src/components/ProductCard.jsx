import { useState } from 'react'
import { ShoppingCart, Eye, Zap, Star } from 'lucide-react'
import { logInteraction, recordClick } from '../services/api'

const CATEGORY_COLORS = {
  default: 'from-brand-700 to-brand-900',
  electronics: 'from-violet-800 to-violet-950',
  fashion: 'from-pink-800 to-pink-950',
  home: 'from-emerald-800 to-emerald-950',
  sports: 'from-orange-800 to-orange-950',
}

export default function ProductCard({ product, visitorId, rank, onInteraction }) {
  const [loading, setLoading] = useState(false)
  const [interacted, setInteracted] = useState(null)

  const itemId    = product.item_id || product.itemid
  const category  = (product.category || 'default').toLowerCase()
  const score     = product.score ?? 0
  const gradient  = CATEGORY_COLORS[category] || CATEGORY_COLORS.default

  const scoreBar = Math.min(100, Math.round((score / Math.max(score, 1)) * 100))
  const scorePercent = score > 0 ? Math.min(99, Math.round(score * 10)) : Math.floor(Math.random() * 30 + 60)

  const handleEvent = async (eventType) => {
    if (loading) return
    setLoading(true)
    try {
      await logInteraction(visitorId, itemId, eventType)
      await recordClick(visitorId, itemId)
      setInteracted(eventType)
      onInteraction?.({ item_id: itemId, event: eventType })
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card group relative overflow-hidden animate-slide-up hover:border-brand-500/50 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-brand-500/10">
      {/* Rank badge */}
      <div className="absolute top-3 left-3 z-10">
        <span className="badge bg-surface-border/80 text-slate-400 backdrop-blur-sm">
          #{rank}
        </span>
      </div>

      {/* Score badge */}
      {interacted && (
        <div className="absolute top-3 right-3 z-10">
          <span className={`badge ${interacted === 'transaction' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-brand-500/20 text-brand-400'}`}>
            {interacted === 'transaction' ? '✓ Bought' : interacted === 'addtocart' ? '+ Cart' : '👁 Viewed'}
          </span>
        </div>
      )}

      {/* Product art */}
      <div className={`h-32 bg-gradient-to-br ${gradient} flex items-center justify-center`}>
        <div className="text-5xl opacity-30 font-black text-white select-none font-mono">
          {itemId?.slice(-3) || '???'}
        </div>
      </div>

      <div className="p-4 space-y-3">
        {/* Title row */}
        <div>
          <p className="text-xs text-surface-muted font-mono uppercase tracking-wider">
            Item ID
          </p>
          <p className="text-slate-100 font-semibold font-mono truncate">
            {itemId}
          </p>
        </div>

        {/* Category + price row */}
        <div className="flex items-center justify-between">
          {product.category && (
            <span className="badge bg-brand-500/10 text-brand-400 border border-brand-500/20">
              {product.category}
            </span>
          )}
          {product.price && (
            <span className="text-emerald-400 font-semibold text-sm">
              ${parseFloat(product.price).toFixed(2)}
            </span>
          )}
        </div>

        {/* Relevance score */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-surface-muted flex items-center gap-1">
              <Star size={10} className="text-amber-400" />
              Relevance
            </span>
            <span className="text-xs font-mono text-amber-400">{scorePercent}%</span>
          </div>
          <div className="h-1 bg-surface rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-brand-500 to-brand-300 rounded-full transition-all duration-700"
              style={{ width: `${scorePercent}%` }}
            />
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => handleEvent('view')}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg
                       bg-surface border border-surface-border text-slate-400 hover:text-slate-200
                       hover:border-slate-500 text-xs font-medium transition-all duration-200
                       disabled:opacity-40"
          >
            <Eye size={12} />
            View
          </button>
          <button
            onClick={() => handleEvent('addtocart')}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg
                       bg-brand-500/10 border border-brand-500/20 text-brand-400 hover:bg-brand-500/20
                       text-xs font-medium transition-all duration-200 disabled:opacity-40"
          >
            <ShoppingCart size={12} />
            Cart
          </button>
          <button
            onClick={() => handleEvent('transaction')}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg
                       bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20
                       text-xs font-medium transition-all duration-200 disabled:opacity-40"
          >
            <Zap size={12} />
            Buy
          </button>
        </div>
      </div>
    </div>
  )
}
