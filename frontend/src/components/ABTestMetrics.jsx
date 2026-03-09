import { useEffect, useState, useCallback } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, Legend
} from 'recharts'
import { TrendingUp, TrendingDown, Minus, RefreshCw, FlaskConical } from 'lucide-react'
import { getABMetrics } from '../services/api'

const VARIANT_COLORS = { model_a: '#0ea5e9', model_b: '#a855f7' }

function MetricCard({ label, a, b, unit = '%', higherIsBetter = true }) {
  const diff = b - a
  const improved = higherIsBetter ? diff > 0 : diff < 0
  const neutral = Math.abs(diff) < 0.01

  return (
    <div className="card p-5 space-y-3">
      <p className="text-xs text-surface-muted uppercase tracking-wider">{label}</p>
      <div className="flex items-end justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-brand-500 inline-block" />
            <span className="text-xs text-surface-muted">Model A</span>
            <span className="text-slate-200 font-mono font-semibold">{a.toFixed(2)}{unit}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-violet-500 inline-block" />
            <span className="text-xs text-surface-muted">Model B</span>
            <span className="text-slate-200 font-mono font-semibold">{b.toFixed(2)}{unit}</span>
          </div>
        </div>
        <div className={`flex items-center gap-1 text-sm font-semibold ${neutral ? 'text-slate-400' : improved ? 'text-emerald-400' : 'text-red-400'}`}>
          {neutral ? <Minus size={14} /> : improved ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
          {Math.abs(diff).toFixed(2)}{unit}
        </div>
      </div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="card p-3 text-xs shadow-xl">
      <p className="text-slate-300 font-semibold mb-1">{label}</p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.fill }} />
          <span className="text-surface-muted">{p.name}:</span>
          <span className="font-mono text-slate-200">{p.value.toFixed(2)}%</span>
        </div>
      ))}
    </div>
  )
}

export default function ABTestMetrics() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchMetrics = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getABMetrics()
      setMetrics(data)
      setLastUpdated(new Date())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMetrics()
    const interval = setInterval(fetchMetrics, 30000) // auto-refresh every 30s
    return () => clearInterval(interval)
  }, [fetchMetrics])

  const a = metrics?.model_a
  const b = metrics?.model_b
  const lift = metrics?.lift_percent

  const chartData = [
    { name: 'CTR', 'Model A': a?.ctr ?? 0, 'Model B': b?.ctr ?? 0 },
    { name: 'Conversion', 'Model A': a?.conversion_rate ?? 0, 'Model B': b?.conversion_rate ?? 0 },
  ]

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConical size={18} className="text-brand-400" />
          <h2 className="text-lg font-semibold text-slate-100">A/B Test Metrics</h2>
          {lastUpdated && (
            <span className="text-xs text-surface-muted">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
        <button
          onClick={fetchMetrics}
          disabled={loading}
          className="flex items-center gap-2 text-xs text-surface-muted hover:text-slate-200
                     border border-surface-border hover:border-slate-500 rounded-xl px-3 py-2
                     transition-all duration-200 disabled:opacity-40"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="card p-4 border-red-500/30 bg-red-500/5">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {!metrics && !loading && !error && (
        <div className="card p-8 text-center">
          <p className="text-surface-muted text-sm">No A/B data yet. Start making recommendation requests.</p>
        </div>
      )}

      {metrics && a && b && (
        <>
          {/* Lift banner */}
          {lift !== null && lift !== undefined && (
            <div className={`card p-4 flex items-center justify-between border-l-4 ${lift > 0 ? 'border-l-emerald-500 bg-emerald-500/5' : lift < 0 ? 'border-l-red-500 bg-red-500/5' : 'border-l-slate-500'}`}>
              <div>
                <p className="text-xs text-surface-muted uppercase tracking-wider">Recommendation Lift</p>
                <p className="text-slate-100 text-sm mt-0.5">Model B vs Model A click-through rate</p>
              </div>
              <div className={`text-3xl font-bold font-mono ${lift > 0 ? 'text-emerald-400' : lift < 0 ? 'text-red-400' : 'text-slate-400'}`}>
                {lift > 0 ? '+' : ''}{lift.toFixed(1)}%
              </div>
            </div>
          )}

          {/* Metric cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <MetricCard label="Click-Through Rate" a={a.ctr} b={b.ctr} />
            <MetricCard label="Conversion Rate"    a={a.conversion_rate} b={b.conversion_rate} />
            <MetricCard label="Avg Rec Score"      a={a.avg_score * 100} b={b.avg_score * 100} />
          </div>

          {/* Volume cards */}
          <div className="grid grid-cols-3 gap-4">
            {['total_served', 'total_clicks', 'total_conversions'].map((key) => (
              <div key={key} className="card p-4 text-center">
                <p className="text-xs text-surface-muted capitalize mb-1">
                  {key.replace(/_/g, ' ')}
                </p>
                <div className="flex justify-around">
                  <div>
                    <div className="text-xs text-brand-400 mb-0.5">Model A</div>
                    <div className="font-mono font-bold text-slate-200">{(a[key] ?? 0).toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-xs text-violet-400 mb-0.5">Model B</div>
                    <div className="font-mono font-bold text-slate-200">{(b[key] ?? 0).toLocaleString()}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Chart */}
          <div className="card p-5">
            <p className="text-sm font-medium text-slate-300 mb-4">Performance Comparison</p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} barCategoryGap="35%">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} unit="%" />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                <Legend
                  iconType="circle" iconSize={8}
                  formatter={(v) => <span style={{ color: '#94a3b8', fontSize: 12 }}>{v}</span>}
                />
                <Bar dataKey="Model A" fill={VARIANT_COLORS.model_a} radius={[4,4,0,0]} />
                <Bar dataKey="Model B" fill={VARIANT_COLORS.model_b} radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
