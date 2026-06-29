FROM node:20-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY package.json package-lock.json turbo.json ./
COPY apps/web ./apps/web
COPY packages ./packages
RUN npm ci || npm install
RUN npm run build --workspace=@hermes/web

FROM node:20-alpine
WORKDIR /app/apps/web
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NODE_ENV=production
COPY --from=builder /app/apps/web/.next ./.next
COPY --from=builder /app/apps/web/package.json ./
COPY --from=builder /app/apps/web/public ./public
COPY --from=builder /app/node_modules /app/node_modules
EXPOSE 3000
CMD ["npx", "next", "start", "--port", "3000"]
