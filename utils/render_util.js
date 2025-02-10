const css = require('css');
const sass = require('sass');
const less = require('less');
const fs = require('fs');
const path = require('path');

class RenderUtil {
  async exists(targetPath) {
    try {
      await fs.promises.access(targetPath);
      return true;
    } catch (error) {
      if (error.code === 'ENOENT') {
        return false;
      } else {
        throw error;
      }
    }
  }
  async ensureExists(filePath) {
    try {
      await fs.promises.access(filePath); 
      console.log(`${filePath} already exists.`);
    } catch (error) {
      if (error.code === 'ENOENT') { 
        const stats = await fs.promises.stat(path.dirname(filePath)); 
        if (stats.isDirectory()) {
          await fs.promises.mkdir(filePath, { recursive: true }); 
          console.log(`Directory ${filePath} created.`);
        } else {
          await fs.promises.writeFile(filePath, ''); 
          console.log(`File ${filePath} created.`);
        }
      } else {
        throw error; 
      }
    }
  }

  async deleteFile(filePath) {
    try {
      await fs.promises.access(filePath); 
      const stats = await fs.promises.stat(filePath); 
      if (stats.isDirectory()) {
        await fs.promises.rm(filePath, { recursive: true, force: true }); 
        console.log(`Directory ${filePath} deleted.`);
      } else {
        await fs.promises.unlink(filePath); 
        console.log(`File ${filePath} deleted.`);
      }
    } catch (error) {
      if (error.code === 'ENOENT') { 
        console.log(`${filePath} does not exist.`);
      } else {
        throw error; 
      }
    }
  }

  extractPackageVersionNumber(versionString) {
    const versionRegex = /(\d+\.\d+\.\d+)/;
    const match = versionString.match(versionRegex);
    const majorVersion = match ? parseInt(match[0].split('.')[0]) : -1;
    const minorVersion = match ? parseInt(match[0].split('.')[1]) : -1;
    const patchVersion = match ? parseInt(match[0].split('.')[2]) : -1;
    return [majorVersion, minorVersion, patchVersion]
  }

  detectStyleLanguage(style) {
    const hasSCSSSyntax = /\$[a-zA-Z0-9\-_]+:|@mixin|@include|&:/g.test(style);

    const hasLESSSyntax = /@[a-zA-Z0-9\-_]+:|\.([a-zA-Z0-9\-_]+\s*\()|& when/g.test(style);

    if (!hasSCSSSyntax && !hasLESSSyntax) {
      return 'CSS';
    } else if (hasSCSSSyntax) {
      return 'SCSS';
    } else if (hasLESSSyntax) {
      return 'LESS';
    } else {
      return null;
    }
  }

  isValidCSS(cssContent) {
    try {
      css.parse(cssContent);
      return true;
    } catch (error) {
      return false;
    }
  }

  isValidSCSS(scssContent) {
    try {
      sass.compileString(scssContent);
      return true;
    } catch (error) {
      return false;
    }
  }

  isValidLESS(lessContent) {
    return new Promise((resolve, reject) => {
      less.parse(lessContent, (error) => {
        if (error) {
          resolve(false);
        } else {
          resolve(true);
        }
      });
    });
  }

  scssToCss(scssString) {
    try {
      // Using the newer API for synchronous rendering
      const result = sass.compileString(scssString, {
        style: 'compressed' // Use 'expanded' for more readable CSS
      });
      return result.css;
    } catch (error) {
      // console.error('Error compiling SCSS:', error);
      return scssString;
    }
  }

  async lessToCss(lessString) {
    try {
      const output = await less.render(lessString, { compress: true });
      return output.css;
    } catch (error) {
      // console.error('Error compiling LESS:', error);
      return lessString;
    }
  }

  async safeCopyFile(src, dest) {
    return new Promise((resolve, reject) => {
      const readStream = fs.createReadStream(src);
      const writeStream = fs.createWriteStream(dest);

      readStream.on('error', reject);
      writeStream.on('error', reject);

      writeStream.on('finish', resolve);

      readStream.pipe(writeStream);

      // Close the write stream when the read stream ends
      readStream.on('end', () => {
        writeStream.end();
      });
    });
  }

  async cpFiles(srcPath, destPath) {
    try {
      // Attempt to access the source path
      await fs.promises.access(srcPath);
    } catch (error) {
      // If an error is thrown, it means the path does not exist or is inaccessible
      console.log('Source path does not exist:', srcPath);
      return;
    }

    try {
      // Check if the destination path exists; create it if it does not
      await fs.promises.access(destPath);
    } catch (error) {
      // If the destination does not exist, create it
      await fs.promises.mkdir(destPath, { recursive: true });
    }

    try {
      const files = await fs.promises.readdir(srcPath);
      const operations = files.map(file => {
        const srcFile = path.join(srcPath, file);
        const destFile = path.join(destPath, file);
        return fs.promises.copyFile(srcFile, destFile)
          .then(() => console.log('File copied:', srcFile, '->', destFile))
          .catch(err => console.error('Error copying file:', err));
      });
      await Promise.all(operations);
    } catch (err) {
      console.error('Error reading directory or copying files:', err);
    }
  }

}
const renderUtil = new RenderUtil();
module.exports = renderUtil;