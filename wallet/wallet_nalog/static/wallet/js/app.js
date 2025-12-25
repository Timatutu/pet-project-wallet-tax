// Main Application Logic
let tonConnectUI = null;
let walletAddress = null;
let cachedMonthlyTaxes = [];

// Initialize TON Connect
function initTonConnect() {
    if (typeof TON_CONNECT_UI !== 'undefined') {
        try {
            tonConnectUI = new TON_CONNECT_UI.TonConnectUI({
                manifestUrl: window.location.origin + '/tonconnect-manifest.json'
            });

            // Listen for wallet connection changes
            tonConnectUI.onStatusChange((wallet) => {
                if (wallet) {
                    handleWalletConnected(wallet);
                } else {
                    console.log('Wallet disconnected');
                    updateWalletStatus(false);
                }
            });
        } catch (e) {
            console.error('Error initializing TonConnect:', e);
        }
    }
}

// Check authentication on load
async function checkAuth() {
    const accessToken = localStorage.getItem('access_token');
    const authPage = document.getElementById('auth-page');
    const mainApp = document.getElementById('main-app');
    
    if (accessToken) {
        api.accessToken = accessToken;
        api.refreshToken = localStorage.getItem('refresh_token');
        
        // Show main app
        if (authPage) authPage.classList.add('hidden');
        if (mainApp) {
            mainApp.classList.remove('hidden');
            // Initialize router after main app is visible
            setTimeout(() => {
                router.handleRoute();
            }, 100);
        }
        
        // Check wallet connection
        await checkWalletConnection();
    } else {
        // Show auth page
        if (authPage) authPage.classList.remove('hidden');
        if (mainApp) mainApp.classList.add('hidden');
    }
    
    // Hide loading screen
    const loadingScreen = document.getElementById('loading-screen');
    if (loadingScreen) loadingScreen.classList.add('hidden');
}

// Check wallet connection
async function checkWalletConnection() {
    try {
        const { response, data } = await api.getWallet();
        
        if (response.ok && data.connected) {
            walletAddress = data.wallet_address;
            updateWalletStatus(true);
            document.getElementById('wallet-address').textContent = 
                formatAddress(walletAddress);
            document.getElementById('wallet-status-text').textContent = 'Активен';
            await loadBalance();
            // Auto-load transactions if wallet is connected
            await loadTransactions();
        } else {
            updateWalletStatus(false);
            document.getElementById('wallet-address').textContent = 'Не подключен';
            document.getElementById('wallet-status-text').textContent = 'Неактивен';
        }
    } catch (error) {
        console.error('Error checking wallet:', error);
        updateWalletStatus(false);
    }
}

// Update wallet status UI
function updateWalletStatus(connected) {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');
    const connectBtn = document.getElementById('connect-wallet-btn');
    
    if (connected) {
        statusDot.classList.add('connected');
        statusText.textContent = 'Подключен';
        if (connectBtn) {
            connectBtn.textContent = 'Отключить кошелек';
            connectBtn.className = 'btn btn-danger';
            connectBtn.onclick = disconnectWallet;
            connectBtn.disabled = false;
        }
    } else {
        statusDot.classList.remove('connected');
        statusText.textContent = 'Не подключен';
        if (connectBtn) {
            connectBtn.textContent = 'Подключить кошелек';
            connectBtn.className = 'btn btn-primary';
            connectBtn.onclick = connectTonkeeper;
            connectBtn.disabled = false;
        }
    }
}

// Format address for display
function formatAddress(address) {
    if (!address) return 'Не подключен';
    if (address.length <= 20) return address;
    return `${address.slice(0, 6)}...${address.slice(-6)}`;
}

