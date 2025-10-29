FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy project files
COPY . .

EXPOSE 3000

# Development command (will be overridden in docker-compose)
CMD ["npm", "run", "dev"]
