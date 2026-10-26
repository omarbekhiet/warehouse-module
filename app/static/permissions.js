// ============================================================
// نظام الصلاحيات
// ============================================================

var PERMISSIONS = {
    ADMIN: {
        label: 'مدير النظام',
        color: '#dc2626',
        screens: ['*']
    },
    ACCOUNTANT: {
        label: 'محاسب',
        color: '#2563eb',
        screens: [
            'index.html', 'accounts.html', 'journal.html', 'clearing.html',
            'financial_reports.html', 'reports.html', 'purchase_invoices.html',
            'sales_invoices.html', 'payments.html', 'customer_receipts.html',
            'settlements.html', 'supplier_balances.html', 'customer_balances.html',
            'supplier_statement.html', 'customer_statement.html',
            'item_movement.html', 'inventory_by_warehouse.html',
            'price_comparison.html', 'supplier_rating.html',
            'cash_boxes.html', 'cash_box_transactions.html',
            'expenses.html', 'expense_categories.html',
            'bank_reconciliation.html', 'cash_box_reports.html', 'branches.html',
            'movements_journal.html', 'trial_balance.html', 'balance_sheet.html',
            'income_statement.html', 'cash_flow.html', 'audit_entries.html',
            'data_io.html', 'settings_accounting.html', 'settings_cash.html'
        ]
    },
    CASHIER: {
        label: 'أمين صندوق',
        color: '#f59e0b',
        screens: [
            'index.html', 'cash_boxes.html', 'cash_box_transactions.html',
            'cash_box_reports.html', 'payments.html', 'customer_receipts.html',
            'payment_methods.html', 'expenses.html', 'expense_categories.html',
            'bank_reconciliation.html', 'settlements.html', 'branches.html'
        ]
    },
    STOREKEEPER: {
        label: 'أمين مخزن',
        color: '#16a34a',
        screens: [
            'index.html', 'warehouses.html', 'items.html', 'item_groups.html',
            'uom.html', 'item_movement.html', 'receipts.html', 'issues.html',
            'transfers.html', 'counts.html', 'material_requests.html',
            'stock_adjustments.html', 'inventory_by_warehouse.html',
            'reports.html', 'adjustments_report.html', 'batches_report.html'
        ]
    },
    
    SALES: {
        label: 'مبيعات',
        color: '#ec4899',
        screens: [
            'index.html', 'customers.html', 'customer_balances.html',
            'customer_statement.html', 'sales_invoices.html',
            'sales_returns.html', 'customer_receipts.html', 'items.html',
            'reports.html', 'price_comparison.html'
        ]
    },
    VIEWER: {
        label: 'مشاهدة فقط',
        color: '#64748b',
        screens: [
            'index.html', 'reports.html', 'financial_reports.html',
            'inventory_by_warehouse.html'
        ]
    }
};

// ============================================================
// الدوال المساعدة
// ============================================================

function getUserRole() {
    return localStorage.getItem('user_role') || 'VIEWER';
}

function getUserName() {
    return localStorage.getItem('user_name') || 'مستخدم';
}

function setUserInfo(role, name, permissions) {
    localStorage.setItem('user_role', role);
    localStorage.setItem('user_name', name);
    if (permissions) {
        localStorage.setItem('user_permissions', JSON.stringify(permissions));
    } else {
        localStorage.removeItem('user_permissions');
    }
}

function clearUserInfo() {
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_name');
    localStorage.removeItem('user_permissions');
    localStorage.removeItem('user_branches');
    localStorage.removeItem('user');
    localStorage.removeItem('token');
}

function canAccess(screenName) {
    if (!screenName) screenName = 'index.html';

    // 1. الصلاحيات المحفوظة (فردية أو حسب الدور)
    var storedPerms = localStorage.getItem('user_permissions');
    if (storedPerms) {
        try {
            var perms = JSON.parse(storedPerms);
            if (Array.isArray(perms) && perms.length > 0) {
                if (perms.indexOf('*') !== -1) return true;
                return perms.indexOf(screenName) !== -1;
            }
        } catch (e) {
            console.error('Error parsing permissions:', e);
        }
    }

    // 2. لو مفيش صلاحيات محفوظة، نرجع للأدوار الافتراضية
    var role = getUserRole();
    var perm = PERMISSIONS[role];
    if (!perm) return false;
    if (perm.screens.indexOf('*') !== -1) return true;
    return perm.screens.indexOf(screenName) !== -1;
}

function checkAccess(screenName) {
    if (!canAccess(screenName)) {
        alert('ليس لديك صلاحية للوصول لهذه الشاشة.\nدورك الحالي: ' + getUserRole());
        window.location.href = 'index.html';
        return false;
    }
    return true;
}

function getRoleLabel(role) {
    return (PERMISSIONS[role] && PERMISSIONS[role].label) || role;
}

function getRoleColor(role) {
    return (PERMISSIONS[role] && PERMISSIONS[role].color) || '#64748b';
}

// ============================================================
// التحقق التلقائي — يشتغل قبل تحميل الصفحة
// ============================================================
(function() {
    if (typeof window === 'undefined') return;

    var skipScreens = ['login.html', 'index.html', 'permissions.js', ''];

    var screenName = window.location.pathname.split('/').pop();
    if (skipScreens.indexOf(screenName) !== -1) return;

    if (!canAccess(screenName)) {
        // إخفاء الصفحة فوراً
        document.documentElement.style.display = 'none';

        // إظهار رسالة، وبعدين توجيه
        setTimeout(function() {
            alert('ليس لديك صلاحية للوصول لهذه الشاشة.\nدورك: ' + getUserRole());
            window.location.replace('index.html');
        }, 50);
    }
})();


// ============================================================
// إضافة X-User-Id تلقائياً لكل الطلبات
// ============================================================
(function() {
    if (typeof window === 'undefined' || !window.fetch) return;

    var originalFetch = window.fetch;

    window.fetch = function(url, options) {
        options = options || {};

        // نضيف X-User-Id في الهيدرز
        options.headers = options.headers || {};
        var userId = localStorage.getItem('user_id') || '1';

        // لو headers كائن عادي
        if (typeof options.headers === 'object' && !(options.headers instanceof Headers)) {
            options.headers['X-User-Id'] = userId;
        } else if (options.headers instanceof Headers) {
            options.headers.set('X-User-Id', userId);
        }

        return originalFetch(url, options);
    };
})();