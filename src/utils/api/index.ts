import config from '@/config';
import ky from 'ky';
import type { ImageResponse, PredictData, VideoResponse } from './predict';
import type { Task, TaskList } from './task';

const API_BASE = config.web.api_base

export const _api = ky.create({
    prefixUrl: API_BASE,
});

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
    const formdata = new FormData();
    if (data.file) formdata.append('file', data.file, data.file.name);
    Object.entries(data).forEach(([key, value]) => {
        if (key !== 'file') {
            formdata.append(key, value);
        }
    });
    const headers = accept ? { Accept: accept } : undefined;
    const response = _api.post<ImageResponse | VideoResponse | Blob>(`model/${modelId}`, { body: formdata, headers });
    if (accept === 'application/json') return response.json();
    return response.blob();
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