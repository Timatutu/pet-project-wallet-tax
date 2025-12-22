// API Client with automatic token refresh
class APIClient {
    constructor() {
        this.baseURL = window.location.origin + '/api';
        this.accessToken = localStorage.getItem('access_token');
        this.refreshToken = localStorage.getItem('refresh_token');
    }

    async refreshAccessToken() {
        if (!this.refreshToken) {
            console.error('No refresh token available');
            return false;
        }

        try {
            const response = await fetch(`${this.baseURL}/refresh/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    refresh_token: this.refreshToken
                })
            });

            const data = await response.json();

            if (response.ok && data.tokens) {
                this.accessToken = data.tokens.access;
                this.refreshToken = data.tokens.refresh;
                localStorage.setItem('access_token', this.accessToken);
                localStorage.setItem('refresh_token', this.refreshToken);
                console.log('Token refreshed successfully');
                return true;
            } else {
                console.error('Token refresh failed:', data);
                this.logout();
                return false;
            }
        } catch (error) {
            console.error('Error refreshing token:', error);
            this.logout();
            return false;
        }
    }

    async fetchWithAuth(url, options = {}) {
        if (!options.headers) {
            options.headers = {};
        }

        if (this.accessToken) {
            options.headers['Authorization'] = `Bearer ${this.accessToken}`;
        }

        let response = await fetch(url, options);

        // If token expired, try to refresh
        if (response.status === 401 || response.status === 403) {
            console.log('Token expired, attempting refresh...');
            const refreshed = await this.refreshAccessToken();

            if (refreshed && this.accessToken) {
                options.headers['Authorization'] = `Bearer ${this.accessToken}`;
                response = await fetch(url, options);
            } else {
                // If refresh failed, redirect to login
                if (window.handleLogout) {
                    window.handleLogout();
                }
                return response;
            }
        }

        return response;
    }

    async register(email, password, passwordConfirm) {
        const response = await fetch(`${this.baseURL}/register/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email,
                password,
                password_confirm: passwordConfirm
            })
        });

        const data = await response.json();
        return { response, data };
    }

    async login(email, password) {
        const response = await fetch(`${this.baseURL}/login/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email,
                password
            })
        });

        const data = await response.json();
        return { response, data };
    }

    async getWallet() {
        const response = await this.fetchWithAuth(`${this.baseURL}/Wallet/`);
        const data = await response.json();
        return { response, data };
    }

    async connectWallet(walletAddress, walletType = 'tonkeeper') {
        const response = await this.fetchWithAuth(`${this.baseURL}/Wallet/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                wallet_address: walletAddress,
                wallet_type: walletType
            })
        });

        const data = await response.json();
        return { response, data };
    }

    async getBalance() {
        const response = await this.fetchWithAuth(`${this.baseURL}/wallet/balance/`);
        const data = await response.json();
        return { response, data };
    }

    async getTransactions(refresh = false) {
        const url = refresh 
            ? `${this.baseURL}/wallet/transactions/?refresh=true`
            : `${this.baseURL}/wallet/transactions/`;
        const response = await this.fetchWithAuth(url);
        const data = await response.json();
        return { response, data };
    }

    async getTaxForMonth(year, month) {
        const response = await this.fetchWithAuth(
            `${this.baseURL}/tax/month/?year=${encodeURIComponent(year)}&month=${encodeURIComponent(month)}`
        );
        const data = await response.json();
        return { response, data };
    }

    async getTaxForAllMonths(startYear = null, startMonth = null) {
        const params = new URLSearchParams();
        if (startYear) params.append('start_year', startYear);
        if (startMonth) params.append('start_month', startMonth);
        
        const response = await this.fetchWithAuth(
            `${this.baseURL}/tax/all/?${params.toString()}`
        );
        const data = await response.json();
        return { response, data };
    }

    async getTotalTax(startYear = null, startMonth = null) {
        const params = new URLSearchParams();
        if (startYear) params.append('start_year', startYear);
        if (startMonth) params.append('start_month', startMonth);
        
        const response = await this.fetchWithAuth(
            `${this.baseURL}/tax/total/?${params.toString()}`
        );
        const data = await response.json();
        return { response, data };
    }

    logout() {
        this.accessToken = null;
        this.refreshToken = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    }
}

// Initialize API client
const api = new APIClient();

