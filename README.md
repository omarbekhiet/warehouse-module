# 🏢 موديول المخازن - Warehouse Module

نظام متكامل لإدارة المخازن والمحاسبة، مبني بـ **Python / Flask** + **SQLite** + **Bootstrap 5**.

---

## 📁 هيكل المشروع

---

## 🚀 الملفات الأساسية

| الملف | الوظيفة |
|---|---|
| `run.py` | نقطة تشغيل التطبيق — `python run.py` |
| `requirements.txt` | المكتبات المطلوبة (`pip install -r requirements.txt`) |
| `start.bat` | تشغيل السيرفر على Windows (يفعّل venv + يشغل Flask) |
| `run.bat` | تشغيل من الديسكتوب (بيستدعي `loader.vbs`) |
| `loader.html` | شاشة تحميل مع ساعة رملية + عداد تنازلي |
| `loader.vbs` | يشغّل `start.bat` مخفي + يفتح `loader.html` |

---

## 📂 مجلد `app/` (التطبيق)

### 1️⃣ الملفات الأساسية

| الملف | الوظيفة |
|---|---|
| `__init__.py` | إنشاء Flask app + تسجيل Blueprints + Middleware `X-User-Id` |
| `config.py` | إعدادات التطبيق (SECRET_KEY، الداتابيز، إلخ) |
| `database.py` | اتصال SQLite + دوال `query`, `execute`, `transaction` |
| `utils.py` | دوال مساعدة: `json_safe`, `to_decimal`, `get_user_id`, `enrich_with_user` |

### 2️⃣ مجلد `app/routes/` (الـ APIs)

كل ملف فيه Blueprint لـ API معين.

| الملف | الوظيفة | الجداول |
|---|---|---|
| `auth_routes.py` | تسجيل الدخول + إدارة المستخدمين والأدوار | `users`, `roles` |
| `warehouse_routes.py` | المستودعات | `warehouses` |
| `item_routes.py` | الأصناف | `items` |
| `group_routes.py` | مجموعات الأصناف | `item_groups` |
| `uom_routes.py` | وحدات القياس | `units_of_measure` |
| `uom_conversion_routes.py` | تحويلات الوحدات | `uom_conversions` |
| `tier_routes.py` | مستويات الوحدات (MAJOR/MEDIUM/MINOR) | `item_tiers` |
| `supplier_routes.py` | الموردين | `suppliers` |
| `customer_routes.py` | العملاء | `customers` |
| `account_routes.py` | الدليل المحاسبي | `accounts`, `account_types` |
| `purchase_order_routes.py` | أوامر الشراء | `purchase_orders` |
| `purchase_invoice_routes.py` | فواتير الشراء | `purchase_invoices` |
| `purchase_return_routes.py` | مرتجع شراء | `purchase_returns` |
| `requisition_routes.py` | طلبات الاحتياج | `purchase_requisitions` |
| `sales_invoice_routes.py` | فواتير البيع | `sales_invoices` |
| `sales_return_routes.py` | مرتجع بيع | `sales_returns` |
| `receipt_routes.py` | الاستلام | `stock_transactions` |
| `issue_routes.py` | الصرف | `stock_transactions` |
| `transfer_routes.py` | التحويلات | `stock_transactions` |
| `count_routes.py` | الجرد + التسويات | `inventory_counts` |
| `material_request_routes.py` | طلبات الصرف | `material_requests` |
| `payment_routes.py` | المدفوعات + التحصيلات | `supplier_payments`, `customer_receipts` |
| `payment_method_routes.py` | طرق الدفع | `payment_methods` |
| `settlement_routes.py` | التسويات | `settlements` |
| `clearing_routes.py` | الحسابات الوسيطة | `journal_entries` |
| `customer_balance_routes.py` | أرصدة العملاء | `customers` |
| `supplier_balance_routes.py` | أرصدة الموردين | `suppliers` |
| `financial_report_routes.py` | التقارير المالية | `journal_entries` |
| `report_routes.py` | التقارير العامة | متعدد |
| `notification_routes.py` | الإشعارات | `notifications` |
| `settings_routes.py` | الإعدادات | `settings` |
| `export_routes.py` | تصدير البيانات | متعدد |
| `txn_edit_routes.py` | تعديل الحركات | `stock_transactions` |

