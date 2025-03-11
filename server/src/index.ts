import { Hono } from 'hono';
import router from "@/routes"
import { HTTPException } from 'hono/http-exception';

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
    host: '0.0.0.0',
    port: 3000,
    fetch: app.fetch.bind(app),
}