const fs = require('fs');
const path = require('path');
const imageSize = require('image-size');
const sharp = require('sharp');


function getBuildDirectory(basePath) {
  const packageJsonPath = path.join(basePath, 'package.json');
  try {
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
    if (!packageJson.buildPath) {
      // check if default build directory exists
      const testDefault1 = path.join(basePath, 'build');
      if (fs.existsSync(testDefault1)) {
        return 'build';
      }
      const testDefault2 = path.join(basePath, 'dist');
      if (fs.existsSync(testDefault2)) {
        return 'dist';
      }
      const testDefault3 = path.join(basePath, 'public');
      if (fs.existsSync(testDefault3)) {
        return 'public';
      }
      const testDefault4 = path.join(basePath, 'out');
      if (fs.existsSync(testDefault4)) {
        return 'out';
      }
      return 'build'; // default to build
    }
    return packageJson.buildPath
  } catch (error) {
    console.error('Error reading package.json:', error);
    return 'build';
  }
}

function extractImagePathsInCSS(code) {
  const urlRegex = /url\(['"]?(.+?\.(jpg|jpeg|png|gif|svg))['"]?\)/gi;
  const urls = new Set(); // Use a set to avoid duplicates
  let match;

  while ((match = urlRegex.exec(code)) !== null) {
    urls.add(match[1]);
  }

  return Array.from(urls);
}

function extractImagePathsInJs(code) {
  const importRegex = /import .* from ['"](.+?\.(jpg|jpeg|png|gif|svg))['"]/g;
  const srcRegex = /src=['"](.+?\.(jpg|jpeg|png|gif|svg))['"]/g;
  const paths = new Set(); // Use a set to avoid duplicates
  let match;

  // Extract from imports
  while ((match = importRegex.exec(code)) !== null) {
    paths.add({ path: match[1], type: 'import' });
  }
  // Extract from JSX
  while ((match = srcRegex.exec(code)) !== null) {
    paths.add({ path: match[1], type: 'src' });
  }

  return Array.from(paths);
}

async function createPlaceholder(imagePath, dimensions) {
  // check if the directory exists
  const dir = path.dirname(imagePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  const { width, height } = dimensions;
  await sharp({
    create: {
      width,
      height,
      channels: 3,
      background: { r: 255, g: 255, b: 255 }
    }
  })
    .png()
    .toFile(imagePath);
}

async function processImagesInCSS(projectPath, cssContent, placeholderDir) {
  const buildDirectory = getBuildDirectory(projectPath);
  const imageUrls = extractImagePathsInCSS(cssContent);

  let cssContentWithPlaceholders = cssContent;
  let cssContentWithRealImgs = cssContent;
  for (const imageUrl of imageUrls) {
    const fullPath = path.join(projectPath, buildDirectory, imageUrl);
    if (fs.existsSync(fullPath)) {
      const dimensions = imageSize(fullPath);
      // console.log(`Image: ${imageUrl}, Width: ${dimensions.width}, Height: ${dimensions.height}`);

      // Create placeholder image
      const oriImageName = path.basename(imageUrl);
      const placeholderFileName = `placeholder_${oriImageName}`;
      const placeholderPath = path.join(placeholderDir, placeholderFileName);
      createPlaceholder(placeholderPath, dimensions).then(() => {
        // save the ori images to the placeholder path as well
        const oriImagePath = path.join(placeholderDir, oriImageName);
        // console.log(`Copying css image: ${fullPath} to ${oriImagePath}`);
        fs.copyFileSync(fullPath, oriImagePath);

        // Replace original URL with placeholder in the CSS content
        cssContentWithPlaceholders = cssContent.replaceAll(imageUrl, `/imgs/${placeholderFileName}`);
        cssContentWithRealImgs = cssContent.replaceAll(imageUrl, `/imgs/${oriImageName}`);
      }).catch((error) => {
        console.error(error);
      })
    } else {
      console.log(`Image not found: ${fullPath}`);
    }
  }
  return {
    cssContentWithPlaceholders,
    cssContentWithRealImgs
  };
}

async function processImagesInJs(projectPath, code, codePath, placeholderDir) {
  console.log('======================= processImagesInJs ========================');
  console.log(`Project path: ${projectPath}, Code path: ${codePath}, Placeholder dir: ${placeholderDir}`);
  let codeWithPlaceholders = code;
  let codeWithRealImgs = code;
  try {

    const buildDirectory = getBuildDirectory(projectPath);
    const imagePaths = extractImagePathsInJs(code);
    const codeDirectory = path.dirname(codePath);


    // Create an array to hold all promises
    const promises = [];

    for (const { path: imagePath, type } of imagePaths) {
      console.log('------------------------------------------------------')
      console.log(`Processing image: ${imagePath}, ${type}`);
      console.log(`Code directory: ${codeDirectory}, code path: ${codePath}, Project path: ${projectPath}, Build directory: ${buildDirectory}`);
      const fullPath = type === 'import' ? path.join(codeDirectory, imagePath) : path.join(projectPath, buildDirectory, imagePath);

      if (fs.existsSync(fullPath)) {
        const dimensions = imageSize(fullPath);

        // Create placeholder image
        const oriImageName = path.basename(imagePath);
        const placeholderName = `placeholder_${oriImageName}`;
        const placeholderPath = path.join(placeholderDir, placeholderName);

        // Add the promise to the promises array
        const promise = createPlaceholder(placeholderPath, dimensions).then(() => {
          // save the ori images to the placeholder path as well
          const oriImagePath = path.join(placeholderDir, oriImageName);
          console.log(`Copying js image: ${fullPath} to ${oriImagePath}`);
          fs.copyFileSync(fullPath, oriImagePath);

          // Replace original path with placeholder in the code
          codeWithPlaceholders = type === 'import' ? codeWithPlaceholders.replaceAll(imagePath, `./imgs/${placeholderName}`) : codeWithPlaceholders.replaceAll(imagePath, `/imgs/${placeholderName}`);
          codeWithRealImgs = type === 'import' ? codeWithRealImgs.replaceAll(imagePath, `./imgs/${oriImageName}`) : codeWithRealImgs.replaceAll(imagePath, `/imgs/${oriImageName}`);
        }).catch((error) => {
          console.error(error);
        });

        promises.push(promise);
      } else {
        console.log(`Image not found: ${fullPath}`);
      }
    }

    // Wait for all promises to resolve
    await Promise.all(promises);
  } catch (e) {
    console.log('*************** Error ***************');
    console.error(e);
    console.log(`Project path: ${projectPath}, Code path: ${codePath}, Placeholder dir: ${placeholderDir}`)
    console.log('*************** end Error ***************');

  }

  return {
    codeWithPlaceholders,
    codeWithRealImgs
  };
}

// Function to recursively walk through directory
function walkDir(dir, callback) {
  fs.readdirSync(dir).forEach(f => {
    let dirPath = path.join(dir, f);
    let isDirectory = fs.statSync(dirPath).isDirectory();
    isDirectory ? walkDir(dirPath, callback) : callback(path.join(dir, f));
  });
}


function main() {
  const args = process.argv.slice(2);

  projectPath = process.cwd();
  console.log('Current working directory: ', projectPath);
  const repoPath = args[0] || 'data/original_repo';
  const componentPath = args[1] || 'data/original_repo_components';

  // Walk through the component directory
  walkDir(componentPath, async function (filePath) {
    // console.log('component path: ', componentPath)
    if (filePath.endsWith('.json') && path.basename(filePath) !== 'package.json' && path.basename(filePath) !== 'pkg_candidate.json' && path.basename(filePath) !== 'statistic.json') {
      console.log('--------------------------------------')
      const fileParentDirPath = path.dirname(filePath);
      const parentFolder = path.basename(fileParentDirPath);

      let content = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      let fileType = content['file_type'];
      let componentCode = content['debug_component'] || content['raw_component'];
      let componentStyle = content['debug_style'] || content['raw_style'];
      let fileName = path.basename(filePath).replace('_bundled.json', `.${fileType}`);

      // Walk through the raw project folder
      let rawProjectFolder = path.join(repoPath, parentFolder);
      let componentRawPath = null;
      console.log(`Parent folder: ${parentFolder}, File: ${path.basename(filePath)}, raw file: ${fileName}, rawProjectFolder: ${rawProjectFolder}`);
      walkDir(rawProjectFolder, function (rawFilePath) {
        if (path.basename(rawFilePath) === fileName) {
          componentRawPath = rawFilePath;
        }
      });

      // create placeholder folder under parentFolder
      let placeholderDir = path.join(fileParentDirPath, 'imgs');
      if (!fs.existsSync(placeholderDir)) {
        fs.mkdirSync(placeholderDir);
      }

      // Process images in the component code
      const {
        cssContentWithPlaceholders,
        cssContentWithRealImgs
      } = await processImagesInCSS(rawProjectFolder, componentStyle, placeholderDir);
      content['style_with_placeholder_img'] = cssContentWithPlaceholders;
      content['style_with_ori_img'] = cssContentWithRealImgs;

      const {
        codeWithPlaceholders,
        codeWithRealImgs
      } = await processImagesInJs(rawProjectFolder, componentCode, componentRawPath, placeholderDir);
      content['code_with_placeholder_img'] = codeWithPlaceholders;
      content['code_with_ori_img'] = codeWithRealImgs;

      // save the new code
      fs.writeFileSync(filePath, JSON.stringify(content, null, 2));
    }
  });
}

main();