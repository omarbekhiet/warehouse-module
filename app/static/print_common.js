// ==========================================
// Print Common JS - دوال مشتركة لطباعة المستندات
// ==========================================

const PRINT_API = 'http://localhost:5000/api/v1';

// ==========================================
// COMPANY_INFO — تُحمّل ديناميكيًا من API
// ==========================================
let COMPANY_INFO = {
    name: 'اسم الشركة',
    name_en: 'Company Name',
    address: 'العنوان - المدينة - الدولة',
    phone: '01000000000',
    email: 'info@company.com',
    tax_number: 'XXX-XXX-XXX',
    commercial_register: 'XXXXX',
    logo_url: '',
    currency: 'ج.م',
    footer_note: ''
};

// دالة تحميل بيانات الشركة من API
async function loadCompanyInfo() {
    try {
        const r = await fetch(`${PRINT_API}/settings/company`).then(x => x.json());
        if (r.success && r.data) {
            const d = r.data;
            COMPANY_INFO = {
                name: d.name_ar || 'اسم الشركة',
                name_en: d.name_en || '',
                address: d.address || '',
                city: d.city || '',
                country: d.country || '',
                phone: d.phone || '',
                phone2: d.phone2 || '',
                mobile: d.mobile || '',
                fax: d.fax || '',
                email: d.email || '',
                website: d.website || '',
                tax_number: d.tax_number || '',
                commercial_register: d.commercial_register || '',
                tax_card: d.tax_card || '',
                logo_url: d.logo_url || '',
                stamp_url: d.stamp_url || '',
                signature_url: d.signature_url || '',
                currency: d.currency_symbol || d.currency || 'ج.م',
                currency_name: d.currency_name || 'جنيه مصري',
                footer_note: d.footer_note || '',
                fiscal_year_start: d.fiscal_year_start || '01',
                fiscal_year_end: d.fiscal_year_end || '12',
                show_logo_in_reports: d.show_logo_in_reports !== false,
                show_tax_in_invoices: d.show_tax_in_invoices !== false,
                show_stamp: d.show_stamp === true
            };
        }
    } catch (e) {
        console.warn('تعذّر تحميل بيانات الشركة من الـ API، استخدام القيم الافتراضية', e);
    }
}

// استدعاء تلقائي عند تحميل الصفحة
loadCompanyInfo();

