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
      if (!API.getToken()) {
        authModal.classList.add('open');
        alert('請先登入系統後再啟動全域掃描！');
        return;
      }

      fullRadarScanBtn.disabled = true;
      fullRadarLoading.style.display = 'block';
      matrixSectionCard.style.display = 'none';
      strategySectionCard.style.display = 'none';

      // 計時器提示
      let elapsed = 0;
      const timerEl = fullRadarLoading.querySelector('p');
      const originalText = timerEl ? timerEl.innerText : '';
      const timerInterval = setInterval(() => {
        elapsed += 1;
        if (timerEl) {
          timerEl.innerText = `Playwright 正在背景掃描日曆與兩大場地... (已耗時 ${elapsed} 秒)`;
        }
      }, 1000);

      try {
        const res = await API.scanFullRadar();
        if (!res.success) {
          throw new Error(res.error || "全域掃描失敗");
        }
        
        state.matrixData = res.matrix;
        renderRadarMatrix(res.matrix);
        matrixSectionCard.style.display = 'block';
      } catch (err) {
        alert('❌ 掃描過程出錯: ' + err.message);
      } finally {
        clearInterval(timerInterval);
        if (timerEl) timerEl.innerText = originalText;
        fullRadarScanBtn.disabled = false;
        fullRadarLoading.style.display = 'none';
      }
    });
  }


  // ==========================================
  // Step 2: 渲染全域空位日曆 (100% 復刻中研院體育館日曆樣式)
  // ==========================================
  const WEEKDAYS_HEADER = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
  if (!state.activeCourt) {
    state.activeCourt = 'A';
  }

  function renderRadarMatrix(matrix) {
    if (!matrix) return;
    state.matrixData = matrix;
    radarMatrixContainer.innerHTML = '';

    const courtA = matrix.A || [];
    const courtB = matrix.B || [];

    if (courtA.length === 0 && courtB.length === 0) {
      radarMatrixContainer.innerHTML = '<div style="text-align:center; padding:2rem; color:#e74c3c; font-weight:600;">⚠️ 未能抓取到日曆時段資料，請檢查網路或中研院系統狀態。</div>';
      return;
    }

    const currentCourt = state.activeCourt || 'A';
    const days = currentCourt === 'A' ? courtA : courtB;
    const courtTitle = currentCourt === 'A' ? '網球場 A Tennis court A' : '網球場 B Tennis court B';
    const monthTitle = matrix.monthTitle || 'September 2026';

    // 1. 球場切換 Tabs (網球場 A / 網球場 B)
    const tabsContainer = document.createElement('div');
    tabsContainer.className = 'sinica-court-tabs';
    tabsContainer.innerHTML = `
      <button class="sinica-court-tab ${currentCourt === 'A' ? 'active' : ''}" id="court-tab-a">
        🎾 網球場 A Tennis court A
      </button>
      <button class="sinica-court-tab ${currentCourt === 'B' ? 'active' : ''}" id="court-tab-b">
        🎾 網球場 B Tennis court B
      </button>
    `;
    radarMatrixContainer.appendChild(tabsContainer);

    tabsContainer.querySelector('#court-tab-a').addEventListener('click', () => {
      state.activeCourt = 'A';
      renderRadarMatrix(state.matrixData);
    });
    tabsContainer.querySelector('#court-tab-b').addEventListener('click', () => {
      state.activeCourt = 'B';
      renderRadarMatrix(state.matrixData);
    });

    // 2. 月份列與導航按鈕 (September 2026 ▲ | < > 當月 兩週內)
    const monthBar = document.createElement('div');
    monthBar.className = 'sinica-month-bar';
    monthBar.innerHTML = `
      <div class="sinica-month-title">
        <span>${monthTitle}</span>
        <span class="sinica-chevron">▲</span>
      </div>
      <div class="calendar__toolbar">
        <button class="sinica-tool-btn" title="上個月">‹</button>
        <button class="sinica-tool-btn" title="下個月">›</button>
        <button class="sinica-tool-btn">當月</button>
        <button class="sinica-tool-btn active">兩週內</button>
      </div>
    `;
    radarMatrixContainer.appendChild(monthBar);

    // 3. 橘色預約備註提示
    const noticeEl = document.createElement('div');
    noticeEl.className = 'sinica-notice';
    noticeEl.textContent = '註：場地可多人預約時，相關資訊會顯示成 N / Max (已約人數 / 可約人數)';
    radarMatrixContainer.appendChild(noticeEl);

    // 4. 圖例列 (可預約、院內同仁、院外人士、團體、不可預約)
    const legendList = document.createElement('ul');
    legendList.className = 'timeline-desc';
    legendList.innerHTML = `
      <li><span class="legend-box legend-available"></span>可預約</li>
      <li><span class="legend-box legend-sinica"></span>院內同仁</li>
      <li><span class="legend-box legend-non-sinica"></span>院外人士</li>
      <li><span class="legend-box legend-group"></span>團體</li>
      <li><span class="legend-box legend-no-open"></span>不可預約</li>
    `;
    radarMatrixContainer.appendChild(legendList);

    // 5. 七欄式兩週日曆主網格
    const scrollWrapper = document.createElement('div');
    scrollWrapper.className = 'calendar__scroll-wrapper';

    const calendarGrid = document.createElement('div');
    calendarGrid.className = 'calendar__date';

    // 5a. 星期表頭 (Su, Mo, Tu, We, Th, Fr, Sa)
    WEEKDAYS_HEADER.forEach(w => {
      const weekHeader = document.createElement('div');
      weekHeader.className = 'calendar__week';
      weekHeader.textContent = w;
      calendarGrid.appendChild(weekHeader);
    });

    // 5b. 14 天日曆格
    days.forEach((dayInfo, dayIdx) => {
      const dayItem = document.createElement('div');
      dayItem.className = 'calendar__day-item';

      const isToday = !!dayInfo.isToday;
      const dayNum = dayInfo.dayNum || String(dayIdx + 1);
      const headerText = dayInfo.headerText || dayNum;

      // 日期標頭 (今天標示深藍圓圈)
      const dayHeader = document.createElement('div');
      dayHeader.className = 'calendar__day-header';
      dayHeader.innerHTML = `<span class="calendar__day-text ${isToday ? 'calendar__selected-date' : ''}">${dayNum}</span>`;
      dayItem.appendChild(dayHeader);

      // 時段清單 (2 欄子網格，左右對齊 16 個時段)
      const detailUl = document.createElement('ul');
      detailUl.className = 'calendar__detail';

      const slots = dayInfo.slots || [];
      slots.forEach(slot => {
        const detailLi = document.createElement('li');
        detailLi.className = 'calendar__detail-item';

        const parsed = parseSinicaSlot(slot, currentCourt, dayNum, headerText);
        const chip = document.createElement('div');
        chip.className = `timeline__identity ${parsed.cls}${parsed.isPicked ? ' selected' : ''}`;
        chip.title = parsed.title;

        if (parsed.isPicked) {
          const badge = document.createElement('span');
          badge.className = 'priority-num-badge';
          badge.textContent = parsed.pickRank;
          chip.appendChild(badge);
        }

        const textSpan = document.createElement('span');
        textSpan.textContent = parsed.displayText;
        chip.appendChild(textSpan);

        if (parsed.clickable) {
          chip.style.cursor = 'pointer';
          chip.addEventListener('click', () => {
            handleSlotClick(currentCourt, dayNum, headerText, slot, parsed);
          });
        }

        detailLi.appendChild(chip);
        detailUl.appendChild(detailLi);
      });

      dayItem.appendChild(detailUl);
      calendarGrid.appendChild(dayItem);
    });

    scrollWrapper.appendChild(calendarGrid);
    radarMatrixContainer.appendChild(scrollWrapper);
  }

  // 解析時段狀態與中研院原生顏色類別
  function parseSinicaSlot(slot, court, dayNum, headerText) {
    const rawClass = slot.className || '';
    const text = slot.text || '';
    const title = slot.title || text;
    let cls = '';
    let displayText = text;
    let clickable = false;

    // 1. 院內同仁預約 - 不可互動，原始箭頭
    if (rawClass.includes('timeline__identity_sinica')) {
      cls = 'timeline__identity_sinica';
      displayText = '已預約';
      clickable = false;
    // 2. 院外人士預約 - 不可互動，原始箭頭
    } else if (rawClass.includes('timeline__identity_non-sinica')) {
      cls = 'timeline__identity_non-sinica';
      displayText = '已預約';
      clickable = false;
    // 3. 團體預約 - 不可互動，原始箭頭
    } else if (rawClass.includes('timeline__identity_group')) {
      cls = 'timeline__identity_group';
      displayText = '已預約';
      clickable = false;
    // 4. 休館/停用 - 不可互動，原始箭頭
    } else if (slot.isClosed || text.includes('休館') || text.includes('不開放') || text.includes('停用')) {
      cls = 'slot-closed';
      displayText = '休館';
      clickable = false;
    // 5. 即將開放/臨時解除開放時段 - 顯眼閃爍提醒 + 滑鼠浮現開放時間 + 手型可互動預約
    } else if (slot.isOpenPending || text.includes('開放') || /^\d{1,2}\/\d{1,2}/.test(text)) {
      cls = 'slot-pending';
      const m = (title + " " + text).match(/(\d{1,2}\/\d{1,2})/);
      const openDate = m ? m[1] : (slot.openDate || '即將開放');
      displayText = `⚡ ${openDate}開放`;
      clickable = true; // 點擊可排定搶位志願
    // 6. 院外人士可預約時段 - 手型可互動
    } else if (slot.isAvailable || text.includes('~')) {
      cls = 'slot-available';
      const timeMatch = title.match(/(\d{2}):\d{2}~/);
      if (timeMatch) {
        const sH = timeMatch[1];
        const eH = String(parseInt(sH, 10) + 1).padStart(2, '0');
        displayText = `${sH}~${eH}`;
      } else if (text.includes('~')) {
        displayText = text.replace(/:\d{2}/g, '');
      }
      clickable = true;
    } else if (slot.isBooked || text.includes('已預約')) {
      cls = 'timeline__identity_non-sinica';
      displayText = '已預約';
      clickable = false;
    } else {
      cls = 'slot-available';
      clickable = true;
    }

    // 滑鼠 hover 提示資訊
    let hoverTitle = title;
    if (cls === 'slot-pending') {
      const openDate = (title + " " + text).match(/(\d{1,2}\/\d{1,2})/) ? (title + " " + text).match(/(\d{1,2}\/\d{1,2})/)[1] : '';
      const timeRange = title.split(' ')[0] || slot.startTime || displayText;
      hoverTitle = `⚡【即將開放預約時段】\n場地時段：${timeRange}\n預約開放時間：${openDate ? openDate + ' 00:00' : '近期開放'}\n👉 點擊可加入優先搶票志願待命清單`;
    } else if (cls === 'slot-available') {
      hoverTitle = `🟢【可預約時段】${title || displayText}\n👉 點擊加入預約清單`;
    } else if (cls === 'slot-closed') {
      hoverTitle = `⚪【休館不開放】${title || '本日暫停營業'}`;
    } else {
      hoverTitle = `🔴【他人已預約】${title || '此時段已被預約'}`;
    }

    const pickedIndex = state.selectedStrategy.findIndex(
      s => s.dayNum === dayNum && s.court === court && (s.startTime === slot.startTime || s.title === title)
    );
    const isPicked = pickedIndex > -1;

    return {
      cls,
      displayText,
      title: hoverTitle,
      clickable,
      isPicked,
      pickRank: isPicked ? pickedIndex + 1 : 0
    };
  }

  function handleSlotClick(court, dayNum, headerText, slot, parsed) {
    const startTime = slot.startTime || parsed.title || parsed.displayText;
    const existIndex = state.selectedStrategy.findIndex(
      s => s.dayNum === dayNum && s.court === court && (s.startTime === slot.startTime || s.title === parsed.title)
    );

    if (existIndex > -1) {
      state.selectedStrategy.splice(existIndex, 1);
    } else {
      state.selectedStrategy.push({
        court: court,
        dayNum: dayNum,
        headerText: headerText,
        startTime: slot.startTime || startTime,
        title: parsed.title,
        displayText: parsed.displayText,
        isPending: parsed.cls === 'slot-pending'
      });
    }

    renderRadarMatrix(state.matrixData);
    renderStrategyQueue();
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
      taskList.innerHTML = `
        <div style="text-align: center; padding: 2rem; color: var(--text-dim);">
          🔒 請先登入以檢視與排定搶票任務
        </div>
      `;
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
      console.warn('Auth error:', err);
      authModal.classList.add('open');
      taskList.innerHTML = `
        <div style="text-align: center; padding: 2rem; color: var(--text-dim);">
          🔒 登入驗證已過期，請重新登入
        </div>
      `;
    }
  }

  window.addEventListener('auth:expired', () => {
    authModal.classList.add('open');
    taskList.innerHTML = `
      <div style="text-align: center; padding: 2rem; color: var(--text-dim);">
        🔒 登入已過期，請重新登入
      </div>
    `;
  });

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

