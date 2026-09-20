# Build stage
FROM golang:1.22-alpine AS builder
WORKDIR /workspace

# Copy dependency manifests
COPY go.mod go.mod
COPY go.sum go.sum
RUN go mod download

# Copy source code
COPY main.go main.go
COPY api/ api/
COPY controllers/ controllers/

# Build with SLSA-recommended reproducibility flags (-trimpath, stripped symbols)
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags="-s -w" -o manager main.go

# Final minimal runner stage
FROM gcr.io/distroless/static:nonroot
WORKDIR /
COPY --from=builder /workspace/manager .
USER 65532:65532

ENTRYPOINT ["/manager"]