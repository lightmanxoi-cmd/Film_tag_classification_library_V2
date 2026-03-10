import { defineConfig } from 'vite';
import { resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
    root: 'web',
    publicDir: 'static',
    base: '/',
    
    server: {
        port: 3000,
        proxy: {
            '/api': {
                target: 'http://localhost:5000',
                changeOrigin: true
            },
            '/video': {
                target: 'http://localhost:5000',
                changeOrigin: true
            },
            '/login': {
                target: 'http://localhost:5000',
                changeOrigin: true
            },
            '/logout': {
                target: 'http://localhost:5000',
                changeOrigin: true
            },
            '/clock-wallpaper': {
                target: 'http://localhost:5000',
                changeOrigin: true
            },
            '/multi-play': {
                target: 'http://localhost:5000',
                changeOrigin: true
            },
            '/random-recommend': {
                target: 'http://localhost:5000',
                changeOrigin: true
            }
        }
    },
    
    build: {
        outDir: '../dist',
        emptyOutDir: true,
        sourcemap: true,
        minify: 'terser',
        terserOptions: {
            compress: {
                drop_console: true,
                drop_debugger: true
            }
        },
        rollupOptions: {
            input: {
                main: resolve(__dirname, 'web/templates/index.html'),
                multiPlay: resolve(__dirname, 'web/templates/multi_play.html'),
                randomRecommend: resolve(__dirname, 'web/templates/random_recommend.html'),
                clockWallpaper: resolve(__dirname, 'web/templates/clock_wallpaper.html'),
                login: resolve(__dirname, 'web/templates/login.html')
            },
            output: {
                manualChunks: {
                    'videojs': ['video.js'],
                    'vendor': []
                },
                chunkFileNames: 'static/js/[name]-[hash].js',
                entryFileNames: 'static/js/[name]-[hash].js',
                assetFileNames: (assetInfo) => {
                    const info = assetInfo.name.split('.');
                    const ext = info[info.length - 1];
                    if (/\.(png|jpe?g|gif|svg|webp|ico)$/i.test(assetInfo.name)) {
                        return 'static/images/[name]-[hash][extname]';
                    }
                    if (/\.css$/i.test(assetInfo.name)) {
                        return 'static/css/[name]-[hash][extname]';
                    }
                    return 'static/[ext]/[name]-[hash][extname]';
                }
            }
        },
        cssCodeSplit: true
    },
    
    css: {
        devSourcemap: true,
        postcss: {
            plugins: []
        }
    },
    
    resolve: {
        alias: {
            '@': resolve(__dirname, 'web/static/js'),
            '@modules': resolve(__dirname, 'web/static/js/modules'),
            '@components': resolve(__dirname, 'web/static/js/modules/components'),
            '@utils': resolve(__dirname, 'web/static/js/modules/utils'),
            '@api': resolve(__dirname, 'web/static/js/modules/api'),
            '@stores': resolve(__dirname, 'web/static/js/modules/stores'),
            '@css': resolve(__dirname, 'web/static/css')
        }
    },
    
    optimizeDeps: {
        include: ['video.js']
    }
});
