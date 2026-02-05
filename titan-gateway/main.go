package main

import (
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"

	"github.com/gin-gonic/gin"
)

func main() {
	// 1. កំណត់ Port (Default: 8000)
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	// 2. កំណត់គោលដៅ Java Core (Default: http://titan-core:8080)
	target := os.Getenv("TARGET_CORE_URL")
	if target == "" {
		target = "http://localhost:8080"
	}

	targetURL, err := url.Parse(target)
	if err != nil {
		log.Fatalf("❌ Invalid Target URL: %v", err)
	}

	// 3. បង្កើត Router
	r := gin.Default()

	log.Printf("🚀 Titan Gateway starting on port %s forwarding to %s", port, target)

	// 4. Proxy Logic (បញ្ជូនគ្រប់យ៉ាងទៅ Java Core)
	// យើងប្រើ "ReverseProxy" ដើម្បីបញ្ជូន Request ទាំងមូល (Header, Body, Query)
	proxy := httputil.NewSingleHostReverseProxy(targetURL)

	// កែសម្រួល Request មុនបញ្ជូន (Optional)
	proxy.Director = func(req *http.Request) {
		req.Header.Add("X-Forwarded-Host", req.Host)
		req.Header.Add("X-Origin", "Titan-Gateway")
		req.URL.Scheme = targetURL.Scheme
		req.URL.Host = targetURL.Host
	}

	// 5. Catch-All Route (ចាប់យកគ្រប់ Request /api/...)
	r.Any("/*proxyPath", func(c *gin.Context) {
		proxy.ServeHTTP(c.Writer, c.Request)
	})

	// 6. Start Server
	if err := r.Run(":" + port); err != nil {
		log.Fatalf("❌ Failed to start server: %v", err)
	}
}