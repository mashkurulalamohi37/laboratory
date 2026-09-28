# syntax=docker/dockerfile:1.7
# Build context: repository root (the app depends on workspace packages).
FROM node:22-alpine AS build
ENV PNPM_HOME=/pnpm PATH=/pnpm:$PATH
RUN corepack enable
WORKDIR /repo
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json .npmrc ./
COPY packages ./packages
COPY apps/console ./apps/console
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile --filter @nirnoy/console...
RUN pnpm --filter @nirnoy/console build

FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime
COPY infrastructure/frontend/spa.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/apps/console/dist /usr/share/nginx/html
EXPOSE 8080
