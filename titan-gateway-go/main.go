package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"gopkg.in/yaml.v3"
)

// =============================================================================
// Config
// =============================================================================

type Config struct {
	Upstreams struct {
		CoreBanking  string `yaml:"core_banking"`
		Notification string `yaml:"notification"`
		Promotion    string `yaml:"promotion"`
		AIService    string `yaml:"ai_service"`
	} `yaml:"upstreams"`
	Auth struct {
		JWTSecret string `yaml:"jwt_secret"`
	} `yaml:"auth"`
	RateLimit struct {
		// Max requests allowed per IP within the window
		MaxRequests int `yaml:"max_requests"`
		// Window duration in seconds (default: 60 = 1 minute)
		WindowSeconds int `yaml:"window_seconds"`
		// How long a blocked IP stays blocked, in minutes (default: 5)
		BlockMinutes int `yaml:"block_minutes"`
	} `yaml:"rate_limit"`
	Server struct {
		Port string `yaml:"port"`
	} `yaml:"server"`
}

func loadConfig() *Config {
	path := "config.yaml"
	if p := os.Getenv("CONFIG_PATH"); p != "" {
		path = p
	}
	data, err := os.ReadFile(path)
	if err != nil {
		log.Fatalf("failed to read config: %v", err)
	}
	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		log.Fatalf("failed to parse config: %v", err)
	}
	// Defaults
	if cfg.Server.Port == "" {
		cfg.Server.Port = "8088"
	}
	if cfg.RateLimit.MaxRequests == 0 {
		cfg.RateLimit.MaxRequests = 100
	}
	if cfg.RateLimit.WindowSeconds == 0 {
		cfg.RateLimit.WindowSeconds = 60
	}
	if cfg.RateLimit.BlockMinutes == 0 {
		cfg.RateLimit.BlockMinutes = 5
	}
	return &cfg
}

// =============================================================================
// Sliding-Window Rate Limiter + IP Blocker
//
// Algorithm:
//   Each IP keeps a list of timestamps for requests made within the window.
//   On every request:
//     1. Check if IP is currently blocked → reject immediately.
//     2. Drop timestamps older than the window.
//     3. Count remaining timestamps.
//     4. If count >= maxRequests → BLOCK the IP for blockDuration, reject.
//     5. Otherwise → append current timestamp, allow.
//
// This is a true sliding window (not fixed bucket), so bursting exactly at
// a window boundary cannot bypass the limit.
// =============================================================================

type ipState struct {
	// timestamps of requests inside the current window
	timestamps []time.Time
	// zero value means not blocked
	blockedUntil time.Time
}

type slidingWindowLimiter struct {
	mu           sync.Mutex
	states       map[string]*ipState
	maxRequests  int
	window       time.Duration
	blockDur     time.Duration
	// cleanup ticker — prevents unbounded memory growth
	cleanupEvery time.Duration
}

func newSlidingWindowLimiter(maxRequests, windowSeconds, blockMinutes int) *slidingWindowLimiter {
	l := &slidingWindowLimiter{
		states:       make(map[string]*ipState),
		maxRequests:  maxRequests,
		window:       time.Duration(windowSeconds) * time.Second,
		blockDur:     time.Duration(blockMinutes) * time.Minute,
		cleanupEvery: 5 * time.Minute,
	}
	go l.cleanupLoop()
	return l
}

// allow returns (allowed bool, blockedUntil time.Time, currentCount int)
func (l *slidingWindowLimiter) allow(ip string) (bool, time.Time, int) {
	l.mu.Lock()
	defer l.mu.Unlock()

	now := time.Now()
	state, ok := l.states[ip]
	if !ok {
		state = &ipState{}
		l.states[ip] = state
	}

	// ── 1. Already blocked? ───────────────────────────────────────────────────
	if now.Before(state.blockedUntil) {
		return false, state.blockedUntil, l.maxRequests
	}

	// ── 2. Slide the window — drop old timestamps ─────────────────────────────
	cutoff := now.Add(-l.window)
	fresh := state.timestamps[:0]
	for _, t := range state.timestamps {
		if t.After(cutoff) {
			fresh = append(fresh, t)
		}
	}
	state.timestamps = fresh

	// ── 3. Count requests in current window ───────────────────────────────────
	count := len(state.timestamps)

	// ── 4. Limit reached → BLOCK ──────────────────────────────────────────────
	if count >= l.maxRequests {
		state.blockedUntil = now.Add(l.blockDur)
		state.timestamps = nil // clear — no point tracking while blocked
		log.Printf("🚫 BLOCKED  IP=%-20s  hit %d req/%ds  blocked for %s",
			ip, l.maxRequests, int(l.window.Seconds()), l.blockDur)
		return false, state.blockedUntil, count
	}

	// ── 5. Allow — record this timestamp ─────────────────────────────────────
	state.timestamps = append(state.timestamps, now)
	return true, time.Time{}, count + 1
}