### 3️⃣ مجلد `app/services/` (منطق الأعمال)

| الملف | الوظيفة |
|---|---|
| `accounting_service.py` | إنشاء القيود المحاسبية |
| `payment_service.py` | معالجة المدفوعات والتحصيلات |
| `settings_service.py` | قراءة وكتابة الإعدادات |
| `valuation_service.py` | تقييم المخزون (FIFO/AVG) |
| `doc_number_service.py` | توليد أرقام المستندات |
| `settlement_service.py` | معالجة التسويات |

### 4️⃣ مجلد `app/static/` (الواجهة)

#### 📌 ملفات مشتركة

| الملف | الوظيفة |
|---|---|
| `style.css` | التنسيق العام لكل الشاشات |
| `permissions.js` | نظام الصلاحيات + `X-User-Id` |
| `print_common.css` | تنسيق الطباعة |
| `print_common.js` | دوال الطباعة |
| `print_helpers.js` | دوال مساعدة للطباعة |
| `company_config.js` | بيانات الشركة |

#### 📌 الشاشات الرئيسية

| الشاشة | الوظيفة |
|---|---|
| `index.html` | لوحة التحكم الرئيسية |
| `login.html` | تسجيل الدخول |
| `notifications.html` | الإشعارات |

#### 📌 البيانات الأساسية

| الشاشة | الوظيفة |
|---|---|
| `warehouses.html` | المستودعات |
| `items.html` | الأصناف |
| `item_groups.html` | مجموعات الأصناف |
| `uom.html` | وحدات القياس |
| `item_movement.html` | حركة الأصناف |
| `suppliers.html` | الموردين |
| `customers.html` | العملاء |
| `accounts.html` | الدليل المحاسبي |

#### 📌 المشتريات

| الشاشة | الوظيفة |
|---|---|
| `requisitions.html` | طلبات الاحتياج |
| `purchase_orders.html` | أوامر الشراء |
| `purchase_invoices.html` | فواتير الشراء |
| `purchase_returns.html` | مرتجع شراء |
| `payments.html` | مدفوعات الموردين |
| `payment_methods.html` | طرق الدفع |
| `settlements.html` | التسويات |
| `receipts.html` | الاستلام |

#### 📌 المبيعات

| الشاشة | الوظيفة |
|---|---|
| `sales_invoices.html` | فواتير البيع |
| `sales_returns.html` | مرتجع بيع |
| `customer_receipts.html` | تحصيلات العملاء |
| `issues.html` | الصرف |

#### 📌 المخازن

| الشاشة | الوظيفة |
|---|---|
| `material_requests.html` | طلبات الصرف |
| `transfers.html` | التحويلات |
| `counts.html` | الجرد |
| `stock_adjustments.html` | التسويات المخزنية |
| `adjustments_report.html` | تقرير التسويات |
| `inventory_by_warehouse.html` | المخزون حسب المستودع |

#### 📌 المحاسبة

| الشاشة | الوظيفة |
|---|---|
| `journal.html` | القيود |
| `clearing.html` | الحسابات الوسيطة |
| `financial_reports.html` | التقارير المالية |

#### 📌 التقارير

| الشاشة | الوظيفة |
|---|---|
| `reports.html` | تقارير المخازن |
| `batches_report.html` | تقارير الدفعات |
| `supplier_rating.html` | تقييم الموردين |
| `price_comparison.html` | مقارنة الأسعار |
| `supplier_balances.html` | أرصدة الموردين |
| `customer_balances.html` | أرصدة العملاء |
| `supplier_statement.html` | كشف حساب مورد |
| `customer_statement.html` | كشف حساب عميل |

#### 📌 الإعدادات

| الشاشة | الوظيفة |
|---|---|
| `settings.html` | إعدادات النظام |
| `settings_company.html` | بيانات الشركة |
| `settings_accounting.html` | الإعدادات المحاسبية |
| `settings_cash.html` | إعدادات النقدية |
| `settings_inventory.html` | إعدادات المخزون |
| `settings_suppliers.html` | إعدادات الموردين |
| `settings_customers.html` | إعدادات العملاء |
| `settings_users.html` | إدارة المستخدمين والصلاحيات |
| `settings_print.html` | إعدادات الطباعة |
| `print_center.html` | مركز الطباعة |

