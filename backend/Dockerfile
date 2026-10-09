FROM node:20-alpine

WORKDIR /app
ENV NODE_ENV=production

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY src ./src
COPY simulate-esp.js ./

USER node
EXPOSE 3000
CMD ["node", "src/index.js"]
