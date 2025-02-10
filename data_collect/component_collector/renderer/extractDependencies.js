const fs = require('fs');
const path = require('path');
const { getSecondLevelFiles } = require('../../../utils/utils');

const CODE_PATH = process.argv[2];
const OUTPUT_FILE = process.argv[3];
const outputDir = path.dirname(OUTPUT_FILE);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

const BATCH_NUM = 100;

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

async function processData(fileList) {
  let allDependencies = new Set();
  for (const filePath of fileList) {
    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    let componentCode = data['code_with_ori_img'] || data['debug_component'] || data['raw_component'] || null
    if (!componentCode) {
      console.log('No component code found in:', filePath);
      continue;
    }
    const dependencies = extractDependenciesFromCode(componentCode);
    // console.log('Dependencies:', dependencies);
    allDependencies = new Set([...allDependencies, ...dependencies]);
  }
  return allDependencies;
}

async function main(codePath) {
  return new Promise(async (resolve, reject) => {
    const jsonFiles = getSecondLevelFiles(codePath, ['package.json']);
    console.log('Processing files:', jsonFiles);
    console.log(`Got ${jsonFiles.length} codes`)
    const promises = [];

    const batchSize = Math.ceil(jsonFiles.length / BATCH_NUM);

    for (let i = 0; i < jsonFiles.length; i += batchSize) {
      const batch = jsonFiles.slice(i, i + batchSize);
      promises.push(processData(batch));
    }

    try {
      let allDependencies = new Set();
      const results = await Promise.all(promises);
      results.forEach((result, index) => {
        // console.log(`Batch ${index + 1} processed successfully`);
        allDependencies = new Set([...allDependencies, ...result, 'ajv']);
      });
      allDependencies = [...allDependencies].map(d => {
        if (d === 'react') {
          return {
            name: 'react',
            version: '17'
          }
        } else if (d === 'react-dom') {
          return {
            name: 'react-dom',
            version: '17'
          }
        } else if (d === 'react-scripts') {
          return {
            name: 'react-scripts',
            version: '4'
          }
        } else if (d === 'react-native') {
          return {
            name: 'react-native',
            version: 'latest'
          }
        } else {
          return {
            name: d,
          }
        }
      })
      console.log('All dependencies:', allDependencies);
      resolve(allDependencies);
    } catch (error) {
      console.error('Failed to process one or more batches:', error);
      reject(error);
    }
  });
}

(async () => {
  try {
    const alldependencies = await main(CODE_PATH);
    const jsonData = JSON.stringify(alldependencies, null, 2);
    await fs.promises.writeFile(OUTPUT_FILE, jsonData);
    console.log(`Dependencies have been saved to ${OUTPUT_FILE}`);
  } catch (err) {
    console.error("Error:", err);
  }
})();