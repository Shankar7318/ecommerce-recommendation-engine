import { useState, useCallback } from 'react'
import { Search, Loader2, AlertCircle, Activity, ChevronRight } from 'lucide-react'
import { getRecommendations } from '../services/api'
import RecommendationList from '../components/RecommendationList'
import ABTestMetrics from '../components/ABTestMetrics'

const DEMO_IDS = ['1150468', '924643', '466800', '1048943', '735966']

const TABS = [
  { id: 'recommendations', label: 'Recommendations' },
  { id: 'ab_testing',      label: 'A/B Testing' },
]

export default function Dashboard() {
  const [visitorId, setVisitorId]   = useState('')
  const [inputVal,  setInputVal]    = useState('')
  const [data,      setData]        = useState(null)
  const [loading,   setLoading]     = useState(false)
  const [error,     setError]       = useState(null)
  const [activeTab, setActiveTab]   = useState('recommendations')

  const fetchRecs = useCallback(async (vid) => {
    const id = (vid || inputVal).trim()
    if (!id) return
    setVisitorId(id)
    setLoading(true)
    setError(null)
    setData(null)
    try {
      const result = await getRecommendations(id, true)
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [inputVal])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') fetchRecs()
  }

  return (
    <div className="min-h-screen bg-surface">
      {/* Nav */}
      <header className="border-b border-surface-border sticky top-0 z-50 bg-surface/95 backdrop-blur-sm">
        <div className="max-w-screen-2xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center">
              <Activity size={16} className="text-white" />
            </div>
            <div>
              <span className="font-semibold text-slate-100">RetailRocket</span>
              <span className="text-surface-muted ml-2 text-sm hidden sm:inline">Recommendation Engine</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="badge bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 animate-pulse-soft">
              ● Live
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-screen-2xl mx-auto px-6 py-8 space-y-8">
        {/* Hero search */}
        <div className="card p-6 md:p-8 space-y-5">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">
              Item-Based Collaborative Filtering
            </h1>
            <p className="text-surface-muted text-sm mt-1">
              Enter a RetailRocket visitor ID to generate top-10 personalised product recommendations
            </p>
          </div>

          <div className="flex gap-3 max-w-xl">
            <div className="relative flex-1">
              <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-surface-muted pointer-events-none" />
              <input
                type="text"
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="e.g. 1150468"
                className="input-field pl-10"
              />
            </div>
            <button
              onClick={() => fetchRecs()}
              disabled={loading || !inputVal.trim()}
              className="btn-primary flex items-center gap-2"
            >
              {loading ? <Loader2 size={15} className="animate-spin" /> : <ChevronRight size={15} />}
              {loading ? 'Loading…' : 'Recommend'}
            </button>
          </div>

          {/* Demo IDs */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-surface-muted">Try demo IDs:</span>
            {DEMO_IDS.map((id) => (
              <button
                key={id}
                onClick={() => { setInputVal(id); fetchRecs(id) }}
                className="font-mono text-xs px-3 py-1.5 rounded-lg bg-surface border border-surface-border
                           text-surface-muted hover:text-slate-200 hover:border-slate-500
                           transition-all duration-200"
              >
                {id}
              </button>
            ))}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-surface-border">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-all duration-200 -mb-px
                ${activeTab === tab.id
                  ? 'border-brand-500 text-brand-400'
                  : 'border-transparent text-surface-muted hover:text-slate-300'}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === 'recommendations' && (
          <div className="min-h-[400px]">
            {error && (
              <div className="card p-5 border-red-500/30 bg-red-500/5 flex items-start gap-3 animate-fade-in">
                <AlertCircle size={16} className="text-red-400 mt-0.5 shrink-0" />
                <div>
                  <p className="text-red-400 font-medium text-sm">Request failed</p>
                  <p className="text-red-400/70 text-xs mt-0.5">{error}</p>
                </div>
              </div>
            )}

            {loading && (
              <div className="flex flex-col items-center justify-center gap-3 py-24 animate-fade-in">
                <Loader2 size={28} className="animate-spin text-brand-400" />
                <p className="text-surface-muted text-sm">Fetching recommendations for <span className="font-mono text-slate-300">{visitorId}</span>…</p>
              </div>
            )}

            {!loading && !error && data && (
              <RecommendationList
                data={data}
                visitorId={visitorId}
                onInteraction={() => {}}
              />
            )}

            {!loading && !error && !data && (
              <div className="flex flex-col items-center justify-center gap-3 py-24 opacity-40">
                <Search size={36} className="text-surface-muted" />
                <p className="text-surface-muted text-sm">Enter a visitor ID above to see recommendations</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'ab_testing' && <ABTestMetrics />}
      </main>
    </div>
  )
}
