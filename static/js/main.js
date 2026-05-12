// 專利法 AI 刷題助手 - Main JavaScript

// ==================== Authentication Management ====================
// Check current user and display user info
async function checkAuth() {
    try {
        const response = await fetch('/auth/current');
        if (response.ok) {
            const userData = await response.json();
            displayUserInfo(userData);
            return userData;
        } else {
            // Not authenticated, redirect to login
            console.log('Not authenticated');
            return null;
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        return null;
    }
}

// Display user info in header
function displayUserInfo(userData) {
    const displayNameElement = document.getElementById('user-display-name');
    if (displayNameElement && userData) {
        displayNameElement.textContent = userData.display_name || userData.username;
    }
}

// Logout function
async function logout() {
    if (confirm('確定要登出嗎？')) {
        try {
            // Use GET method for logout (simpler)
            window.location.href = '/auth/logout';
        } catch (error) {
            console.error('Logout failed:', error);
            showToast('登出失敗', 'error');
        }
    }
}

// Initialize auth on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    checkAuth();
    
    // Add logout button listener
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
});

// ==================== Language Management ====================
// Get current language from localStorage (default: zh-TW)
function getCurrentLang() {
    return localStorage.getItem('appLang') || 'zh-TW';
}

// Set language and save to localStorage
function setLanguage(lang) {
    localStorage.setItem('appLang', lang);
    updateLanguageButtons(lang);
    // Reload current page to apply language change
    window.location.reload();
}

// Update language toggle buttons state
function updateLanguageButtons(lang) {
    const buttons = document.querySelectorAll('.lang-btn');
    buttons.forEach(btn => {
        if (btn.dataset.lang === lang) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// Initialize language toggle on page load (integrated with auth check)
document.addEventListener('DOMContentLoaded', function() {
    const currentLang = getCurrentLang();
    updateLanguageButtons(currentLang);
    
    // Add click listeners to language buttons
    const langButtons = document.querySelectorAll('.lang-btn');
    langButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const newLang = this.dataset.lang;
            if (newLang !== currentLang) {
                setLanguage(newLang);
            }
        });
    });
});

// ==================== Law Type Management ====================
// Get current law type from session
async function getCurrentLawType() {
    try {
        const response = await fetch('/api/law-types/current');
        if (response.ok) {
            const data = await response.json();
            return data.type;  // Return only the type string
        }
        return 'patent-act'; // Default fallback
    } catch (error) {
        console.error('Failed to get current law type:', error);
        return 'patent-act';
    }
}

// Set law type and reload page
async function setLawType(lawType) {
    try {
        const response = await fetch('/api/law-types/select', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ law_type: lawType })
        });
        
        if (response.ok) {
            const data = await response.json();
            showToast(`已切換到：${data.name_zh}`, 'success');
            
            // Reload page after a short delay to show toast
            setTimeout(() => {
                window.location.reload();
            }, 500);
            return true;
        } else {
            const error = await response.json();
            showToast(error.error || '切換法律類型失敗', 'error');
            return false;
        }
    } catch (error) {
        console.error('Failed to set law type:', error);
        showToast('切換法律類型時發生錯誤', 'error');
        return false;
    }
}

// Update law type selector UI
function updateLawTypeSelector(currentLawType) {
    const selector = document.getElementById('law-type-select');
    if (selector && currentLawType) {
        selector.value = currentLawType;
    }
    
    // Language toggle visibility: only show for patent-act (supports both zh-TW and EN)
    // Hide for patent-examination (only has zh-TW content)
    const langToggle = document.querySelector('.lang-toggle');
    if (langToggle) {
        // Show for patent-act, hide for patent-examination (works on all screen sizes)
        langToggle.style.display = currentLawType === 'patent-act' ? 'flex' : 'none';
    }
}

// Initialize law type selector on page load
document.addEventListener('DOMContentLoaded', async function() {
    // Get and display current law type
    const currentLawType = await getCurrentLawType();
    updateLawTypeSelector(currentLawType);
    
    // Add change listener to law type selector
    const lawTypeSelect = document.getElementById('law-type-select');
    if (lawTypeSelect) {
        lawTypeSelect.addEventListener('change', function() {
            const newLawType = this.value;
            if (newLawType !== currentLawType) {
                setLawType(newLawType);
            }
        });
    }
});

// ==================== Utilities ====================
// Utility: Show toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        left: 50%;
        transform: translateX(-50%);
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
        z-index: 1000;
        animation: slideUp 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideDown 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Utility: Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) return '今天';
    if (days === 1) return '昨天';
    if (days < 7) return `${days} 天前`;
    
    return date.toLocaleDateString('zh-TW', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Utility: API fetch wrapper with error handling
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showToast(error.message || '請求失敗，請稍後再試', 'error');
        throw error;
    }
}

// Local storage helpers
const storage = {
    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch {
            return defaultValue;
        }
    },
    
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('Storage error:', error);
        }
    },
    
    remove(key) {
        localStorage.removeItem(key);
    }
};

// Add CSS animation keyframes
const style = document.createElement('style');
style.textContent = `
    @keyframes slideUp {
        from {
            transform: translateX(-50%) translateY(100%);
            opacity: 0;
        }
        to {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }
    }
    
    @keyframes slideDown {
        from {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }
        to {
            transform: translateX(-50%) translateY(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ==================== Additional Law Type Utilities ====================
// Get available law types
async function getLawTypes() {
    try {
        const response = await fetch('/api/law-types');
        if (response.ok) {
            return await response.json();
        }
        return null;
    } catch (error) {
        console.error('Failed to get law types:', error);
        return null;
    }
}

// Export utilities for use in other scripts
window.appUtils = {
    showToast,
    formatDate,
    apiCall,
    storage,
    // Law type management (NEW)
    getLawTypes,
    getCurrentLawType,
    setLawType
};

console.log('📚 法律 AI 刷題助手已載入（支持多法律類型）');
