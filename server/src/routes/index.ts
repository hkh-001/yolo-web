import { Hono } from 'hono';
import { HTTPException } from 'hono/http-exception';
import config from '@/config';
import { sql } from '@/utils/init';
import * as uuid from 'uuid';

const router = new Hono({})

router.get('/models', async (c) => {
    return Response.json(config.models.map(({ id, name }) => ({ id, name })))
});

router.post('/model/:id', async (c) => {
    const modelId = c.req.param("id");
    const startTime = Date.now();
    console.log(`[Backend] 收到模型请求: ${modelId}, 时间: ${new Date().toISOString()}`);
    
    const model = config.models.find((m) => m.id === modelId);
    if (!model) {
        console.error(`[Backend] 模型未找到: ${modelId}`);
        throw new HTTPException(404, { message: 'Model not found' });
    }
    
    console.log(`[Backend] 转发到: ${model.api_url}`);
    console.log(`[Backend] 请求方法: ${c.req.method}`);
    
    const header = new Headers(c.req.raw.headers);
    header.set('X-Api-Key', model.api_key);
    
    try {
        console.log(`[Backend] ➡️ 准备构造请求对象...`);
        const request = new Request(model.api_url, {
            method: c.req.method.toUpperCase(),
            headers: header,
            body: c.req.raw.body,
        });
        console.log(`[Backend] ➡️ 请求对象构造完成，准备 fetch...`);
        
        const fetchStart = Date.now();
        const response = await fetch(request);
        console.log(`[Backend] ⬅️ fetch 完成，耗时: ${Date.now() - fetchStart}ms`);
        const duration = Date.now() - startTime;
        console.log(`[Backend] 模型响应成功, 耗时: ${duration}ms, 状态: ${response.status}`);
        return response;
    } catch (error) {
        const duration = Date.now() - startTime;
        console.error(`[Backend] 模型请求失败, 耗时: ${duration}ms, 错误:`, error);
        throw new HTTPException(502, { message: 'Model service error' });
    }
});

router.get('/files/:filename', async (c) => {
    const filename = c.req.param("filename");
    const path = `data/files/${filename}`;
    const file = Bun.file(path);
    if (!await file.exists()) {
        return new Response('File not found', { status: 404 });
    }
    return new Response(file, {
        headers: {
            'Content-Type': 'application/octet-stream',
        }
    });
})

async function sha256File(file: File) {
    const buffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

router.post('/upload', async (c) => {
    const body = await c.req.formData();
    const file = body.get('file') as File | null
    if (!file) {
        throw new HTTPException(400, { message: 'No file uploaded' });
    }
    // calculate sha256
    const fn = await sha256File(file);
    const path = `data/files/${fn}`;
    await Bun.write(path, file);
    return Response.json({ id: fn });
})

router.get('/task/:uuid', async (c) => {
    const task = await sql.getTask(c.req.param("uuid"));
    if (!task) return new Response('Task not found', { status: 404 });
    return Response.json(task);
});

router.delete('/task/:uuid', async (c) => {
    const task_id = c.req.param("uuid");
    const task = await sql.getTask(task_id);
    if (!task) return new Response('Task not found', { status: 404 });
    await sql.deleteTask(c.req.param("uuid"));
    const fns = [task.input_blob, task.results_blob];
    const deletePool: Promise<void>[] = [];
    for (const fn of fns) {
        if (!fn) continue;
        const p = sql.existsFile(fn).then(async (exists) => {
            if (!exists) {
                const path = `data/files/${fn}`;
                const file = Bun.file(path);
                if (await file.exists()) {
                    await file.delete();
                }
            }
        })
        deletePool.push(p);
    }
    await Promise.all(deletePool);
    return Response.json({ task: task_id, message: 'Task deleted' });
});

router.post('/task', async (c) => {
    const body = await c.req.json();
    const task_id = await sql.insertTask(body);
    return Response.json({ task_id });
})

router.get('tasks', async (c) => {
    const tasks = await sql.listTasks();
    return Response.json(tasks);
})

export default router;