// ページ切り替え
const navItems = document.querySelectorAll('.nav-item');
const pages = document.querySelectorAll('.page');

navItems.forEach(item => {
  item.addEventListener('click', () => {
    const pageName = item.dataset.page;

    navItems.forEach(n => n.classList.remove('active'));
    item.classList.add('active');

    pages.forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${pageName}`).classList.add('active');

    if (pageName === 'dashboard') {
      loadDashboard();
    } else if (pageName === 'record') {
      loadRecordList();
    } else if (pageName === 'settings') {
      loadSettingsPage();
    } else {
      loadList(pageName);
    }
  });
});

// 通知表示
function showNotification(message, isError = false) {
  const el = document.getElementById('notification');
  el.textContent = message;
  el.className = 'notification show' + (isError ? ' error' : '');
  setTimeout(() => { el.className = 'notification'; }, 3000);
}

// === モーダル ===
const modalOverlay = document.getElementById('modal-overlay');
const modalTitle = document.getElementById('modal-title');
const modalBody = document.getElementById('modal-body');
const modalFooter = document.getElementById('modal-footer');

document.getElementById('modal-close').addEventListener('click', closeModal);
modalOverlay.addEventListener('click', (e) => {
  if (e.target === modalOverlay) closeModal();
});

function closeModal() {
  modalOverlay.classList.remove('show');
}

const STATUS_LABELS = { pending: '選考中', accepted: '採用', rejected: '不採用', completed: '完了', in_progress: '進行中' };

// 詳細モーダルを表示（閲覧モード）
function showDetailModal(item, category, onUpdate) {
  modalTitle.textContent = item.title || '無題';

  let fields = '';

  if (category === 'application') {
    fields += modalField('日付', formatDate(item.date || item.savedAt));
    fields += modalField('ステータス', STATUS_LABELS[item.status] || item.status || '-');
    if (item.url) fields += modalField('URL', `<a href="#">${escapeHtml(item.url)}</a>`);
    if (item.type) fields += modalField('種別', item.type);
    if (item.result) fields += modalField('メモ', item.result);
  } else if (category === 'proposal') {
    fields += modalField('日付', formatDate(item.date || item.savedAt));
    if (item.templateType) fields += modalField('テンプレート種別', item.templateType);
    if (item.body) fields += modalField('提案文', item.body);
  } else if (category === 'deliverable') {
    fields += modalField('日付', formatDate(item.date || item.savedAt));
    if (item.type) fields += modalField('種別', item.type);
    if (item.body) fields += modalField('成果物', item.body);
    if (item.rating) fields += modalField('評価', item.rating);
  } else if (category === 'feedback') {
    fields += modalField('日付', formatDate(item.date || item.savedAt));
    if (item.rating) fields += modalField('評価', item.rating);
    if (item.body) fields += modalField('フィードバック内容', item.body);
    if (item.summary) fields += modalField('要点', item.summary);
  } else if (category === 'improvement') {
    fields += modalField('日付', formatDate(item.date || item.savedAt));
    if (item.improvementCategory) fields += modalField('カテゴリ', item.improvementCategory);
    if (item.body) fields += modalField('詳細内容', item.body);
    if (item.summary) fields += modalField('まとめ', item.summary);
  }

  fields += modalField('保存日時', item.savedAt || '-');
  if (item.updatedAt) fields += modalField('更新日時', item.updatedAt);

  modalBody.innerHTML = fields;
  modalFooter.innerHTML = `
    <button class="btn-edit" id="modal-btn-edit">編集</button>
    <button class="btn-delete" id="modal-btn-delete">削除</button>
  `;

  document.getElementById('modal-btn-edit').addEventListener('click', () => {
    showEditModal(item, category, onUpdate);
  });

  document.getElementById('modal-btn-delete').addEventListener('click', async () => {
    if (!confirm('本当に削除しますか？')) return;
    const res = await window.api.deleteData(category, item.filename);
    if (res.success) {
      showNotification('削除しました');
      closeModal();
      if (onUpdate) onUpdate();
    } else {
      showNotification('削除に失敗しました', true);
    }
  });

  modalOverlay.classList.add('show');
}

function modalField(label, value) {
  return `<div class="modal-field">
    <div class="modal-field-label">${escapeHtml(label)}</div>
    <div class="modal-field-value">${value && value.startsWith('<') ? value : escapeHtml(value || '-')}</div>
  </div>`;
}

// 編集モーダルを表示
function showEditModal(item, category, onUpdate) {
  modalTitle.textContent = '編集: ' + (item.title || '無題');

  let fields = '';

  if (category === 'application') {
    fields += editField('title', '案件名', 'text', item.title);
    fields += editField('date', '日付', 'date', item.date || '');
    fields += editSelect('status', 'ステータス', [
      ['pending', '選考中'], ['accepted', '採用'], ['rejected', '不採用'],
      ['completed', '完了'], ['in_progress', '進行中']
    ], item.status);
    fields += editField('url', 'URL', 'url', item.url || '');
    fields += editField('type', '種別', 'text', item.type || '');
    fields += editTextarea('result', 'メモ', item.result || '', 3);
  } else if (category === 'proposal') {
    fields += editField('title', '対象案件名', 'text', item.title);
    fields += editField('date', '日付', 'date', item.date || '');
    fields += editField('templateType', 'テンプレート種別', 'text', item.templateType || '');
    fields += editTextarea('body', '提案文', item.body || '', 8);
  } else if (category === 'deliverable') {
    fields += editField('title', '案件名', 'text', item.title);
    fields += editField('date', '日付', 'date', item.date || '');
    fields += editField('type', '種別', 'text', item.type || '');
    fields += editTextarea('body', '成果物', item.body || '', 8);
    fields += editField('rating', '評価', 'text', item.rating || '');
  } else if (category === 'feedback') {
    fields += editField('title', '案件名', 'text', item.title);
    fields += editField('date', '日付', 'date', item.date || '');
    fields += editSelect('rating', '評価', [
      ['', '未選択'], ['★★★★★', '★★★★★'], ['★★★★', '★★★★'],
      ['★★★', '★★★'], ['★★', '★★'], ['★', '★']
    ], item.rating || '');
    fields += editTextarea('body', 'フィードバック内容', item.body || '', 5);
    fields += editTextarea('summary', '要点', item.summary || '', 3);
  } else if (category === 'improvement') {
    fields += editField('title', 'テーマ', 'text', item.title);
    fields += editField('date', '日付', 'date', item.date || '');
    fields += editSelect('improvementCategory', 'カテゴリ', [
      ['提案文改善', '提案文改善'], ['ライティング技術', 'ライティング技術'],
      ['クライアント対応', 'クライアント対応'], ['効率化', '効率化'], ['その他', 'その他']
    ], item.improvementCategory || '');
    fields += editTextarea('body', '詳細内容', item.body || '', 6);
    fields += editTextarea('summary', 'まとめ', item.summary || '', 3);
  }

  modalBody.innerHTML = `<form id="modal-edit-form">${fields}</form>`;
  modalFooter.innerHTML = `
    <button class="btn-save" id="modal-btn-save">保存</button>
    <button class="btn-cancel" id="modal-btn-cancel">キャンセル</button>
  `;

  document.getElementById('modal-btn-save').addEventListener('click', async () => {
    const form = document.getElementById('modal-edit-form');
    const inputs = form.querySelectorAll('input, select, textarea');
    const newData = {};
    inputs.forEach(el => { newData[el.name] = el.value; });

    const res = await window.api.updateData(category, item.filename, newData);
    if (res.success) {
      showNotification('更新しました');
      closeModal();
      if (onUpdate) onUpdate();
    } else {
      showNotification('更新に失敗しました: ' + res.error, true);
    }
  });

  document.getElementById('modal-btn-cancel').addEventListener('click', () => {
    showDetailModal(item, category, onUpdate);
  });
}

function editField(name, label, type, value) {
  return `<div class="modal-edit-group">
    <label>${escapeHtml(label)}</label>
    <input type="${type}" name="${name}" value="${escapeHtml(value || '')}">
  </div>`;
}

function editSelect(name, label, options, selected) {
  const opts = options.map(([val, text]) =>
    `<option value="${escapeHtml(val)}" ${val === selected ? 'selected' : ''}>${escapeHtml(text)}</option>`
  ).join('');
  return `<div class="modal-edit-group">
    <label>${escapeHtml(label)}</label>
    <select name="${name}">${opts}</select>
  </div>`;
}

function editTextarea(name, label, value, rows) {
  return `<div class="modal-edit-group">
    <label>${escapeHtml(label)}</label>
    <textarea name="${name}" rows="${rows}">${escapeHtml(value || '')}</textarea>
  </div>`;
}

// === URL自動取得 ===
const btnFetch = document.getElementById('btn-fetch-title');
const urlInput = document.getElementById('record-url');
const titleInput = document.getElementById('record-title');
const fetchStatus = document.getElementById('fetch-status');

btnFetch.addEventListener('click', async () => {
  const url = urlInput.value.trim();
  if (!url) {
    fetchStatus.textContent = 'URLを入力してください';
    fetchStatus.className = 'fetch-status error';
    return;
  }

  btnFetch.disabled = true;
  fetchStatus.textContent = '取得中...';
  fetchStatus.className = 'fetch-status loading';

  const result = await window.api.fetchTitleFromUrl(url);
  btnFetch.disabled = false;

  if (result.success) {
    titleInput.value = result.title;
    fetchStatus.textContent = '案件名を取得しました';
    fetchStatus.className = 'fetch-status success';
  } else {
    fetchStatus.textContent = result.error;
    fetchStatus.className = 'fetch-status error';
  }
});

urlInput.addEventListener('paste', () => {
  setTimeout(async () => {
    const url = urlInput.value.trim();
    if (url && url.startsWith('http')) {
      btnFetch.click();
    }
  }, 100);
});

// === 案件記録フォーム送信 ===
const formRecord = document.getElementById('form-record');
formRecord.addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData(formRecord);
  const data = {};
  formData.forEach((value, key) => { data[key] = value; });

  const saves = [];

  saves.push(window.api.saveData('application', {
    title: data.title, url: data.url, date: data.date,
    status: data.status, type: data.type, result: data.memo
  }));

  if (data.proposalBody && data.proposalBody.trim()) {
    saves.push(window.api.saveData('proposal', {
      title: data.title, date: data.date, templateType: data.type, body: data.proposalBody
    }));
  }

  if (data.deliverableBody && data.deliverableBody.trim()) {
    saves.push(window.api.saveData('deliverable', {
      title: data.title, date: data.date, type: data.type, body: data.deliverableBody, rating: data.rating
    }));
  }

  if ((data.feedbackBody && data.feedbackBody.trim()) || (data.rating && data.rating.trim())) {
    saves.push(window.api.saveData('feedback', {
      title: data.title, date: data.date, rating: data.rating, body: data.feedbackBody, summary: data.memo
    }));
  }

  const results = await Promise.all(saves);
  if (results.every(r => r.success)) {
    showNotification('保存しました');
    formRecord.reset();
    document.querySelectorAll('#form-record input[type="date"]').forEach(input => {
      input.value = new Date().toISOString().slice(0, 10);
    });
    fetchStatus.textContent = '';
    loadRecordList();
  } else {
    showNotification('一部の保存に失敗しました', true);
  }
});

// === 案件記録一覧（クリックで詳細モーダル） ===
async function loadRecordList() {
  const container = document.getElementById('list-record');

  const [appResult, propResult, delResult, fbResult] = await Promise.all([
    window.api.loadData('application'),
    window.api.loadData('proposal'),
    window.api.loadData('deliverable'),
    window.api.loadData('feedback')
  ]);

  const apps = appResult.data || [];
  const proposals = propResult.data || [];
  const deliverables = delResult.data || [];
  const feedbacks = fbResult.data || [];

  if (apps.length === 0) {
    container.innerHTML = '<p style="color:#888; padding:10px;">まだデータがありません</p>';
    return;
  }

  let html = '';
  apps.forEach((app, i) => {
    const proposal = proposals.find(p => p.title === app.title);
    const deliverable = deliverables.find(d => d.title === app.title);
    const feedback = feedbacks.find(f => f.title === app.title);

    html += `
      <div class="data-card" style="flex-direction:column;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; width:100%;">
          <div class="data-card-info">
            <div class="data-card-title clickable" data-index="${i}">${escapeHtml(app.title || '無題')}</div>
            <div class="data-card-meta">
              ${formatDate(app.date || app.savedAt)}
              | ${STATUS_LABELS[app.status] || app.status || '-'}
              ${app.type ? ' | ' + escapeHtml(app.type) : ''}
              ${feedback && feedback.rating ? ' | ' + escapeHtml(feedback.rating) : ''}
            </div>
          </div>
          <button class="btn-delete" data-category="application" data-filename="${escapeHtml(app.filename)}">削除</button>
        </div>
        ${proposal ? `
          <div style="margin-top:10px; padding-top:10px; border-top:1px solid #eee; width:100%;">
            <div style="font-size:12px; color:#3498db; font-weight:bold; margin-bottom:4px;">提案文</div>
            <div class="data-card-body">${escapeHtml(proposal.body)}</div>
          </div>
        ` : ''}
        ${deliverable ? `
          <div style="margin-top:10px; padding-top:10px; border-top:1px solid #eee; width:100%;">
            <div style="font-size:12px; color:#27ae60; font-weight:bold; margin-bottom:4px;">成果物</div>
            <div class="data-card-body">${escapeHtml(deliverable.body)}</div>
          </div>
        ` : ''}
        ${feedback && feedback.body ? `
          <div style="margin-top:10px; padding-top:10px; border-top:1px solid #eee; width:100%;">
            <div style="font-size:12px; color:#e67e22; font-weight:bold; margin-bottom:4px;">フィードバック</div>
            <div class="data-card-body">${escapeHtml(feedback.body)}</div>
          </div>
        ` : ''}
      </div>
    `;
  });

  container.innerHTML = html;

  // タイトルクリックで詳細モーダル
  container.querySelectorAll('.data-card-title.clickable').forEach(el => {
    el.addEventListener('click', () => {
      const idx = parseInt(el.dataset.index);
      const app = apps[idx];
      showDetailModal(app, 'application', loadRecordList);
    });
  });

  // 削除ボタン
  container.querySelectorAll('.btn-delete').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm('本当に削除しますか？')) return;
      const res = await window.api.deleteData(btn.dataset.category, btn.dataset.filename);
      if (res.success) {
        showNotification('削除しました');
        loadRecordList();
      } else {
        showNotification('削除に失敗しました', true);
      }
    });
  });
}

// === 学習・改善記録フォーム ===
const formImprovement = document.getElementById('form-improvement');
formImprovement.addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData(formImprovement);
  const data = {};
  formData.forEach((value, key) => { data[key] = value; });

  const result = await window.api.saveData('improvement', data);
  if (result.success) {
    showNotification('保存しました');
    formImprovement.reset();
    document.querySelectorAll('#form-improvement input[type="date"]').forEach(input => {
      input.value = new Date().toISOString().slice(0, 10);
    });
    loadList('improvement');
  } else {
    showNotification('保存に失敗しました: ' + result.error, true);
  }
});

// === 学習・改善記録一覧（クリックで詳細モーダル） ===
async function loadList(category) {
  const container = document.getElementById(`list-${category}`);
  if (!container) return;

  const result = await window.api.loadData(category);
  const items = result.data || [];

  if (items.length === 0) {
    container.innerHTML = '<p style="color:#888; padding:10px;">まだデータがありません</p>';
    return;
  }

  container.innerHTML = '<h2>保存済みデータ</h2>' + items.map((item, i) => `
    <div class="data-card">
      <div class="data-card-info">
        <div class="data-card-title clickable" data-category="${category}" data-index="${i}">${escapeHtml(item.title || '無題')}</div>
        <div class="data-card-meta">${formatDate(item.date || item.savedAt)}${item.improvementCategory ? ' | ' + escapeHtml(item.improvementCategory) : ''}</div>
        ${item.body ? `<div class="data-card-body">${escapeHtml(item.body)}</div>` : ''}
        ${item.summary ? `<div class="data-card-meta" style="margin-top:4px;">まとめ: ${escapeHtml(item.summary)}</div>` : ''}
      </div>
      <button class="btn-delete" data-category="${category}" data-filename="${escapeHtml(item.filename)}">削除</button>
    </div>
  `).join('');

  // タイトルクリックで詳細モーダル
  container.querySelectorAll('.data-card-title.clickable').forEach(el => {
    el.addEventListener('click', () => {
      const idx = parseInt(el.dataset.index);
      showDetailModal(items[idx], el.dataset.category, () => loadList(category));
    });
  });

  container.querySelectorAll('.btn-delete').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm('本当に削除しますか？')) return;
      const res = await window.api.deleteData(btn.dataset.category, btn.dataset.filename);
      if (res.success) {
        showNotification('削除しました');
        loadList(btn.dataset.category);
      } else {
        showNotification('削除に失敗しました', true);
      }
    });
  });
}

// === ダッシュボード（クリックで詳細モーダル） ===
let dashboardAllData = {};

async function loadDashboard() {
  const grid = document.getElementById('dashboard-grid');
  dashboardAllData = await window.api.getDashboard();

  const categoryLabels = {
    application: '応募内容',
    proposal: '提案文',
    deliverable: '案件成果物',
    feedback: 'フィードバック',
    improvement: '学習・改善記録'
  };

  let html = '';
  for (const [category, label] of Object.entries(categoryLabels)) {
    const items = dashboardAllData[category] || [];
    const recent = items.slice(0, 3);

    html += `
      <div class="dashboard-card">
        <h3>${label}</h3>
        <div class="count">${items.length}</div>
        <div class="label">件のデータ</div>
        ${recent.length > 0 ? '<div style="margin-top:12px">' + recent.map((item, i) => `
          <div class="recent-item clickable" data-category="${category}" data-index="${i}">${escapeHtml(item.title || '無題')} - ${formatDate(item.savedAt)}</div>
        `).join('') + '</div>' : '<div class="recent-item" style="color:#aaa">データなし</div>'}
      </div>
    `;
  }

  grid.innerHTML = html;

  // ダッシュボードのアイテムクリックで詳細モーダル
  grid.querySelectorAll('.recent-item.clickable').forEach(el => {
    el.addEventListener('click', () => {
      const cat = el.dataset.category;
      const idx = parseInt(el.dataset.index);
      const item = dashboardAllData[cat][idx];
      showDetailModal(item, cat, loadDashboard);
    });
  });
}

// === ユーティリティ ===
function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  return dateStr.slice(0, 10);
}

// 初期表示：日付フィールドに今日の日付をセット
document.querySelectorAll('input[type="date"]').forEach(input => {
  input.value = new Date().toISOString().slice(0, 10);
});

// === 設定画面 ===
const loginStatusEl = document.getElementById('login-status');

async function loadSettingsPage() {
  updateLoginStatus();
}

async function updateLoginStatus() {
  const status = await window.api.cwLoginStatus();
  if (status.loggedIn) {
    loginStatusEl.textContent = 'ログイン済み';
    loginStatusEl.className = 'login-status logged-in';
  } else {
    loginStatusEl.textContent = '未ログイン';
    loginStatusEl.className = 'login-status logged-out';
  }
}

document.getElementById('btn-cw-login').addEventListener('click', async () => {
  const btn = document.getElementById('btn-cw-login');
  btn.disabled = true;
  btn.textContent = 'ログイン画面を開いています...';

  const result = await window.api.cwLogin();
  btn.disabled = false;
  btn.textContent = 'CrowdWorksにログイン';

  if (result.success) {
    showNotification('CrowdWorksにログインしました');
  } else {
    showNotification(result.error, true);
  }
  updateLoginStatus();
});

// 初回ダッシュボード読み込み
loadDashboard();
