const { extractDependenciesFromCode } = require("../../../utils/depedencyAnalyzer");
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const net = require('net');
// const { runCommand } = require('../utils');
const { exec } = require('child_process');
const fetch = require('node-fetch');


// load jsonl file
function loadTestCode(path) {
  // load json data
  const fileContents = fs.readFileSync(path, 'utf8');
  const testData = JSON.parse(fileContents);
  return testData;
}

function runCommand(path, cmd) {
  return new Promise((resolve, reject) => {
    // const command = 'npm cache clean --force';
    console.log('run command: ', cmd);
    exec(cmd, { cwd: path }, (error, stdout, stderr) => {
      if (error) {
        console.error(`Error: ${error.message}`);
        console.error(`stderr: ${stderr}`);
        return resolve(false);
      }
      console.log(`stdout: ${stdout}`);
      console.log('cmd success.');
      resolve(true);
    });
  });
}

async function clearProject(templateProjectPath) {
  await runCommand(templateProjectPath, 'npm cache clean --force');
  await runCommand(templateProjectPath, 'rm -rf package-lock.json');
  await runCommand(templateProjectPath, 'rm -rf ' + path.join(templateProjectPath, 'src', 'components', '*'));
}

function writeblankPackageJson(templateProjectPath) {
  const packageTemplate = {
    "name": "",
    "version": "0.1.0",
    "private": true,
    "scripts": {
      "start": "react-scripts start --watch-options-poll=1000",
      "build": "react-scripts build",
      "test": "react-scripts test",
      "eject": "react-scripts eject"
    },
    "browserslist": {
      "production": [
        ">0.2%",
        "not dead",
        "not op_mini all"
      ],
      "development": [
        "last 1 chrome version",
        "last 1 firefox version",
        "last 1 safari version"
      ]
    }
  }
  console.log('writing package.json', path.join(templateProjectPath, 'package.json'));
  try {
    fs.writeFileSync(path.join(templateProjectPath, 'package.json'), JSON.stringify(packageTemplate, null, 2));
  } catch (e) {
    console.log('writting package.json error: ', e);
  }
}

function installDependencies(projectPath, dependencies) {
  if (dependencies.length === 0) {
    return Promise.resolve(true);
  }
  return new Promise((resolve, reject) => {
    const command = `npm install ${dependencies.join(' ')}`;

    exec(command, { cwd: projectPath }, (error, stdout, stderr) => {
      if (error) {
        console.error(`Error installing dependencies: ${error.message}`);
        console.error(`stderr: ${stderr}`);
        return resolve(false);
      }
      console.log(`stdout: ${stdout}`);
      console.log('Dependencies installed successfully.');
      resolve(true);
    });
  });
}

