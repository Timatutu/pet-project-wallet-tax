// Simple Router for SPA
class Router {
    constructor() {
        this.routes = {
            'dashboard': 'dashboard-page',
            'transactions': 'transactions-page',
            'tax': 'tax-page'
        };
        this.currentPage = 'dashboard';
        this.init();
    }

    init() {
        // Handle hash changes
        window.addEventListener('hashchange', () => this.handleRoute());
        window.addEventListener('load', () => this.handleRoute());
    }

    handleRoute() {
        // Check if main app is visible
        const mainApp = document.getElementById('main-app');
        if (!mainApp || mainApp.classList.contains('hidden')) {
            return; // Don't handle routes if main app is not visible
        }
        
        const hash = window.location.hash.slice(1) || 'dashboard';
        const pageId = this.routes[hash] || this.routes['dashboard'];
        
        // Hide all pages
        document.querySelectorAll('.content-page').forEach(page => {
            page.classList.remove('active');
        });

        // Show target page
        const targetPage = document.getElementById(pageId);
        if (targetPage) {
            targetPage.classList.add('active');
            this.currentPage = hash;
        }

        // Update nav links
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-page') === hash) {
                link.classList.add('active');
            }
        });

        // Update page title
        const titles = {
            'dashboard': 'Главная',
            'transactions': 'Транзакции',
            'tax': 'Налоги'
        };
        const titleEl = document.getElementById('page-title');
        if (titleEl) {
            titleEl.textContent = titles[hash] || 'Главная';
        }
        
        // Auto-load transactions when navigating to transactions page
        if (hash === 'transactions' && typeof walletAddress !== 'undefined' && walletAddress) {
            setTimeout(() => {
                if (typeof loadTransactions === 'function') {
                    loadTransactions();
                }
            }, 100);
        }
    }

    navigate(page) {
        window.location.hash = page;
    }
}

// Initialize router
const router = new Router();

