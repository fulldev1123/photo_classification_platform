# --- Build stage: compile TypeScript and bundle with Vite ---
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY . .
# Backend URLs are baked into the static bundle at build time. Override with:
# docker build --build-arg VITE_AUTH_API=... --build-arg VITE_SUBMISSION_API=...
ARG VITE_AUTH_API=http://localhost:8001
ARG VITE_SUBMISSION_API=http://localhost:8002
ENV VITE_AUTH_API=$VITE_AUTH_API
ENV VITE_SUBMISSION_API=$VITE_SUBMISSION_API
RUN npm run build

# --- Runtime: serve the static bundle with nginx ---
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost/ >/dev/null || exit 1
