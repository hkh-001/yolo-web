import config from '@/config';
import ky from 'ky';
import type { ImageResponse } from './predict';

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

export function callModels(modelId: string, data: { file?: File, [key: string]: any }) {
    const formdata = new FormData();
    if (data.file) formdata.append('file', data.file, data.file.name);
    Object.entries(data).forEach(([key, value]) => {
        if (key !== 'file') {
            formdata.append(key, value);
        }
    });
    return _api.post<ImageResponse>(`model/${modelId}`, { body: formdata }).json();
}
