process.env.NODE_ENV = 'development';
process.env.PUBLIC_URL = "/public/";

const fs = require('fs-extra');
const paths = require('react-scripts/config/paths');
const webpack = require('webpack');
const config = require('react-scripts/config/webpack.config.js');
const path = require('path');

const conf = config('development');


// We needed to output to a specific folder for cross-framework interop.
// Make sure to change the output path or to remove this line if the behavior
// of the original gist is sufficient for your needs!
conf.output.path = path.join(process.cwd(), './build');
conf.output.publicPath = process.env.PUBLIC_URL;

webpack(conf).watch({}, (err, stats) => {
  if (err) {
    console.error(err);
  } else {
    copyPublicFolder();
  }
  console.error(stats.toString({
    chunks: false,
    colors: true
  }));
});

function copyPublicFolder() {
  fs.copySync(paths.appPublic, paths.appBuild, {
    dereference: true,
    filter: file => file !== paths.appHtml
  });
}