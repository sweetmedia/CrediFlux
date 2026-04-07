FROM node:20-alpine

WORKDIR /app

# Copy all source files first
COPY . .

# Install dependencies (postinstall will generate .source)
RUN npm install

# Expose port
EXPOSE 3001

# Start development server
CMD ["npm", "run", "dev", "--", "-p", "3001"]
