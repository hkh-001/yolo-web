import { Hono } from 'hono';
import { HTTPException } from 'hono/http-exception';
import config from '@/config';

const router = new Hono({})

router.get('/models', async (c) => {
    return Response.json(config.models.map(({ id, name }) => ({ id, name })))
});

router.post('/model/:id', async (c) => {
    const model = config.models.find((m) => m.id === c.req.param("id"))!;
    if (!model) {
        throw new HTTPException(404, { message: 'Model not found' });
    }
    const header = new Headers(c.req.raw.headers);
    header.set('X-Api-Key', model.api_key);
    const request = new Request(model.api_url, {
        method: c.req.method.toUpperCase(),
        headers: header,
        body: c.req.raw.body,
    })
    return fetch(request);
});

export default router;