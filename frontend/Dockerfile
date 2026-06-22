# Stage 1: Build the static assets
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (leverage caching)
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the application
COPY . .

# Build the project
# Ensure EXPORT_STATIC=true and NEXT_PUBLIC_API_URL=/api are set during build
ENV EXPORT_STATIC=true
ENV NEXT_PUBLIC_API_URL=/api
RUN npm run build

# Stage 2: Serve using Nginx
FROM nginx:1.27-alpine

# Copy custom Nginx configuration for the SPA
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build output to Nginx HTML directory
COPY --from=builder /app/out /usr/share/nginx/html

# Expose Nginx port
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
