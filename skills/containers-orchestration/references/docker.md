# Docker & Container Best Practices

**Goal:** Production-ready Docker patterns, multi-stage builds, security scanning, and compose orchestration.

## Guiding Principles

1. **Security First**: Non-root users, minimal base images, vulnerability scanning
2. **Efficiency**: Multi-stage builds, layer optimization, build cache
3. **Reproducibility**: Pin versions, explicit dependencies, deterministic builds
4. **Observability**: Health checks, proper logging, metrics endpoints

---

## Dockerfile Best Practices

### Use Official Base Images

```dockerfile
# ✅ GOOD - Official, minimal, secure
FROM python:3.14-slim
FROM node:20-alpine

# ⭐ EXCELLENT - Distroless for production
FROM gcr.io/distroless/python3-debian12
FROM gcr.io/distroless/nodejs20-debian12

# ❌ AVOID - Large, unnecessary packages
FROM ubuntu:latest
```

### Pin Versions Explicitly

```dockerfile
# ✅ GOOD - Explicit version pinning
FROM python:3.14.0-slim-bookworm
FROM node:20.10.0-alpine3.19

# ❌ BAD - Unpredictable, non-reproducible
FROM python:latest
FROM node:alpine
```

### Use Multi-Stage Builds

**Node.js Example:**

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine
WORKDIR /app
# Copy only production artifacts
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package.json ./

# Run as non-root
USER node
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

**Python Example:**

```dockerfile
# Build stage
FROM python:3.14-slim AS builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.14-slim
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY src/ ./src/

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["python", "-m", "src.main"]
```

**Go Example:**

```dockerfile
# Build stage
FROM golang:1.25.0-alpine3.22 AS builder
WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source and build
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main .

# Production stage - Use distroless for minimal attack surface
FROM gcr.io/distroless/static-debian12
COPY --from=builder /app/main /main

USER nonroot:nonroot
EXPOSE 8080
ENTRYPOINT ["/main"]
```

---

## Layer Optimization

### Order Instructions by Change Frequency

```dockerfile
# ✅ GOOD - Least changing first, most changing last
FROM python:3.14-slim

# System dependencies (rarely change)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (change occasionally)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (changes frequently)
COPY src/ ./src/

# ❌ BAD - Application code copied before dependencies
FROM python:3.14-slim
COPY . .  # Invalidates cache on every code change
RUN pip install -r requirements.txt
```

### Combine RUN Commands to Reduce Layers

```dockerfile
# ✅ GOOD - Single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# ❌ BAD - Multiple unnecessary layers
RUN apt-get update
RUN apt-get install -y ca-certificates
RUN apt-get install -y curl
RUN apt-get install -y git
RUN rm -rf /var/lib/apt/lists/*
```

### Use .dockerignore

```dockerignore
# .dockerignore file
**/.git
**/.gitignore
**/.DS_Store
**/node_modules
**/dist
**/coverage
**/*.md
!README.md
**/.env
**/.env.*
**/Dockerfile*
**/docker-compose*.yml
**/.pytest_cache
**/__pycache__
**/*.pyc
**/.terraform
**/.terraform-cache
**/venv
**/.venv
**/logs
**/tmp
```

---

## Security Best Practices

### Run as Non-Root User

**Python:**

```dockerfile
FROM python:3.14-slim
WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install dependencies as root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Switch to non-root user
USER appuser

COPY --chown=appuser:appuser src/ ./src/
CMD ["python", "-m", "src.main"]
```

**Node.js (use built-in 'node' user):**

```dockerfile
FROM node:20-alpine
WORKDIR /app

# Install dependencies as root
COPY package*.json ./
RUN npm ci --only=production

# Switch to node user (built-in)
USER node

COPY --chown=node:node . .
CMD ["node", "index.js"]
```

### Use Distroless Images for Production

```dockerfile
# Python distroless
FROM python:3.14-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt
COPY src/ ./src/

FROM gcr.io/distroless/python3-debian12
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/src /app/src
ENV PATH=/root/.local/bin:$PATH
WORKDIR /app
CMD ["python", "-m", "src.main"]
```

### Scan for Vulnerabilities

```bash
## Prefer registry-native scanning gates
#
# For container image vulnerability scanning, rely on a centralized scanner that
# runs in your registry / artifact-promotion pipeline (not ad-hoc on laptops):
#
# - JFrog Artifactory: JFrog Xray policies (block promotion/deploy on HIGH/CRITICAL)
# - AWS ECR: Enhanced scanning (Amazon Inspector) policies (block deploy on findings)
```

### Sign Images

```bash
# Docker Content Trust
export DOCKER_CONTENT_TRUST=1
docker push acme.com/myapp:v1.0.0

# Cosign (Sigstore)
cosign sign --key cosign.key acme.com/myapp:v1.0.0
cosign verify --key cosign.pub acme.com/myapp:v1.0.0
```

---

## Health Checks

### Application Health Check

**Python FastAPI:**

```dockerfile
FROM python:3.14-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Node.js Express:**

```dockerfile
FROM node:20-alpine
WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node healthcheck.js || exit 1

EXPOSE 3000
CMD ["node", "index.js"]
```

### Simple wget/curl Health Check

```dockerfile
# Using wget (smaller than curl in Alpine)
FROM node:20-alpine
RUN apk add --no-cache wget

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

# Using curl
FROM python:3.14-slim
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

---

## Build Optimization

### Use BuildKit for Better Performance

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Build with BuildKit features
docker build --build-arg BUILDKIT_INLINE_CACHE=1 -t myapp:latest .

