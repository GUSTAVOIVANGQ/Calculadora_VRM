import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins:[react()],
  base:'/',
  build:{outDir:'dist',emptyOutDir:true,assetsDir:'assets',manifest:true},
  server:{proxy:{'/api':'http://127.0.0.1:8084','/login':'http://127.0.0.1:8084','/logout':'http://127.0.0.1:8084','/crear-cuenta':'http://127.0.0.1:8084','/register':'http://127.0.0.1:8084'}},
});
