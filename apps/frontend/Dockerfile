FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
COPY apps/frontend/package.json ./apps/frontend/package.json
COPY packages ./packages
COPY apps/frontend ./apps/frontend

RUN npm install

EXPOSE 3000

WORKDIR /app/apps/frontend
CMD ["npm", "run", "dev"]
