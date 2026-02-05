# ដំណាក់កាលទី ១: Build (ប្រើ Go 1.24 ឬថ្មីជាងនេះ)
FROM golang:1.25-alpine AS builder

WORKDIR /app

# Copy dependency files
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build ឱ្យចេញជា Binary
RUN go build -o main .

# ដំណាក់កាលទី ២: Run
FROM alpine:latest
WORKDIR /root/

# Copy Binary ពីដំណាក់កាលទី ១
COPY --from=builder /app/main .

EXPOSE 8000

CMD ["./main"]