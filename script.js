/* Professional XE.com Style JavaScript */

const API_BASE_URL = '/api';

// Currency to flag mapping
const currencyFlags = {
  USD: '🇺🇸',
  EUR: '🇪🇺',
  GBP: '🇬🇧',
  JPY: '🇯🇵',
  CAD: '🇨🇦',
  AUD: '🇦🇺',
  CHF: '🇨🇭',
  CNY: '🇨🇳',
  INR: '🇮🇳',
  BRL: '🇧🇷',
  MXN: '🇲🇽',
  SGD: '🇸🇬',
  NZD: '🇳🇿',
  KRW: '🇰🇷',
  RUB: '🇷🇺',
  SEK: '🇸🇪',
  NOK: '🇳🇴',
  DKK: '🇩🇰',
  PLN: '🇵🇱',
  TRY: '🇹🇷',
  ZAR: '🇿🇦',
  HKD: '🇭🇰',
  THB: '🇹🇭',
  MYR: '🇲🇾',
  PHP: '🇵🇭',
};

// Currency full names
const currencyNames = {
  USD: 'US Dollar',
  EUR: 'Euro',
  GBP: 'British Pound',
  JPY: 'Japanese Yen',
  CAD: 'Canadian Dollar',
  AUD: 'Australian Dollar',
  CHF: 'Swiss Franc',
  CNY: 'Chinese Yuan',
  INR: 'Indian Rupee',
  BRL: 'Brazilian Real',
  MXN: 'Mexican Peso',
  SGD: 'Singapore Dollar',
  NZD: 'New Zealand Dollar',
  KRW: 'South Korean Won',
  RUB: 'Russian Ruble',
  SEK: 'Swedish Krona',
  NOK: 'Norwegian Krone',
  DKK: 'Danish Krone',
  PLN: 'Polish Zloty',
  TRY: 'Turkish Lira',
  ZAR: 'South African Rand',
  HKD: 'Hong Kong Dollar',
  THB: 'Thai Baht',
  MYR: 'Malaysian Ringgit',
  PHP: 'Philippine Peso',
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function () {
  initializeApp();
});

function initializeApp() {
  loadCurrencies();
  setupEventListeners();
  setupResponsiveMenu();
  loadPopularRates();
}

async function loadCurrencies() {
  try {
    const response = await fetch(`${API_BASE_URL}/currencies`);
    if (!response.ok) throw new Error('Failed to fetch currencies.');
    const data = await response.json();
    const currencyList = data.currencies;

    const fromSelect = document.getElementById('fromCurrency');
    const toSelect = document.getElementById('toCurrency');

    // Clear existing options
    fromSelect.innerHTML = '';
    toSelect.innerHTML = '';

    // Add currency options
    currencyList.forEach((currency) => {
      const name = currencyNames[currency] || currency;
      const option1 = new Option(`${currency} - ${name}`, currency);
      const option2 = new Option(`${currency} - ${name}`, currency);

      fromSelect.add(option1);
      toSelect.add(option2);
    });

    // Set default values
    fromSelect.value = 'USD';
    toSelect.value = 'EUR';
    updateCurrencyFlags();
  } catch (error) {
    console.error('Error loading currencies:', error);
    showError('Error loading currencies. Please try again.');
  }
}

function setupEventListeners() {
  // Currency change listeners
  document
    .getElementById('fromCurrency')
    .addEventListener('change', function () {
      updateCurrencyFlags();
      convertCurrency();
    });

  document.getElementById('toCurrency').addEventListener('change', function () {
    updateCurrencyFlags();
    convertCurrency();
  });

  // Amount input listener
  document.getElementById('amount').addEventListener('input', function () {
    if (this.value && !isNaN(this.value) && parseFloat(this.value) > 0) {
      convertCurrency();
    }
  });

  // Popular conversion buttons
  document.querySelectorAll('.popular-card').forEach((card) => {
    card.addEventListener('click', function () {
      const from = this.dataset.from;
      const to = this.dataset.to;

      if (from && to) {
        document.getElementById('fromCurrency').value = from;
        document.getElementById('toCurrency').value = to;
        document.getElementById('amount').value = 1;

        updateCurrencyFlags();
        convertCurrency();
      }
    });
  });

  // Auto-refresh rates every 60 seconds
  setInterval(() => {
    loadPopularRates();
  }, 60000);
}

