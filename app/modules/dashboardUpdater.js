const fs = require('fs');
const path = require('path');
const { getAllData, CATEGORY_MAP } = require('./fileManager');

const STATUS_LABELS = {
  'pending': '選考中',
  'accepted': '採用',
  'rejected': '不採用',
  'completed': '完了',
  'in_progress': '進行中'
};

function formatDate(isoString) {
  if (!isoString) return '-';
  return isoString.slice(0, 10);
}

function buildApplicationTable(items) {
  let table = '| No. | 案件名 | 応募日 | ステータス | 結果 |\n';
  table += '|-----|--------|--------|-----------|------|\n';
  if (items.length === 0) {
    table += '| - | まだデータがありません | - | - | - |\n';
  } else {
    items.forEach((item, i) => {
      table += `| ${i + 1} | ${item.title || '-'} | ${formatDate(item.date || item.savedAt)} | ${STATUS_LABELS[item.status] || item.status || '-'} | ${item.result || '-'} |\n`;
    });
  }
  return table;
}

function buildProposalTable(items) {
  let table = '| No. | 対象案件 | 作成日 | テンプレート種別 | 採用結果 |\n';
  table += '|-----|---------|--------|----------------|--------|\n';
  if (items.length === 0) {
    table += '| - | まだデータがありません | - | - | - |\n';
  } else {
    items.forEach((item, i) => {
      table += `| ${i + 1} | ${item.title || '-'} | ${formatDate(item.date || item.savedAt)} | ${item.templateType || '-'} | ${item.result || '-'} |\n`;
    });
  }
  return table;
}

function buildDeliverableTable(items) {
  let table = '| No. | 案件名 | 納品日 | 種別 | 評価 |\n';
  table += '|-----|--------|--------|------|------|\n';
  if (items.length === 0) {
    table += '| - | まだデータがありません | - | - | - |\n';
  } else {
    items.forEach((item, i) => {
      table += `| ${i + 1} | ${item.title || '-'} | ${formatDate(item.date || item.savedAt)} | ${item.type || '-'} | ${item.rating || '-'} |\n`;
    });
  }
  return table;
}

function buildFeedbackTable(items) {
  let table = '| No. | 案件名 | 受領日 | 評価 | 要点 |\n';
  table += '|-----|--------|--------|------|------|\n';
  if (items.length === 0) {
    table += '| - | まだデータがありません | - | - | - |\n';
  } else {
    items.forEach((item, i) => {
      table += `| ${i + 1} | ${item.title || '-'} | ${formatDate(item.date || item.savedAt)} | ${item.rating || '-'} | ${item.summary || '-'} |\n`;
    });
  }
  return table;
}

function buildImprovementTable(items) {
  let table = '| No. | テーマ | 記録日 | カテゴリ | 改善内容 |\n';
  table += '|-----|--------|--------|---------|--------|\n';
  if (items.length === 0) {
    table += '| - | まだデータがありません | - | - | - |\n';
  } else {
    items.forEach((item, i) => {
      table += `| ${i + 1} | ${item.title || '-'} | ${formatDate(item.date || item.savedAt)} | ${item.improvementCategory || '-'} | ${item.summary || '-'} |\n`;
    });
  }
  return table;
}

async function update(basePath) {
  try {
    const allData = await getAllData(basePath);

    const content = `# ダッシュボード - データ蓄積・学習環境

## 応募内容サマリー
${buildApplicationTable(allData.application)}
## 提案文サマリー
${buildProposalTable(allData.proposal)}
## 案件成果物サマリー
${buildDeliverableTable(allData.deliverable)}
## フィードバックサマリー
${buildFeedbackTable(allData.feedback)}
## 学習・改善記録サマリー
${buildImprovementTable(allData.improvement)}
---
*最終更新: ${new Date().toISOString().slice(0, 19).replace('T', ' ')}*
`;

    const dashboardPath = path.join(basePath, 'ダッシュボード.md');
    fs.writeFileSync(dashboardPath, content, 'utf-8');
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

module.exports = { update };
