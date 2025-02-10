const fs = require('fs');
const path = require('path');
const { Worker } = require('worker_threads');
const renderUtil = require('../../utils/render_util');
const { exec } = require('child_process');

const PROJECT_DIR = process.argv[2];
const MODEL_NAME = process.argv[3];
const BATCH_NUM = process.argv[4];
const TARGET_GEN_CODE_PATH = process.argv[5]

const BASE_DIR = path.join(PROJECT_DIR, 'evaluator/gen_v2')
const REACT_APP_DIR = path.join(PROJECT_DIR, 'render_templates/linked')
const SCREENSHOT_DIR = process.argv[6]

function runService(baseDir, workerData) {
  return new Promise((resolve, reject) => {
    const worker = new Worker(`${baseDir}/render_gen_worker_with_restart.js`, { workerData });
    worker.on('message', resolve);
    worker.on('error', reject);
    worker.on('exit', (code) => {
      if (code !== 0) {
        reject(new Error(`Worker stopped with exit code ${code}`));
      }
    });
  });
}

// Main function to run in parallel
async function main() {
  const targetCodeJson = path.join(TARGET_GEN_CODE_PATH, `${MODEL_NAME}_results.json`)
  const targetScreenshotDir = path.join(SCREENSHOT_DIR, MODEL_NAME)
  await renderUtil.ensureExists(targetScreenshotDir)

  const codes = JSON.parse(fs.readFileSync(targetCodeJson, 'utf8'));
  console.log(`Got ${codes.length} codes`)
  const promises = [];

  const batchSize = Math.ceil(codes.length / BATCH_NUM);

  console.log(`Processing ${BATCH_NUM} batches with size ${batchSize}...`);
  for (let i = 0; i < codes.length; i += batchSize) {
    const batch = codes.slice(i, i + batchSize);
    promises.push(runService(BASE_DIR, {
      batch,
      batchIdx: i / batchSize + 1,
      batchSize: batchSize,
      reactAppDir: REACT_APP_DIR,
      screenshotDir: targetScreenshotDir,
    }));
  }

  try {
    // run npm clean cache first
    exec('npm cache clean --force', (error, stdout, stderr) => {
      if (error) {
        console.log('Failed to clean npm cache:', error.message);
      }
      console.log('npm cache cleaned');
    });

    const results = await Promise.all(promises);
    results.forEach((result, index) => {
      console.log(`Batch ${index + 1} processed successfully`);
    });
  } catch (error) {
    console.error('Failed to process one or more batches:', error);
  }
}

main().catch(console.error);
