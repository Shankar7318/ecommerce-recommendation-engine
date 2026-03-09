import { Clock, Zap, Database, FlaskConical } from 'lucide-react'
import ProductCard from './ProductCard'

function StatPill({ icon: Icon, label, value, color = 'text-slate-400' }) {
  return (
    <div className="flex items-center gap-2 bg-surface border border-surface-border rounded-xl px-4 py-2.5">
      <Icon size={14} className={color} />
      <span className="text-xs text-surface-muted">{label}</span>
      <span className={`text-sm font-mono font-semibold ${color}`}>{value}</span>
    </div>
  )
}

export default function RecommendationList({ data, visitorId, onInteraction }) {
  if (!data) return null

  const { recommendations = [], count, latency_ms, cache_hit, model_variant } = data

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-3">
        <StatPill
          icon={Clock}
          label="Latency"
          value={`${latency_ms} ms`}
          color={latency_ms < 50 ? 'text-emerald-400' : latency_ms < 100 ? 'text-amber-400' : 'text-red-400'}
        />
        <StatPill
          icon={Database}
          label="Cache"
          value={cache_hit ? 'HIT' : 'MISS'}
          color={cache_hit ? 'text-emerald-400' : 'text-slate-400'}
        />
        <StatPill
          icon={FlaskConical}
          label="Variant"
          value={model_variant || '—'}
          color="text-brand-400"
        />
        <StatPill
          icon={Zap}
          label="Results"
          value={count}
          color="text-slate-300"
        />
      </div>

      {/* Grid */}
      {recommendations.length === 0 ? (
        <div className="card p-12 text-center">
          <p className="text-surface-muted text-sm">No recommendations found.</p>
          <p className="text-surface-muted text-xs mt-1">
            This may be a cold-start visitor. Try training the model first.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
          {recommendations.map((product, idx) => (
            <ProductCard
              key={product.item_id || idx}
              product={product}
              visitorId={visitorId}
              rank={idx + 1}
              onInteraction={onInteraction}
            />
          ))}
        </div>
      )}
    </div>
  )
}
