import { Hono } from 'hono';
import { HTTPException } from 'hono/http-exception';
import config from '@/config';
import { sql } from '@/utils/init';
import * as uuid from 'uuid';
import trainRouter from './train';

const router = new Hono({})

// 挂载训练路由
router.route('/api', trainRouter)

router.get('/models', async (c) => {
    return Response.json(config.models.map(({ id, name }) => ({ id, name })))
});

router.post('/model/:id', async (c) => {
    const modelId = c.req.param("id");
    const startTime = Date.now();
    console.log(`[Backend] ========== 收到模型请求: ${modelId} ==========`);
    console.log(`[Backend] 时间: ${new Date().toISOString()}`);
    
    const model = config.models.find((m) => m.id === modelId);
    if (!model) {
        console.error(`[Backend] ❌ 模型未找到: ${modelId}`);
        return Response.json({
            success: false,
            message: `模型 ${modelId} 未配置`,
            available_models: config.models.map(m => m.id)
        }, { status: 404 });
    }
    
    console.log(`[Backend] 目标: ${model.api_url}`);
    
    // 处理 body 转发
    let bodyData: ArrayBuffer | Blob | null = null;
    const contentType = c.req.header('content-type') || '';
    
    try {
        if (contentType.includes('multipart/form-data')) {
            // 对于 multipart/form-data，使用 blob 保持原始格式
            bodyData = await c.req.blob();
            console.log(`[Backend] Body 读取成功 (Blob): ${bodyData.size} bytes`);
        } else {
            // 其他类型使用 arrayBuffer
            bodyData = await c.req.arrayBuffer();
            console.log(`[Backend] Body 读取成功 (ArrayBuffer): ${bodyData.byteLength} bytes`);
        }
    } catch (e) {
        console.error(`[Backend] ❌ Body 读取失败:`, e);
        return Response.json({
            success: false,
            message: '读取请求体失败'
        }, { status: 400 });
    }
    
    const header = new Headers();
    header.set('X-Api-Key', model.api_key);
    
    // 复制 content-type（multipart 会自动设置 boundary）
    if (contentType) {
        header.set('Content-Type', contentType);
        console.log(`[Backend] Content-Type: ${contentType}`);
    }
    
    // 复制 accept（关键！决定 5000 返回 JSON 还是图片）
    const acceptHeader = c.req.header('accept');
    if (acceptHeader) {
        header.set('Accept', acceptHeader);
        console.log(`[Backend] Accept: ${acceptHeader}`);
    }
    
    try {
        console.log(`[Backend] ➡️ 开始 fetch (超时 30s)...`);
        const fetchStart = Date.now();
        
        // 使用 AbortController 实现超时（Real-ESRGAN 可能需要更长时间）
        const controller = new AbortController();
        const timeoutMs = modelId.startsWith('enhance') ? 120000 : 30000; // enhance 系列模型 120 秒超时，其他 30 秒
        const timeoutId = setTimeout(() => {
            console.error(`[Backend] ⏱️ fetch 超时 (${timeoutMs/1000}s)，主动取消`);
            controller.abort();
        }, timeoutMs);
        
        const response = await fetch(model.api_url, {
            method: 'POST',
            headers: header,
            body: bodyData,
            signal: controller.signal,
        });
        
        clearTimeout(timeoutId);
        const fetchDuration = Date.now() - fetchStart;
        console.log(`[Backend] ⬅️ fetch 完成，耗时: ${fetchDuration}ms, 状态: ${response.status}`);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`[Backend] ❌ 模型返回错误: ${response.status}, ${errorText}`);
            return Response.json({
                success: false,
                message: `模型服务返回错误: ${response.status}`,
                detail: errorText
            }, { status: 502 });
        }
        
        // 透传响应
        const responseBody = await response.arrayBuffer();
        console.log(`[Backend] ✅ 成功返回，总耗时: ${Date.now() - startTime}ms`);
        
        return new Response(responseBody, {
            status: response.status,
            headers: {
                'Content-Type': response.headers.get('content-type') || 'application/json'
            }
        });
        
    } catch (error: any) {
        const duration = Date.now() - startTime;
        console.error(`[Backend] ❌ fetch 异常, 耗时: ${duration}ms`);
        console.error(`[Backend]    错误名: ${error.name}`);
        console.error(`[Backend]    错误消息: ${error.message}`);
        
        if (error.name === 'AbortError') {
            const timeoutSec = modelId.startsWith('enhance') ? 120 : 30;
            return Response.json({
                success: false,
                message: `模型服务响应超时 (${timeoutSec}s)`,
                detail: '请检查模型服务是否正常启动，或模型是否正在加载中'
            }, { status: 504 });
        }
        
        if (error.code === 'ECONNREFUSED' || error.message?.includes('connect')) {
            return Response.json({
                success: false,
                message: '无法连接到模型服务',
                detail: `请检查 ${model.api_url} 是否可访问`
            }, { status: 503 });
        }
        
        return Response.json({
            success: false,
            message: '模型服务请求失败',
            detail: error.message || String(error)
        }, { status: 502 });
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