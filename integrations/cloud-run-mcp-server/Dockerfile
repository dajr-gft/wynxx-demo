# syntax=docker/dockerfile:1
#
# Wynxx MCP server — container image for Cloud Run.
# Multi-stage build keeps the runtime image small and rootless.

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ----------------------------------------------------------------------------
# Builder: install dependencies into a virtual environment.
# ----------------------------------------------------------------------------
FROM base AS builder
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

# ----------------------------------------------------------------------------
# Runtime: copy the venv and source, run as a non-root user.
# ----------------------------------------------------------------------------
FROM base AS runtime
WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH"

# Cloud Run injects PORT; FastMCP binds host/port from the app config.
ENV PORT=8080 \
    WYNXX_MODE=stub \
    WYNXX_HOST=0.0.0.0

COPY --from=builder /opt/venv /opt/venv
COPY server.py ./
COPY wynxx_mcp ./wynxx_mcp

# Run as an unprivileged user.
RUN useradd --no-create-home --uid 10001 appuser
USER 10001

EXPOSE 8080
CMD ["python", "server.py"]