// blockedIPs returns a snapshot of currently blocked IPs (for /health/rate-limits)
func (l *slidingWindowLimiter) blockedIPs() map[string]string {
	l.mu.Lock()
	defer l.mu.Unlock()
	now := time.Now()
	result := make(map[string]string)
	for ip, state := range l.states {
		if now.Before(state.blockedUntil) {
			result[ip] = fmt.Sprintf("blocked until %s (%.0fs remaining)",
				state.blockedUntil.Format(time.RFC3339),
				time.Until(state.blockedUntil).Seconds())
		}
	}
	return result
}

// cleanupLoop removes expired entries every cleanupEvery interval.
func (l *slidingWindowLimiter) cleanupLoop() {
	ticker := time.NewTicker(l.cleanupEvery)
	defer ticker.Stop()
	for range ticker.C {
		l.mu.Lock()
		now := time.Now()
		cutoff := now.Add(-l.window)
		removed := 0
		for ip, state := range l.states {
			// Remove if not blocked and has no recent timestamps
			if now.After(state.blockedUntil) {
				fresh := state.timestamps[:0]
				for _, t := range state.timestamps {
					if t.After(cutoff) {
						fresh = append(fresh, t)
					}
				}
				if len(fresh) == 0 {
					delete(l.states, ip)
					removed++
				} else {
					state.timestamps = fresh
				}
			}
		}
		if removed > 0 {
			log.Printf("🧹 rate-limiter cleanup: removed %d idle IP entries", removed)
		}
		l.mu.Unlock()
	}
}

// =============================================================================
// Public path list — skip JWT check
// =============================================================================

var publicPaths = []string{
	"/api/v1/auth/login",
	"/api/v1/auth/register",
	"/health",
}

func isPublic(path string) bool {
	for _, p := range publicPaths {
		if strings.HasPrefix(path, p) {
			return true
		}
	}
	return false
}

// =============================================================================
// Middleware: CORS
// =============================================================================

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Idempotency-Key")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

// =============================================================================
// Middleware: Rate Limit (sliding window + IP block)
// =============================================================================

func rateLimitMiddleware(lim *slidingWindowLimiter, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ip := extractIP(r)
		allowed, blockedUntil, count := lim.allow(ip)

		// Always add informational headers (like GitHub API does)
		w.Header().Set("X-RateLimit-Limit", fmt.Sprintf("%d", lim.maxRequests))
		w.Header().Set("X-RateLimit-Window", fmt.Sprintf("%ds", int(lim.window.Seconds())))
		w.Header().Set("X-RateLimit-Remaining", fmt.Sprintf("%d", max(0, lim.maxRequests-count)))

		if !allowed {
			retryAfter := int(time.Until(blockedUntil).Seconds())
			w.Header().Set("Retry-After", fmt.Sprintf("%d", retryAfter))
			w.Header().Set("X-RateLimit-Remaining", "0")
			w.Header().Set("X-RateLimit-Reset", blockedUntil.UTC().Format(time.RFC3339))
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusTooManyRequests)
			json.NewEncoder(w).Encode(map[string]any{
				"error":       "Too many requests — your IP has been temporarily blocked",
				"ip":          ip,
				"blockedUntil": blockedUntil.UTC().Format(time.RFC3339),
				"retryAfter":  fmt.Sprintf("%ds", retryAfter),
			})
			return
		}

		next.ServeHTTP(w, r)
	})
}

// =============================================================================
// Middleware: JWT
// =============================================================================

