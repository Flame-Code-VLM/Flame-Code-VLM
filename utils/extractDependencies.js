const fs = require('fs');
const path = require('path');

const MODEL_NAME = process.argv[2];
if (!MODEL_NAME) {
  console.error("Error: MODEL_NAME is required.");
  console.log("Usage: node script.js <MODEL_NAME>");
  process.exit(1);
}
const TARGET_GEN_CODE_PATH = process.argv[3];
const OUTPUT_FILE = process.argv[4];
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

function extractComponentCode(output) {
  // split by one of the following: '// JavaScript (JS)', 'TypeScript (TS)', 'JavaScript XML (JSX)', 'TypeScript XML (TSX)'
  let blocks = output.split(/\/\/ JavaScript \(JS\)|TypeScript \(TS\)|JavaScript XML \(JSX\)|TypeScript XML \(TSX\)/);
  if (blocks.length < 2) {
    // split by the first import statement
    blocks = output.split(/import\s/);
    if (blocks.length < 2) {
      return null;
    } else {
      return blocks[1];
    }
  } else {
    return blocks[1];
  }
}

async function processData(dataList) {
  let allDependencies = new Set();
  for (const data of dataList) {
    const componentCode = extractComponentCode(data['output']);
    if (!componentCode) {
      console.log('No component code found in:', data['output']);
      continue;
    }
    const dependencies = extractDependenciesFromCode(data['output']);
    // console.log('Dependencies:', dependencies);
    allDependencies = new Set([...allDependencies, ...dependencies]);
  }
  return allDependencies;
}

async function main(modelName) {
  return new Promise(async (resolve, reject) => {
    const gen_results_path = `${TARGET_GEN_CODE_PATH}/${modelName}_results.json`;
    const jsonDataList = JSON.parse(await fs.readFileSync(gen_results_path, 'utf8'));
    console.log(`Got ${jsonDataList.length} codes`)
    const promises = [];

    const batchSize = Math.ceil(jsonDataList.length / BATCH_NUM);

    for (let i = 0; i < jsonDataList.length; i += batchSize) {
      const batch = jsonDataList.slice(i, i + batchSize);
      // console.log(`Processing batch ${i / batchSize}...`);
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
    const alldependencies = await main(MODEL_NAME);
    const jsonData = JSON.stringify(alldependencies, null, 2);
    await fs.promises.writeFile(OUTPUT_FILE, jsonData);

    console.log(`Dependencies have been saved to ${OUTPUT_FILE}`);
  } catch (err) {
    console.error("Error:", err);
  }
})();