---

## 📂 مجلد `database/`

| الملف | الوظيفة |
|---|---|
| `warehouse.db` | الداتابيز الرئيسية (SQLite) |

### 📊 جداول الداتابيز (41 جدول)

#### 🔐 المستخدمين والصلاحيات
- `users` — المستخدمين
- `roles` — الأدوار

#### 📦 البيانات الأساسية
- `warehouses` — المستودعات
- `items` — الأصناف
- `item_groups` — مجموعات الأصناف
- `item_categories` — تصنيفات الأصناف
- `units_of_measure` — وحدات القياس
- `uom_conversions` — تحويلات الوحدات
- `suppliers` — الموردين
- `customers` — العملاء

#### 🧮 المحاسبة
- `accounts` — الدليل المحاسبي
- `account_types` — أنواع الحسابات
- `journal_entries` — القيود
- `journal_entry_lines` — بنود القيود
- `inventory_account_mappings` — ربط المخزون بالحسابات

#### 🛒 المشتريات
- `purchase_requisitions` — طلبات الاحتياج
- `purchase_requisition_lines` — بنود الطلبات
- `purchase_orders` — أوامر الشراء
- `purchase_order_lines` — بنود الأوامر
- `purchase_invoices` — فواتير الشراء
- `purchase_invoice_lines` — بنود الفواتير
- `purchase_returns` — مرتجع شراء
- `purchase_return_lines` — بنود المرتجع

#### 💰 المبيعات
- `sales_invoices` — فواتير البيع
- `sales_invoice_lines` — بنود الفواتير
- `sales_returns` — مرتجع بيع
- `sales_return_lines` — بنود المرتجع

#### 📦 المخازن
- `stock_transactions` — الحركات المخزنية
- `stock_transaction_lines` — بنود الحركات
- `stock_balances` — أرصدة المخزون
- `cost_layers` — طبقات التكلفة (FIFO)
- `material_requests` — طلبات الصرف
- `material_request_lines` — بنود الطلبات
- `inventory_counts` — الجرد
- `inventory_count_lines` — بنود الجرد

#### 💵 المدفوعات
- `payment_methods` — طرق الدفع
- `supplier_payments` — مدفوعات الموردين
- `customer_receipts` — تحصيلات العملاء
- `payment_allocations` — توزيع المدفوعات
- `settlements` — التسويات
- `cheque_settlements` — تسويات الشيكات
- `card_settlements` — تسويات البطاقات

#### ⚙️ الإعدادات
- `settings` — الإعدادات العامة

---

## 🔑 نظام الصلاحيات

### 1. الأدوار الافتراضية

| الدور | الوصف |
|---|---|
| `ADMIN` | مدير النظام — كل الصلاحيات |
| `ACCOUNTANT` | محاسب — الحركات المالية |
| `CASHIER` | أمين صندوق — الدفعات والتحصيلات |
| `STOREKEEPER` | أمين مخزن — حركات المخزون |
| `SALES` | مبيعات — فواتير البيع والعملاء |
| `VIEWER` | مشاهدة فقط |

### 2. الصلاحيات الفردية

كل مستخدم له `permissions` (JSON array) في جدول `users`.

- لو `permissions` فاضي → يستخدم صلاحيات الدور.
- لو `permissions` فيه شاشات → يستخدمها.

### 3. الفروع

كل مستخدم له `branch_ids` (JSON array) في جدول `users`.

- لو `branch_ids` فاضي → كل الفروع.
- لو فيه IDs → فروع محددة.

### 4. تسجيل المستخدم في الحركات

كل حركة بتسجل `created_by` (user_id):
- `journal_entries` — القيود
- `stock_transactions` — الحركات المخزنية
- `purchase_invoices` — فواتير الشراء
- `sales_invoices` — فواتير البيع
- إلخ.

---

## 🔌 APIs الرئيسية

### المصادقة

