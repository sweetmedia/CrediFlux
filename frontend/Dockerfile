# CrediFlux Frontend — build de producción.
# Vite genera una SPA estática (dist/) que sirve nginx con fallback a
# index.html para las rutas del cliente.

# Stage 1: build
FROM node:24.22.1-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY . .

# Variables de build: Vite las incrusta en el bundle (import.meta.env).
ARG VITE_API_URL=http://10.0.0.93:8600
ARG VITE_APP_URL=http://10.0.0.93:3600
ENV VITE_API_URL=$VITE_API_URL \
    VITE_APP_URL=$VITE_APP_URL

RUN npm run build

# Stage 2: nginx
FROM nginx:1.27-alpine AS runner
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 3000
