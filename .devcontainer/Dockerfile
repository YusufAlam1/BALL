FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# --- System packages -------------------------------------------------------
# libpq-dev / build-essential: needed for psycopg2 / scientific wheels fallback
# Node.js: required by the Claude Code CLI
# The base image ships a Yarn apt source whose signing key has expired, which
# breaks `apt-get update`. We don't use Yarn, so remove that source first.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Node.js LTS (for Claude Code). The base image ships nvm; use the devcontainer
# node feature instead via devcontainer.json, but install a global npm here too.
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# --- Claude Code CLI -------------------------------------------------------
RUN npm install -g @anthropic-ai/claude-code

# --- Python dependencies ---------------------------------------------------
# Copied separately so the layer is cached unless requirements.txt changes.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    # connect.py imports `supabase`, which isn't pinned in requirements.txt
    && pip install --no-cache-dir supabase

# The base image already provides a non-root `vscode` user.
