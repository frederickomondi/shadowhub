// ===== MAIN JS =====

document.addEventListener('DOMContentLoaded', function() {
  // Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // Quantity controls (for cart and product pages)
  document.querySelectorAll('.qty-minus').forEach(btn => {
    btn.addEventListener('click', function() {
      const input = this.parentElement.querySelector('.qty-field');
      if (parseInt(input.value) > 1) {
        input.value = parseInt(input.value) - 1;
        input.dispatchEvent(new Event('change'));
      }
    });
  });
  document.querySelectorAll('.qty-plus').forEach(btn => {
    btn.addEventListener('click', function() {
      const input = this.parentElement.querySelector('.qty-field');
      const max = parseInt(input.getAttribute('max')) || 999;
      if (parseInt(input.value) < max) {
        input.value = parseInt(input.value) + 1;
        input.dispatchEvent(new Event('change'));
      }
    });
  });

  // Payment method cards on checkout
  document.querySelectorAll('.payment-radio').forEach(radio => {
    radio.addEventListener('change', function() {
      document.querySelectorAll('.payment-option-card').forEach(c => c.classList.remove('selected'));
      const card = this.closest('.payment-method-option');
      if (card) card.querySelector('.payment-option-card').classList.add('selected');
      const walletDisplays = document.querySelectorAll('.wallet-address-display');
      walletDisplays.forEach(el => el.classList.add('d-none'));
      const target = document.getElementById('wallet-' + this.value);
      if (target) target.classList.remove('d-none');
    });
  });

  document.querySelectorAll('.payment-method-option').forEach(opt => {
    opt.addEventListener('click', function() {
      const radio = this.querySelector('.payment-radio');
      if (radio) {
        radio.checked = true;
        radio.dispatchEvent(new Event('change'));
      }
    });
  });

  // Initialize selected payment method display
  const defaultRadio = document.querySelector('.payment-radio:checked');
  if (defaultRadio) {
    const card = defaultRadio.closest('.payment-method-option');
    if (card) card.querySelector('.payment-option-card').classList.add('selected');
    const walletEl = document.getElementById('wallet-' + defaultRadio.value);
    if (walletEl) walletEl.classList.remove('d-none');
  }

  // Navbar scroll effect
  const navbar = document.querySelector('.shadow-navbar');
  if (navbar) {
    window.addEventListener('scroll', function() {
      if (window.scrollY > 50) {
        navbar.style.background = 'rgba(10, 10, 26, 0.99)';
      } else {
        navbar.style.background = 'rgba(10, 10, 26, 0.95)';
      }
    });
  }
});

// ===== COPY TO CLIPBOARD =====
function copyToClipboard(text) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      showToast('Copied to clipboard!');
    }).catch(() => {
      fallbackCopy(text);
    });
  } else {
    fallbackCopy(text);
  }
}

function fallbackCopy(text) {
  const el = document.createElement('textarea');
  el.value = text;
  el.style.position = 'fixed';
  el.style.opacity = '0';
  document.body.appendChild(el);
  el.select();
  try {
    document.execCommand('copy');
    showToast('Copied to clipboard!');
  } catch (e) {
    showToast('Failed to copy. Please copy manually.');
  }
  document.body.removeChild(el);
}

// ===== TOAST NOTIFICATION =====
function showToast(message, type) {
  const existing = document.querySelector('.toast-notification');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast-notification';
  toast.textContent = message;
  if (type === 'error') toast.style.background = '#e94560';
  document.body.appendChild(toast);

  setTimeout(() => toast.classList.add('show'), 50);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 300);
  }, 3000);
}

// ===== COPY WALLET ADDRESS =====
function copyWallet() {
  const addr = document.getElementById('wallet-address');
  if (addr) {
    copyToClipboard(addr.textContent.trim());
  }
}

// ===== COUNTDOWN TIMER (for order confirmation page) =====
// Initialized inline in order_confirmation.html
// Exposed globally for reuse if needed
window.ShadowHub = {
  showToast: showToast,
  copyToClipboard: copyToClipboard,
  copyWallet: copyWallet
};
