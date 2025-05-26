const apiKey = 'your-api-key';  // Get an API key from ExchangeRate-API or Open Exchange Rates
const apiURL = `https://v6.exchangerate-api.com/v6/${apiKey}/latest/USD`;

async function loadCurrencies() {
    const response = await fetch(apiURL);
    const data = await response.json();
    const currencyList = Object.keys(data.conversion_rates);

    const fromSelect = document.getElementById("fromCurrency");
    const toSelect = document.getElementById("toCurrency");

    currencyList.forEach(currency => {
        fromSelect.innerHTML += `<option value="${currency}">${currency}</option>`;
        toSelect.innerHTML += `<option value="${currency}">${currency}</option>`;
    });
}

async function convertCurrency() {
    const amount = document.getElementById("amount").value;
    const fromCurrency = document.getElementById("fromCurrency").value;
    const toCurrency = document.getElementById("toCurrency").value;

    const response = await fetch(apiURL);
    const data = await response.json();
    const rate = data.conversion_rates[toCurrency] / data.conversion_rates[fromCurrency];
    const convertedAmount = (amount * rate).toFixed(2);

    document.getElementById("result").textContent = `Converted Amount: ${convertedAmount} ${toCurrency}`;
}

function toggleTheme() {
    document.body.classList.toggle("dark-mode");
}

window.onload = loadCurrencies;