// ==========================================
// تنسيق الأرقام
// ==========================================
function fmtNum(n, decimals = 2) {
    if (n === null || n === undefined || n === '') return '0.00';
    const v = parseFloat(n);
    if (isNaN(v)) return '0.00';
    return v.toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

// ==========================================
// التفقيط بالعربي
// ==========================================
const AR_ONES = ['', 'واحد', 'اثنان', 'ثلاثة', 'أربعة', 'خمسة', 'ستة', 'سبعة', 'ثمانية', 'تسعة',
    'عشرة', 'أحد عشر', 'اثنا عشر', 'ثلاثة عشر', 'أربعة عشر', 'خمسة عشر',
    'ستة عشر', 'سبعة عشر', 'ثمانية عشر', 'تسعة عشر'];
const AR_TENS = ['', '', 'عشرون', 'ثلاثون', 'أربعون', 'خمسون', 'ستون', 'سبعون', 'ثمانون', 'تسعون'];
const AR_HUNDREDS = ['', 'مائة', 'مائتان', 'ثلاثمائة', 'أربعمائة', 'خمسمائة', 'ستمائة', 'سبعمائة', 'ثمانمائة', 'تسعمائة'];

function arNumber(n) {
    n = Math.floor(Math.abs(n));
    if (n === 0) return 'صفر';
    if (n < 20) return AR_ONES[n];
    if (n < 100) {
        const t = Math.floor(n / 10);
        const o = n % 10;
        return o === 0 ? AR_TENS[t] : AR_ONES[o] + ' و' + AR_TENS[t];
    }
    if (n < 1000) {
        const h = Math.floor(n / 100);
        const r = n % 100;
        return r === 0 ? AR_HUNDREDS[h] : AR_HUNDREDS[h] + ' و' + arNumber(r);
    }
    if (n < 1000000) {
        const th = Math.floor(n / 1000);
        const r = n % 1000;
        let t;
        if (th === 1) t = 'ألف';
        else if (th === 2) t = 'ألفان';
        else if (th <= 10) t = arNumber(th) + ' آلاف';
        else t = arNumber(th) + ' ألف';
        return r === 0 ? t : t + ' و' + arNumber(r);
    }
    if (n < 1000000000) {
        const m = Math.floor(n / 1000000);
        const r = n % 1000000;
        let t;
        if (m === 1) t = 'مليون';
        else if (m === 2) t = 'مليونان';
        else if (m <= 10) t = arNumber(m) + ' ملايين';
        else t = arNumber(m) + ' مليون';
        return r === 0 ? t : t + ' و' + arNumber(r);
    }
    const b = Math.floor(n / 1000000000);
    const r = n % 1000000000;
    let t = b === 1 ? 'مليار' : (b === 2 ? 'ملياران' : arNumber(b) + ' مليار');
    return r === 0 ? t : t + ' و' + arNumber(r);
}

function tafqeet(amount) {
    if (!amount) return 'صفر جنيه';
    const num = Math.abs(parseFloat(amount));
    const intPart = Math.floor(num);
    const fracPart = Math.round((num - intPart) * 100);

    let result = '';
    if (intPart > 0) {
        result = arNumber(intPart);
        if (intPart === 1) result += ' جنيه';
        else if (intPart === 2) result += ' جنيهان';
        else if (intPart <= 10) result += ' جنيهات';
        else result += ' جنيهًا';
    }
    if (fracPart > 0) {
        if (result) result += ' و';
        result += arNumber(fracPart);
        if (fracPart === 1) result += ' قرش';
        else if (fracPart === 2) result += ' قرشان';
        else if (fracPart <= 10) result += ' قروش';
        else result += ' قرشًا';
    }
    return (result || 'صفر جنيه') + ' لا غير';
}

// ==========================================
// استخراج query param
// ==========================================
function getQueryParam(key) {
    return new URLSearchParams(window.location.search).get(key);
}

// ==========================================
// أزرار
// ==========================================
function printPage() { window.print(); }
function closePage() { window.close(); }
function savePDF() {
    alert('اختر "حفظ كـ PDF" من نافذة الطباعة');
    setTimeout(() => window.print(), 300);
}

// ==========================================
// Header الشركة
// ==========================================
function renderCompanyHeader() {
    const logoHtml = COMPANY_INFO.logo_url
        ? `<img src="${COMPANY_INFO.logo_url}" alt="logo">`
        : `<i class="bi bi-box-seam"></i>`;

    return `
        <div class="company-info">
            <div class="company-logo">${logoHtml}</div>
            <div>
                <div class="company-name">${COMPANY_INFO.name}</div>
                <div class="company-meta">
                    ${COMPANY_INFO.address}<br>
                    ت: ${COMPANY_INFO.phone} | ${COMPANY_INFO.email}<br>
                    الرقم الضريبي: ${COMPANY_INFO.tax_number}
                </div>
            </div>
        </div>`;
}

// ==========================================
// Toolbar
// ==========================================
function renderToolbar(title) {
    return `
        <div class="print-toolbar">
            <h3><i class="bi bi-file-earmark-text"></i> ${title}</h3>
            <div class="d-flex gap-2">
                <button class="btn btn-primary" onclick="printPage()">
                    <i class="bi bi-printer-fill"></i> طباعة
                </button>
                <button class="btn btn-success" onclick="savePDF()">
                    <i class="bi bi-file-pdf"></i> حفظ PDF
                </button>
                <button class="btn btn-outline-secondary" onclick="closePage()">
                    <i class="bi bi-x-circle"></i> إغلاق
                </button>
            </div>
        </div>`;
}

// ==========================================
// Status ar
// ==========================================
function statusAr(s) {
    const map = {
        'DRAFT': 'مسودة',
        'APPROVED': 'معتمد',
        'POSTED': 'مرحّل',
        'REJECTED': 'مرفوض',
        'PARTIAL': 'استلام جزئي',
        'COMPLETED': 'مكتمل'
    };
    return map[s] || s || '—';
}

// ==========================================
// Page footer
// ==========================================
function renderPageFooter() {
    return `
        <div class="page-footer">
            <div>${COMPANY_INFO.name} - ${COMPANY_INFO.phone}</div>
            <div>طُبعت في: ${new Date().toLocaleDateString('ar-EG')}</div>
        </div>`;
}

// ==========================================
// Signatures
// ==========================================
function renderSignatures(sign1 = 'توقيع المستلم', sign2 = 'توقيع المسؤول') {
    return `
        <div class="signatures">
            <div class="sign-box"><div class="sign-line">${sign1}</div></div>
            <div class="sign-box"><div class="sign-line">${sign2}</div></div>
        </div>`;
}

// ==========================================
// Loading
// ==========================================
function renderLoading(text = 'جاري التحميل...') {
    return `<div class="a4-page"><div class="loading-state"><div class="spinner"></div><div>${text}</div></div></div>`;
}

function renderError(msg) {
    return `<div class="a4-page"><div class="print-alert print-alert-danger"><i class="bi bi-exclamation-triangle"></i> ${msg}</div></div>`;
}

// ==========================================
// رقم الفاتورة من URL (يختصر)
// ==========================================
function getIdFromUrl() {
    const id = getQueryParam('id');
    if (!id) {
        document.getElementById('content').innerHTML = renderError('رقم المستند غير محدد');
        return null;
    }
    return id;
}