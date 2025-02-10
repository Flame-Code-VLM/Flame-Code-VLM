const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const nodeVersion = process.versions.node;
const reactProjectDir = path.resolve(__dirname);

function getCompatibleVersion(package) {
  const { name: packageName, version: packageVersion } = package;
  console.log(`Checking compatibility for ${packageName}...`);
  try {
    if (packageVersion) {
      return `${packageName}@${packageVersion}`;
    } else {
      const metadata = JSON.parse(execSync(`npm view ${packageName} --json`).toString());

      const engines = metadata.engines?.node || '';
      if (checkCompatibility(engines, nodeVersion)) {
        console.log(`Is compatible ${packageName}`);
        return `${packageName}@latest`;
      } else {
        console.log(`Is not compatible ${packageName}`);
        const compatibleVersion = findCompatibleVersion(packageName, metadata.versions, nodeVersion);
        if (compatibleVersion) {
          return `${packageName}@${compatibleVersion}`;
        } else {
          console.warn(`No compatible version found for ${packageName} with Node.js ${nodeVersion}`);
          return null;
        }
      }
    }
  } catch (error) {
    console.error(`Failed to check compatibility for ${packageName}:`, error.message);
    return null;
  }
}

function checkCompatibility(engines, nodeVersion) {
  if (!engines) return true; 
  const range = engines.replace(/[^\d.<>=|]/g, ''); 
  return satisfiesVersion(nodeVersion, range);
}

function satisfiesVersion(version, range) {
  const semver = require('semver');
  return semver.satisfies(version, range);
}

function findCompatibleVersion(packageName, versions, nodeVersion) {
  const semver = require('semver');
  for (const version of versions.reverse()) {
    const metadata = JSON.parse(execSync(`npm view ${packageName}@${version} --json`).toString());
    const engines = metadata.engines?.node || '';
    if (checkCompatibility(engines, nodeVersion)) {
      return version;
    }
  }
  return null;
}

function installPackages(packages, targetDir) {
  const packagesToInstall = packages
    .map(package => getCompatibleVersion(package))
    .filter(Boolean);

  if (packagesToInstall.length > 0) {
    try {
      console.log(`Installing packages: ${packagesToInstall.join(', ')}...`);
      if (!fs.existsSync(targetDir)) {
        console.error(`Error: Target directory ${targetDir} does not exist.`);
        return;
      }
      execSync(`npm install ${packagesToInstall.join(' ')} --legacy-peer-deps --no-package-lock --maxsockets=200`, { stdio: 'inherit', cwd: targetDir });
      console.log('Installation completed successfully.');
    } catch (error) {
      console.error('Installation failed:', error.message);
    }
  } else {
    console.warn('No compatible packages to install.');
  }
}

const filePath = path.join(__dirname, "dependencies.json");
try {
  const fileContent = fs.readFileSync(filePath, "utf-8");
  const packages = JSON.parse(fileContent);
  console.log("packages:", packages);
  installPackages(packages, reactProjectDir);
} catch (err) {
  console.error("error reading file:", err);
}
