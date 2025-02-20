let mix = require('laravel-mix');

/*
 |--------------------------------------------------------------------------
 | Mix Asset Management
 |--------------------------------------------------------------------------
 |
 | Mix provides a clean, fluent API for defining some Webpack build steps
 | for your Laravel application. By default, we are compiling the Sass
 | file for the application as well as bundling up all the JS files.
 |
 */


mix.webpackConfig({
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

// complie all scss file to correctponse folder in public




