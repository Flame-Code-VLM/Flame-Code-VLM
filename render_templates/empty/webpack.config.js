const path = require('path');

module.exports = {
  watchOptions: {
    ignored: /node_modules/,
    poll: 10000  // Optional: Enable polling to handle file changes
  }
};
