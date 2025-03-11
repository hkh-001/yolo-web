// @ts-check
import { defineConfig } from 'astro/config';

import vue from '@astrojs/vue';
import react from '@astrojs/react';

import tailwindcss from '@tailwindcss/vite';
import ElementPlus from 'unplugin-element-plus/vite'


// https://astro.build/config
export default defineConfig({
  integrations: [vue(), react()],
  vite: {
    plugins: [tailwindcss(), ElementPlus({})],
    ssr: {
      noExternal: ['element-plus']
    }
  }
});