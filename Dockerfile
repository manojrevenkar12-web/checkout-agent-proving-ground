# The service image: the API, the demo world and the built dashboard.
FROM node:22-slim AS web
WORKDIR /web
RUN corepack enable
COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm build

FROM python:3.13-slim
RUN useradd --system --uid 10001 cap
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY cap/ cap/
COPY config/ config/
COPY reports/ reports/
COPY --from=web /web/dist web/dist
USER 10001
ENV CAP_DATABASE_URL=sqlite+pysqlite:////tmp/orders.db
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "cap.service.api:app", "--host", "0.0.0.0", "--port", "8080"]
