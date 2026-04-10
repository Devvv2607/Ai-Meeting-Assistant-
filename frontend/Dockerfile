# Frontend Dockerfile

FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* /app/

# Install dependencies
RUN npm ci

# Copy application
COPY . .

# Build application
RUN npm run build

# Production image
FROM node:18-alpine

WORKDIR /app

# Copy from builder
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# Run application
CMD ["npm", "start"]
