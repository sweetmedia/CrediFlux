# Frontend de CrediFlux en desarrollo (Vite dev server).
FROM node:20-alpine

WORKDIR /app

# `npm ci`: exactamente lo de package-lock.json.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

# Los compose lo sobreescriben con `npm run dev` (vite en 0.0.0.0:3000).
CMD ["npm", "run", "dev"]
