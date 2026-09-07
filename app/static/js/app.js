document.addEventListener('DOMContentLoaded', () => {
  // 狀態管理
  const state = {
    user: null,
    credential: null,
    matrixData: null,          // { A: [...days], B: [...days] }
    selectedStrategy: [],     // [ { dayNum, headerText, court, startTime, title } ]
    tasks: []
  };

  // DOM 元素快取
  const authModal = document.getElementById('auth-modal');
  const credModal = document.getElementById('cred-modal');
  const dryRunModal = document.getElementById('dry-run-modal');
  
  const userProfileBtn = document.getElementById('user-profile-btn');
  const credStatusBadge = document.getElementById('cred-status-badge');
  const taskList = document.getElementById('task-list');
  
  const fullRadarScanBtn = document.getElementById('full-radar-scan-btn');
  const fullRadarLoading = document.getElementById('full-radar-loading');
  const matrixSectionCard = document.getElementById('matrix-section-card');
  const radarMatrixContainer = document.getElementById('radar-matrix-container');
  
  const strategySectionCard = document.getElementById('strategy-section-card');
  const strategyQueueList = document.getElementById('strategy-queue-list');
  const armStrategyBtn = document.getElementById('arm-strategy-btn');

  // 摺疊面板切換
  const accordionHeader = document.getElementById('accordion-header');
  const accordionBody = document.getElementById('accordion-body');
  if (accordionHeader) {
    accordionHeader.addEventListener('click', () => {
      accordionBody.classList.toggle('open');
    });
  }

  // ==========================================
  // Step 1: 啟動全域空位掃描
  // ==========================================
  if (fullRadarScanBtn) {
    fullRadarScanBtn.addEventListener('click', async () => {
      fullRadarScanBtn.disabled = true;
      fullRadarLoading.style.display = 'block';
      matrixSectionCard.style.display = 'none';
      strategySectionCard.style.display = 'none';

      try {
        const res = await API.scanFullRadar();
        if (!res.success) {
          throw new Error(res.error || "全域掃描失敗");
        }
        
        state.matrixData = res.matrix;
        renderRadarMatrix(res.matrix);
        matrixSectionCard.style.display = 'block';
        
        // 滾動至矩陣區塊
        matrixSectionCard.scrollIntoView({ behavior: 'smooth' });
      } catch (err) {
        alert('❌ 掃描過程出錯: ' + err.message);
      } finally {
        fullRadarScanBtn.disabled = false;
        fullRadarLoading.style.display = 'none';
      }
    });
  }

  // ==========================================
  // Step 2: 渲染全域空位矩陣
  // ==========================================
  function renderRadarMatrix(matrix) {
    radarMatrixContainer.innerHTML = '';

    const daysA = matrix.A || [];
    const daysB = matrix.B || [];

    if (daysA.length === 0 && daysB.length === 0) {
      radarMatrixContainer.innerHTML = '<div style="text-align:center; color:var(--accent-red);">未能在中研院系統抓取到任何日曆格</div>';
      return;
    }

    // 依日期組合 (以 daysA 順序為基準)
    daysA.forEach((dayInfoA, index) => {
      const dayInfoB = daysB[index] || { slots: [] };
      const dayNum = dayInfoA.dayNum;
      const headerText = dayInfoA.headerText || `05/${dayNum}`;

      const dayBlock = document.createElement('div');
      dayBlock.className = 'radar-day-block';

      let courtAHTML = renderCourtRowHTML('A', dayNum, headerText, dayInfoA.slots);
      let courtBHTML = renderCourtRowHTML('B', dayNum, headerText, dayInfoB.slots);

      dayBlock.innerHTML = `
        <div class="radar-day-header">
          📅 ${headerText} (日曆格 ${dayNum})
        </div>
        ${courtAHTML}
        ${courtBHTML}
      `;

      radarMatrixContainer.appendChild(dayBlock);
    });

    // 為所有 slot 綁定點擊事件
    bindSlotClickEvents();
  }

  function renderCourtRowHTML(court, dayNum, headerText, slots) {
    if (!slots || slots.length === 0) {
      return `
        <div class="radar-court-row">
          <span class="radar-court-badge badge-court-${court.toLowerCase()}">${court} 場</span>
          <span style="font-size:0.75rem; color:var(--text-dim);">當日不開放或無時段資訊</span>
        </div>
      `;
    }

    const slotChipsHTML = slots.map(slot => {
      let statusClass = 'status-booked';
      let statusLabel = '已預約';

      if (slot.isAvailable) {
        statusClass = 'status-available';
        statusLabel = '可預約';
      } else if (slot.isOpenPending) {
        statusClass = 'status-pending';
        statusLabel = '即將開放';
      }

      const isPicked = state.selectedStrategy.findIndex(
        s => s.dayNum === dayNum && s.court === court && s.startTime === slot.startTime
      );

      const pickedBadge = isPicked > -1 ? `<span class="slot-pick-badge">${isPicked + 1}</span>` : '';
      const selectedClass = isPicked > -1 ? 'selected' : '';

      return `
        <div class="matrix-slot-chip ${statusClass} ${selectedClass}" 
             data-day="${dayNum}" 
             data-header="${headerText}" 
             data-court="${court}" 
             data-start="${slot.startTime}" 
             data-title="${slot.title}">
          ${slot.startTime || slot.text} ${slot.isAvailable ? '🟢' : (slot.isOpenPending ? '🟡' : '🔴')}
          ${pickedBadge}
        </div>
      `;
    }).join('');

    return `
      <div class="radar-court-row">
        <span class="radar-court-badge badge-court-${court.toLowerCase()}">${court} 場</span>
        <div class="radar-slots-flex">
          ${slotChipsHTML}
        </div>
      </div>
    `;
  }

  function bindSlotClickEvents() {
    document.querySelectorAll('.matrix-slot-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const dayNum = chip.dataset.day;
        const headerText = chip.dataset.header;
        const court = chip.dataset.court;
        const startTime = chip.dataset.start;
        const title = chip.dataset.title;

        if (!startTime) {
          alert('該時段無法辨識具體時間');
          return;
        }

        const existIndex = state.selectedStrategy.findIndex(
          s => s.dayNum === dayNum && s.court === court && s.startTime === startTime
        );

        if (existIndex > -1) {
          // 移除
          state.selectedStrategy.splice(existIndex, 1);
        } else {
          // 加入志願清單
          state.selectedStrategy.push({ dayNum, headerText, court, startTime, title });
        }

        // 重新渲染矩陣 (更新數字 badge)
        renderRadarMatrix(state.matrixData);
        // 更新 Step 3 志願清單
        renderStrategyQueue();
      });
    });
  }

  // ==========================================
  // Step 3: 搶票策略確認與排隊清單
  // ==========================================
  function renderStrategyQueue() {
    if (state.selectedStrategy.length === 0) {
      strategySectionCard.style.display = 'none';
      return;
    }

    strategySectionCard.style.display = 'block';
    strategyQueueList.innerHTML = state.selectedStrategy.map((s, idx) => `
      <div class="strategy-item">
        <div>
          <span class="strategy-rank">志願 ${idx + 1}</span>
          <strong>${s.headerText}</strong> — 網球場 ${s.court} (${s.startTime})
        </div>
        <button class="strategy-remove-btn" onclick="removeStrategyItem(${idx})">✕</button>
      </div>
    `).join('');

    strategySectionCard.scrollIntoView({ behavior: 'smooth' });
  }

  window.removeStrategyItem = (idx) => {
    state.selectedStrategy.splice(idx, 1);
    renderRadarMatrix(state.matrixData);
    renderStrategyQueue();
  };

  // 點擊「🎯 制定腳本並讓程式進入待命」
  if (armStrategyBtn) {
    armStrategyBtn.addEventListener('click', async () => {
      if (state.selectedStrategy.length === 0) {
        alert('請先在空位地圖中點擊選擇至少一個志願時段！');
        return;
      }

      armStrategyBtn.disabled = true;
      armStrategyBtn.innerText = '制定腳本中...';

      // 拿第一志願作為 main target
      const primaryTarget = state.selectedStrategy[0];
      const primarySlots = Array.from(new Set(state.selectedStrategy.map(s => s.startTime)));
      const courtOrder = Array.from(new Set(state.selectedStrategy.map(s => s.court)));
      if (courtOrder.length === 1) {
        courtOrder.push(courtOrder[0] === 'A' ? 'B' : 'A');
      }

      const payload = {
        target_date: primaryTarget.headerText,
        target_day_num: primaryTarget.dayNum,
        primary_slots: primarySlots,
        court_order: courtOrder,
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
        alert('🎉 搶票策略腳本已成功制定並進入待命！系統將在 23:50 自動預熱並於 00:00 執行！');
        await loadTasks();
      } catch (err) {
        alert('待命失敗: ' + err.message);
      } finally {
        armStrategyBtn.disabled = false;
        armStrategyBtn.innerText = '🎯 制定腳本並讓程式進入待命';
      }
    });
  }

  // ==========================================
  // 右側任務監控與通訊
  // ==========================================
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
          🎾 目前無待命任務，請先點擊左側「啟動全域空位掃描」！
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

  window.deleteTask = async (id) => {
    if (!confirm('確定刪除該待命任務？')) return;
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

  // 憑證管理
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

  // 帳號與認證流程
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

  checkAuthAndCreds();
});
