const fs = require('fs');
const path = require('path');

function getSecondLevelFiles(dir, excludeFiles) {
  const fileList = [];
  const firstLevelItems = fs.readdirSync(dir);
  firstLevelItems.forEach(firstLevelItem => {
    const firstLevelPath = path.join(dir, firstLevelItem);
    const stat = fs.statSync(firstLevelPath);

    if (stat.isDirectory()) {
      const secondLevelItems = fs.readdirSync(firstLevelPath);
      secondLevelItems.forEach(secondLevelItem => {
        const secondLevelPath = path.join(firstLevelPath, secondLevelItem);
        const secondLevelStat = fs.statSync(secondLevelPath);
        if (secondLevelStat.isFile() && !excludeFiles.includes(secondLevelItem)) {
          fileList.push(secondLevelPath);
      }
      });
    }
  });

  return fileList;
}


module.exports = {
  getSecondLevelFiles
};