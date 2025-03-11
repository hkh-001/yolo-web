import config from "config.toml";

export interface Config {
    web: {
        name: string;
        api_base: string;
    };
}

export default config as Config;