import config from '@/config';
import ky from 'ky';
import type { ImageResponse, PredictData, VideoResponse } from './predict';
import type { Task, TaskList } from './task';

const API_BASE = config.web.api_base

export const _api = ky.create({
    prefixUrl: API_BASE,
    timeout: 60000, // 60 秒超时，YOLO 推理可能需要较长时间
});

// 调试日志开关
const DEBUG = true;

export interface ModelInfo {
    id: string
    name: string
}

export function getModels() {
    return _api.get<ModelInfo[]>('models').json();
}

export interface CallModelInput { file?: File, [key: string]: any }
export type CallModelResponse<T extends PredictData["source"]> = {
    image: ImageResponse | Blob
    video: VideoResponse | Blob
}[T]

export function callModels<T extends PredictData["source"]>(modelId: string, data: CallModelInput, accept?: string): Promise<CallModelResponse<T>> {
    const startTime = Date.now();
    if (DEBUG) {
        console.log(`[API] 开始请求模型: ${modelId}, 时间: ${new Date().toISOString()}`);
        console.log(`[API] 文件: ${data.file?.name}, 大小: ${data.file?.size} bytes`);
    }

    const formdata = new FormData();
    if (data.file) formdata.append('file', data.file, data.file.name);
    Object.entries(data).forEach(([key, value]) => {
        if (key !== 'file') {
            formdata.append(key, value);
        }
    });
    const headers = accept ? { Accept: accept } : undefined;
    
    return _api.post<ImageResponse | VideoResponse | Blob>(`model/${modelId}`, { 
        body: formdata, 
        headers 
    }).then(response => {
        const duration = Date.now() - startTime;
        if (DEBUG) {
            console.log(`[API] 请求成功, 耗时: ${duration}ms`);
        }
        if (accept === 'application/json') return response.json();
        return response.blob();
    }).catch(error => {
        const duration = Date.now() - startTime;
        console.error(`[API] 请求失败, 耗时: ${duration}ms, 错误:`, error.name, error.message);
        throw error;
    });
}

export function getFile(filename: string) {
    return _api.get(`files/${filename}`).blob();
}

export function uploadFile(blob: Blob) {
    const formdata = new FormData();
    formdata.append('file', blob, 'file');
    return _api.post<{ id: string }>('upload', { body: formdata }).json();
}

export function getTask(task_id: string) {
    return _api.get<Task>(`task/${task_id}`).json();
}

export function deleteTask(task_id: string) {
    return _api.delete<{ task: string, message: string }>(`task/${task_id}`).json();
}

export function saveTask(task: Omit<Task, 'id' | 'timestamp' | 'task_id'>) {
    return _api.post<{ task_id: string }>('task', { json: task }).json();
}

export function listTasks() {
    return _api.get<TaskList>('tasks').json();
}