FROM node:20-alpine

WORKDIR /app

# Install dependencies rapidly
COPY package*.json ./
RUN npm ci

# Copy the rest of the application
COPY . .

# Expose Vite's default port
EXPOSE 5173

# Run the dev server matching docker-compose
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
