import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

// Response interceptor — unwrap data, surface errors
api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const message = err.response?.data?.detail || err.message || 'Network error'
    return Promise.reject(new Error(message))
  }
)

// ── Recommendations ──────────────────────────────────────────────────────────

/**
 * Fetch top-10 recommendations for a visitor.
 * @param {string} visitorId
 * @param {boolean} abTest - enable A/B variant assignment
 * @returns {Promise<{visitor_id, model_variant, recommendations, count, latency_ms, cache_hit}>}
 */
export const getRecommendations = (visitorId, abTest = true) =>
  api.get(`/recommend/${visitorId}`, { params: { ab_test: abTest } })

// ── Interactions ─────────────────────────────────────────────────────────────

/**
 * Log a user interaction event.
 * @param {string} visitorId
 * @param {string} itemId
 * @param {'view'|'addtocart'|'transaction'} event
 */
export const logInteraction = (visitorId, itemId, event = 'view') =>
  api.post('/interaction/', { visitor_id: visitorId, item_id: itemId, event })

/**
 * Get interaction history for a visitor.
 */
export const getInteractionHistory = (visitorId, limit = 20) =>
  api.get(`/interaction/${visitorId}`, { params: { limit } })

// ── A/B Testing ──────────────────────────────────────────────────────────────

/**
 * Get aggregated A/B test metrics.
 * @returns {Promise<{model_a, model_b, lift_percent}>}
 */
export const getABMetrics = () => api.get('/ab-test/metrics')

/**
 * Record a click event for A/B tracking.
 */
export const recordClick = (visitorId, itemId) =>
  api.post('/ab-test/click', { visitor_id: visitorId, item_id: itemId })

/**
 * Record a conversion event.
 */
export const recordConversion = (visitorId, itemId) =>
  api.post('/ab-test/conversion', { visitor_id: visitorId, item_id: itemId })

/**
 * Check which A/B variant a visitor is assigned to.
 */
export const getVariant = (visitorId) =>
  api.get(`/ab-test/variant/${visitorId}`)

// ── Health ───────────────────────────────────────────────────────────────────

export const healthCheck = () => api.get('/health')

export default api
