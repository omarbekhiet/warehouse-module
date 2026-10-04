import sqlite3

conn = sqlite3.connect('database/warehouse.db')
cur = conn.cursor()

# حذف الجداول القديمة إن وجدت
cur.execute("DROP TABLE IF EXISTS accounts")
cur.execute("DROP TABLE IF EXISTS account_types")

# ============ جدول أنواع الحسابات ============
cur.execute("""
CREATE TABLE account_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name_ar TEXT NOT NULL,
    name_en TEXT,
    normal_side TEXT NOT NULL,
    statement_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# ============ جدول الحسابات ============
cur.execute("""
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name_ar TEXT NOT NULL,
    name_en TEXT,
    level TEXT NOT NULL,
    parent_code TEXT,
    nature TEXT NOT NULL,
    financial_statement TEXT,
    bs_group TEXT,
    pl_group TEXT,
    is_group INTEGER DEFAULT 0,
    is_leaf INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("CREATE INDEX idx_accounts_code ON accounts(code)")
cur.execute("CREATE INDEX idx_accounts_parent ON accounts(parent_code)")

# ============ أنواع الحسابات ============
types = [
    ('ASSET',     'أصول',        'Assets',       'D', 'BS'),
    ('LIABILITY', 'خصوم',        'Liabilities',  'C', 'BS'),
    ('EQUITY',    'حقوق ملكية',  'Equity',       'C', 'EQ'),
    ('REVENUE',   'إيرادات',     'Revenue',      'C', 'IS'),
    ('EXPENSE',   'مصروفات',     'Expenses',     'D', 'IS'),
    ('COGS',      'تكلفة النشاط','Cost of Sales','D', 'IS'),
    ('TAX',       'ضرائب',       'Taxes',        'D', 'IS'),
]
cur.executemany("INSERT INTO account_types (code, name_ar, name_en, normal_side, statement_type) VALUES (?, ?, ?, ?, ?)", types)
print(f"OK: {len(types)} account types")

# ============ الحسابات ============
accounts = [
    # ===== الأصول =====
    ('1000', 'الأصول', 'ASSETS', 'L1', None, 'D', 'BS', None, None, 1, 0),
    ('1100', 'الأصول غير المتداولة', 'Non-Current Assets', 'L2', '1000', 'D', 'BS', 'NCA', None, 1, 0),
    ('1110', 'الأصول الثابتة', 'Fixed Assets', 'L3', '1100', 'D', 'BS', 'NCA', None, 1, 0),
    ('1111', 'الأراضي', 'Land', 'L4', '1110', 'D', 'BS', 'NCA', None, 0, 1),
    ('1112', 'المباني والإنشاءات', 'Buildings', 'L4', '1110', 'D', 'BS', 'NCA', None, 0, 1),
    ('1113', 'الآلات والمعدات', 'Machinery', 'L4', '1110', 'D', 'BS', 'NCA', None, 0, 1),
    ('1114', 'الأثاث والتجهيزات', 'Furniture', 'L4', '1110', 'D', 'BS', 'NCA', None, 0, 1),
    ('1115', 'أجهزة الحاسب والبرمجيات', 'IT Hardware', 'L4', '1110', 'D', 'BS', 'NCA', None, 0, 1),
    ('1116', 'وسائل النقل', 'Vehicles', 'L4', '1110', 'D', 'BS', 'NCA', None, 0, 1),
    ('1117', 'تحسينات على أصول مستأجرة', 'Leasehold Impr.', 'L4', '1110', 'D', 'BS', 'NCA', None, 0, 1),
    ('1118', 'مشروعات تحت التنفيذ', 'Capital WIP', 'L4', '1110', 'D', 'BS', 'NCA', None, 0, 1),
    ('1120', 'الأصول غير الملموسة', 'Intangible Assets', 'L3', '1100', 'D', 'BS', 'NCA', None, 1, 0),
    ('1121', 'الشهرة', 'Goodwill', 'L4', '1120', 'D', 'BS', 'NCA', None, 0, 1),
    ('1122', 'العلامات التجارية', 'Trademarks', 'L4', '1120', 'D', 'BS', 'NCA', None, 0, 1),
    ('1123', 'حقوق الملكية الفكرية', 'IP', 'L4', '1120', 'D', 'BS', 'NCA', None, 0, 1),
    ('1124', 'براءات الاختراع', 'Patents', 'L4', '1120', 'D', 'BS', 'NCA', None, 0, 1),
    ('1130', 'مجمع الإهلاك', 'Accum. Depreciation', 'L3', '1100', 'CC', 'BS', 'NCA', None, 1, 0),
    ('1131', 'مجمع إهلاك المباني', 'Acc.Dep.Buildings', 'L4', '1130', 'CC', 'BS', 'NCA', None, 0, 1),
    ('1132', 'مجمع إهلاك الآلات', 'Acc.Dep.Machinery', 'L4', '1130', 'CC', 'BS', 'NCA', None, 0, 1),
    ('1133', 'مجمع إهلاك الأثاث', 'Acc.Dep.Furniture', 'L4', '1130', 'CC', 'BS', 'NCA', None, 0, 1),
    ('1134', 'مجمع إهلاك السيارات', 'Acc.Dep.Vehicles', 'L4', '1130', 'CC', 'BS', 'NCA', None, 0, 1),
    ('1200', 'الأصول المتداولة', 'Current Assets', 'L2', '1000', 'D', 'BS', 'CA', None, 1, 0),
    ('1210', 'النقدية وما يعادلها', 'Cash & Equiv.', 'L3', '1200', 'D', 'BS', 'CA', None, 1, 0),
    ('1211', 'النقدية بالصندوق', 'Cash on Hand', 'L4', '1210', 'D', 'BS', 'CA', None, 0, 1),
    ('1212', 'النقدية بالبنوك', 'Cash at Banks', 'L4', '1210', 'D', 'BS', 'CA', None, 0, 1),
    ('1213', 'استثمارات قصيرة الأجل', 'ST Investments', 'L4', '1210', 'D', 'BS', 'CA', None, 0, 1),
    ('1220', 'الذمم المدينة التجارية', 'Trade Receivables', 'L3', '1200', 'D', 'BS', 'CA', None, 1, 0),
    ('1221', 'ذمم العملاء', 'Customer Receivables', 'L4', '1220', 'D', 'BS', 'CA', None, 0, 1),
    ('1222', 'أوراق القبض', 'Notes Receivable', 'L4', '1220', 'D', 'BS', 'CA', None, 0, 1),
    ('1223', 'ذمم شركات مرتبطة', 'Related Party Rec.', 'L4', '1220', 'D', 'BS', 'CA', None, 0, 1),
    ('1229', '(-) مخصص الديون المشكوك فيها', 'Allowance Doubtful', 'L4', '1220', 'CC', 'BS', 'CA', None, 0, 1),
    ('1230', 'المخزون', 'Inventory', 'L3', '1200', 'D', 'BS', 'CA', None, 1, 0),
    ('1231', 'مواد خام', 'Raw Materials', 'L4', '1230', 'D', 'BS', 'CA', None, 0, 1),
    ('1232', 'إنتاج تحت التشغيل', 'WIP', 'L4', '1230', 'D', 'BS', 'CA', None, 0, 1),
    ('1233', 'منتجات تامة', 'Finished Goods', 'L4', '1230', 'D', 'BS', 'CA', None, 0, 1),
    ('1234', 'بضاعة جاهزة للبيع', 'Merchandise', 'L4', '1230', 'D', 'BS', 'CA', None, 0, 1),
    ('1235', 'مستلزمات تشغيلية', 'Operating Supplies', 'L4', '1230', 'D', 'BS', 'CA', None, 0, 1),
    ('1236', 'حسابات مخزنية وسيطة', 'Inv. Clearing', 'L4', '1230', 'C', 'BS', 'CA', None, 1, 0),
    ('1236-01', 'وسيط - استلام بضاعة', 'GRNI', 'L4', '1236', 'C', 'BS', 'CA', None, 0, 1),
    ('1236-02', 'وسيط - تسليم للعملاء', 'GDNI', 'L4', '1236', 'C', 'BS', 'CA', None, 0, 1),
    ('1236-03', 'وسيط - حركات أخرى', 'Other Clearing', 'L4', '1236', 'C', 'BS', 'CA', None, 0, 1),
    ('1240', 'المصروفات المقدمة', 'Prepaid Expenses', 'L3', '1200', 'D', 'BS', 'CA', None, 1, 0),
    ('1241', 'إيجار مقدم', 'Prepaid Rent', 'L4', '1240', 'D', 'BS', 'CA', None, 0, 1),
    ('1242', 'تأمين مقدم', 'Prepaid Insurance', 'L4', '1240', 'D', 'BS', 'CA', None, 0, 1),
    ('1243', 'مصروفات مقدمة أخرى', 'Other Prepaid', 'L4', '1240', 'D', 'BS', 'CA', None, 0, 1),
    ('1250', 'أرصدة مدينة أخرى', 'Other Debits', 'L3', '1200', 'D', 'BS', 'CA', None, 1, 0),
    ('1251', 'ضريبة مدخلات (VAT)', 'VAT Input', 'L4', '1250', 'D', 'BS', 'CA', None, 0, 1),
    ('1252', 'سلف موظفين', 'Employee Advances', 'L4', '1250', 'D', 'BS', 'CA', None, 0, 1),
    ('1253', 'أرصدة مدينة أخرى', 'Other Debits', 'L4', '1250', 'D', 'BS', 'CA', None, 0, 1),
    
    # ===== الخصوم =====
    ('2000', 'الخصوم', 'LIABILITIES', 'L1', None, 'C', 'BS', None, None, 1, 0),
    ('2100', 'الخصوم غير المتداولة', 'Non-Current Liab.', 'L2', '2000', 'C', 'BS', 'NCL', None, 1, 0),
    ('2110', 'القروض طويلة الأجل', 'LT Loans', 'L3', '2100', 'C', 'BS', 'NCL', None, 1, 0),
    ('2111', 'قروض بنكية', 'Bank Loans', 'L4', '2110', 'C', 'BS', 'NCL', None, 0, 1),
    ('2112', 'قروض من جهات أخرى', 'Other Loans', 'L4', '2110', 'C', 'BS', 'NCL', None, 0, 1),
    ('2120', 'المخصصات طويلة الأجل', 'LT Provisions', 'L3', '2100', 'C', 'BS', 'NCL', None, 1, 0),
    ('2121', 'مخصص نهاية الخدمة', 'End-of-Service', 'L4', '2120', 'C', 'BS', 'NCL', None, 0, 1),
    ('2122', 'مخصص ضريبة مؤجلة', 'Deferred Tax', 'L4', '2120', 'C', 'BS', 'NCL', None, 0, 1),
    ('2200', 'الخصوم المتداولة', 'Current Liab.', 'L2', '2000', 'C', 'BS', 'CL', None, 1, 0),
    ('2210', 'الذمم الدائنة التجارية', 'Trade Payables', 'L3', '2200', 'C', 'BS', 'CL', None, 1, 0),
    ('2211', 'ذمم الموردين', 'Supplier Payables', 'L4', '2210', 'C', 'BS', 'CL', None, 0, 1),
    ('2212', 'أوراق الدفع', 'Notes Payable', 'L4', '2210', 'C', 'BS', 'CL', None, 0, 1),
    ('2213', 'ذمم شركات مرتبطة', 'Related Party Pay.', 'L4', '2210', 'C', 'BS', 'CL', None, 0, 1),
    ('2220', 'المصروفات المستحقة', 'Accrued Expenses', 'L3', '2200', 'C', 'BS', 'CL', None, 1, 0),
    ('2221', 'رواتب مستحقة', 'Accrued Salaries', 'L4', '2220', 'C', 'BS', 'CL', None, 0, 1),
    ('2222', 'مصروفات مستحقة أخرى', 'Other Accruals', 'L4', '2220', 'C', 'BS', 'CL', None, 0, 1),
    ('2230', 'الضرائب والتأمينات', 'Taxes & Insurance', 'L3', '2200', 'C', 'BS', 'CL', None, 1, 0),
    ('2231', 'ضريبة مخرجات (VAT)', 'VAT Output', 'L4', '2230', 'C', 'BS', 'CL', None, 0, 1),
    ('2232', 'ضريبة دخل مستحقة', 'Income Tax Payable', 'L4', '2230', 'C', 'BS', 'CL', None, 0, 1),
    ('2233', 'تأمينات اجتماعية', 'Social Insurance', 'L4', '2230', 'C', 'BS', 'CL', None, 0, 1),
    ('2234', 'ضريبة كسب عمل', 'Payroll Tax', 'L4', '2230', 'C', 'BS', 'CL', None, 0, 1),
    ('2240', 'الإيرادات المقدمة والأمانات', 'Deferred Revenue', 'L3', '2200', 'C', 'BS', 'CL', None, 1, 0),
    ('2241', 'إيرادات مقدمة', 'Deferred Revenue', 'L4', '2240', 'C', 'BS', 'CL', None, 0, 1),
    ('2242', 'أمانات وودائع', 'Deposits', 'L4', '2240', 'C', 'BS', 'CL', None, 0, 1),
    ('2250', 'القروض قصيرة الأجل', 'ST Loans', 'L3', '2200', 'C', 'BS', 'CL', None, 1, 0),
    ('2251', 'سحب على المكشوف', 'Bank Overdraft', 'L4', '2250', 'C', 'BS', 'CL', None, 0, 1),
    ('2252', 'قروض قصيرة', 'ST Loans', 'L4', '2250', 'C', 'BS', 'CL', None, 0, 1),
    ('2253', 'الجزء الجاري من القروض', 'Current Portion LT', 'L4', '2250', 'C', 'BS', 'CL', None, 0, 1),
    
    # ===== حقوق الملكية =====
    ('8000', 'حقوق الملكية', 'EQUITY', 'L1', None, 'C', 'EQ', 'EQ', None, 1, 0),
    ('8100', 'رأس المال', 'Capital', 'L2', '8000', 'C', 'EQ', 'EQ', None, 1, 0),
    ('8110', 'رأس المال المدفوع', 'Paid-in Capital', 'L3', '8100', 'C', 'EQ', 'EQ', None, 1, 0),
    ('8111', 'رأس المال', 'Capital', 'L4', '8110', 'C', 'EQ', 'EQ', None, 0, 1),
    ('8120', 'رأس المال الاحتياطي', 'Reserve Capital', 'L3', '8100', 'C', 'EQ', 'EQ', None, 1, 0),
    ('8121', 'رأس مال احتياطي', 'Reserve Capital', 'L4', '8120', 'C', 'EQ', 'EQ', None, 0, 1),
    ('8200', 'الاحتياطيات', 'Reserves', 'L2', '8000', 'C', 'EQ', 'EQ', None, 1, 0),
    ('8210', 'الاحتياطي القانوني', 'Legal Reserve', 'L3', '8200', 'C', 'EQ', 'EQ', None, 1, 0),
    ('8211', 'احتياطي قانوني', 'Legal Reserve', 'L4', '8210', 'C', 'EQ', 'EQ', None, 0, 1),
    ('8220', 'احتياطيات أخرى', 'Other Reserves', 'L3', '8200', 'C', 'EQ', 'EQ', None, 1, 0),
    ('8221', 'احتياطيات أخرى', 'Other Reserves', 'L4', '8220', 'C', 'EQ', 'EQ', None, 0, 1),
    ('8300', 'الأرباح المحتجزة', 'Retained Earnings', 'L2', '8000', 'C', 'EQ', 'EQ', None, 1, 0),
    ('8310', 'أرباح مرحّلة', 'Retained Earnings b/f', 'L3', '8300', 'C', 'EQ', 'EQ', None, 1, 0),
    ('8311', 'أرباح مرحّلة', 'Retained Earnings b/f', 'L4', '8310', 'C', 'EQ', 'EQ', None, 0, 1),
    ('8320', 'أرباح السنة', 'Current Year Profit', 'L3', '8300', 'C', 'EQ', 'EQ', None, 1, 0),
    ('8321', 'أرباح السنة', 'Current Year Profit', 'L4', '8320', 'C', 'EQ', 'EQ', None, 0, 1),
    
    # ===== تكلفة النشاط =====
    ('3000', 'تكلفة النشاط', 'COST OF SALES', 'L1', None, 'D', 'IS', None, 'COGS', 1, 0),
    ('3100', 'تكلفة المواد المباشرة', 'Direct Materials', 'L2', '3000', 'D', 'IS', None, 'Direct Materials', 1, 0),
    ('3110', 'المواد الخام المستخدمة', 'RM Used', 'L3', '3100', 'D', 'IS', None, 'Direct Materials', 1, 0),
    ('3111', 'مواد خام رئيسية', 'Main Raw Materials', 'L4', '3110', 'D', 'IS', None, 'Direct Materials', 0, 1),
    ('3112', 'مواد تعبئة وتغليف', 'Packaging', 'L4', '3110', 'D', 'IS', None, 'Direct Materials', 0, 1),
    ('3120', 'المشتريات', 'Purchases', 'L3', '3100', 'D', 'IS', None, 'Direct Materials', 1, 0),
    ('3121', 'مشتريات بضاعة', 'Merch. Purchases', 'L4', '3120', 'D', 'IS', None, 'Direct Materials', 0, 1),
    ('3122', 'مشتريات مستلزمات', 'Supplies Purchases', 'L4', '3120', 'D', 'IS', None, 'Direct Materials', 0, 1),
    ('3130', 'مردودات وخصومات المشتريات', 'Purchase Returns', 'L3', '3100', 'CC', 'IS', None, 'Direct Materials', 1, 0),
    ('3131', 'مردودات المشتريات', 'Purchase Returns', 'L4', '3130', 'CC', 'IS', None, 'Direct Materials', 0, 1),
    ('3132', 'خصومات المشتريات', 'Purchase Discounts', 'L4', '3130', 'CC', 'IS', None, 'Direct Materials', 0, 1),
    ('3200', 'تكلفة العمالة المباشرة', 'Direct Labor', 'L2', '3000', 'D', 'IS', None, 'Direct Labor', 1, 0),
    ('3210', 'أجور الإنتاج', 'Production Wages', 'L3', '3200', 'D', 'IS', None, 'Direct Labor', 1, 0),
    ('3211', 'أجور عمال الإنتاج', 'Workers Wages', 'L4', '3210', 'D', 'IS', None, 'Direct Labor', 0, 1),
    ('3220', 'المزايا والبدلات', 'Benefits', 'L3', '3200', 'D', 'IS', None, 'Direct Labor', 1, 0),
    ('3221', 'تأمينات العمال', 'Workers Insurance', 'L4', '3220', 'D', 'IS', None, 'Direct Labor', 0, 1),
    ('3300', 'تكاليف صناعية غير مباشرة', 'Mfg Overhead', 'L2', '3000', 'D', 'IS', None, 'Mfg Overhead', 1, 0),
    ('3310', 'تكاليف مرافق المصنع', 'Factory Utilities', 'L3', '3300', 'D', 'IS', None, 'Mfg Overhead', 1, 0),
    ('3311', 'كهرباء المصنع', 'Factory Electricity', 'L4', '3310', 'D', 'IS', None, 'Mfg Overhead', 0, 1),
    ('3320', 'إيجار المصنع', 'Factory Rent', 'L3', '3300', 'D', 'IS', None, 'Mfg Overhead', 1, 0),
    ('3321', 'إيجار المصنع', 'Factory Rent', 'L4', '3320', 'D', 'IS', None, 'Mfg Overhead', 0, 1),
    ('3400', 'تكلفة الخدمات', 'Cost of Services', 'L2', '3000', 'D', 'IS', None, 'Cost of Services', 1, 0),
    ('3410', 'تكلفة الخدمات المباشرة', 'Direct Service Cost', 'L3', '3400', 'D', 'IS', None, 'Cost of Services', 1, 0),
    ('3411', 'تكلفة تنفيذ الخدمة', 'Service Delivery Cost', 'L4', '3410', 'D', 'IS', None, 'Cost of Services', 0, 1),
    
    # ===== الإيرادات =====
    ('4000', 'الإيرادات', 'REVENUES', 'L1', None, 'C', 'IS', None, 'Revenue', 1, 0),
    ('4100', 'الإيرادات التشغيلية', 'Operating Rev.', 'L2', '4000', 'C', 'IS', None, 'Revenue', 1, 0),
    ('4110', 'إيرادات المبيعات', 'Sales Revenue', 'L3', '4100', 'C', 'IS', None, 'Sales Revenue', 1, 0),
    ('4111', 'مبيعات محلية', 'Local Sales', 'L4', '4110', 'C', 'IS', None, 'Sales Revenue', 0, 1),
    ('4112', 'مبيعات تصدير', 'Export Sales', 'L4', '4110', 'C', 'IS', None, 'Sales Revenue', 0, 1),
    ('4120', 'إيرادات الخدمات', 'Service Revenue', 'L3', '4100', 'C', 'IS', None, 'Service Revenue', 1, 0),
    ('4121', 'إيرادات خدمات', 'Service Income', 'L4', '4120', 'C', 'IS', None, 'Service Revenue', 0, 1),
    ('4130', 'مردودات وخصومات المبيعات', 'Sales Returns', 'L3', '4100', 'CC', 'IS', None, 'Sales Returns', 1, 0),
    ('4131', 'مردودات المبيعات', 'Sales Returns', 'L4', '4130', 'CC', 'IS', None, 'Sales Returns', 0, 1),
    ('4132', 'خصومات المبيعات', 'Sales Discounts', 'L4', '4130', 'CC', 'IS', None, 'Sales Returns', 0, 1),
    ('4200', 'إيرادات أخرى', 'Other Income', 'L2', '4000', 'C', 'IS', None, 'Other Income', 1, 0),
    ('4210', 'إيرادات استثمارية', 'Investment Income', 'L3', '4200', 'C', 'IS', None, 'Other Income', 1, 0),
    ('4211', 'أرباح استثمارات', 'Investment Gains', 'L4', '4210', 'C', 'IS', None, 'Other Income', 0, 1),
    ('4220', 'إيرادات إيجارات', 'Rental Income', 'L3', '4200', 'C', 'IS', None, 'Other Income', 1, 0),
    ('4221', 'إيجار عقارات', 'Property Rent', 'L4', '4220', 'C', 'IS', None, 'Other Income', 0, 1),
    ('4230', 'إيرادات متنوعة', 'Misc Income', 'L3', '4200', 'C', 'IS', None, 'Other Income', 1, 0),
    ('4231', 'إيرادات متنوعة', 'Misc Income', 'L4', '4230', 'C', 'IS', None, 'Other Income', 0, 1),
    
    # ===== المصروفات =====
    ('5000', 'المصروفات التشغيلية', 'OPERATING EXPENSES', 'L1', None, 'D', 'IS', None, 'OPEX', 1, 0),
    ('5100', 'الرواتب والأجور', 'Salaries & Wages', 'L2', '5000', 'D', 'IS', None, 'Salaries', 1, 0),
    ('5110', 'رواتب إدارية', 'Admin Salaries', 'L3', '5100', 'D', 'IS', None, 'Salaries', 1, 0),
    ('5111', 'رواتب الإدارة العامة', 'G&A Salaries', 'L4', '5110', 'D', 'IS', None, 'Salaries', 0, 1),
    ('5120', 'مزايا وبدلات', 'Benefits', 'L3', '5100', 'D', 'IS', None, 'Salaries', 1, 0),
    ('5121', 'تأمينات اجتماعية', 'Social Insurance', 'L4', '5120', 'D', 'IS', None, 'Salaries', 0, 1),
    ('5122', 'مكافآت وحوافز', 'Bonuses', 'L4', '5120', 'D', 'IS', None, 'Salaries', 0, 1),
    ('5200', 'الإيجارات والمرافق', 'Rent & Utilities', 'L2', '5000', 'D', 'IS', None, 'Rent & Utilities', 1, 0),
    ('5210', 'الإيجارات', 'Rent', 'L3', '5200', 'D', 'IS', None, 'Rent & Utilities', 1, 0),
    ('5211', 'إيجار المكاتب', 'Office Rent', 'L4', '5210', 'D', 'IS', None, 'Rent & Utilities', 0, 1),
    ('5212', 'إيجار المخازن', 'Warehouse Rent', 'L4', '5210', 'D', 'IS', None, 'Rent & Utilities', 0, 1),
    ('5220', 'المرافق', 'Utilities', 'L3', '5200', 'D', 'IS', None, 'Rent & Utilities', 1, 0),
    ('5221', 'كهرباء', 'Electricity', 'L4', '5220', 'D', 'IS', None, 'Rent & Utilities', 0, 1),
    ('5222', 'مياه', 'Water', 'L4', '5220', 'D', 'IS', None, 'Rent & Utilities', 0, 1),
    ('5223', 'اتصالات وإنترنت', 'Telecom', 'L4', '5220', 'D', 'IS', None, 'Rent & Utilities', 0, 1),
    ('5300', 'الإهلاك والإطفاء', 'Depreciation & Amort.', 'L2', '5000', 'D', 'IS', None, 'D&A', 1, 0),
    ('5310', 'إهلاك الأصول الثابتة', 'Depreciation', 'L3', '5300', 'D', 'IS', None, 'D&A', 1, 0),
    ('5311', 'إهلاك المباني', 'Building Dep.', 'L4', '5310', 'D', 'IS', None, 'D&A', 0, 1),
    ('5312', 'إهلاك الآلات', 'Machinery Dep.', 'L4', '5310', 'D', 'IS', None, 'D&A', 0, 1),
    ('5313', 'إهلاك الأثاث', 'Furniture Dep.', 'L4', '5310', 'D', 'IS', None, 'D&A', 0, 1),
    ('5314', 'إهلاك السيارات', 'Vehicle Dep.', 'L4', '5310', 'D', 'IS', None, 'D&A', 0, 1),
    ('5320', 'إطفاء الأصول غير الملموسة', 'Amortization', 'L3', '5300', 'D', 'IS', None, 'D&A', 1, 0),
    ('5321', 'إطفاء الشهرة', 'Goodwill Amort.', 'L4', '5320', 'D', 'IS', None, 'D&A', 0, 1),
    ('5400', 'التسويق والبيع', 'Marketing & Selling', 'L2', '5000', 'D', 'IS', None, 'Marketing', 1, 0),
    ('5410', 'الإعلان والتسويق', 'Advertising', 'L3', '5400', 'D', 'IS', None, 'Marketing', 1, 0),
    ('5411', 'إعلانات رقمية', 'Digital Advertising', 'L4', '5410', 'D', 'IS', None, 'Marketing', 0, 1),
    ('5412', 'إعلانات مطبوعة', 'Print Advertising', 'L4', '5410', 'D', 'IS', None, 'Marketing', 0, 1),
    ('5420', 'عمولات البيع', 'Sales Commissions', 'L3', '5400', 'D', 'IS', None, 'Marketing', 1, 0),
    ('5421', 'عمولات', 'Commissions', 'L4', '5420', 'D', 'IS', None, 'Marketing', 0, 1),
    ('5500', 'المصروفات العمومية والإدارية', 'G&A', 'L2', '5000', 'D', 'IS', None, 'G&A', 1, 0),
    ('5510', 'الأتعاب المهنية', 'Professional Fees', 'L3', '5500', 'D', 'IS', None, 'G&A', 1, 0),
    ('5511', 'أتعاب قانونية', 'Legal Fees', 'L4', '5510', 'D', 'IS', None, 'G&A', 0, 1),
    ('5512', 'أتعاب مراجعة', 'Audit Fees', 'L4', '5510', 'D', 'IS', None, 'G&A', 0, 1),
    ('5513', 'أتعاب استشارية', 'Consulting Fees', 'L4', '5510', 'D', 'IS', None, 'G&A', 0, 1),
    ('5520', 'الصيانة والإصلاح', 'Repairs & Maint.', 'L3', '5500', 'D', 'IS', None, 'G&A', 1, 0),
    ('5521', 'صيانة المعدات', 'Equipment Maint.', 'L4', '5520', 'D', 'IS', None, 'G&A', 0, 1),
    ('5522', 'صيانة المباني', 'Building Maint.', 'L4', '5520', 'D', 'IS', None, 'G&A', 0, 1),
    ('5530', 'التأمينات', 'Insurance', 'L3', '5500', 'D', 'IS', None, 'G&A', 1, 0),
    ('5531', 'تأمين الممتلكات', 'Property Insurance', 'L4', '5530', 'D', 'IS', None, 'G&A', 0, 1),
    ('5540', 'السفر والانتقالات', 'Travel', 'L3', '5500', 'D', 'IS', None, 'G&A', 1, 0),
    ('5541', 'سفر', 'Travel', 'L4', '5540', 'D', 'IS', None, 'G&A', 0, 1),
    ('5542', 'انتقالات', 'Transportation', 'L4', '5540', 'D', 'IS', None, 'G&A', 0, 1),
    ('5550', 'التدريب والتطوير', 'Training', 'L3', '5500', 'D', 'IS', None, 'G&A', 1, 0),
    ('5551', 'تدريب الموظفين', 'Employee Training', 'L4', '5550', 'D', 'IS', None, 'G&A', 0, 1),
    ('5560', 'مصروفات متنوعة', 'Misc Expenses', 'L3', '5500', 'D', 'IS', None, 'G&A', 1, 0),
    ('5561', 'قرطاسية ومطبوعات', 'Stationery', 'L4', '5560', 'D', 'IS', None, 'G&A', 0, 1),
    ('5562', 'ضيافة', 'Entertainment', 'L4', '5560', 'D', 'IS', None, 'G&A', 0, 1),
    ('5563', 'مصروفات متنوعة أخرى', 'Other Misc', 'L4', '5560', 'D', 'IS', None, 'G&A', 0, 1),
    
    # ===== تكاليف التمويل =====
    ('6000', 'تكاليف التمويل', 'FINANCE COSTS', 'L1', None, 'D', 'IS', None, 'Finance Cost', 1, 0),
    ('6100', 'فوائد القروض', 'Loan Interest', 'L2', '6000', 'D', 'IS', None, 'Finance Cost', 1, 0),
    ('6110', 'فوائد قروض طويلة الأجل', 'LT Loan Interest', 'L3', '6100', 'D', 'IS', None, 'Finance Cost', 1, 0),
    ('6111', 'فوائد قروض بنكية', 'Bank Loan Interest', 'L4', '6110', 'D', 'IS', None, 'Finance Cost', 0, 1),
    ('6120', 'فوائد قروض قصيرة الأجل', 'ST Loan Interest', 'L3', '6100', 'D', 'IS', None, 'Finance Cost', 1, 0),
    ('6121', 'فوائد سحب على المكشوف', 'Overdraft Interest', 'L4', '6120', 'D', 'IS', None, 'Finance Cost', 0, 1),
    ('6200', 'عمولات ومصاريف بنكية', 'Bank Charges', 'L2', '6000', 'D', 'IS', None, 'Finance Cost', 1, 0),
    ('6210', 'عمولات بنكية', 'Bank Commissions', 'L3', '6200', 'D', 'IS', None, 'Finance Cost', 1, 0),
    ('6211', 'عمولات بنكية', 'Bank Commissions', 'L4', '6210', 'D', 'IS', None, 'Finance Cost', 0, 1),
    ('6300', 'فروق عملة', 'FX Differences', 'L2', '6000', 'D', 'IS', None, 'Finance Cost', 1, 0),
    ('6310', 'خسائر فروق عملة', 'FX Losses', 'L3', '6300', 'D', 'IS', None, 'Finance Cost', 1, 0),
    ('6311', 'خسائر فروق عملة', 'FX Losses', 'L4', '6310', 'D', 'IS', None, 'Finance Cost', 0, 1),
    
    # ===== ضريبة الدخل =====
    ('7000', 'ضريبة الدخل', 'INCOME TAX', 'L1', None, 'D', 'IS', None, 'Income Tax', 1, 0),
    ('7100', 'ضريبة الدخل الحالية', 'Current Income Tax', 'L2', '7000', 'D', 'IS', None, 'Income Tax', 1, 0),
    ('7110', 'ضريبة دخل السنة', 'Annual Income Tax', 'L3', '7100', 'D', 'IS', None, 'Income Tax', 1, 0),
    ('7111', 'ضريبة الدخل', 'Income Tax', 'L4', '7110', 'D', 'IS', None, 'Income Tax', 0, 1),
    ('7200', 'ضريبة مؤجلة', 'Deferred Income Tax', 'L2', '7000', 'D', 'IS', None, 'Income Tax', 1, 0),
    ('7210', 'ضريبة مؤجلة', 'Deferred Tax', 'L3', '7200', 'D', 'IS', None, 'Income Tax', 1, 0),
    ('7211', 'ضريبة مؤجلة', 'Deferred Tax', 'L4', '7210', 'D', 'IS', None, 'Income Tax', 0, 1),
]

for a in accounts:
    cur.execute("""
        INSERT INTO accounts
        (code, name_ar, name_en, level, parent_code, nature, financial_statement,
         bs_group, pl_group, is_group, is_leaf, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, a)

conn.commit()

# إحصائيات
cur.execute("SELECT COUNT(*) FROM accounts")
n = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM accounts WHERE is_leaf=1")
n_leaf = cur.fetchone()[0]

print(f"OK: {len(types)} account types")
print(f"OK: {n} accounts")
print(f"OK: {n_leaf} leaf accounts (قابلة للترحيل)")
conn.close()
print()
print("Done!")
