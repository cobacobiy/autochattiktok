FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    supervisor \
    procps \
    tzdata \
    fluxbox \
    && ln -s /usr/share/novnc/vnc.html /usr/share/novnc/index.html \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Jakarta

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && playwright install chromium

COPY . bot/

RUN mkdir -p /data/ginee-profile /data/logs

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 6080 8080 5900

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080')"

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
