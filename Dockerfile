# Hermes Hive — Docker Production Image
FROM python:3.11-slim

LABEL org.opencontainers.image.title="Hermes Hive"
LABEL org.opencontainers.image.description="Autonomous Multi-Agent Trading Ecosystem — 7 repos, 21 agents, immortal"
LABEL org.opencontainers.image.authors="Mulky Malikul Dhaher"
LABEL org.opencontainers.image.version="4.0.0"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git ca-certificates nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /hermes

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Clone ecosystem
RUN git clone https://github.com/dhaher-labs/blackhornet.git . \
    && git clone https://github.com/dhaher-labs/ProxyGateLLM.git /proxygate \
    && git clone https://github.com/dhaher-labs/mnemosyne.git /mnemosyne

# Install Hermes Agent
RUN git clone https://github.com/NousResearch/hermes-agent.git /hermes-agent \
    && cd /hermes-agent && UV_PYTHON=python3 bash setup-hermes.sh --skip-setup --non-interactive

# Install Python deps
RUN pip install -r requirements.txt openai

# Install ProxyGateLLM deps
RUN cd /proxygate && npm install --omit=dev

# Setup
RUN mkdir -p /root/.hermes logs data
ENV HERMES_HOME=/root/.hermes
ENV PROXYGATE_DIR=/proxygate
ENV MNEMOSYNE_DIR=/mnemosyne

# Expose ports
EXPOSE 3333 3001

# Entrypoint — start everything
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
