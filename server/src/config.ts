import fs from 'node:fs';
import toml from 'toml';

const configStr = fs.readFileSync('config.toml', 'utf8');

export interface Config {
    models: {
        id: string;
        name: string;
        api_url: string;
        api_key: string;
    }[]
}

export default toml.parse(configStr) as Config;