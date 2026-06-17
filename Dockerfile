# BH Hive — Docker Production Image
FROM python:3.11-slim

LABEL org.opencontainers.image.title="BH Hive"
LABEL org.opencontainers.image.description="Autonomous Multi-Agent Trading Ecosystem — swarm intelligence, self-healing, immortal"
LABEL org.opencontainers.image.authors="Mulky Malikul Dhaher"
LABEL org.opencontainers.image.version="5.0.0"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git ca-certificates nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /blackhornet

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy BlackHornet source
COPY . /blackhornet

# Ensure bh-doctor scripts are executable
RUN chmod +x /blackhornet/bh-doctor.sh /blackhornet/bh-doctor 2>/dev/null || true

# Install Python deps
RUN pip install -e .

# Setup
RUN mkdir -p /root/.bh logs data
ENV BH_HOME=/root/.bh

# Expose ports
EXPOSE 3333 3001

# Entrypoint — start everything
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
