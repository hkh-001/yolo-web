FROM oven/bun:1.1.20-slim

RUN mkdir -p /app

WORKDIR /app

COPY ./package.json /app
COPY ./config.toml /app
COPY ./tsconfig.json /app
COPY ./src /app/src

RUN mkdir -p /app/data

RUN bun install

ENV BUN_ENV=production
ENV NODE_ENV=production

CMD ["bun", "run", "start"]

EXPOSE 3000