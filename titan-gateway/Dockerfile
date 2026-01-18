# 🛠️ STAGE 1: Build the Go App
FROM golang:alpine AS builder

WORKDIR /app

COPY . .

# 🔥 បន្ថែមបន្ទាត់នេះ៖ វានឹងបង្កើត go.sum និងទាញយក Library ដោយស្វ័យប្រវត្តិ
RUN go mod tidy

# Build កូដ
RUN go build -o main .

# 🚀 STAGE 2: Run the App
FROM alpine:latest
WORKDIR /root/
COPY --from=builder /app/main .
EXPOSE 8000
CMD ["./main"]
