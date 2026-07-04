# BH Omega — Docker Production Image
# Multi-stage: builder → runtime
FROM python:3.12-slim AS builder

LABEL org.opencontainers.image.title="BlackHornet Omega"
LABEL org.opencontainers.image.description="BlackHornet Ω — Autonomous AGI Engine (OmegaEngine CLI)"
LABEL org.opencontainers.image.authors="Mulky Malikul Dhaher"
LABEL org.opencontainers.image.version="5.0.0"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /build
COPY pyproject.toml ./
COPY src/ ./src/
COPY deploy/entrypoint-omega.sh /entrypoint.sh

RUN pip install --no-cache-dir -e . && \
    chmod +x /entrypoint.sh

FROM python:3.12-slim AS runtime

RUN groupadd -r bh && useradd -r -g bh -d /bh -s /sbin/nologin bh

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /entrypoint.sh /entrypoint.sh

RUN mkdir -p /bh/data /bh/logs && chown -R bh:bh /bh

ENV DHAHERLABS=/bh/data
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

USER bh
WORKDIR /bh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bh-omega", "start", "--loop", "1"]