func jwtMiddleware(secret string, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if isPublic(r.URL.Path) {
			next.ServeHTTP(w, r)
			return
		}
		authHeader := r.Header.Get("Authorization")
		tokenStr, found := strings.CutPrefix(authHeader, "Bearer ")
		if !found || tokenStr == "" {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			json.NewEncoder(w).Encode(map[string]string{"error": "Missing Authorization header"})
			return
		}
		_, err := jwt.Parse(tokenStr, func(t *jwt.Token) (interface{}, error) {
			if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, jwt.ErrSignatureInvalid
			}
			return []byte(secret), nil
		})
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			json.NewEncoder(w).Encode(map[string]string{"error": "Invalid or expired token"})
			return
		}
		next.ServeHTTP(w, r)
	})
}

// =============================================================================
// Middleware: Logging
// =============================================================================

func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		lrw := &loggingResponseWriter{ResponseWriter: w, statusCode: http.StatusOK}
		next.ServeHTTP(lrw, r)
		// Highlight blocked requests in logs
		prefix := "✅"
		if lrw.statusCode == http.StatusTooManyRequests {
			prefix = "🚫"
		} else if lrw.statusCode >= 400 {
			prefix = "⚠️ "
		}
		log.Printf("%s %-6s %-45s %d  %v  ip=%s",
			prefix, r.Method, r.URL.Path, lrw.statusCode,
			time.Since(start), extractIP(r))
	})
}

type loggingResponseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (lrw *loggingResponseWriter) WriteHeader(code int) {
	lrw.statusCode = code
	lrw.ResponseWriter.WriteHeader(code)
}

// =============================================================================
// Helpers
// =============================================================================

