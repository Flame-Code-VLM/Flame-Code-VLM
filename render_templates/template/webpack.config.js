module.exports = {
  watch: false,
  output: {
    hashFunction: 'sha256',
  },
  watchOptions: {
    ignored: /node_modules/,
    poll: 10000,
    usePolling: true 
  }
};