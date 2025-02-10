const { parentPort, workerData } = require('worker_threads');
const fs = require('fs').promises;
const path = require('path');
const puppeteer = require('puppeteer');
const net = require('net');
const { spawn } = require('child_process');
const http = require('http');
const renderUtil = require('../../../utils/render_util');
const { llmChat } = require('../../../utils/llm');


const fatalLLMError = (error_code) => {
  return false
  // return error_code !== INTERNAL_SERVER_ERROR && error_code !== GATEWAT_TIMEOUT_ERROR;
}

// Main class for rendering
class Renderer {
  constructor(repoPath, templatePath, port) {
    this.repoPath = repoPath;
    this.templatePath = templatePath;
    this.currentComponentConfigPath = null;
    this.currentComponentConfig = {};
    this.port = port;
  }

  async init() {
    this.port = await this.findAvailablePort(this.port);
    let cpImgResult = await this.cpImgs();
    console.log('cpImgResult:', cpImgResult);
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

  async renderCode(componentStyle, componentType, componentCode, screenshotPath) {
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
      await this.takeScreenshot(serverUrl, screenshotPath);
      console.log(`Screenshot taken: ${screenshotPath}`);
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

  async hasBugInStartLog(log) {
    const prompt = `Objective: Assess whether any critical issues present in the log entries can prevent the server from starting successfully after executing npm start.

    Input Log Content:

    ${log}
    Instructions for Analysis:

    Filter for Critical Errors and Warnings: Search the logs for any entries that include "error", "failed", "exception", "unable to connect", "missing", or any other indicators that are typically associated with critical failures.
    Determine Criticality: Evaluate whether the identified errors or warnings are directly related to server startup processes such as binding to required ports, loading essential configuration files, or establishing necessary database connections.
    Issue Criticality Assessment: Based on the errors and warnings:
    If any log entry directly impacts the server’s ability to start or indicates a service-critical failure, respond with "yes".
    If no such entries are found and the issues are minor or unrelated to immediate startup processes, respond with "no".

    Expected Outcome:
    A single word, "yes" or "no", indicating whether a critical issue preventing server startup is present in the logs, no other comments, explanations, or any other content are needed.`
    const llmDetectBugResult = await llmChat.chat({ prompt })
    const detectBug = llmDetectBugResult.content;
    const statusCode = llmDetectBugResult.error_code;
    if (detectBug) {
      const hasBug = this.postProcessLLMResult(detectBug);
      return [hasBug === 'yes', false];
    } else {
      return [false, fatalLLMError(statusCode)];
    }
  }

  async genStartServerDebugPrompt(err_msg, component_file_path) {
    const componentCode = await this.loadComponentFile(component_file_path);
    const prompt = `Task: Resolve server start errors by updating the React component code.

    Error Message:
    ${err_msg}
    
    Component Code:
    ${componentCode}
    
    Instructions:
    1. Parse the provided error message from the server start process.
    2. Examine the current component code for any discrepancies or issues that could be causing the server start failure. Note that the code may be in JavaScript or TypeScript.
    3. Correct any syntax errors or typos found in the code.
    4. Ensure the component's structure is valid and adheres to React conventions.
    5. Make necessary adjustments to the code to resolve the errors indicated by the error message, without adding any new debugging statements.
    6. Remove any dependencies that are causing the server start failure, and replace them with inline code or self-contained solutions.
    
    Expected Output:
    Respond with the corrected version of the component code only. The output should be formatted in a markdown code block. Specify in the code block tag whether the output code is JavaScript or TypeScript, based on the input code's language:
    
    \`\`\`javascript
    <UPDATED_COMPONENT_CODE>
    \`\`\`
    
    or
    
    \`\`\`typescript
    <UPDATED_COMPONENT_CODE>
    \`\`\`
    
    Ensure that the response includes only the code block in markdown format, with no additional comments, labels, or explanatory text.
    `;
    return prompt;
  }

  async cpImgs() {
    await renderUtil.ensureExists(path.join(this.templatePath, 'public'))
    await renderUtil.ensureExists(path.join(this.templatePath, 'build'))
    await renderUtil.ensureExists(path.join(this.templatePath, 'src'))
    await renderUtil.ensureExists(path.join(this.templatePath, 'src/components'))

    const inputImgPath = path.join(this.repoPath, 'imgs');
    const outputImgPath1 = path.join(this.templatePath, 'public/imgs');
    const outputImgPath2 = path.join(this.templatePath, 'build/imgs');
    const outputImgPath3 = path.join(this.templatePath, 'src/components/imgs');

    await renderUtil.ensureExists(outputImgPath1)
    await renderUtil.ensureExists(outputImgPath2)
    await renderUtil.ensureExists(outputImgPath3)

    if (await renderUtil.exists(inputImgPath)) {
      const files = await fs.readdir(inputImgPath);
      await Promise.all([
        ...files.map(async file => await renderUtil.safeCopyFile(path.join(inputImgPath, file), path.join(outputImgPath1, file))),
        ...files.map(async file => await renderUtil.safeCopyFile(path.join(inputImgPath, file), path.join(outputImgPath2, file))),
        ...files.map(async file => await renderUtil.safeCopyFile(path.join(inputImgPath, file), path.join(outputImgPath3, file)))
      ]);
    }
    return true
  }

  async llmDebugStartServer(err_msg, component_file_path) {
    console.log('******************* llmDebugStartServer *******************');
    const prompt = await this.genStartServerDebugPrompt(err_msg, component_file_path);
    const llmDebugResult = await llmChat.chat({ prompt })
    const dsDebug = llmDebugResult.content;
    const statusCode = llmDebugResult.error_code;
    // console.log(prompt);
    console.log('//////////////////////////////// refined code')
    // console.log(dsDebug)
    // console.log('////////////////////////////////')
    if (dsDebug) {
      const refinedComponentCode = this.postProcessLLMResult(dsDebug);
      console.log(refinedComponentCode);
      console.log('******************* end llmDebugStartServer *******************');
      await fs.writeFile(component_file_path, refinedComponentCode);
      return {
        refinedComponentCode: refinedComponentCode,
        hasLLMErr: false,
      }
    } else {
      return {
        refinedComponentCode: null,
        hasLLMErr: fatalLLMError(statusCode),
      };
    }
  }

  async startServer(component_file_path) {
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

        // const [hasbug, hasFatalLLMErr] = await this.hasBugInStartLog(err_log);
        // if (hasbug) {
        //   console.log('Server start has bug.');
        //   throw new Error('Server start has hidden bug.');
        // }
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
          const debugResult = await this.llmDebugStartServer(err_log, component_file_path);
          if (debugResult.hasLLMErr) {
            throw new Error('Fatal LLMErr detected');
          }

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

async function processBatch(batch, batchIdx, reactAppDir, screenshotDir) {
  for (let j = 0; j < batch.length; j++) {
    await new Promise(resolve => setTimeout(resolve, 1000));
    // const code = batch[j];
    const codeFile = batch[j];
    const compName = path.basename(codeFile).split('.')[0];
    const repoPath = path.dirname(codeFile);
    const repoName = path.basename(repoPath);
    const codeJsonStr = await fs.readFile(codeFile, 'utf8');
    const codeJson = JSON.parse(codeJsonStr);
    
    const renderer = new Renderer(repoPath, `${reactAppDir}/t-${batchIdx}`, 3000 + batchIdx * 100);
    renderer.init();
    console.log('=====================================================================================');
    console.log(' ')
    console.log(`Processing ${j + 1}/${batch.length} code...`);
    console.log(' ')
    console.log('=====================================================================================');

    const componentStyle = codeJson['filtered_css'] || codeJson['raw_css'] || ''
    const componentType = codeJson['file_type'] || 'jsx'
    const componentCode = codeJson['code_with_ori_img'] || codeJson['debug_component'] || codeJson['raw_component'] || null
    if (!componentCode) {
      console.log('No component code found in:', codeFile);
      continue;
    }

    const screenshotPath = path.join(screenshotDir, `${repoName}-_-_-${compName}.png`);
    await renderer.renderCode(componentStyle, componentType, componentCode, screenshotPath)
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