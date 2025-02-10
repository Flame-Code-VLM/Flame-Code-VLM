const fs = require('fs');
const path = require('path');
const { Worker } = require('worker_threads');
const renderUtil = require('../../../utils/render_util');
const { getSecondLevelFiles } = require('../../../utils/utils');
const { exec } = require('child_process');

const PROJECT_DIR = process.cwd();
const BATCH_NUM = process.argv[2];
const CODE_PATH = process.argv[3];
const REACT_APP_DIR = process.argv[4];
const SCREENSHOT_DIR = process.argv[5];
const BASE_DIR = path.join(PROJECT_DIR, 'data_collect/component_collector/renderer')

function runService(baseDir, workerData) {
  return new Promise((resolve, reject) => {
    const worker = new Worker(`${baseDir}/render_gen_worker.js`, { workerData });
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
async function main(codePath, reactAppDir, screenshotDir, batchNum) {
  await renderUtil.ensureExists(screenshotDir)

  const jsonFiles = getSecondLevelFiles(codePath, ['package.json']);
  console.log(`Got ${jsonFiles.length} codes`)
  const promises = [];

  const batchSize = Math.ceil(jsonFiles.length / batchNum);

  console.log(`Processing ${batchNum} batches with size ${batchSize}...`);
  for (let i = 0; i < jsonFiles.length; i += batchSize) {
    const batch = jsonFiles.slice(i, i + batchSize);
    // console.log(`Processing batch ${i / batchSize}...`);
    promises.push(runService(BASE_DIR, {
      batch,
      batchIdx: i / batchSize + 1,
      batchSize: batchSize,
      reactAppDir: reactAppDir,
      screenshotDir: screenshotDir,
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

main(CODE_PATH, REACT_APP_DIR, SCREENSHOT_DIR, BATCH_NUM).catch(console.error);