| Method | Endpoint | الوظيفة |
|---|---|---|
| `POST` | `/api/v1/auth/login` | تسجيل الدخول |
| `GET` | `/api/v1/auth/users` | كل المستخدمين |
| `POST` | `/api/v1/auth/users` | إضافة مستخدم |
| `PUT` | `/api/v1/auth/users/{id}` | تعديل مستخدم |
| `DELETE` | `/api/v1/auth/users/{id}` | حذف مستخدم |
| `GET` | `/api/v1/auth/roles` | كل الأدوار |
| `POST` | `/api/v1/auth/roles` | إضافة دور |
| `PUT` | `/api/v1/auth/roles/{id}` | تعديل دور |
| `DELETE` | `/api/v1/auth/roles/{id}` | حذف دور |

### البيانات الأساسية

| Method | Endpoint | الوظيفة |
|---|---|---|
| `GET/POST` | `/api/v1/warehouses/` | المستودعات |
| `GET/POST` | `/api/v1/items/` | الأصناف |
| `GET/POST` | `/api/v1/groups/` | مجموعات الأصناف |
| `GET/POST` | `/api/v1/uom/` | وحدات القياس |
| `GET/POST` | `/api/v1/suppliers/` | الموردين |
| `GET/POST` | `/api/v1/customers/` | العملاء |
| `GET/POST` | `/api/v1/accounts/` | الدليل المحاسبي |

### الحركات

| Method | Endpoint | الوظيفة |
|---|---|---|
| `GET/POST` | `/api/v1/purchase-orders/` | أوامر الشراء |
| `GET/POST` | `/api/v1/purchase-invoices/` | فواتير الشراء |
| `GET/POST` | `/api/v1/sales-invoices/` | فواتير البيع |
| `GET/POST` | `/api/v1/purchase-returns/` | مرتجع شراء |
| `GET/POST` | `/api/v1/sales-returns/` | مرتجع بيع |
| `GET/POST` | `/api/v1/receipts/` | الاستلام |
| `GET/POST` | `/api/v1/issues/` | الصرف |
| `GET/POST` | `/api/v1/transfers/` | التحويلات |
| `GET/POST` | `/api/v1/counts/` | الجرد |
| `GET/POST` | `/api/v1/material-requests/` | طلبات الصرف |

### التقارير

| Method | Endpoint | الوظيفة |
|---|---|---|
| `GET` | `/api/v1/reports/journal-entries` | القيود |
| `GET` | `/api/v1/reports/inventory-by-warehouse` | المخزون حسب المستودع |
| `GET` | `/api/v1/financial-reports/trial-balance` | ميزان المراجعة |
| `GET` | `/api/v1/financial-reports/balance-sheet` | الميزانية |
| `GET` | `/api/v1/financial-reports/income-statement` | قائمة الدخل |
| `GET` | `/api/v1/financial-reports/aging/ar` | أعمار AR |
| `GET` | `/api/v1/financial-reports/aging/ap` | أعمار AP |

---

## 🚀 التشغيل

### 1. تشغيل السيرفر

```bash
python run.py


http://localhost:5000/login

3. المستخدم الافتراضي

    Username: admin

    Password: admin123

🛠️ التقنيات المستخدمة
التقنية	الإصدار	الاستخدام
Python	3.10+	لغة البرمجة
Flask	3.x	إطار الويب
SQLite	3.x	الداتابيز
Bootstrap	5.3	التصميم
Bootstrap Icons	1.11	الأيقونات
Chart.js	4.4	الرسوم البيانية
Cairo Font	—	الخط العربي
📝 ملاحظات مهمة

    كل الحركات بتسجل created_by → مين عمل الحركة.

    الصلاحيات تُفحص في كل شاشة → permissions.js.

    X-User-Id بيتبعت في كل طلب → permissions.js.

    enrich_with_user بتضيف اسم المستخدم → app/utils.py.

    النسخ الاحتياطية → بره المشروع (J:\warehouse-module_FULL_BACKUP_*).

📞 الدعم

لو فيه أي مشكلة، راجع:

    app/utils.py — الدوال المساعدة.

    app/__init__.py — Middleware.

    permissions.js — الصلاحيات.

    login.html — حفظ بيانات المستخدم.

آخر تحديث: 6 أكتوبر 2026
text


**احفظ الملف.**

---

## 📌 الخطوة 2: تأكد من الملف

```powershell
Test-Path J:\warehouse-module\README.md




http://localhost:5000/login