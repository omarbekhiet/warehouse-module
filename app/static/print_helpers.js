// ============================================
// Print Helpers - دوال مشتركة لطباعة الفواتير
// ============================================

const PRINT_API = 'http://localhost:5000/api/v1';

// ============================================
// 1. تنسيق الأرقام
// ============================================
function fmtNum(n, decimals = 2) {
    if (n === null || n === undefined) return '0.00';
    return parseFloat(n).toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

// ============================================
// 2. تنسيق التاريخ
// ============================================
function fmtDate(d) {
    if (!d) return '—';
    // نتوقع YYYY-MM-DD
    return d;
}

// ============================================
// 3. التفقيط بالعربي (Tafqeet)
// ============================================
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
        if (o === 0) return AR_TENS[t];
        return AR_ONES[o] + ' و' + AR_TENS[t];
    }
    if (n < 1000) {
        const h = Math.floor(n / 100);
        const r = n % 100;
        if (r === 0) return AR_HUNDREDS[h];
        return AR_HUNDREDS[h] + ' و' + arNumber(r);
    }
    if (n < 1000000) {
        const th = Math.floor(n / 1000);
        const r = n % 1000;
        let thText;
        if (th === 1) thText = 'ألف';
        else if (th === 2) thText = 'ألفان';
        else if (th <= 10) thText = arNumber(th) + ' آلاف';
        else thText = arNumber(th) + ' ألف';
        if (r === 0) return thText;
        return thText + ' و' + arNumber(r);
    }
    if (n < 1000000000) {
        const m = Math.floor(n / 1000000);
        const r = n % 1000000;
        let mText;
        if (m === 1) mText = 'مليون';
        else if (m === 2) mText = 'مليونان';
        else if (m <= 10) mText = arNumber(m) + ' ملايين';
        else mText = arNumber(m) + ' مليون';
        if (r === 0) return mText;
        return mText + ' و' + arNumber(r);
    }
    const b = Math.floor(n / 1000000000);
    const r = n % 1000000000;
    let bText = b === 1 ? 'مليار' : (b === 2 ? 'ملياران' : arNumber(b) + ' مليار');
    if (r === 0) return bText;
    return bText + ' و' + arNumber(r);
}

function tafqeet(amount) {
    if (!amount) return 'صفر جنيه';
    const num = parseFloat(amount);
    const intPart = Math.floor(num);
    const fracPart = Math.round((num - intPart) * 100);

    let result = arNumber(intPart);

    // الجنيهات
    if (intPart === 1) result += ' جنيه';
    else if (intPart === 2) result += ' جنيهان';
    else if (intPart >= 3 && intPart <= 10) result += ' جنيهات';
    else if (intPart === 0) result = '';
    else result += ' جنيهًا';

    // القروش
    if (fracPart > 0) {
        if (result) result += ' و';
        result += arNumber(fracPart);
        if (fracPart === 1) result += ' قرش';
        else if (fracPart === 2) result += ' قرشان';
        else if (fracPart >= 3 && fracPart <= 10) result += ' قروش';
        else result += ' قرشًا';
    }

    return result + ' لا غير';
}

// ============================================
// 4. بيانات الشركة (عدّلها لاحقًا)
// ============================================
const COMPANY_INFO = {
    name: 'اسم الشركة',
    name_en: 'Company Name',
    address: 'العنوان - المدينة - الدولة',
    phone: '01000000000',
    email: 'info@company.com',
    tax_number: 'XXX-XXX-XXX',
    commercial_register: 'XXXXX',
    logo_url: '' // اتركه فاضي لو مفيش شعار
};

// ============================================
// 5. معرفة نوع الفاتورة من الـ URL
// ============================================
function getQueryParam(key) {
    return new URLSearchParams(window.location.search).get(key);
}

// ============================================
// 6. طباعة
// ============================================
function printPage() {
    window.print();
}

function closePage() {
    window.close();
}

// ============================================
// 7. حفظ كـ PDF (طباعة من المتصفح)
// ============================================
function savePDF() {
    alert('اختر "حفظ كـ PDF" من نافذة الطباعة');
    setTimeout(() => window.print(), 300);
}