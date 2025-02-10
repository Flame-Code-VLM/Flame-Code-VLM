// parseImports.js
const fs = require('fs');
const parser = require('@babel/parser');

function extractImports(filePath) {
  try {
    const code = fs.readFileSync(filePath, 'utf8');
    const ast = parser.parse(code, {
      sourceType: 'module',
      plugins: ['jsx', 'typescript', ['decorators', { decoratorsBeforeExport: true }]]
    });

    const imports = ast.program.body.filter(node => node.type === 'ImportDeclaration');
    console.log(JSON.stringify(imports));
  } catch (error) {
    console.error(`Error parsing file: ${filePath}, ${error}`);
  }
}

// Take file path from command line arguments
const filePath = process.argv[2];
extractImports(filePath);