async function findAvailablePort(startPort = 3000) { // delay in milliseconds
  const server = net.createServer();
  server.unref();
  return new Promise((resolve, reject) => {
    server.on('error', (e) => {
      server.close();
      resolve(this.findAvailablePort(startPort + 1));
    });
    server.listen(startPort, () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}

async function waitForServer(port, timeout = 30000) {
  const startTime = Date.now();
  return new Promise((resolve, reject) => {
    const check = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:${port}`);
        if (response.ok) {
          clearInterval(check);
          resolve();
        }
        if (Date.now() - startTime > timeout) {
          clearInterval(check);
          reject(new Error(`Server did not respond on port ${port} within timeout`));
        }
      } catch (error) {
        console.error('Error:', error.message);
        reject(new Error(`Server did not respond on port ${port} with error`));
      }
    }, 1000);
  });
}

async function startServer(projectPath, port) {
  return new Promise(async (resolve) => {
    const command = `PORT=${port} npm run start`;

    const startProcess = exec(command, { cwd: projectPath });

    startProcess.stdout.on('data', async (data) => {
      console.log(`stdout: ${data}`);
      if (data.includes('Compiled successfully')) {
        try {
          await waitForServer(port);
          console.log('Project started successfully on port', port);
          resolve(true);
        } catch (error) {
          console.error('Error: ', error.message);
          resolve(false);
        }
      }
    });

    startProcess.stderr.on('data', (data) => {
      console.error(`stderr: ${data}`);
    });

    startProcess.on('error', (error) => {
      console.error(`Error starting project: ${error.message}`);
      resolve(false);
    });
  });
}

function stopServer(port) {
  return new Promise((resolve, reject) => {
    exec(`lsof -t -i:${port}`, (error, stdout) => {
      if (error) {
        console.error(`Error finding process: ${error.message}`);
        return reject(false);
      }

      const pid = stdout.trim();
      if (pid) {
        exec(`kill -9 ${pid}`, (killError) => {
          if (killError) {
            console.error(`Error stopping server: ${killError.message}`);
            return reject(false);
          }
          console.log(`Server on port ${port} stopped successfully.`);
          resolve(true);
        });
      } else {
        console.log(`No server running on port ${port}.`);
        resolve(false);
      }
    });
  });
}

async function takeScreenshot(url, outputPath) {
  let browser = null;
  try {
    browser = await puppeteer.launch({
      // executablePath: '/usr/bin/chromium-browser',
      // executablePath: '/bin/google-chrome',
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    await page.goto(url, { waitUntil: 'networkidle0' });
    // await page.goto(url, { waitUntil: 'networkidle0' });
    await page.goto(url, { waitUntil: 'load', timeout: 60000 });
    await page.evaluate(async () => {
      await new Promise((resolve) => {
        let totalHeight = 0;
        const distance = 100;
        const timer = setInterval(() => {
          window.scrollBy(0, distance);
          totalHeight += distance;
          if (totalHeight >= document.body.scrollHeight) {
            clearInterval(timer);
            resolve();
          }
        }, 100);
      });
    });

    await page.evaluate(() => {
      document.body.style.overflow = 'visible';
      document.documentElement.style.overflow = 'visible';
    });
    await page.screenshot({ path: outputPath, fullPage: true });
  } catch (error) {
    console.error('Error taking screenshot:', error);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

function extractDependenciesInPackageJson(packageJsonPath) {
  const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
  const dependencies = Object.keys(packageJson.dependencies || {});
  return dependencies;
}

async function run() {
  const testData = loadTestCode('./testDataEN80.json');
  const outputPath = path.join(__dirname, 'imgs');

  if (!fs.existsSync(outputPath)) {
    fs.mkdirSync(outputPath, { recursive: true });
  }

  const templateProjectPath = path.join(__dirname, 'template');

  for (const item of testData) {
    const { problem_id, file_type, image, style, component } = item;

    await clearProject(templateProjectPath);

    const componentPath = path.join(templateProjectPath, 'src', 'components');
    if (!fs.existsSync(componentPath)) {
      fs.mkdirSync(componentPath, { recursive: true });
    }
    fs.writeFileSync(path.join(componentPath, 'style.css'), style);
    fs.writeFileSync(path.join(componentPath, 'component.' + file_type), 'import "./style.css"\n' + component);

    const dependencies = extractDependenciesFromCode(component);

    const dependenciesInPackageJson = extractDependenciesInPackageJson(path.join(templateProjectPath, 'package.json'));
    const diff = dependencies.filter(dep => !dependenciesInPackageJson.includes(dep));

    let bugFree = await installDependencies(templateProjectPath, diff);
    const port = await findAvailablePort();
    const startBugFree = await startServer(templateProjectPath, port);
    // const startBugFree = await runCommand(templateProjectPath, `PORT=${port} npm run start`);
    const outputImgPath = path.join(outputPath, problem_id);
    if (!fs.existsSync(outputImgPath)) {
      fs.mkdirSync(outputImgPath, { recursive: true });
    }
    const outputImgName = `${problem_id}.png`;
    const url = `http://localhost:${port}`;
    await new Promise(resolve => setTimeout(resolve, 5000));
    await takeScreenshot(url, path.join(outputImgPath, outputImgName));

    await new Promise(resolve => setTimeout(resolve, 2000));
    await stopServer(port);
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  console.log('All done.')
}


run();