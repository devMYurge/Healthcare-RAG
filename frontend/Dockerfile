FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Install serve to serve the built files
RUN npm install -g serve

# Serve the built application
CMD ["serve", "-s", "dist", "-l", "3000"]
