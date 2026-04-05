const fs = require('fs');
const path = require('path');

const CATEGORY_MAP = {
  'application': '応募内容',
  'proposal': '提案文',
  'deliverable': '案件成果物',
  'feedback': 'フィードバック',
  'improvement': '学習・改善記録'
};

function getCategoryDir(basePath, category) {
  const dirName = CATEGORY_MAP[category];
  if (!dirName) throw new Error(`不明なカテゴリ: ${category}`);
  return path.join(basePath, dirName);
}

function generateFilename(data) {
  const date = new Date().toISOString().slice(0, 10);
  const sanitized = (data.title || 'untitled').replace(/[\\/:*?"<>|]/g, '_').slice(0, 50);
  const timestamp = Date.now();
  return `${date}_${sanitized}_${timestamp}.json`;
}

async function saveData(basePath, category, data) {
  try {
    const dir = getCategoryDir(basePath, category);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    const filename = generateFilename(data);
    const filePath = path.join(dir, filename);

    const record = {
      ...data,
      savedAt: new Date().toISOString(),
      category: category
    };

    fs.writeFileSync(filePath, JSON.stringify(record, null, 2), 'utf-8');
    return { success: true, filename, path: filePath };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

async function loadData(basePath, category) {
  try {
    const dir = getCategoryDir(basePath, category);
    if (!fs.existsSync(dir)) return { success: true, data: [] };

    const files = fs.readdirSync(dir).filter(f => f.endsWith('.json'));
    const data = files.map(filename => {
      const content = fs.readFileSync(path.join(dir, filename), 'utf-8');
      return { filename, ...JSON.parse(content) };
    });

    data.sort((a, b) => new Date(b.savedAt) - new Date(a.savedAt));
    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message, data: [] };
  }
}

async function getAllData(basePath) {
  const result = {};
  for (const category of Object.keys(CATEGORY_MAP)) {
    const loaded = await loadData(basePath, category);
    result[category] = loaded.data || [];
  }
  return result;
}

async function deleteData(basePath, category, filename) {
  try {
    const dir = getCategoryDir(basePath, category);
    const filePath = path.join(dir, filename);

    if (!filePath.startsWith(dir)) {
      return { success: false, error: '不正なファイルパス' };
    }

    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
      return { success: true };
    }
    return { success: false, error: 'ファイルが見つかりません' };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

async function updateData(basePath, category, filename, newData) {
  try {
    const dir = getCategoryDir(basePath, category);
    const filePath = path.join(dir, filename);

    if (!filePath.startsWith(dir)) {
      return { success: false, error: '不正なファイルパス' };
    }

    if (!fs.existsSync(filePath)) {
      return { success: false, error: 'ファイルが見つかりません' };
    }

    const existing = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    const updated = { ...existing, ...newData, updatedAt: new Date().toISOString() };
    fs.writeFileSync(filePath, JSON.stringify(updated, null, 2), 'utf-8');
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

module.exports = { saveData, loadData, getAllData, deleteData, updateData, CATEGORY_MAP };
