function extractDependenciesFromCode(code) {
  const dependencies = extractDependencies(code);
  const necessaryDependencies = ['react', 'react-dom', 'react-scripts', 'html-webpack-plugin']
  return [...new Set([...dependencies, ...necessaryDependencies])];
}

function extractDependencies(code) {
  const importRegex = /import\s[\w*\s{},]*\sfrom\s['"]([^'"]+)['"]|import\s['"]([^'"]+)['"]/g;
  const requireRegex = /require\(['"]([^'"]+)['"]\)/g;

  const dependencies = new Set();

  let match;
  while ((match = importRegex.exec(code)) !== null) {
    if (match[1]) dependencies.add(match[1]);
    if (match[2]) dependencies.add(match[2]);
  }

  while ((match = requireRegex.exec(code)) !== null) {
    dependencies.add(match[1]);
  }

  // console.log("dependencies: ", dependencies);

  return filterDependencies(dependencies);
}

function extractPackageName(name) {
  if (name.startsWith('@')) {
    const parts = name.split('/');
    return parts[0] + '/' + parts[1];
  }
  const parts = name.split('/');
  return parts[0];
}

function filterDependencies(dependencies) {
  return Array.from(dependencies)
    .filter(name => !name.startsWith('.') && !name.startsWith('/'))
    .map(name => extractPackageName(name))
    .sort();
}

module.exports = {
  extractDependenciesFromCode,
}