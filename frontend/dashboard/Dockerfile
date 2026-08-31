FROM node:18-alpine AS builder

WORKDIR /app

COPY package.json pnpm-lock.yaml* ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM node:18-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

RUN npm install -g serve
EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
