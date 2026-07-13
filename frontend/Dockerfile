FROM node:20-slim AS build
# Build context is the repo root (not frontend/) so that workload/frontend
# is visible here as a sibling directory — routes-manifest.ts's
# import.meta.glob walks up to it via a relative path at build time.
WORKDIR /repo
COPY frontend/package.json frontend/package.json
COPY frontend/scripts frontend/scripts
# `npm install`'s postinstall (frontend/scripts/link-node-modules.cjs) links
# frontend/node_modules up to /repo/node_modules — without it, workload/frontend
# (a sibling of frontend/, not an ancestor of its node_modules) couldn't
# resolve npm imports like "lucide-react" in its pages, since Node/Rollup
# module resolution only walks up ANCESTOR directories from the importing file.
RUN npm --prefix frontend install
COPY frontend frontend
COPY workload/frontend workload/frontend
ARG VITE_API_BASE_URL
ARG VITE_API_KEY
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_API_KEY=$VITE_API_KEY
RUN npm --prefix frontend run build

FROM nginx:1.27-alpine AS serve
COPY --from=build /repo/frontend/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
# Regenerates config.js from runtime env vars (API_BASE_URL/API_KEY) on every
# container start — see frontend/docker-entrypoint.sh and
# frontend/src/api/client.ts, which reads window.__CONFIG__ first.
COPY --chmod=755 frontend/docker-entrypoint.sh /docker-entrypoint.d/40-generate-config.sh
EXPOSE 80
