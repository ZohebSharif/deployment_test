# Builds the React frontend, then serves it (plus the API proxy) with nginx.
# Build context is the repo root:  docker build -f nginx/Dockerfile .

FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend /frontend/dist /usr/share/nginx/html
