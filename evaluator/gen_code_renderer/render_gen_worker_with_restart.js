const { parentPort, workerData } = require('worker_threads');
const fs = require('fs').promises;
const path = require('path');
const puppeteer = require('puppeteer');
const net = require('net');
const { spawn } = require('child_process');
const http = require('http');
const renderUtil = require('../../utils/render_util');
const DsChat = require('../../utils/ds');


const fatalLLMError = (error_code) => {
  return false
  // return error_code !== INTERNAL_SERVER_ERROR && error_code !== GATEWAT_TIMEOUT_ERROR;
}

const translateContentType = (splitter) => {
  switch (splitter) {
    case '// JavaScript (JS)':
      return 'js';
    case '// TypeScript (TS)':
      return 'ts';
    case '// JavaScript XML (JSX)':
      return 'jsx';
    case '// TypeScript XML (TSX)':
      return 'tsx';
    default:
      return 'jsx';
  }
}

const processStrings = (str) => {
  const splitPatterns = [
    /(\/\/ JavaScript \(JS\))/,
    /(\/\/ TypeScript \(TS\))/,
    /(\/\/ JavaScript XML \(JSX\))/,
    /(\/\/ TypeScript XML \(TSX\))/
  ];

  const pattern = new RegExp(splitPatterns.map(p => p.source).join('|'));

  const match = str.match(pattern);

  if (match) {
    const matchedPattern = match[0];
    const splitIndex = str.indexOf(matchedPattern);

    let firstPart = str.slice(0, splitIndex).trim();
    let secondPart = str.slice(splitIndex + matchedPattern.length).trim();

    firstPart = firstPart.replace(/^\/\/ CSS/, '').trim();

    return [firstPart, translateContentType(matchedPattern), secondPart];
  } else {
    const cleanedStr = str.replace(/^\/\/ CSS/, '').trim();
    return [cleanedStr, 'jsx', ''];
  }
};

// Main class for rendering
class Renderer {
  constructor(templatePath, port) {
    this.templatePath = templatePath;
    this.currentComponentConfigPath = null;
    this.currentComponentConfig = {};
    this.port = port;

    this.llmChat = new DsChat();
    this.modelName = 'deepseek-chat'
    this.llmChat.init();
  }

  async init() {
    this.port = await this.findAvailablePort(this.port);
    console.log('Clearing project...');
  }

