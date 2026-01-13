# Build stage
FROM node:25-alpine AS build-stage

WORKDIR /app

# Copy package files for dependency installation
COPY package*.json /app/

# Install all dependencies (dev dependencies needed for build)
RUN npm ci --no-audit --no-fund

# Copy source code
COPY ./ /app/

# Set build arg for API URL placeholder
ARG VITE_API_URL=__VITE_API_URL__

# Build the application
RUN npm run build

# Production stage
FROM nginx:1-alpine

# Install sed for runtime variable replacement (already available in alpine)
# Copy built application
COPY --from=build-stage /app/dist/ /usr/share/nginx/html

# Copy nginx configuration
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
COPY ./nginx-backend-not-found.conf /etc/nginx/extra-conf.d/backend-not-found.conf

# Copy and setup entrypoint script
COPY ./docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