# Use build secrets (never in image)
docker build --secret id=npmtoken,src=$HOME/.npmrc -t myapp:latest .
```

### Cache Mounts for Package Managers

**Python:**

```dockerfile
FROM python:3.14-slim
WORKDIR /app

COPY requirements.txt .

# Mount pip cache to speed up builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
CMD ["python", "-m", "src.main"]
```

**Node.js:**

```dockerfile
FROM node:20-alpine
WORKDIR /app

COPY package*.json ./

# Mount npm cache
RUN --mount=type=cache,target=/root/.npm \
    npm ci --only=production

COPY . .
CMD ["node", "index.js"]
```

**Go:**

```dockerfile
FROM golang:1.25.0-alpine3.22 AS builder
WORKDIR /app

COPY go.mod go.sum ./

# Mount Go module cache
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    CGO_ENABLED=0 go build -o main .

FROM gcr.io/distroless/static-debian12
COPY --from=builder /app/main /main
CMD ["/main"]
```

---

## Docker Compose Best Practices

### Production-Ready Compose File

```yaml
version: '3.9'

services:
  web:
    image: acme.com/webapp:${VERSION:-latest}
    container_name: webapp
    restart: unless-stopped

    ports:
      - "8000:8000"

    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=${LOG_LEVEL:-info}

    env_file:
      - .env

    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

    networks:
      - backend

    volumes:
      - ./logs:/app/logs:rw

    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  db:
    image: postgres:16-alpine
    container_name: postgres
    restart: unless-stopped

    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
      - POSTGRES_DB=mydb

    secrets:
      - db_password

    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5

    networks:
      - backend

    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro

  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped

    command: redis-server --appendonly yes

    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

    networks:
      - backend

    volumes:
      - redis_data:/data

networks:
  backend:
    driver: bridge

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

### Development Compose Override

```yaml
# docker-compose.override.yml (for local development)
version: '3.9'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile.dev

    volumes:
      - ./src:/app/src:ro  # Mount source for hot reload
      - /app/node_modules  # Prevent overwriting

    environment:
      - DEBUG=true
      - LOG_LEVEL=debug

    ports:
      - "8000:8000"
      - "9229:9229"  # Node.js debugger

  db:
    ports:
      - "5432:5432"  # Expose for local access

    environment:
      - POSTGRES_PASSWORD=devpassword  # Simpler password for dev
```

---

## Common Patterns

### Nginx Reverse Proxy

```dockerfile
FROM nginx:1.25-alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom config
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

# Copy static files
COPY dist/ /usr/share/nginx/html/

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:80/health || exit 1

EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]
```

**nginx.conf:**

```nginx
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    keepalive_timeout 65;
    gzip on;

    include /etc/nginx/conf.d/*.conf;
}
```

### AWS Lambda Container

```dockerfile
# AWS Lambda container compatible
FROM public.ecr.aws/lambda/python:3.14

# Copy requirements and install
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy function code
COPY src/ ${LAMBDA_TASK_ROOT}/src/
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to handler
CMD ["lambda_handler.handler"]
```

---

## CI/CD Integration

### GitHub Actions Build & Push

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]
    tags: ['v*']

permissions:
  contents: read
  packages: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix=,suffix=,format=short

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      # Vulnerability scanning should be enforced centrally in the registry:
      # - JFrog Artifactory: JFrog Xray policies (block promotion/deploy)
      # - AWS ECR: Enhanced scanning (Amazon Inspector) findings (block deploy)
```

---

## Troubleshooting

### Common Issues

**Problem: Image is too large**

```bash
# Solution: Use multi-stage builds, alpine base, .dockerignore
docker images --format "{{.Repository}}:{{.Tag}}\t{{.Size}}"
docker history myapp:latest
```

**Problem: Slow builds**

```bash
# Solution: Order layers correctly, use cache mounts, BuildKit
export DOCKER_BUILDKIT=1
docker build --progress=plain -t myapp:latest .
```

**Problem: Container exits immediately**

```bash
# Debug: Override entrypoint
docker run --rm -it --entrypoint /bin/sh myapp:latest

# Check logs
docker logs <container_id>

# Inspect container
docker inspect <container_id>
```

**Problem: Can't connect to service in container**

```bash
# Check if service is listening on 0.0.0.0 (not 127.0.0.1)
# Bad:  app.run(host='127.0.0.1', port=8000)
# Good: app.run(host='0.0.0.0', port=8000)

# Verify port mapping
docker ps
docker port <container_id>
```

---

## Best Practices Checklist

### Dockerfile Review Checklist

- [ ] Pin all base image versions
- [ ] Use multi-stage builds for compiled languages
- [ ] Run as non-root user
- [ ] Use minimal base images (alpine, slim, distroless)
- [ ] Order instructions by change frequency
- [ ] Combine RUN commands to reduce layers
- [ ] Add .dockerignore file
- [ ] Include HEALTHCHECK instruction
- [ ] Clean up package manager caches
- [ ] Don't install unnecessary packages
- [ ] Use BuildKit cache mounts
- [ ] Scan for vulnerabilities
- [ ] Sign images for production

### Docker Compose Review Checklist

- [ ] Use explicit version (3.9)
- [ ] Pin all image versions
- [ ] Use restart policies (unless-stopped)
- [ ] Configure health checks
- [ ] Use depends_on with conditions
- [ ] Set resource limits
- [ ] Use secrets for sensitive data (not environment variables)
- [ ] Use named volumes for persistence
- [ ] Use custom networks
- [ ] Provide override file for development
