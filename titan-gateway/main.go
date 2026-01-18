package main

import (
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
	
	_ "titan-gateway/docs" 
)

// Config holds environment variables
type Config struct {
	Port          string
	TargetCoreURL string
}

// @title           Titan Core Banking API
// @version         1.0
// @description     API Gateway for Titan System.
// @host            rabbit-das-trusted-trading.trycloudflare.com
// @BasePath        /
// @schemes         https
func main() {
	cfg := loadConfig()
	gin.SetMode(gin.ReleaseMode)

	targetURL, err := url.Parse(cfg.TargetCoreURL)
	if err != nil {
		log.Fatalf("Invalid Target URL: %v", err)
	}
	proxy := httputil.NewSingleHostReverseProxy(targetURL)
	proxy.Director = func(req *http.Request) {
		req.Header.Add("X-Forwarded-Host", req.Host)
		req.URL.Scheme = targetURL.Scheme
		req.URL.Host = targetURL.Host
	}

	r := gin.New()
	r.Use(gin.Recovery())
	r.Use(cors.Default())

	// ✅ 1. Swagger Route
	r.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

	// ✅ 2. Health Check
	r.GET("/health", HealthCheck)

	// ✅ 3. Demo API
	r.GET("/api/v1/demo", DemoHandler)

	// 🔀 Proxy Everything Else
	r.NoRoute(func(c *gin.Context) {
		proxy.ServeHTTP(c.Writer, c.Request)
	})

	log.Printf("🚀 Gateway running on port %s", cfg.Port)
	r.Run(":" + cfg.Port)
}

// HealthCheck godoc
// @Summary      Show Gateway Health
// @Description  Check if the gateway is running.
// @Tags         System
// @Accept       json
// @Produce      json
// @Success      200  {object}  map[string]string
// @Router       /health [get]
func HealthCheck(c *gin.Context) {
	c.JSON(200, gin.H{
		"status": "Online 🟢",
		"system": "Titan Gateway",
	})
}

// DemoHandler godoc
// @Summary      Test Transaction API
// @Description  This is a fake endpoint to show on Swagger.
// @Tags         Transactions
// @Accept       json
// @Produce      json
// @Success      200  {object}  map[string]string
// @Router       /api/v1/demo [get]
func DemoHandler(c *gin.Context) {
	c.JSON(200, gin.H{
		"message": "This is a demo transaction",
	})
}

func loadConfig() Config {
	target := os.Getenv("TARGET_CORE_URL")
	if target == "" {
		target = "http://localhost:8080"
	}
	return Config{
		Port:          "8000",
		TargetCoreURL: target,
	}
}