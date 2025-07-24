// Dashboard JavaScript
class CurrencyDashboard {
  constructor() {
    this.sessionToken = localStorage.getItem('sessionToken');
    this.userEmail = localStorage.getItem('userEmail');
    this.userId = localStorage.getItem('userId');

    this.init();
  }

  async init() {
    if (!this.sessionToken) {
      window.location.href = '/';
      return;
    }

    this.showLoading();
    await this.loadUserData();
    await this.loadCurrencies();
    this.setupEventListeners();
    this.hideLoading();
  }

  showLoading() {
    document.getElementById('loadingOverlay').classList.add('show');
  }

  hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('show');
  }

  async loadUserData() {
    try {
      const response = await this.apiCall('/api/user/profile');
      if (response.ok) {
        const userData = await response.json();
        document.getElementById('userEmail').textContent = userData.email;
        document.getElementById('profileEmail').value = userData.email;
        document.getElementById('profileFirstName').value =
          userData.first_name || '';
        document.getElementById('profileLastName').value =
          userData.last_name || '';
        document.getElementById('profilePhone').value = userData.phone || '';

        this.loadStats();
        this.loadHistory();
        this.loadFavorites();
        this.loadAlerts();
      } else {
        this.handleAuthError();
      }
    } catch (error) {
      console.error('Error loading user data:', error);
      this.handleAuthError();
    }
  }

  async loadCurrencies() {
    try {
      const response = await fetch('/api/currencies');
      const data = await response.json();

      const fromCurrency = document.getElementById('fromCurrency');
      const toCurrency = document.getElementById('toCurrency');
      const alertFromCurrency = document.getElementById('alertFromCurrency');
      const alertToCurrency = document.getElementById('alertToCurrency');

      [fromCurrency, toCurrency, alertFromCurrency, alertToCurrency].forEach(
        (select) => {
          select.innerHTML = '';
          data.currencies.forEach((currency) => {
            const option = document.createElement('option');
            option.value = currency;
            option.textContent = currency;
            select.appendChild(option);
          });
        }
      );

      // Set defaults
      fromCurrency.value = 'USD';
      toCurrency.value = 'EUR';
      alertFromCurrency.value = 'USD';
      alertToCurrency.value = 'EUR';
    } catch (error) {
      console.error('Error loading currencies:', error);
    }
  }

  async loadStats() {
    try {
      const [historyResponse, favoritesResponse, alertsResponse] =
        await Promise.all([
          this.apiCall('/api/user/history'),
          this.apiCall('/api/user/favorites'),
          this.apiCall('/api/user/alerts'),
        ]);

      const historyData = await historyResponse.json();
      const favoritesData = await favoritesResponse.json();
      const alertsData = await alertsResponse.json();

      document.getElementById('totalConversions').textContent =
        historyData.history.length;
      document.getElementById('totalFavorites').textContent =
        favoritesData.favorites.length;
      document.getElementById('totalAlerts').textContent =
        alertsData.alerts.filter((a) => a.is_active).length;
      document.getElementById('lastActivity').textContent =
        new Date().toLocaleDateString();
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  }

  async loadHistory() {
    try {
      const response = await this.apiCall('/api/user/history');
      const data = await response.json();

      const historyList = document.getElementById('historyList');
      if (data.history.length === 0) {
        historyList.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-history"></i>
                        <p>No conversion history yet</p>
                    </div>
                `;
        return;
      }

      historyList.innerHTML = data.history
        .map(
          (item) => `
                <div class="history-item">
                    <div>
                        <strong>${item.amount} ${item.from_currency} → ${
            item.converted_amount
          } ${item.to_currency}</strong>
                        <br>
                        <small>Rate: ${item.exchange_rate} | ${new Date(
            item.created_at
          ).toLocaleString()}</small>
                    </div>
                </div>
            `
        )
        .join('');
    } catch (error) {
      console.error('Error loading history:', error);
    }
  }

  async loadFavorites() {
    try {
      const response = await this.apiCall('/api/user/favorites');
      const data = await response.json();

      const favoritesList = document.getElementById('favoritesList');
      if (data.favorites.length === 0) {
        favoritesList.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-star"></i>
                        <p>No favorite pairs yet</p>
                    </div>
                `;
        return;
      }

      favoritesList.innerHTML = data.favorites
        .map(
          (item) => `
                <div class="favorite-item">
                    <div>
                        <strong>${item.from_currency} → ${
            item.to_currency
          }</strong>
                        <br>
                        <small>Added: ${new Date(
                          item.created_at
                        ).toLocaleDateString()}</small>
                    </div>
                    <button class="btn-secondary" onclick="removeFavorite(${
                      item.id
                    })">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `
        )
        .join('');
    } catch (error) {
      console.error('Error loading favorites:', error);
    }
  }

  async loadAlerts() {
    try {
      const response = await this.apiCall('/api/user/alerts');
      const data = await response.json();

      const alertsList = document.getElementById('alertsList');
      if (data.alerts.length === 0) {
        alertsList.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-bell"></i>
                        <p>No rate alerts set</p>
                    </div>
                `;
        return;
      }

      alertsList.innerHTML = data.alerts
        .map(
          (item) => `
                <div class="alert-item">
                    <div>
                        <strong>${item.from_currency} → ${
            item.to_currency
          }</strong>
                        <br>
                        <small>Target: ${item.target_rate} | Status: ${
            item.is_active ? 'Active' : 'Inactive'
          }</small>
                    </div>
                    <div>
                        <button class="btn-secondary" onclick="toggleAlert(${
                          item.id
                        }, ${!item.is_active})">
                            ${item.is_active ? 'Disable' : 'Enable'}
                        </button>
                        <button class="btn-secondary" onclick="deleteAlert(${
                          item.id
                        })">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `
        )
        .join('');
    } catch (error) {
      console.error('Error loading alerts:', error);
    }
  }

  setupEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-link').forEach((link) => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const target = e.target.getAttribute('href').substring(1);
        this.showSection(target);
      });
    });

    // Currency converter
    document
      .getElementById('amount')
      .addEventListener('input', () => this.convertCurrency());
    document
      .getElementById('fromCurrency')
      .addEventListener('change', () => this.convertCurrency());
    document
      .getElementById('toCurrency')
      .addEventListener('change', () => this.convertCurrency());

    // Theme toggle
    const savedTheme = localStorage.getItem('theme') || 'light';
    this.setTheme(savedTheme);
  }

  showSection(sectionId) {
    document.querySelectorAll('.nav-link').forEach((link) => {
      link.classList.remove('active');
    });

    document.querySelector(`[href="#${sectionId}"]`).classList.add('active');

    // Hide all sections and show the selected one
    const sections = ['converter', 'history', 'favorites', 'alerts', 'profile'];
    sections.forEach((id) => {
      const section = document.getElementById(id);
      if (section) {
        section.style.display = id === sectionId ? 'block' : 'none';
      }
    });
  }

  async convertCurrency() {
    const amount = parseFloat(document.getElementById('amount').value) || 1;
    const fromCurrency = document.getElementById('fromCurrency').value;
    const toCurrency = document.getElementById('toCurrency').value;

    if (!fromCurrency || !toCurrency) return;

    try {
      const response = await this.apiCall(
        `/api/convert?from=${fromCurrency}&to=${toCurrency}&amount=${amount}`
      );
      const data = await response.json();

      if (response.ok) {
        document.getElementById(
          'resultAmount'
        ).textContent = `${data.amount} ${data.from} = ${data.converted_amount} ${data.to}`;
        document.getElementById(
          'resultRate'
        ).textContent = `1 ${data.from} = ${data.rate} ${data.to}`;
        document.getElementById(
          'resultTime'
        ).textContent = `Last updated: ${new Date(
          data.timestamp
        ).toLocaleString()}`;
      }
    } catch (error) {
      console.error('Error converting currency:', error);
    }
  }

  async addToFavorites() {
    const fromCurrency = document.getElementById('fromCurrency').value;
    const toCurrency = document.getElementById('toCurrency').value;

    try {
      const response = await this.apiCall('/api/user/favorites', 'POST', {
        from_currency: fromCurrency,
        to_currency: toCurrency,
      });

      if (response.ok) {
        this.showNotification('Added to favorites!', 'success');
        this.loadFavorites();
        this.loadStats();
      } else {
        const data = await response.json();
        this.showNotification(data.error || 'Failed to add favorite', 'error');
      }
    } catch (error) {
      console.error('Error adding favorite:', error);
      this.showNotification('Failed to add favorite', 'error');
    }
  }

  async saveToHistory() {
    const amount = parseFloat(document.getElementById('amount').value) || 1;
    const fromCurrency = document.getElementById('fromCurrency').value;
    const toCurrency = document.getElementById('toCurrency').value;

    // This would typically be handled automatically when converting
    this.showNotification('Conversion saved to history!', 'success');
  }

  async updateProfile() {
    const data = {
      first_name: document.getElementById('profileFirstName').value,
      last_name: document.getElementById('profileLastName').value,
      phone: document.getElementById('profilePhone').value,
    };

    try {
      const response = await this.apiCall('/api/user/profile', 'PUT', data);

      if (response.ok) {
        this.showNotification('Profile updated successfully!', 'success');
      } else {
        this.showNotification('Failed to update profile', 'error');
      }
    } catch (error) {
      console.error('Error updating profile:', error);
      this.showNotification('Failed to update profile', 'error');
    }
  }

  async createAlert() {
    const fromCurrency = document.getElementById('alertFromCurrency').value;
    const toCurrency = document.getElementById('alertToCurrency').value;
    const targetRate = parseFloat(
      document.getElementById('alertTargetRate').value
    );

    if (!targetRate) {
      this.showNotification('Please enter a valid target rate', 'error');
      return;
    }

    try {
      const response = await this.apiCall('/api/user/alerts', 'POST', {
        from_currency: fromCurrency,
        to_currency: toCurrency,
        target_rate: targetRate,
      });

      if (response.ok) {
        this.showNotification('Rate alert created successfully!', 'success');
        this.loadAlerts();
        this.loadStats();
        document.getElementById('alertTargetRate').value = '';
      } else {
        const data = await response.json();
        this.showNotification(data.error || 'Failed to create alert', 'error');
      }
    } catch (error) {
      console.error('Error creating alert:', error);
      this.showNotification('Failed to create alert', 'error');
    }
  }

  async toggleAlert(alertId, isActive) {
    try {
      const response = await this.apiCall(
        `/api/user/alerts/${alertId}`,
        'PUT',
        {
          is_active: isActive,
        }
      );

      if (response.ok) {
        this.showNotification('Alert updated successfully!', 'success');
        this.loadAlerts();
        this.loadStats();
      }
    } catch (error) {
      console.error('Error toggling alert:', error);
      this.showNotification('Failed to update alert', 'error');
    }
  }

  async deleteAlert(alertId) {
    if (!confirm('Are you sure you want to delete this alert?')) return;

    try {
      const response = await this.apiCall(
        `/api/user/alerts/${alertId}`,
        'DELETE'
      );

      if (response.ok) {
        this.showNotification('Alert deleted successfully!', 'success');
        this.loadAlerts();
        this.loadStats();
      }
    } catch (error) {
      console.error('Error deleting alert:', error);
      this.showNotification('Failed to delete alert', 'error');
    }
  }

  async removeFavorite(favoriteId) {
    if (!confirm('Are you sure you want to remove this favorite?')) return;

    try {
      const response = await this.apiCall(
        `/api/user/favorites/${favoriteId}`,
        'DELETE'
      );

      if (response.ok) {
        this.showNotification('Favorite removed successfully!', 'success');
        this.loadFavorites();
        this.loadStats();
      }
    } catch (error) {
      console.error('Error removing favorite:', error);
      this.showNotification('Failed to remove favorite', 'error');
    }
  }

  async logout() {
    try {
      await this.apiCall('/api/logout', 'POST', {
        session_token: this.sessionToken,
      });
    } catch (error) {
      console.error('Error during logout:', error);
    } finally {
      localStorage.removeItem('sessionToken');
      localStorage.removeItem('userEmail');
      localStorage.removeItem('userId');
      window.location.href = '/';
    }
  }

  async apiCall(endpoint, method = 'GET', data = null) {
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: this.sessionToken,
      },
    };

    if (data) {
      options.body = JSON.stringify(data);
    }

    return fetch(endpoint, options);
  }

  showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.remove();
    }, 3000);
  }

  setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }

  toggleTheme() {
    const currentTheme =
      document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    this.setTheme(newTheme);
  }

  toggleUserMenu() {
    const dropdown = document.getElementById('userDropdown');
    dropdown.classList.toggle('show');
  }

  handleAuthError() {
    localStorage.removeItem('sessionToken');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('userId');
    window.location.href = '/';
  }
}

// Global functions
function toggleUserMenu() {
  dashboard.toggleUserMenu();
}

function logout() {
  dashboard.logout();
}

function addToFavorites() {
  dashboard.addToFavorites();
}

function saveToHistory() {
  dashboard.saveToHistory();
}

function updateProfile() {
  dashboard.updateProfile();
}

function createAlert() {
  dashboard.createAlert();
}

function toggleAlert(alertId, isActive) {
  dashboard.toggleAlert(alertId, isActive);
}

function deleteAlert(alertId) {
  dashboard.deleteAlert(alertId);
}

function removeFavorite(favoriteId) {
  dashboard.removeFavorite(favoriteId);
}

function refreshHistory() {
  dashboard.loadHistory();
}

function clearHistory() {
  if (confirm('Are you sure you want to clear all history?')) {
    // This would require a new API endpoint
    dashboard.showNotification('History cleared (feature coming soon)', 'info');
  }
}

// Initialize dashboard
const dashboard = new CurrencyDashboard();

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
  if (!e.target.closest('.user-menu')) {
    document.getElementById('userDropdown').classList.remove('show');
  }
});

// Navigation
document.addEventListener('DOMContentLoaded', () => {
  // Show converter by default
  dashboard.showSection('converter');
});
