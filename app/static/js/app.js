document.addEventListener('DOMContentLoaded', () => {
  // 狀態管理
  const state = {
    user: null,
    credential: null,
    selectedDate: null,      // { dateStr: "09/06", dayNum: "06" }
    selectedSlots: [],       // ["17:00", "18:00"]
    tasks: []
  };

  // DOM 元素快取
  const authModal = document.getElementById('auth-modal');
  const credModal = document.getElementById('cred-modal');
  const dryRunModal = document.getElementById('dry-run-modal');
  
  const userProfileBtn = document.getElementById('user-profile-btn');
  const credStatusBadge = document.getElementById('cred-status-badge');
  const dateGrid = document.getElementById('date-grid');
  const slotGrid = document.getElementById('slot-grid');
  const taskList = document.getElementById('task-list');
  const submitTaskBtn = document.getElementById('submit-task-btn');
  
  // 摺疊面板切換
  const accordionHeader = document.getElementById('accordion-header');
  const accordionBody = document.getElementById('accordion-body');
  accordionHeader.addEventListener('click', () => {
    accordionBody.classList.toggle('open');
  });

  // 1. 初始化日曆 Chips (未來 7 天)
  function renderDateChips() {
    dateGrid.innerHTML = '';
    const now = new Date();
    const daysOfWeek = ['日', '一', '二', '三', '四', '五', '六'];

    for (let i = 1; i <= 7; i++) {
      const d = new Date();
      d.setDate(now.getDate() + i);
      
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      const dateStr = `${mm}/${dd}`;
      const dayNum = dd;
      const dayName = `週${daysOfWeek[d.getDay()]}`;

      const chip = document.createElement('div');
      chip.className = `date-chip ${i === 4 ? 'active' : ''}`; // 預設選中 5 天後
      chip.innerHTML = `
        <div class="date-day">${dayName}</div>
        <div class="date-num">${dd}</div>
        <div class="date-open">${i === 4 ? '🔥 推薦目標' : (i <= 4 ? '可預約' : '即將開放')}</div>
      `;

      chip.addEventListener('click', () => {
        document.querySelectorAll('.date-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        state.selectedDate = { dateStr, dayNum };
      });

      dateGrid.appendChild(chip);
      if (i === 4) {
        state.selectedDate = { dateStr, dayNum };
      }
    }
  }

  // 2. 時段按鈕點擊 (支援 1st / 2nd 志願序選擇)
  const slotButtons = document.querySelectorAll('.slot-btn');
  slotButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const slotTime = btn.dataset.time;
      const index = state.selectedSlots.indexOf(slotTime);

      if (index > -1) {
        // 取消選取
        state.selectedSlots.splice(index, 1);
      } else {
        // 最多選取 2 個時段
        if (state.selectedSlots.length >= 2) {
          state.selectedSlots.shift(); // 移除第一個，推入新的
        }
        state.selectedSlots.push(slotTime);
      }

      updateSlotUI();
    });
  });

  function updateSlotUI() {
    slotButtons.forEach(btn => {
      const time = btn.dataset.time;
      btn.classList.remove('selected-1', 'selected-2');
      const oldTag = btn.querySelector('.slot-rank-tag');
      if (oldTag) oldTag.remove();

      const rankIndex = state.selectedSlots.indexOf(time);
      if (rankIndex === 0) {
        btn.classList.add('selected-1');
        btn.insertAdjacentHTML('beforeend', '<span class="slot-rank-tag">首選 1</span>');
      } else if (rankIndex === 1) {
        btn.classList.add('selected-2');
        btn.insertAdjacentHTML('beforeend', '<span class="slot-rank-tag rank-2">志願 2</span>');
      }
    });

    submitTaskBtn.disabled = state.selectedSlots.length === 0;
  }

  // 3. 載入任務清單
  async function loadTasks() {
    if (!state.user) return;
    try {
      state.tasks = await API.listTasks();
      renderTasks();
    } catch (err) {
      console.error(err);
    }
  }

  function renderTasks() {
    if (state.tasks.length === 0) {
      taskList.innerHTML = `
        <div style="text-align: center; padding: 2rem; color: var(--text-dim);">
          🎾 目前無預約任務，請在左側設定並建立新任務！
        </div>
      `;
      return;
    }

    taskList.innerHTML = state.tasks.map(t => `
      <div class="task-item" id="task-${t.id}">
        <div class="task-info">
          <h4>📅 ${t.target_date} (網球場 ${t.court_order.join('/')})</h4>
          <div class="task-meta">
            <span>🎯 志願: ${t.primary_slots.join(', ')}</span>
            <span>⚡ 狀態: <b style="color:${getStatusColor(t.status)}">${getStatusText(t.status)}</b></span>
          </div>
          ${t.result_message ? `<div style="font-size:0.75rem; color:var(--text-dim); margin-top:4px;">${t.result_message}</div>` : ''}
        </div>
        <div class="task-actions">
          <button class="btn btn-outline btn-sm" onclick="triggerDryRun(${t.id})">🧪 模擬</button>
          <button class="btn btn-outline btn-sm" style="color:var(--accent-red);" onclick="deleteTask(${t.id})">✕</button>
        </div>
      </div>
    `).join('');
  }

  function getStatusColor(status) {
    if (status === 'success') return '#34d399';
    if (status === 'running') return '#60a5fa';
    if (status === 'failed') return '#f87171';
    return '#fbbf24';
  }

  function getStatusText(status) {
    const map = { pending: '待命中 (23:50預熱)', running: '搶票進行中', success: '預約成功', failed: '已結束' };
    return map[status] || status;
  }

  // 4. 建立任務提交
  submitTaskBtn.addEventListener('click', async () => {
    if (!state.selectedDate || state.selectedSlots.length === 0) {
      alert('請先選擇目標日期與至少一個時段！');
      return;
    }

    submitTaskBtn.disabled = true;
    submitTaskBtn.innerText = '建立任務中...';

    const payload = {
      target_date: state.selectedDate.dateStr,
      target_day_num: state.selectedDate.dayNum,
      primary_slots: state.selectedSlots,
      court_order: [document.getElementById('court-priority-select').value, document.getElementById('court-priority-select').value === 'A' ? 'B' : 'A'],
      enable_fallback: document.getElementById('fallback-check').checked,
      fallback_min_hour: 14,
      fallback_max_hour: 17,
      refresh_attempts: parseInt(document.getElementById('refresh-attempts-input').value) || 40,
      refresh_interval_ms: parseInt(document.getElementById('refresh-interval-input').value) || 300,
      telegram_bot_token: document.getElementById('telegram-token-input').value || null,
      telegram_chat_id: document.getElementById('telegram-chatid-input').value || null
    };

    try {
      await API.createTask(payload);
      alert('🎉 搶票任務建立成功！系統將在 23:50 自動預熱並在 00:00:00 執行搶票！');
      await loadTasks();
    } catch (err) {
      alert('建立失敗: ' + err.message);
    } finally {
      submitTaskBtn.disabled = false;
      submitTaskBtn.innerText = '🚀 建立並啟動 00:00 自動搶票任務';
    }
  });

  // 全域動作函數
  window.deleteTask = async (id) => {
    if (!confirm('確定刪除該搶票任務？')) return;
    try {
      await API.deleteTask(id);
      await loadTasks();
    } catch (err) {
      alert('刪除失敗: ' + err.message);
    }
  };

  window.triggerDryRun = async (id) => {
    dryRunModal.classList.add('open');
    const logBox = document.getElementById('dry-run-log');
    logBox.innerText = '⏳ 正在啟動背景 Chromium 模擬推演... 請稍候 5~10 秒...';
    try {
      const res = await API.runDryRun(id, 5);
      logBox.innerText = `✅ ${res.message}\n截圖存證檔: ${res.screenshot || '無'}`;
    } catch (err) {
      logBox.innerText = `❌ 推演失敗: ${err.message}`;
    }
  };

  // 5. 憑證管理
  window.openCredModal = () => credModal.classList.add('open');
  window.closeCredModal = () => credModal.classList.remove('open');
  window.closeDryRunModal = () => dryRunModal.classList.remove('open');

  document.getElementById('save-cred-btn').addEventListener('click', async () => {
    const acc = document.getElementById('sinica-acc-input').value;
    const pwd = document.getElementById('sinica-pwd-input').value;
    if (!acc || !pwd) {
      alert('請填寫完整中研院帳號與密碼');
      return;
    }
    const btn = document.getElementById('save-cred-btn');
    btn.disabled = true;
    btn.innerText = '正在登入中研院驗證...';

    try {
      const res = await API.saveCredential(acc, pwd);
      alert(res.message);
      closeCredModal();
      await checkAuthAndCreds();
    } catch (err) {
      alert('驗證失敗: ' + err.message);
    } finally {
      btn.disabled = false;
      btn.innerText = '🔒 加密儲存並驗證登入';
    }
  });

  // 6. 帳號與認證流程
  async function checkAuthAndCreds() {
    const token = API.getToken();
    if (!token) {
      authModal.classList.add('open');
      return;
    }

    try {
      state.user = await API.getMe();
      userProfileBtn.innerText = `👤 ${state.user.name || state.user.email}`;
      
      state.credential = await API.getCredentialStatus();
      if (state.credential.has_credential && state.credential.is_valid) {
        credStatusBadge.className = 'badge badge-success';
        credStatusBadge.innerHTML = `🟢 憑證有效 (${state.credential.masked_account})`;
      } else {
        credStatusBadge.className = 'badge badge-warning';
        credStatusBadge.innerHTML = '🟡 尚未設定中研院帳密';
      }

      await loadTasks();
    } catch (err) {
      authModal.classList.add('open');
    }
  }

  // 登入 / 註冊切換
  document.getElementById('auth-submit-btn').addEventListener('click', async () => {
    const email = document.getElementById('auth-email-input').value;
    const pwd = document.getElementById('auth-pwd-input').value;
    const isRegister = document.getElementById('auth-is-register').checked;

    try {
      if (isRegister) {
        await API.register(email, pwd);
      } else {
        await API.login(email, pwd);
      }
      authModal.classList.remove('open');
      await checkAuthAndCreds();
    } catch (err) {
      alert('認證失敗: ' + err.message);
    }
  });

  // 啟動初始化
  renderDateChips();
  // 預設選中 17:00 & 18:00
  state.selectedSlots = ['17:00', '18:00'];
  updateSlotUI();
  checkAuthAndCreds();
});
