const API = {
  getToken() {
    return localStorage.getItem('court_jwt_token') || '';
  },

  setToken(token) {
    localStorage.setItem('court_jwt_token', token);
  },

  clearToken() {
    localStorage.removeItem('court_jwt_token');
  },

  async request(endpoint, options = {}) {
    const token = this.getToken();
    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...(options.headers || {})
    };

    try {
      const response = await fetch(endpoint, {
        ...options,
        headers
      });

      if (response.status === 401) {
        this.clearToken();
        window.dispatchEvent(new CustomEvent('auth:expired'));
        throw new Error('登入逾時，請重新登入');
      }

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || data.message || '請求失敗');
      }
      return data;
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      throw err;
    }
  },

  // 認證 API
  async register(email, password, name = '') {
    const res = await this.request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name })
    });
    this.setToken(res.access_token);
    return res;
  },

  async login(email, password) {
    const res = await this.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    this.setToken(res.access_token);
    return res;
  },

  async getMe() {
    return await this.request('/api/auth/me');
  },

  // 憑證 API
  async getCredentialStatus() {
    return await this.request('/api/credentials/');
  },

  async saveCredential(sinica_account, sinica_password) {
    return await this.request('/api/credentials/save', {
      method: 'POST',
      body: JSON.stringify({ sinica_account, sinica_password })
    });
  },

  // 任務 API
  async listTasks() {
    return await this.request('/api/tasks/');
  },

  async createTask(taskData) {
    return await this.request('/api/tasks/create', {
      method: 'POST',
      body: JSON.stringify(taskData)
    });
  },

  async deleteTask(taskId) {
    return await this.request(`/api/tasks/${taskId}`, {
      method: 'DELETE'
    });
  },

  async runDryRun(taskId, seconds = 5) {
    return await this.request(`/api/tasks/${taskId}/dry-run?seconds=${seconds}`, {
      method: 'POST'
    });
  },

  // 雷達掃描 API
  async scanSlots(court = 'A', day = '05') {
    return await this.request(`/api/scanner/slots?court=${court}&day=${day}`);
  }
};