// Switch to main app
async function switchToMainApp() {
    console.log('switchToMainApp called');
    
    const authPage = document.getElementById('auth-page');
    const mainApp = document.getElementById('main-app');
    
    if (!authPage) {
        console.error('Auth page not found!');
        return;
    }
    
    if (!mainApp) {
        console.error('Main app not found!');
        return;
    }
    
    console.log('Switching to main app...');
    console.log('Auth page classes before:', authPage.className);
    console.log('Main app classes before:', mainApp.className);
    
    // Hide auth page and show main app
    authPage.classList.add('hidden');
    mainApp.classList.remove('hidden');
    
    console.log('Auth page classes after:', authPage.className);
    console.log('Main app classes after:', mainApp.className);
    
    // Wait a bit for DOM to update
    await new Promise(resolve => setTimeout(resolve, 50));
    
    // Initialize router
    if (typeof router !== 'undefined' && router.handleRoute) {
        router.handleRoute();
        console.log('Router initialized');
    } else {
        console.error('Router not found!');
    }
    
    // Check wallet connection
    try {
        await checkWalletConnection();
    } catch (error) {
        console.error('Error checking wallet connection:', error);
    }
    
    console.log('Main app is now visible');
}

// Handle login
async function handleLogin() {
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const messageDiv = document.getElementById('login-message');

    if (!email || !password) {
        showMessage(messageDiv, 'Заполните все поля', 'error');
        return;
    }

    try {
        const { response, data } = await api.login(email, password);
        
        console.log('Login response status:', response.status);
        console.log('Login response data:', JSON.stringify(data, null, 2));

        if (response.ok) {
            // Check if tokens exist in response
            if (data.tokens && data.tokens.access && data.tokens.refresh) {
                api.accessToken = data.tokens.access;
                api.refreshToken = data.tokens.refresh;
                localStorage.setItem('access_token', api.accessToken);
                localStorage.setItem('refresh_token', api.refreshToken);
                
                console.log('Tokens saved successfully');
                showMessage(messageDiv, 'Вход выполнен успешно!', 'success');
                
                // Switch to main app
                setTimeout(() => {
                    switchToMainApp();
                }, 300);
            } else {
                console.error('Tokens not found in response:', data);
                showMessage(messageDiv, 'Ошибка: Токены не получены от сервера', 'error');
            }
        } else {
            console.error('Login failed:', data);
            const errors = data.error || (data.detail || '') || Object.values(data).flat().join(', ') || 'Неизвестная ошибка';
            showMessage(messageDiv, `Ошибка: ${errors}`, 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showMessage(messageDiv, `Ошибка: ${error.message}`, 'error');
    }
}

// Handle register
async function handleRegister() {
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const passwordConfirm = document.getElementById('register-password-confirm').value;
    const messageDiv = document.getElementById('register-message');

    if (!email || !password || !passwordConfirm) {
        showMessage(messageDiv, 'Заполните все поля', 'error');
        return;
    }

    if (password !== passwordConfirm) {
        showMessage(messageDiv, 'Пароли не совпадают', 'error');
        return;
    }

    try {
        const { response, data } = await api.register(email, password, passwordConfirm);
        
        console.log('Register response:', response.status, data);

        if (response.ok) {
            // Check if tokens exist in response
            if (data.tokens && data.tokens.access && data.tokens.refresh) {
                api.accessToken = data.tokens.access;
                api.refreshToken = data.tokens.refresh;
                localStorage.setItem('access_token', api.accessToken);
                localStorage.setItem('refresh_token', api.refreshToken);
                
                console.log('Tokens saved successfully');
                showMessage(messageDiv, 'Регистрация успешна!', 'success');
                
                // Switch to main app
                setTimeout(() => {
                    switchToMainApp();
                }, 300);
            } else {
                console.error('Tokens not found in response:', data);
                showMessage(messageDiv, 'Ошибка: Токены не получены от сервера', 'error');
            }
        } else {
            console.error('Register failed:', data);
            const errors = data.error || (data.detail || '') || Object.values(data).flat().join(', ') || 'Неизвестная ошибка';
            showMessage(messageDiv, `Ошибка: ${errors}`, 'error');
        }
    } catch (error) {
        console.error('Register error:', error);
        showMessage(messageDiv, `Ошибка: ${error.message}`, 'error');
    }
}

// Show message
function showMessage(element, message, type) {
    element.textContent = message;
    element.className = `message ${type}`;
    element.style.display = 'block';
    
    setTimeout(() => {
        element.style.display = 'none';
    }, 5000);
}

// Handle logout
async function handleLogout() {
    api.logout();
    walletAddress = null;
    
    if (tonConnectUI) {
        tonConnectUI.disconnect();
    }
    
    const authPage = document.getElementById('auth-page');
    const mainApp = document.getElementById('main-app');
    
    if (authPage) authPage.classList.remove('hidden');
    if (mainApp) mainApp.classList.add('hidden');
    
    // Clear forms
    const loginEmail = document.getElementById('login-email');
    const loginPassword = document.getElementById('login-password');
    const registerEmail = document.getElementById('register-email');
    const registerPassword = document.getElementById('register-password');
    const registerPasswordConfirm = document.getElementById('register-password-confirm');
    
    if (loginEmail) loginEmail.value = '';
    if (loginPassword) loginPassword.value = '';
    if (registerEmail) registerEmail.value = '';
    if (registerPassword) registerPassword.value = '';
    if (registerPasswordConfirm) registerPasswordConfirm.value = '';
    
    // Clear messages
    const loginMessage = document.getElementById('login-message');
    const registerMessage = document.getElementById('register-message');
    if (loginMessage) loginMessage.innerHTML = '';
    if (registerMessage) registerMessage.innerHTML = '';
}

// Connect Tonkeeper
async function connectTonkeeper() {
    if (!tonConnectUI) {
        alert('TonConnect не загружен. Перезагрузите страницу.');
        return;
    }

    if (!api.accessToken) {
        alert('Сначала войдите в систему');
        return;
    }

    try {
        const wallet = await tonConnectUI.connectWallet();
        if (wallet && wallet.account) {
            await handleWalletConnected(wallet);
        }
    } catch (error) {
        console.error('Error connecting wallet:', error);
        // Don't show alert if user cancelled
        if (error.message && !error.message.includes('User rejected')) {
            alert('Ошибка подключения кошелька: ' + error.message);
        }
    }
}

// Disconnect wallet
async function disconnectWallet() {
    if (!confirm('Вы уверены, что хотите отключить кошелек?')) {
        return;
    }

    try {
        // Check if wallet is actually connected before trying to disconnect
        if (tonConnectUI) {
            try {
                // Get current wallet state
                const wallet = tonConnectUI.wallet();
                if (wallet && wallet.account) {
                    // Wallet is connected, try to disconnect
                    await tonConnectUI.disconnect();
                } else {
                    // Wallet is already disconnected, just clear local state
                    console.log('Wallet already disconnected');
                }
            } catch (tonError) {
                // If disconnect fails (e.g., wallet already disconnected), just continue
                console.log('TON Connect disconnect error (ignored):', tonError.message);
                // Don't show error to user if wallet is already disconnected
                if (!tonError.message || !tonError.message.includes('not connected')) {
                    console.warn('Unexpected disconnect error:', tonError);
                }
            }
        }

        // Clear wallet address and local state
        walletAddress = null;
        
        // Update UI
        updateWalletStatus(false);
        const walletAddressEl = document.getElementById('wallet-address');
        const walletStatusTextEl = document.getElementById('wallet-status-text');
        const balanceValueEl = document.getElementById('balance-value');
        const totalTransactionsEl = document.getElementById('total-transactions');
        
        if (walletAddressEl) walletAddressEl.textContent = 'Не подключен';
        if (walletStatusTextEl) walletStatusTextEl.textContent = 'Неактивен';
        if (balanceValueEl) balanceValueEl.textContent = '0.00 TON';
        if (totalTransactionsEl) totalTransactionsEl.textContent = '0';
        
        // Always clear transactions container, regardless of current page
        const container = document.getElementById('transactions-container');
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M21 12H3M16 6l6 6-6 6M8 6l-6 6 6 6"></path>
                    </svg>
                    <h3>Нет транзакций</h3>
                    <p>Подключите кошелек для просмотра транзакций</p>
                </div>
            `;
        }
        
        console.log('Wallet disconnected successfully');
    } catch (error) {
        // Even if there's an error, clear local state
        walletAddress = null;
        updateWalletStatus(false);
        
        console.error('Error disconnecting wallet:', error);
        // Only show error if it's not about wallet already being disconnected
        if (error.message && !error.message.includes('not connected')) {
            alert('Ошибка при отключении кошелька: ' + error.message);
        }
    }
}

// Handle wallet connected
async function handleWalletConnected(wallet) {
    if (!wallet || !wallet.account || !wallet.account.address) {
        alert('Ошибка: не получен адрес кошелька');
        return;
    }

    const address = wallet.account.address;
    walletAddress = address;

    try {
        const { response, data } = await api.connectWallet(address, 'tonkeeper');

        if (response.ok) {
            updateWalletStatus(true);
            document.getElementById('wallet-address').textContent = formatAddress(address);
            document.getElementById('wallet-status-text').textContent = 'Активен';
            
            // Auto-load balance and transactions
            setTimeout(async () => {
                await loadBalance();
                // Auto-load transactions after wallet connection
                await loadTransactions();
            }, 500);
        } else {
            alert('Ошибка сохранения кошелька: ' + (data.error || JSON.stringify(data)));
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
        console.error('Error saving wallet:', error);
    }
}

// Load balance
async function loadBalance() {
    try {
        const { response, data } = await api.getBalance();

        if (response.ok) {
            document.getElementById('balance-value').textContent = 
                `${parseFloat(data.balance_ton).toFixed(2)} TON`;
            document.getElementById('wallet-status-text').textContent = 
                data.is_active ? 'Активен' : 'Неактивен';
        } else {
            console.error('Error loading balance:', data.error);
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

// Load transactions
async function loadTransactions(forceRefresh = false) {
    const container = document.getElementById('transactions-container');
    
    if (!container) return;
    
    container.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><p>Загрузка транзакций...</p></div>';

    try {
        const { response, data } = await api.getTransactions(forceRefresh);

        if (response.ok && data.transactions && Array.isArray(data.transactions)) {
            if (data.transactions.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M21 12H3M16 6l6 6-6 6M8 6l-6 6 6 6"></path>
                        </svg>
                        <h3>Нет транзакций</h3>
                        <p>Транзакции появятся здесь после подключения кошелька</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = '';
            
            // Update total transactions count
            document.getElementById('total-transactions').textContent = data.count || data.transactions.length;

            data.transactions.forEach((tx) => {
                // Для демо-транзакций определяем isOutgoing по operation_type
                let isOutgoing = false;
                if (tx.is_demo && tx.operation_type) {
                    isOutgoing = tx.operation_type === 'sell';
                } else {
                    isOutgoing = normalizeAddress(tx.from_address) === normalizeAddress(walletAddress);
                }
                const txElement = createTransactionElement(tx, isOutgoing);
                container.appendChild(txElement);
            });
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>Ошибка загрузки</h3>
                    <p>${data.error || 'Неизвестная ошибка'}</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
        container.innerHTML = `
            <div class="empty-state">
                <h3>Ошибка</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// Create transaction element
function createTransactionElement(tx, isOutgoing) {
    const div = document.createElement('div');
    const isDemo = tx.is_demo || false;
    
    // Для демо-транзакций определяем тип по operation_type
    let transactionType = '';
    let isOutgoingFinal = isOutgoing;
    
    if (isDemo && tx.operation_type) {
        if (tx.operation_type === 'buy') {
            transactionType = 'Покупка';
            isOutgoingFinal = false;
        } else if (tx.operation_type === 'sell') {
            transactionType = 'Продажа';
            isOutgoingFinal = true;
        }
    } else {
        transactionType = isOutgoing ? 'Исходящая' : 'Входящая';
    }
    
    div.className = `transaction-item ${isDemo ? 'demo-transaction' : ''}`;
    
    const date = tx.timestamp ? new Date(tx.timestamp).toLocaleString('ru-RU') : 'Неизвестно';
    const amount = parseFloat(tx.amount_ton || tx.amount || 0);
    const amountUsd = parseFloat(tx.amount_usd || 0);
    const profitUsd = parseFloat(tx.profit_usd || 0);
    
    // Формируем строку с прибылью/убытком для продаж или суммой в USD для покупок
    let profitText = '';
    if (isDemo && tx.operation_type === 'sell') {
        // Для продаж показываем прибыль/убыток (profit_usd)
        if (profitUsd !== undefined && profitUsd !== null) {
            const profitSign = profitUsd >= 0 ? '+' : '';
            const profitClass = profitUsd >= 0 ? 'profit-positive' : 'profit-negative';
            profitText = `<div class="transaction-profit ${profitClass}" style="font-size: 12px; margin-top: 4px;">
                ${profitSign}${profitUsd.toFixed(2)} USD
            </div>`;
        } else if (amountUsd > 0) {
            // Если profit_usd нет, показываем сумму продажи
            profitText = `<div class="transaction-amount-usd" style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">
                ${amountUsd.toFixed(2)} USD
            </div>`;
        }
    } else if ((isDemo && tx.operation_type === 'buy' && amountUsd > 0) || (!isDemo && amountUsd > 0)) {
        // Для покупок и обычных транзакций показываем сумму в USD
        profitText = `<div class="transaction-amount-usd" style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">
            ${amountUsd.toFixed(2)} USD
        </div>`;
    }
    
    div.innerHTML = `
        <div class="transaction-left">
            <div class="transaction-icon ${isOutgoingFinal ? 'outgoing' : 'incoming'} ${isDemo ? 'demo' : ''}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    ${isOutgoingFinal 
                        ? '<path d="M5 12h14M12 5l7 7-7 7"/>'
                        : '<path d="M19 12H5M12 5l-7 7 7 7"/>'
                    }
                </svg>
            </div>
            <div class="transaction-info">
                <div class="transaction-type ${isDemo ? 'demo-type' : ''}">${transactionType}</div>
                <div class="transaction-date">${date}</div>
                <div class="transaction-hash">${tx.tx_hash || 'N/A'}</div>
            </div>
        </div>
        <div class="transaction-amount ${isOutgoingFinal ? 'negative' : 'positive'}">
            ${isOutgoingFinal ? '-' : '+'}${Math.abs(amount).toFixed(9)} TON
            ${profitText}
        </div>
    `;
    
    return div;
}

// Normalize address
function normalizeAddress(addr) {
    if (!addr) return '';
    return addr.toString().trim().toLowerCase();
}

// Load tax for month
async function loadTaxForMonth() {
    const year = document.getElementById('tax-year').value;
    const month = document.getElementById('tax-month').value;
    const resultsDiv = document.getElementById('tax-results');

    if (!year || !month) {
        resultsDiv.innerHTML = `
            <div class="empty-state">
                <h3>Укажите год и месяц</h3>
            </div>
        `;
        return;
    }

    resultsDiv.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><p>Расчет налога...</p></div>';

    try {
        const { response, data } = await api.getTaxForMonth(year, month);

        if (!response.ok) {
            resultsDiv.innerHTML = `
                <div class="empty-state">
                    <h3>Ошибка</h3>
                    <p>${data.error || 'Неизвестная ошибка'}</p>
                </div>
            `;
            return;
        }

        const tax = data;
        resultsDiv.innerHTML = `
            <div class="tax-summary">
                <div class="tax-summary-item">
                    <div class="tax-summary-label">Объем исходящих</div>
                    <div class="tax-summary-value">${(tax.total_sent_ton || 0).toFixed(2)} TON</div>
                    <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">
                        ${(tax.total_sent_usd || 0).toFixed(2)} USD
                    </div>
                </div>
                <div class="tax-summary-item">
                    <div class="tax-summary-label">Транзакций</div>
                    <div class="tax-summary-value">${tax.transactions_count || 0}</div>
                </div>
                <div class="tax-summary-item">
                    <div class="tax-summary-label">Налог к уплате</div>
                    <div class="tax-summary-value" style="color: var(--warning);">
                        ${(tax.total_tax_usd || 0).toFixed(2)} USD
                    </div>
                    <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">
                        ${(tax.total_tax_ton || 0).toFixed(2)} TON
                    </div>
                </div>
            </div>
        `;

        // Update total tax on dashboard
        document.getElementById('total-tax').textContent = 
            `${(tax.total_tax_usd || 0).toFixed(2)} USD`;
    } catch (error) {
        resultsDiv.innerHTML = `
            <div class="empty-state">
                <h3>Ошибка</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// Load tax for all months
async function loadTaxForAllMonths() {
    const startYear = document.getElementById('tax-start-year').value;
    const startMonth = document.getElementById('tax-start-month').value;
    const resultsDiv = document.getElementById('tax-results');

    resultsDiv.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><p>Загрузка...</p></div>';

    try {
        const { response, data } = await api.getTaxForAllMonths(startYear || null, startMonth || null);

        if (!response.ok) {
            resultsDiv.innerHTML = `
                <div class="empty-state">
                    <h3>Ошибка</h3>
                    <p>${data.error || 'Неизвестная ошибка'}</p>
                </div>
            `;
            return;
        }

        const monthly = data.monthly_taxes || [];
        if (monthly.length === 0) {
            resultsDiv.innerHTML = `
                <div class="empty-state">
                    <h3>Нет данных</h3>
                    <p>Нет данных по налогу за выбранный период</p>
                </div>
            `;
            return;
        }

        cachedMonthlyTaxes = monthly;

        let html = '<div style="margin-bottom: 24px;"><h3 style="margin-bottom: 16px;">Помесячный налог</h3><ul style="list-style: none; padding: 0;">';
        monthly.forEach((item, idx) => {
            const y = item.year || '';
            const m = item.month || '';
            const taxTon = item.total_tax_ton || 0;
            const taxUsd = item.total_tax_usd || 0;
            html += `
                <li style="padding: 12px; margin-bottom: 8px; background: var(--surface-elevated); border-radius: 8px; cursor: pointer; transition: all 0.2s;" 
                    onclick="showMonthlyTaxDetail(${idx})" 
                    onmouseover="this.style.background='var(--surface-hover)'" 
                    onmouseout="this.style.background='var(--surface-elevated)'">
                    <strong>${m}.${y}</strong> — налог ${taxUsd.toFixed(2)} USD (${taxTon.toFixed(2)} TON)
                </li>
            `;
        });
        html += '</ul></div>';
        resultsDiv.innerHTML = html;
    } catch (error) {
        resultsDiv.innerHTML = `
            <div class="empty-state">
                <h3>Ошибка</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// Load total tax
async function loadTotalTax() {
    const startYear = document.getElementById('tax-start-year').value;
    const startMonth = document.getElementById('tax-start-month').value;
    const resultsDiv = document.getElementById('tax-results');

    resultsDiv.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><p>Расчет итогового налога...</p></div>';

    try {
        const { response, data } = await api.getTotalTax(startYear || null, startMonth || null);

        if (!response.ok) {
            resultsDiv.innerHTML = `
                <div class="empty-state">
                    <h3>Ошибка</h3>
                    <p>${data.error || 'Неизвестная ошибка'}</p>
                </div>
            `;
            return;
        }

        const tax = data;
        resultsDiv.innerHTML = `
            <div class="tax-summary">
                <div class="tax-summary-item">
                    <div class="tax-summary-label">Общий объем</div>
                    <div class="tax-summary-value">${(tax.total_sent_ton || 0).toFixed(2)} TON</div>
                    <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">
                        ${(tax.total_sent_usd || 0).toFixed(2)} USD
                    </div>
                </div>
                <div class="tax-summary-item">
                    <div class="tax-summary-label">Транзакций</div>
                    <div class="tax-summary-value">${tax.total_transactions || 0}</div>
                </div>
                <div class="tax-summary-item">
                    <div class="tax-summary-label">Итоговый налог</div>
                    <div class="tax-summary-value" style="color: var(--warning); font-size: 28px;">
                        ${(tax.total_tax_usd || 0).toFixed(2)} USD
                    </div>
                    <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">
                        ${(tax.total_tax_ton || tax.total_tax || 0).toFixed(2)} TON
                    </div>
                </div>
            </div>
            <div style="margin-top: 24px; padding: 16px; background: var(--surface-elevated); border-radius: 12px;">
                <div style="font-size: 14px; color: var(--text-secondary);">
                    Курс TON/USD: ${tax.ton_price_usd || '—'}
                </div>
            </div>
        `;
    } catch (error) {
        resultsDiv.innerHTML = `
            <div class="empty-state">
                <h3>Ошибка</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// Show monthly tax detail
function showMonthlyTaxDetail(index) {
    const resultsDiv = document.getElementById('tax-results');
    if (!cachedMonthlyTaxes || !cachedMonthlyTaxes[index]) {
        resultsDiv.innerHTML = `
            <div class="empty-state">
                <h3>Данные не найдены</h3>
            </div>
        `;
        return;
    }

    const item = cachedMonthlyTaxes[index];
    const y = item.year || '';
    const m = item.month || '';

    // Update input fields
    document.getElementById('tax-year').value = y;
    document.getElementById('tax-month').value = m;

    resultsDiv.innerHTML = `
        <div class="tax-summary">
            <div class="tax-summary-item">
                <div class="tax-summary-label">Объем исходящих</div>
                <div class="tax-summary-value">${(item.total_sent_ton || 0).toFixed(2)} TON</div>
                <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">
                    ${(item.total_sent_usd || 0).toFixed(2)} USD
                </div>
            </div>
            <div class="tax-summary-item">
                <div class="tax-summary-label">Транзакций</div>
                <div class="tax-summary-value">${item.transactions_count || 0}</div>
            </div>
            <div class="tax-summary-item">
                <div class="tax-summary-label">Налог к уплате</div>
                <div class="tax-summary-value" style="color: var(--warning);">
                    ${(item.total_tax_usd || 0).toFixed(2)} USD
                </div>
                <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">
                    ${(item.total_tax_ton || 0).toFixed(2)} TON
                </div>
            </div>
        </div>
    `;
}

// Auth tabs switching
document.addEventListener('DOMContentLoaded', () => {
    const authTabs = document.querySelectorAll('.auth-tab');
    const authForms = document.querySelectorAll('.auth-form');

    authTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.getAttribute('data-tab');
            
            authTabs.forEach(t => t.classList.remove('active'));
            authForms.forEach(f => f.classList.remove('active'));
            
            tab.classList.add('active');
            document.getElementById(`${targetTab}-form`).classList.add('active');
        });
    });

    // Enter key handlers
    document.getElementById('login-password')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleLogin();
    });

    document.getElementById('register-password-confirm')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleRegister();
    });
});

// Initialize app
window.addEventListener('DOMContentLoaded', () => {
    initTonConnect();
    
    // Check auth and initialize router
    checkAuth().then(() => {
        // After auth check, initialize router if we're in main app
        if (document.getElementById('main-app') && !document.getElementById('main-app').classList.contains('hidden')) {
            router.handleRoute();
            
            // Auto-load transactions when on transactions page
            if (router.currentPage === 'transactions' && walletAddress) {
                loadTransactions();
            }
        }
    });
});

// Make functions global
window.handleLogin = handleLogin;
window.handleRegister = handleRegister;
window.handleLogout = handleLogout;
window.connectTonkeeper = connectTonkeeper;
window.disconnectWallet = disconnectWallet;
window.loadBalance = loadBalance;
window.loadTransactions = loadTransactions;
window.loadTaxForMonth = loadTaxForMonth;
window.loadTaxForAllMonths = loadTaxForAllMonths;
window.loadTotalTax = loadTotalTax;
window.showMonthlyTaxDetail = showMonthlyTaxDetail;

