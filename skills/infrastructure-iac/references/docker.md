# Docker Patterns

## Multi-Stage Build (Python)

```dockerfile
# Build stage
FROM python:3.14-slim AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.14-slim
WORKDIR /app

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY . .

RUN useradd -m appuser
USER appuser

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0"]
```

## Multi-Stage Build (Go)

```dockerfile
FROM golang:1.25.0-alpine3.22 AS builder
WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/server .

# Distroless for minimal attack surface
FROM gcr.io/distroless/static-debian12
COPY --from=builder /app/server /server
ENTRYPOINT ["/server"]
```

## Layer Optimization

```dockerfile
# GOOD - Separate layers for caching
COPY package.json package-lock.json ./
RUN npm ci --only=production

COPY . .

# BAD - Invalidates cache on any change
COPY . .
RUN npm ci
```

## Security Hardening

```dockerfile
# Non-root user
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser
USER appuser

# Read-only filesystem
FROM python:3.14-slim
# ... build steps ...
USER appuser
# Run with: docker run --read-only --tmpfs /tmp

# No shell (prevents shell injection)
FROM gcr.io/distroless/python3
```

## Health Checks

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
```

## .dockerignore

```
.git
.gitignore
*.md
Dockerfile*
docker-compose*
.env*
__pycache__
*.pyc
node_modules
.pytest_cache
.coverage
.venv
dist
build
```

## Docker Compose

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/app
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

## Build Arguments

```dockerfile
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

ARG BUILD_DATE
ARG GIT_SHA
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${GIT_SHA}"
```

## Security Scanning

```bash
## Prefer registry-native scanning gates
#
# For container image vulnerability scanning, rely on a centralized scanner that
# runs in your registry / artifact-promotion pipeline (not ad-hoc on laptops):
#
# - JFrog Artifactory: JFrog Xray policies (block promotion/deploy on HIGH/CRITICAL)
# - AWS ECR: Enhanced scanning (Amazon Inspector) policies (block deploy on findings)

# Lint Dockerfile
hadolint Dockerfile
```
