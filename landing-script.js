// Modal functionality
function openLoginModal() {
  document.getElementById('loginModal').style.display = 'block';
  document.getElementById('registerModal').style.display = 'none';
}

function closeLoginModal() {
  document.getElementById('loginModal').style.display = 'none';
}

function openRegisterModal() {
  document.getElementById('registerModal').style.display = 'block';
  document.getElementById('loginModal').style.display = 'none';
}

function closeRegisterModal() {
  document.getElementById('registerModal').style.display = 'none';
}

function switchToLogin() {
  closeRegisterModal();
  openLoginModal();
}

function switchToRegister() {
  closeLoginModal();
  openRegisterModal();
}

// Close modals when clicking outside
window.onclick = function (event) {
  const loginModal = document.getElementById('loginModal');
  const registerModal = document.getElementById('registerModal');

  if (event.target === loginModal) {
    closeLoginModal();
  }
  if (event.target === registerModal) {
    closeRegisterModal();
  }
};

// Mobile menu toggle
function toggleMobileMenu() {
  const navMenu = document.querySelector('.nav-menu');
  const navButtons = document.querySelector('.nav-buttons');

  navMenu.classList.toggle('active');
  navButtons.classList.toggle('active');
}

// Smooth scrolling
function scrollToCalculator() {
  document.querySelector('.hero-calculator').scrollIntoView({
    behavior: 'smooth',
  });
}

// Currency calculator functionality
const exchangeRates = {
  USD: { EUR: 0.85, GBP: 0.73, INR: 74.5, CAD: 1.25, AUD: 1.35 },
  EUR: { USD: 1.18, GBP: 0.86, INR: 87.6, CAD: 1.47, AUD: 1.59 },
  GBP: { USD: 1.37, EUR: 1.16, INR: 102.1, CAD: 1.71, AUD: 1.85 },
};

function updateCalculator() {
  const sendAmount =
    parseFloat(document.getElementById('sendAmount').value) || 0;
  const sendCurrency = document.getElementById('sendCurrency').value;
  const receiveCurrency = document.getElementById('receiveCurrency').value;

  if (sendCurrency === receiveCurrency) {
    document.getElementById('receiveAmount').value = sendAmount;
  } else {
    const rate = exchangeRates[sendCurrency]?.[receiveCurrency] || 1;
    document.getElementById('receiveAmount').value = (
      sendAmount * rate
    ).toFixed(2);
  }

  // Update rate display
  const rate = exchangeRates[sendCurrency]?.[receiveCurrency] || 1;
  document.querySelector(
    '.rate-info span'
  ).textContent = `1 ${sendCurrency} = ${rate.toFixed(2)} ${receiveCurrency}`;
}

// Form handling
document
  .getElementById('loginForm')
  .addEventListener('submit', async function (e) {
    e.preventDefault();

    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          password: password,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Store session data
        localStorage.setItem('sessionToken', data.session_token);
        localStorage.setItem('userEmail', data.email);
        localStorage.setItem('userId', data.user_id);

        alert('Login successful! Redirecting to dashboard...');
        window.location.href = '/dashboard';
      } else {
        alert(data.error || 'Login failed. Please try again.');
      }
    } catch (error) {
      console.error('Login error:', error);
      alert('Login failed. Please check your connection and try again.');
    }
  });

document
  .getElementById('registerForm')
  .addEventListener('submit', async function (e) {
    e.preventDefault();

    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    if (password !== confirmPassword) {
      alert('Passwords do not match!');
      return;
    }

    if (password.length < 8) {
      alert('Password must be at least 8 characters long!');
      return;
    }

    try {
      const response = await fetch('/api/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          password: password,
          confirmPassword: confirmPassword,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        alert('Account created successfully! Please log in.');
        switchToLogin();
      } else {
        alert(data.error || 'Registration failed. Please try again.');
      }
    } catch (error) {
      console.error('Registration error:', error);
      alert('Registration failed. Please check your connection and try again.');
    }
  });

// Initialize calculator
document.addEventListener('DOMContentLoaded', function () {
  updateCalculator();

  // Add event listeners for calculator
  document
    .getElementById('sendAmount')
    .addEventListener('input', updateCalculator);
  document
    .getElementById('sendCurrency')
    .addEventListener('change', updateCalculator);
  document
    .getElementById('receiveCurrency')
    .addEventListener('change', updateCalculator);
});

// Smooth scroll for navigation links
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener('click', function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      target.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }
  });
});

// Add mobile menu styles dynamically
const style = document.createElement('style');
style.textContent = `
    @media (max-width: 768px) {
        .nav-menu.active, .nav-buttons.active {
            display: flex;
            flex-direction: column;
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            padding: 1rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .nav-menu.active {
            gap: 1rem;
        }
        
        .nav-buttons.active {
            gap: 0.5rem;
            align-items: stretch;
        }
    }
`;
document.head.appendChild(style);
