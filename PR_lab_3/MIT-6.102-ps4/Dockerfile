# Use Node.js 20 LTS as base image
FROM node:20-slim

# Set working directory inside container
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./
COPY eslint.config.mjs ./

# Install dependencies
RUN npm install

# Copy source code
COPY src/ ./src/
COPY test/ ./test/
COPY boards/ ./boards/
COPY public/ ./public/

# Compile TypeScript
RUN npm run compile

# Expose port 8080 for the HTTP server
EXPOSE 8080

# Set default command to run the server
# Default board is perfect.txt, can be overridden with docker run arguments
CMD ["node", "dist/src/server.js", "8080", "boards/perfect.txt"]