  async findAvailablePort(startPort) { // delay in milliseconds
    const unavailablePorts = [6000]
    if (unavailablePorts.includes(startPort)) {
      return this.findAvailablePort(startPort + 1);
    }
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

  runCommand(command, commandArr, timeout, env = {}) {
    return spawn(command, commandArr, {
      cwd: this.templatePath,
      env: { ...process.env, ...env, PATH: process.env.PATH + ':/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin' },
      shell: '/bin/bash',
      timeout: timeout
    });
  }

  postProcessLLMResult(content) {
    if (!content) {
      return null;
    }

    // If there is </s> at the end of the content, remove it
    content = content.replace(/<\/s>$/g, '');

    // Regular expression to find code blocks
    const pattern = /```(.*?)\n(.*?)```/s;
    let matches = content.match(pattern);

    if (matches && matches.length > 2) {
      // Extract the code from the match
      return matches[2];
    }

    const pattern2 = /'''(.*?)\n(.*?)'''/s;
    matches = content.match(pattern2);
    if (matches && matches.length > 2) {
      // Extract the code from the match
      return matches[2];
    }

    // Remove \n at the end first
    content = content.trim();

    if (content.startsWith('```')) {
      content = content.substring(3);
    }
    if (content.startsWith("'''")) {
      content = content.substring(3);
    }
    // Check whether there is ``` or ''' at the end
    if (content.endsWith('```')) {
      content = content.slice(0, -3);
    }
    if (content.endsWith("'''")) {
      content = content.slice(0, -3);
    }

    if (content.startsWith('javascript\n')) {
      content = content.slice(11);
    } else if (content.startsWith('typescript\n')) {
      content = content.slice(11);
    } else if (content.startsWith('css\n')) {
      content = content.slice(4);
    } else if (content.startsWith('scss\n')) {
      content = content.slice(5);
    } else if (content.startsWith('sass\n')) {
      content = content.slice(5);
    } else if (content.startsWith('less\n')) {
      content = content.slice(5);
    } else if (content.startsWith('bash\n')) {
      content = content.slice(5);
    }

    return content;
  }

  async isPortAvailable(port, host = '127.0.0.1') {
    return new Promise((resolve, reject) => {
      const server = net.createServer();

      server.once('error', (err) => {
        if (err.code === 'EADDRINUSE') {
          // Port is occupied
          resolve(false);
        } else {
          reject(err);
        }
      });

      server.once('listening', () => {
        // Port is available, close the server
        server.close();
        resolve(true);
      });

      server.listen(port, host);
    });
  }

  async renderCode(id, index, componentStyle, componentType, componentCode, screenshotDir, repeat) {
    const screenshotPath = path.join(screenshotDir, `${id}_${index}_0.png`)

    // check if the screenshot already exists
    if (await fs.access(screenshotPath).then(() => true).catch(() => false)) {
      console.log(`Screenshot already exists: ${screenshotPath}`);
      return;
    }

    // console.log('Rendering component:', id, index);
    // console.log('Component type:', componentType);
    // console.log('Component code:', componentCode);
    // console.log('Component style:', componentStyle);
    // detect the style language and check validity
    let isValidStyle = false
    const styleLanguage = renderUtil.detectStyleLanguage(componentStyle);

    if (styleLanguage === 'CSS') {
      isValidStyle = renderUtil.isValidCSS(componentStyle);
    } else if (styleLanguage === 'SCSS') {
      isValidStyle = renderUtil.isValidSCSS(componentStyle);
    } else if (styleLanguage === 'LESS') {
      isValidStyle = renderUtil.isValidLESS(componentStyle);
    }
    const destFolder = path.join(this.templatePath, 'src/components');
    console.log('destFolder:', destFolder)
    await renderUtil.ensureExists(destFolder)
    const destCodePath = path.join(this.templatePath, 'src/components', `component.${componentType}`);

    if (isValidStyle) {
      console.log('style is valid', styleLanguage)
      if (styleLanguage === 'SCSS') {
        componentStyle = renderUtil.scssToCss(componentStyle);
      } else if (styleLanguage === 'LESS') {
        componentStyle = await renderUtil.lessToCss(componentStyle);
      }
      // const styleFileName = `style.${styleLanguage.toLowerCase()}`;
      if (componentStyle) {
        const destStylePath = path.join(this.templatePath, 'src/components', 'style.css');
        await fs.writeFile(destStylePath, componentStyle);
        await fs.writeFile(destCodePath, `import './style.css';\n` + componentCode);
      } else {
        await fs.writeFile(destCodePath, componentCode);
      }
    } else {
      console.log('style is invalid', styleLanguage)
      await fs.writeFile(destCodePath, componentCode);
    }

    try {
      await this.startServer(destCodePath);
      console.log(`Server started at http://localhost:${this.port}`);

      const serverUrl = `http://localhost:${this.port}`;
      await new Promise(resolve => setTimeout(resolve, 2000));
      await renderUtil.ensureExists(screenshotDir)
      await this.takeScreenshot(serverUrl, screenshotPath);
      console.log(`Screenshot taken: ${screenshotPath}`);

      // copy the screenshot for repeat times
      for (let i = 1; i < repeat; i++) {
        const screenshotPathRepeat = path.join(screenshotDir, `${id}_${index}_${i}.png`)
        // copy the screenshot
        await fs.copyFile(screenshotPath, screenshotPathRepeat);
      }
    } catch (error) {
      console.error(`Error processing component: ${error}`);
      if (error.message === 'Fatal LLMErr detected') {
        return false;
      }
    } finally {
      try {
        // kill process that occupies the port
        console.log(`Killing process that occupies port ${this.port}`)
        await this.clearPort(this.port);
      } catch (error) {
        console.error(`Error cleaning up after processing component: ${error}`);
      } finally {
        // clear the component folder
        console.log(`Clearing component folder...`);
        await renderUtil.deleteFile(path.join(this.templatePath, 'src/components'))

        console.log('Recreating components folder...');
        await fs.mkdir(path.join(this.templatePath, 'src/components'), { recursive: true });
      }
    }
  }

  // puppeteer version
  async takeScreenshot(url, outputPath) {
    let browser = null;
    try {
      browser = await puppeteer.launch({
        // executablePath: '/usr/bin/chromium-browser',
        executablePath: '/usr/bin/google-chrome',
        // executablePath: '/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome', // local
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
      });
      const page = await browser.newPage();
      // await page.goto(url, { waitUntil: 'networkidle0' });
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      // await page.goto(url, { waitUntil: 'load', timeout: 60000 });
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

  async checkServerIsResponsive(url) {
    return new Promise((resolve) => {
      http.get(url, (res) => {
        console.log('statusCode:', url, res.statusCode);
        resolve(res.statusCode === 200);
      }).on('error', (e) => {
        console.error('Server not responsive:', url, e.message);
        resolve(false);
      });
    });
  }

  async loadComponentFile(file_path) {
    const componentCode = await fs.readFile(file_path, 'utf8');
    return componentCode;
  }

  async checkServerStatus(hostname, port, path) {
    return new Promise((resolve, reject) => {
      const options = {
        hostname: hostname,
        port: port,
        path: path,
        method: 'GET'
      };

      const req = http.request(options, (res) => {
        if (res.statusCode === 200) {
          resolve(true);
        } else {
          resolve(false);
        }
      });

      req.on('error', (e) => {
        resolve(false);
      });

      req.end();
    });
  }

  async startServer() {
    console.log(`Starting server at port ${this.port}...`);
    const startTimeout = 120000;

    let retry_num = 0;
    const max_retry = 2;

    while (retry_num < max_retry) {
      console.log('******************************************')
      console.log('** server start round:', retry_num, this.port)
      console.log('******************************************')
      let err_log = '';
      let isServerStarted = false;
      let server;
      await new Promise((resolve, reject) => {
        server = this.runCommand('npm', ['run', 'start'], startTimeout, { PORT: this.port });

        const timeoutId = setTimeout(async () => {
          console.error('Server start timeout, pass to taking screenshot to check whether there is error.');
          server.kill('SIGTERM'); // Attempt to gracefully terminate
          isServerStarted = true;
          resolve();// resolve and let the taking screenshot handle the error
          // reject(new Error('Server start timed out. Process terminated.'));
        }, 90000);

        server.stdout.on('data', (data) => {
          const dataStr = data.toString() || '';
          err_log += dataStr;
          if (dataStr.includes('Something is already running on port')) {
            server.kill('SIGTERM'); // Attempt to gracefully terminate
            reject(new Error('Port already in use. Please clear the port and try again.'));
          }

          // Try to extract the port from various formats of the URL
          const match = dataStr.match(/http:\/\/(?:localhost|127\.0\.0\.1):(\d+)/);
          if (match) {
            console.log('Found port:', match[1]);
            this.port = parseInt(match[1], 10);
            isServerStarted = true;
            clearTimeout(timeoutId);  // Clear the timeout
            resolve();  // Resolve when the port is found
          }
        });

        server.stderr.on('data', (data) => {
          err_log += data.toString() || '';
        });

        server.on('error', (error) => {
          console.error('Error occurred:', error);
          server.kill('SIGTERM'); // Attempt to gracefully terminate
          reject(new Error(`npm start failed: ${error.message}`));
        });

        server.on('close', (code) => {
          console.log('Server closed with code:', code);
          clearTimeout(timeoutId);  // Clear the timeout

          if ((code !== 0 && !this.port) || err_log.includes('Failed to compile') || !isServerStarted) {
            server.kill('SIGTERM'); // Attempt to gracefully terminate
            reject(new Error(`Server exited with code ${code}: ${err_log}`));
          } else {
            console.log('npm start completed successfully.');
            resolve();
          }
        });
      }).then(async () => {
        console.log('***************** record server start log *****************');
        console.log(err_log);
        console.log('***************** end record server start log *****************');

        console.log('Server started.');
        retry_num = max_retry; // Force exit from the loop
      }).catch(async (error) => {
        console.error('Failed to start server:', error);
        try {
          console.log('Clearing port...', this.port);
          await this.clearPort(this.port);
        } catch (e) {
          console.log('Failed to clear port after server start failure:', e);
        }
        if (!err_log.includes('Something is already running on port')) {
          await new Promise(resolve => setTimeout(resolve, 2000));
          console.log('***************** record error log *****************');
          console.log(err_log);
          console.log('***************** end record error log *****************');

          err_log = '';
          retry_num++;
          console.log(`Debug start server retry number: ${retry_num}`);
          if (retry_num >= max_retry) {
            throw error;
          }
        }

      }).finally(async () => {
        if (server) {
          server.kill('SIGTERM');
        }
      });
    }
  }

  async clearPort(port) {
    try {
      const portOccupy = this.runCommand('lsof', ['-t', `-i:${port}`], 5000);
      const pids = await new Promise((resolve, reject) => {
        let output = '';
        portOccupy.stdout.on('data', (data) => (output += data.toString()));
        portOccupy.on('close', (code) => {
          if (code === 0) {
            resolve(output.trim());
          } else {
            reject(new Error(`Failed to find process on port ${port}`));
          }
        });
      });

      if (pids) {
        const pidArr = pids.split('\n');
        for (const pid of pidArr) {
          console.log(`Killing process with PID: ${pid}`);
          await new Promise((resolve, reject) => {
            const killProcess = this.runCommand('kill', ['-9', pid], 5000);
            killProcess.on('close', (code) => {
              if (code === 0) {
                resolve();
              } else {
                reject(new Error(`Failed to kill process ${pid}`));
              }
            });
          });
        }
      }
    } catch (error) {
      console.error('Failed to clear port:', error);
      throw error;
    }
  }
}

function extractComponentCode(output) {
  console.log('Extracting component code...');
  const [tmpStyle, tmpType, tmpCode] = processStrings(output);
  if (tmpCode) {
    return [tmpStyle, tmpType, tmpCode]
  }
  const index = output.indexOf("import ");
  let style = '';
  let component = '';
  if (index === -1) {
    return [output.replace(/^\/\/ CSS/, '').trim(), 'jsx', ''];
  }
  style = output.slice(0, index).replace(/^\/\/ CSS/, '').trim();
  component = output.slice(index).trim();
  return [style, 'jsx', component];
}

async function processBatch(batch, batchIdx, reactAppDir, screenshotDir) {
  const renderer = new Renderer(`${reactAppDir}/t-${batchIdx}`, 3000 + batchIdx * 100);
  renderer.init();
  console.log('Running at:', renderer.port);
  console.log('Rendering all components...');

  for (let j = 0; j < batch.length; j++) {
    await new Promise(resolve => setTimeout(resolve, 1000));
    const code = batch[j];
    console.log('=====================================================================================');
    console.log(' ')
    console.log(`Processing ${j + 1}/${batch.length} code...`);
    console.log(' ')
    console.log('=====================================================================================');

    const [componentStyle, componentType, componentCode] = extractComponentCode(code.output);
    // console.log('Component style:', componentStyle);
    // console.log('Component type:', componentType);
    // console.log('Component code:', componentCode);
    if (!componentCode) {
      // console.log('No component code found in:', code.output);
      continue;
    }
    await renderer.renderCode(code.id, code.index, componentStyle, componentType, componentCode, screenshotDir, code.repeat)
    // break
  }
  console.log('Batch processing completed');
}

processBatch(
  workerData.batch,
  workerData.batchIdx,
  workerData.reactAppDir,
  workerData.screenshotDir,
).then(() => {
  console.log('Batch processing completed');
}).catch(error => {
  console.error('Error processing batch:', error);
  parentPort.postMessage('Batch processing failed');
});