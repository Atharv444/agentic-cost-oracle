# ── Stage 1: Build ────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="Agentic Cost-Oracle"
LABEL description="AI-powered cloud cost optimization for GitHub PRs"

# Install Infracost CLI
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh | sh && \
    apt-get purge -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app
COPY app/ ./app/

# Non-root user for security
RUN useradd --create-home --shell /bin/bash oracle
USER oracle

ENTRYPOINT ["python", "-m", "app.main"]