function updateCurrencyFlags() {
  const fromCurrency = document.getElementById('fromCurrency').value;
  const toCurrency = document.getElementById('toCurrency').value;

  document.getElementById('fromFlag').textContent =
    currencyFlags[fromCurrency] || '🏳️';
  document.getElementById('toFlag').textContent =
    currencyFlags[toCurrency] || '🏳️';
}

async function convertCurrency() {
  const amount = parseFloat(document.getElementById('amount').value);
  const fromCurrency = document.getElementById('fromCurrency').value;
  const toCurrency = document.getElementById('toCurrency').value;

  const resultAmountEl = document.getElementById('resultAmount');
  const resultRateEl = document.getElementById('resultRate');
  const resultTimeEl = document.getElementById('resultTime');

  if (isNaN(amount) || amount <= 0) {
    return; // Do nothing if input is invalid
  }

  // Show loading state
  resultAmountEl.textContent = 'Converting...';
  resultRateEl.textContent = 'Please wait';
  resultTimeEl.textContent = 'Fetching latest rates...';

  try {
    const response = await fetch(
      `${API_BASE_URL}/convert?from=${fromCurrency}&to=${toCurrency}&amount=${amount}`
    );
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Conversion failed');
    }
    const data = await response.json();

    resultAmountEl.textContent = `${formatAmount(data.amount)} ${
      data.from
    } = ${formatAmount(data.converted_amount)} ${data.to}`;
    resultRateEl.textContent = `1 ${data.from} = ${data.rate.toFixed(6)} ${
      data.to
    }`;
    resultTimeEl.textContent = `Last updated: ${new Date(
      data.timestamp
    ).toLocaleTimeString()}`;
  } catch (error) {
    console.error('Error converting currency:', error);
    showError(error.message);
  }
}

function formatAmount(amount) {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(amount);
}

function showError(message) {
  const resultAmountEl = document.getElementById('resultAmount');
  const resultRateEl = document.getElementById('resultRate');
  const resultTimeEl = document.getElementById('resultTime');

  resultAmountEl.textContent = message;
  resultAmountEl.style.color = 'var(--accent-red)';
  resultRateEl.textContent = 'Please check your connection or try again.';
  resultTimeEl.textContent = 'Error';

  // Reset color after a few seconds
  setTimeout(() => {
    resultAmountEl.style.color = '';
  }, 5000);
}

async function loadPopularRates() {
  const pairs = [
    ['EUR', 'USD'],
    ['USD', 'EUR'],
    ['GBP', 'USD'],
    ['USD', 'JPY'],
    ['EUR', 'GBP'],
    ['USD', 'CAD'],
  ];

  for (const [from, to] of pairs) {
    const element = document.getElementById(`rate-${from}-${to}`);
    if (!element) continue;

    try {
      const response = await fetch(
        `${API_BASE_URL}/convert?from=${from}&to=${to}&amount=1`
      );
      if (!response.ok) {
        element.textContent = 'N/A';
        continue;
      }
      const data = await response.json();
      if (data.rate) {
        element.textContent = data.rate.toFixed(4);
      }
    } catch (error) {
      element.textContent = 'N/A';
      console.error(`Error fetching rate for ${from}/${to}:`, error);
    }
  }
}

function swapCurrencies() {
  const fromSelect = document.getElementById('fromCurrency');
  const toSelect = document.getElementById('toCurrency');

  const fromValue = fromSelect.value;
  const toValue = toSelect.value;

  fromSelect.value = toValue;
  toSelect.value = fromValue;

  updateCurrencyFlags();
  convertCurrency();
}

function setupResponsiveMenu() {
  const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
  const mobileMenu = document.getElementById('mobileMenu');

  if (mobileMenuToggle && mobileMenu) {
    mobileMenuToggle.addEventListener('click', function () {
      mobileMenu.classList.toggle('active');
    });
  }
}

// Initialize dark mode
function toggleTheme() {
  document.body.classList.toggle('dark-mode');
  const isDark = document.body.classList.contains('dark-mode');
  localStorage.setItem('darkMode', isDark);
}
