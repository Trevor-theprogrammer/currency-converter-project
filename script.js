const apiKey = '88831ddf4487978ce70b4661';  // 
const apiURL = `https://v6.exchangerate-api.com/v6/${apiKey}/latest/USD`;

async function loadCurrencies() {
    try {
        const response = await fetch(apiURL);
        if (!response.ok) throw new Error("Failed to fetch currencies.");
        const data = await response.json();
        const currencyList = Object.keys(data.conversion_rates);

        const fromSelect = document.getElementById("fromCurrency");
        const toSelect = document.getElementById("toCurrency");

        currencyList.forEach(currency => {
            fromSelect.innerHTML += `<option value="${currency}">${currency}</option>`;
            toSelect.innerHTML += `<option value="${currency}">${currency}</option>`;
        });
    } catch (error) {
        document.getElementById("result").textContent = "Error loading currencies.";
    }
}

async function convertCurrency() {
    const amount = parseFloat(document.getElementById("amount").value);
    const fromCurrency = document.getElementById("fromCurrency").value;
    const toCurrency = document.getElementById("toCurrency").value;

    if (isNaN(amount) || amount <= 0) {
        document.getElementById("result").textContent = "Please enter a valid amount.";
        return;
    }

    try {
        const response = await fetch(apiURL);
        if (!response.ok) throw new Error("Failed to fetch rates.");
        const data = await response.json();
        const rate = data.conversion_rates[toCurrency] / data.conversion_rates[fromCurrency];
        const convertedAmount = (amount * rate).toFixed(2);

        document.getElementById("result").textContent = `Converted Amount: ${convertedAmount} ${toCurrency}`;
        renderChart(fromCurrency, toCurrency); // Update chart after conversion
    } catch (error) {
        document.getElementById("result").textContent = "Error converting currency.";
    }
}

async function renderChart(from = "USD", to = "EUR") {
    const end = new Date().toISOString().split('T')[0];
    const start = new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]; // last 7 days
    const url = `https://api.exchangerate.host/timeseries?start_date=${start}&end_date=${end}&base=${from}&symbols=${to}`;

    try {
        const res = await fetch(url);
        const data = await res.json();
        const labels = Object.keys(data.rates);
        const rates = labels.map(date => data.rates[date][to]);

        const ctx = document.getElementById('rateChart').getContext('2d');
        if (window.rateChartInstance) window.rateChartInstance.destroy(); // Remove old chart if exists
        window.rateChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: `${from} to ${to} (last 7 days)`,
                    data: rates,
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0,123,255,0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                }
            }
        });
    } catch {
        document.getElementById('rateChart').style.display = 'none';
    }
}

// live rates
async function loadLiveRates() {
    const pairs = [
        ["EUR", "USD"], ["USD", "EUR"], ["USD", "JPY"], ["JPY", "USD"],
        // Remove XAU and BTC if not supported by your plan
    ];
    const tbody = document.querySelector("#liveRatesTable tbody");
    tbody.innerHTML = "";

    for (const [base, symbol] of pairs) {
        const url = `https://v6.exchangerate-api.com/v6/${apiKey}/latest/${base}`;
        try {
            const res = await fetch(url);
            if (!res.ok) throw new Error("Network response was not ok");
            const data = await res.json();
            const rate = data.conversion_rates[symbol];
            tbody.innerHTML += `
                <tr>
                    <td>${base}/${symbol}</td>
                    <td>${rate ? rate.toFixed(6) : "N/A"}</td>
                    <td>${rate ? rate.toFixed(6) : "N/A"}</td>
                </tr>
            `;
        } catch (error) {
            tbody.innerHTML += `
                <tr>
                    <td>${base}/${symbol}</td>
                    <td colspan="2">Error</td>
                </tr>
            `;
        }
    }
}

function toggleTheme() {
    document.body.classList.toggle("dark-mode");
}

window.onload = function() {
    loadCurrencies().then(() => {
        const from = document.getElementById("fromCurrency").value || "USD";
        const to = document.getElementById("toCurrency").value || "EUR";
        renderChart(from, to);
    });
    loadLiveRates();

    // Update chart when currency selection changes
    document.getElementById("fromCurrency").addEventListener("change", function() {
        renderChart(this.value, document.getElementById("toCurrency").value);
    });
    document.getElementById("toCurrency").addEventListener("change", function() {
        renderChart(document.getElementById("fromCurrency").value, this.value);
    });

    document.querySelectorAll('.popular-conversions button').forEach(btn => {
        btn.addEventListener('click', function() {
            const [amount, from, , to] = this.textContent.split(' ');
            document.getElementById('fromCurrency').value = from;
            document.getElementById('toCurrency').value = to;
            document.getElementById('amount').value = 1;
            convertCurrency();
            renderChart(from, to);
        });
    });

    setInterval(loadLiveRates, 60000); // Refresh every 60 seconds
};
