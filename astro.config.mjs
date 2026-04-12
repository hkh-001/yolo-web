// @ts-check
import { defineConfig } from 'astro/config';
import toml from 'toml';

import vue from '@astrojs/vue';
import react from '@astrojs/react';

import tailwindcss from '@tailwindcss/vite';
import ElementPlus from 'unplugin-element-plus/vite'


// https://astro.build/config
export default defineConfig({
  integrations: [vue(), react()],
  vite: {
    plugins: [tailwindcss(), ElementPlus({}), {
      name: "toml-loader",
      transform(code, id) {
        if (id.endsWith('.toml')) {
          return `export default ${JSON.stringify(toml.parse(code))}`
        }
      }
    }],
    server: {
      watch: {
        ignored: [
          'server/**/*',
          '**/runs/**',
          '**/train_status/**',
          '**/train_tasks.json',
          '**/*.pt',
          '**/*.pth',
          '**/*.ckpt',
          '**/*.log',
          '**/results.csv',
          '**/results.png',
          '**/args.yaml',
          '**/confusion_matrix.png',
          '**/F1_curve.png',
          '**/PR_curve.png',
        ]
      },
      proxy: {
        '/api': {
          target: 'http://localhost:3000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, '')
        }
      }
    },
    ssr: {
      noExternal: ['element-plus']
    }
  }
});