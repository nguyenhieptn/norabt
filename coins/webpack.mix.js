let mix = require('laravel-mix');

/*
 |--------------------------------------------------------------------------
 | Mix Asset Management (Strict Memory & CPU Optimization)
 |--------------------------------------------------------------------------
 | Khống chế tối đa 2 CPU cores và 1.5GB RAM khi biên dịch Webpack
 */

mix.options({
    processCssUrls: false,
    terser: {
        parallel: 2,               // Giới hạn Minifier chỉ chạy trên tối đa 2 CPU Cores
        extractComments: false
    }
});

// Tắt source maps trong production để tiết kiệm hơn 50% RAM
mix.sourceMaps(false);

mix.webpackConfig({
    parallelism: 2,                // Giới hạn Webpack Compiler chỉ chạy song song 2 modules
    stats: 'errors-warnings',      // Chỉ lưu trữ log lỗi/cảnh báo, giảm giữ AST trong RAM
    resolve: {
        extensions: ['.js', '.scss', '.json'],
        alias: {
            "@root": __dirname + "/resources",
            "@react": __dirname + "/resources/react",
            "@comp": __dirname + "/resources/react/components",
        },
    },
    module: {
        rules: [{
            test: /\.scss$/i,
            use: ["sass-loader"]
        }]
    },
});

mix.js('resources/react/app.js', 'public/react/js').react();
mix.js('resources/simulation/app.js', 'public/simulation/js').react();
