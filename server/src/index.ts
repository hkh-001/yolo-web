import { Hono } from 'hono';
import router from "@/routes"
import { HTTPException } from 'hono/http-exception';
import config from '@/config';
import '@/utils/init';

const app = new Hono();

app.route("/", router);

app.onError((e, c) => {
    if (e instanceof HTTPException) {
        return new Response(e.message, { status: e.status });
    } else {
        console.error(e);
        return new Response('Internal Server Error', { status: 500 });
    }
})

export default {
    host: config.server.host,
    port: config.server.port,
    fetch: app.fetch.bind(app),
}