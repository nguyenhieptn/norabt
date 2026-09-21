# syntax=docker/dockerfile:1
#
# Image for `python3 -m Agent.backend.run_web` -- the Starlette/uvicorn HTTP
# dashboard defined in Agent/backend/web/app.py (routes: /, /api/bots,
# /api/markets, /api/leaderboard, /api/analyze, /healthz). See
# Agent/deploy/README.md for the full deploy runbook and
# Agent/deploy/docker-compose.yml for how this image is actually run.
#
# Build context: this Dockerfile is built with context=Agent/ (one level up
# from this file), not the repo root and not Agent/deploy/ itself -- see
# docker-compose.yml's `build.context: ..` and Agent/deploy/.dockerignore's
# own header comment for exactly why. Every COPY below is therefore relative
# to Agent/.

# ---------------------------------------------------------------------------
# Stage 1/2: builder -- resolve and install Python dependencies into an
# isolated venv, so the runtime stage can copy just the finished venv and
# leave pip's cache / wheel downloads / *.dist-info build leftovers behind.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Why 3.12 and not 3.14 (what developer machines in this repo actually run,
# see Agent/deploy/README.md's "Ghi chú" section for the full reasoning):
#   - This is meant to run 24/7 taking requests from the internet --
#     predictable third-party wheel support matters more here than running
#     the newest interpreter.
#   - numpy, pydantic-core and redis-py all ship pre-built manylinux wheels
#     for cp312 with a long track record; 3.14 is comparatively new and a
#     missing wheel for any transitive dependency would silently fall back to
#     compiling from source inside the image, needing a C/Rust toolchain this
#     Dockerfile otherwise never has to install.
#   - python:3.12-slim is one of the most widely used official Python base
#     images, so it gets frequent upstream security-patch rebuilds.
# Nothing under Agent/backend uses a 3.13+/3.14-only language feature (no
# `except*`, no PEP 695 generic syntax) -- confirmed by grep before this
# choice was made -- so this costs nothing functionally.

WORKDIR /build

# A venv (not system site-packages) so stage 2 can copy exactly this
# directory and get a clean, self-contained set of packages.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Copied alone, before the rest of the source, so this layer -- the slow
# `pip install` -- is only invalidated when requirements.txt itself changes,
# not on every backend/ code edit.
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2/2: runtime -- no compiler, no pip cache, no build-only tooling.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Fixed, non-system UID/GID (10001) rather than a dynamically-allocated
# `useradd -m` one, so the numeric owner of anything this user touches (e.g.
# the bind-mounted Agent/data/cache/candles/ directory on the host) is the
# same across every rebuild instead of shifting with image layer order.
#
# Running as non-root is not optional here: this is the one process in the
# stack that ends up executing attacker-shaped input directly-ish (POST
# /api/analyze scores a caller-supplied `code` string end to end, behind
# nginx but still the first process on the host to touch it) -- a container
# breakout or an unnoticed path-traversal bug is far less damaging as an
# unprivileged UID than as root.
RUN groupadd --system --gid 10001 agent \
    && useradd --system --uid 10001 --gid agent --home-dir /app \
       --shell /usr/sbin/nologin agent

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Explicit ALLOW-list COPY -- never a wildcard "COPY . ." -- so
# Agent/data (bot ledgers, ~260MB), Agent/.env (OKX credentials) and
# Agent/test can never end up in the image, regardless of which
# .dockerignore Docker happens to apply for this build context (see
# Agent/deploy/.dockerignore's own header comment). Destination paths keep
# the "Agent/..." prefix on purpose: the code imports itself as
# `Agent.backend...`, which only resolves correctly when run with a working
# directory that has an `Agent/` package folder directly inside it -- exactly
# how it already runs uncontainerized from the repo root.
COPY requirements.txt /app/Agent/requirements.txt
COPY backend /app/Agent/backend

# Agent/data is bind-mounted at runtime (see docker-compose.yml), never
# baked in. Creating the mount point ahead of time and handing it to the
# unprivileged user avoids a root-owned directory silently pre-existing
# under the bind mount.
RUN mkdir -p /app/Agent/data && chown -R agent:agent /app

USER agent

EXPOSE 8770

# --host 0.0.0.0 is required *inside* the container: Docker's published-port
# forwarding targets the container's own network-namespace interface, not
# its loopback, so binding to run_web.py's own default of 127.0.0.1 here
# would make the app completely unreachable from outside the container even
# though it is running fine (see Agent/deploy/README.md's "agent không lên"
# troubleshooting entry). This is still safe end to end: docker-compose.yml
# publishes the container's 8770 only to the HOST's 127.0.0.1
# ("127.0.0.1:8770:8770"), so the process is reachable from the host's own
# loopback alone -- nginx (running on the host, outside Docker) is the only
# intended path in from the public internet. run_web.py itself prints a
# stderr warning about listening on every interface when --host 0.0.0.0 is
# used, written for the case of running it directly on a host with no such
# proxy in front; that warning is expected and harmless in this container's
# logs specifically because docker-compose's port publishing is the actual
# access boundary, not this flag.
#
# The container healthcheck itself lives in docker-compose.yml (single
# source of truth for it, see that file), not duplicated here.
CMD ["python3", "-m", "Agent.backend.run_web", "--host", "0.0.0.0", "--port", "8770"]
