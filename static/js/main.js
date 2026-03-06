/* ═══════════════════════════════════════════════════
   JOB SKILL PORTAL — Main JavaScript Utilities
   ═══════════════════════════════════════════════════ */

// ─── Mobile Navigation Toggle ───
document.addEventListener('DOMContentLoaded', () => {
    const hamburger = document.querySelector('.nav-hamburger');
    const navLinks = document.querySelector('.nav-links');

    if (hamburger) {
        hamburger.addEventListener('click', () => {
            navLinks.classList.toggle('open');
        });
    }

    // Scroll-based fade-in animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

    // Animate stat counters
    document.querySelectorAll('.stat-value[data-count]').forEach(el => {
        animateCounter(el, parseInt(el.dataset.count));
    });
});

// ─── Counter Animation ───
function animateCounter(element, target) {
    let current = 0;
    const increment = target / 60;
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            clearInterval(timer);
            current = target;
        }
        element.textContent = Math.round(current).toLocaleString();
    }, 20);
}

// ─── API Helper ───
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showNotification('An error occurred. Please try again.', 'error');
        return null;
    }
}

// ─── Notifications ───
function showNotification(message, type = 'info') {
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();

    const colors = {
        info: 'var(--accent-blue)',
        success: 'var(--accent-green)',
        error: 'var(--accent-red)',
        warning: 'var(--accent-gold)'
    };

    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.style.cssText = `
        position: fixed; top: 90px; right: 20px; z-index: 9999;
        padding: 1rem 1.5rem; border-radius: 12px;
        background: rgba(13,17,23,0.95);
        border: 1px solid ${colors[type]};
        color: ${colors[type]};
        font-size: 0.9rem;
        animation: fadeInUp 0.3s ease;
        max-width: 400px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 4000);
}

// ─── Category Badge Helper ───
function getCategoryClass(category) {
    const cat = category.toUpperCase();
    if (cat.includes('INFORMATION') || cat.includes('IT')) return 'it';
    if (cat.includes('HR') || cat.includes('HUMAN')) return 'hr';
    if (cat.includes('FINANCE')) return 'finance';
    if (cat.includes('SALES')) return 'sales';
    if (cat.includes('BUSINESS')) return 'business';
    return 'it';
}

function getCategoryDisplay(category) {
    const cat = category.toUpperCase();
    if (cat.includes('INFORMATION')) return 'IT';
    if (cat.includes('BUSINESS')) return 'BIZ DEV';
    return category;
}

// ─── Debounce ───
function debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}
