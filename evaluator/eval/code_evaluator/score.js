const fs = require('fs');
const path = require('path');
const parser = require('@babel/parser');
const traverse = require('@babel/traverse').default;

function analyzeReactCode(code) {
  let ast;
  try {
    ast = parser.parse(code, {
      sourceType: 'module',
      plugins: ['jsx', 'typescript'],
    });
  } catch (err) {
    return { error: true, message: `Parse error: ${err.message}` };
  }

  let hooksUsed = 0;
  let eventAttributes = 0;
  let eventCallbackUpdatesCount = 0;
  let components = 0;

  function isReactHook(name) {
    const officialHooks = [
      'useState', 'useEffect', 'useReducer', 'useContext',
      'useCallback', 'useMemo', 'useRef', 'useLayoutEffect',
      'useImperativeHandle',
    ];
    return officialHooks.includes(name) || (name.startsWith('use') && name.length > 3);
  }

  function detectStateUpdateInFunction(bodyNode) {
    let foundUpdate = false;
    traverse(
      { type: 'File', program: { type: 'Program', body: [bodyNode] } },
      {
        CallExpression(path) {
          const callee = path.node.callee;
          if (callee.type === 'Identifier' && (callee.name.startsWith('set') || callee.name === 'dispatch')) {
            foundUpdate = true;
          }
        },
      },
    );
    return foundUpdate;
  }

  traverse(ast, {
    CallExpression(path) {
      const callee = path.node.callee;
      if (callee.type === 'Identifier' && isReactHook(callee.name)) {
        hooksUsed += 1;
      }
    },
    JSXOpeningElement(path) {
      const attributes = path.node.attributes || [];
      attributes.forEach((attr) => {
        if (attr.name && /^on[A-Z]/.test(attr.name.name)) {
          eventAttributes += 1;

          const callbackNode = attr.value?.expression;
          if (callbackNode && (callbackNode.type === 'ArrowFunctionExpression' || callbackNode.type === 'FunctionExpression')) {
            const hasUpdate = detectStateUpdateInFunction(callbackNode.body);
            if (hasUpdate) {
              eventCallbackUpdatesCount += 1;
            }
          }
        }
      });
    },
    FunctionDeclaration(path) {
      if (path.node.id && /^[A-Z]/.test(path.node.id.name)) {
        components += 1;
      }
    },
    VariableDeclarator(path) {
      if (path.node.id.type === 'Identifier' && /^[A-Z]/.test(path.node.id.name)) {
        components += 1;
      }
    },
    ClassDeclaration(path) {
      if (path.node.id && /^[A-Z]/.test(path.node.id.name)) {
        components += 1;
      }
    },
  });

  const total = hooksUsed + eventAttributes + eventCallbackUpdatesCount + components;

  return {
    hooksUsed,
    eventAttributes,
    eventCallbackUpdatesCount,
    components,
    total,
  };
}

function calculateReactCodeSimilarity(metricsA, metricsB, targetMetrics) {
  let matricsASum = 0;
  let matricsBSum = 0;
  for (const metric of targetMetrics) {
    matricsASum += metricsA[metric] || 0;
    matricsBSum += metricsB[metric] || 0;
  }
  if (matricsASum === 0 && matricsBSum !== 0) {
    return 0;
  } else {
    return 1;
  }
}

(function main() {
  const args = process.argv.slice(2);
  try {
    const genCode = args[0];
    const refCode = args[1];
    const genCodeResult = analyzeReactCode(genCode);
    const refCodeResult = analyzeReactCode(refCode);
    const targetMetrics = ['hooksUsed', 'eventAttributes', 'eventCallbackUpdatesCount'];
    const genScore = calculateReactCodeSimilarity(genCodeResult, refCodeResult, targetMetrics);
    console.log(JSON.stringify({
      genCodeResult,
      refCodeResult,
      genScore,
    }, null, 2));
  } catch (e) {
    console.log(JSON.stringify({
      genCodeResult: '',
      refCodeResult: '',
      genScore: 0,
    }, null, 2))
  }
})();