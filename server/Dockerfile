FROM oven/bun:1.1.20-slim

RUN mkdir -p /app

WORKDIR /app

COPY ./package.json /app
COPY ./config.toml /app
COPY ./tsconfig.json /app
COPY ./src /app/src

RUN mkdir -p /app/data

RUN bun install

CMD ["bun", "run", "start"]

EXPOSE 3000