// extractIP gets the real client IP, respecting X-Real-IP / X-Forwarded-For.
func extractIP(r *http.Request) string {
	// Trust X-Real-IP set by a trusted upstream (nginx, load balancer)
	if ip := r.Header.Get("X-Real-IP"); ip != "" {
		return strings.TrimSpace(ip)
	}
	// X-Forwarded-For: client, proxy1, proxy2 — take the first
	if fwd := r.Header.Get("X-Forwarded-For"); fwd != "" {
		parts := strings.SplitN(fwd, ",", 2)
		return strings.TrimSpace(parts[0])
	}
	// Fall back to RemoteAddr (strip port)
	ip := r.RemoteAddr
	if i := strings.LastIndex(ip, ":"); i != -1 {
		ip = ip[:i]
	}
	return ip
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// =============================================================================
// Reverse Proxy
// =============================================================================

func newProxy(target string) http.Handler {
	u, err := url.Parse(target)
	if err != nil {
		log.Fatalf("invalid upstream %q: %v", target, err)
	}
	proxy := httputil.NewSingleHostReverseProxy(u)
	orig := proxy.Director
	proxy.Director = func(req *http.Request) {
		orig(req)
		req.Header.Set("X-Gateway", "titan-gateway-go")
		req.Header.Set("X-Real-IP", extractIP(req))
	}
	return proxy
}

// =============================================================================
// Main
// =============================================================================

func main() {
	cfg := loadConfig()
	lim := newSlidingWindowLimiter(
		cfg.RateLimit.MaxRequests,
		cfg.RateLimit.WindowSeconds,
		cfg.RateLimit.BlockMinutes,
	)

	log.Printf("🛡️  Rate limit: %d req per %ds window — violators blocked %dm",
		cfg.RateLimit.MaxRequests,
		cfg.RateLimit.WindowSeconds,
		cfg.RateLimit.BlockMinutes)

	coreBanking  := newProxy(cfg.Upstreams.CoreBanking)
	notification := newProxy(cfg.Upstreams.Notification)
	promotion    := newProxy(cfg.Upstreams.Promotion)
	aiService    := newProxy(cfg.Upstreams.AIService)

	mux := http.NewServeMux()

	// ── Health check ─────────────────────────────────────────────────────────
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"status":  "UP",
			"service": "titan-gateway-go",
			"rateLimit": map[string]any{
				"maxRequests":   cfg.RateLimit.MaxRequests,
				"windowSeconds": cfg.RateLimit.WindowSeconds,
				"blockMinutes":  cfg.RateLimit.BlockMinutes,
			},
		})
	})

	// ── Rate limit status (shows currently blocked IPs) ───────────────────────
	mux.HandleFunc("/health/rate-limits", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		blocked := lim.blockedIPs()
		json.NewEncoder(w).Encode(map[string]any{
			"blockedCount": len(blocked),
			"blockedIPs":   blocked,
		})
	})

	// ── Auth routes (public — no JWT) ─────────────────────────────────────────
	mux.Handle("/api/v1/auth/", coreBanking)

	// ── Core-Banking routes ───────────────────────────────────────────────────
	mux.Handle("/api/v1/accounts/",              coreBanking)
	mux.Handle("/api/v1/accounts",               coreBanking)
	mux.Handle("/api/v1/transactions/",          coreBanking)
	mux.Handle("/api/v1/transactions",           coreBanking)
	mux.Handle("/api/v1/loans/",                 coreBanking)
	mux.Handle("/api/v1/loans",                  coreBanking)
	mux.Handle("/api/v1/qr/",                    coreBanking)
	mux.Handle("/api/v1/atm/",                   coreBanking)
	mux.Handle("/api/v1/users/",                 coreBanking)
	mux.Handle("/api/v1/users",                  coreBanking)
	mux.Handle("/api/v1/otp/",                   coreBanking)
	mux.Handle("/api/v1/notifications/",         coreBanking)
	mux.Handle("/api/v1/scheduled-transactions/",coreBanking)
	mux.Handle("/api/v1/scheduled-transactions", coreBanking)
	mux.Handle("/api/v1/fixed-deposits/",        coreBanking)
	mux.Handle("/api/v1/fixed-deposits",         coreBanking)
	mux.Handle("/api/v1/statements/",            coreBanking)
	mux.Handle("/api/v1/statements",             coreBanking)
	// OTP path used by core banking controller: /api/auth/otp/...
	mux.Handle("/api/auth/otp/",                 coreBanking)
	mux.Handle("/api/auth/otp",                  coreBanking)

	// ── Notification-service routes ───────────────────────────────────────────
	mux.Handle("/api/notify",       notification)
	mux.Handle("/api/audit/",       notification)
	mux.Handle("/api/preferences/", notification)

	// ── Promotion-service routes ──────────────────────────────────────────────
	// Legacy /promotions/... paths (deposit bonus, campaign status)
	mux.Handle("/promotions/",       promotion)
	mux.Handle("/promotions",        promotion)
	// Quest, referral, merchant, shadow rule, admin campaign paths
	mux.Handle("/api/quests/",       promotion)
	mux.Handle("/api/quests",        promotion)
	mux.Handle("/api/referrals/",    promotion)
	mux.Handle("/api/referrals",     promotion)
	mux.Handle("/api/merchant/",     promotion)
	mux.Handle("/api/merchant",      promotion)
	mux.Handle("/api/shadow/",       promotion)
	mux.Handle("/api/shadow",        promotion)
	mux.Handle("/admin/campaigns/",  promotion)
	mux.Handle("/admin/campaigns",   promotion)
	// v1-prefixed promotion paths (kept for future migration)
	mux.Handle("/api/v1/promotions/",promotion)
	mux.Handle("/api/v1/promotions", promotion)

	// ── AI service routes ─────────────────────────────────────────────────────
	mux.Handle("/api/ai/", aiService)

	// ── Middleware chain ──────────────────────────────────────────────────────
	handler := loggingMiddleware(
		corsMiddleware(
			rateLimitMiddleware(lim,
				jwtMiddleware(cfg.Auth.JWTSecret, mux),
			),
		),
	)

	addr := "0.0.0.0:" + cfg.Server.Port
	log.Printf("🚀 titan-gateway-go  listening on %s", addr)
	log.Printf("   core-banking  → %s", cfg.Upstreams.CoreBanking)
	log.Printf("   notifications → %s", cfg.Upstreams.Notification)
	log.Printf("   promotions    → %s", cfg.Upstreams.Promotion)
	log.Printf("   ai-service    → %s", cfg.Upstreams.AIService)

	srv := &http.Server{
		Addr:         addr,
		Handler:      handler,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 60 * time.Second,
		IdleTimeout:  120 * time.Second,
	}
	if err := srv.ListenAndServe(); err != nil {
		log.Fatal(err)
	}
}
