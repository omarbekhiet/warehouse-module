import sqlite3
conn = sqlite3.connect('database/warehouse.db')

# مسح البيانات القديمة (إن وُجدت)
conn.execute("DELETE FROM item_groups")

groups = [
    # ============ المستوى 1 (المجموعات الرئيسية) ============
    (1, 'GRP-RM',    'المواد الخام',          'Raw Materials',    None, 1, '1231', '3111', None,   '1236-01', None,       None),
    (2, 'GRP-PKG',   'مواد التعبئة والتغليف', 'Packaging',        None, 1, '1231', '3112', None,   '1236-01', None,       None),
    (3, 'GRP-WIP',   'الإنتاج تحت التشغيل',   'Work in Progress', None, 1, '1232', '3110', None,   None,      None,       None),
    (4, 'GRP-FG',    'المنتجات التامة',       'Finished Goods',   None, 1, '1233', '3000', '4111', '1236-02', None,       None),
    (5, 'GRP-MER',   'البضاعة التجارية',      'Merchandise',      None, 1, '1234', '3121', '4111', '1236-01', None,       None),
    (6, 'GRP-SUP',   'المستلزمات التشغيلية',  'Operating Supplies',None,1, '1235', '3122', None,   '1236-01', None,       None),
    
    # ============ المستوى 2 (مجموعات فرعية) ============
    # تحت المواد الخام
    (7, 'GRP-RM-MET',  'مواد خام معدنية',      'Metallic Raw Materials', 1, 2, '1231', '3111', None, '1236-01', 'WEIGHTED_AVERAGE', 4),
    (8, 'GRP-RM-PLS',  'مواد خام بلاستيكية',   'Plastic Raw Materials',  1, 2, '1231', '3111', None, '1236-01', 'WEIGHTED_AVERAGE', 4),
    (9, 'GRP-RM-CHM',  'مواد خام كيميائية',    'Chemical Raw Materials', 1, 2, '1231', '3111', None, '1236-01', 'WEIGHTED_AVERAGE', 5),
    
    # تحت مواد التعبئة
    (10, 'GRP-PKG-BOX', 'كراتين وصناديق',       'Cartons & Boxes',       2, 2, '1231', '3112', None, '1236-01', 'FIFO', 1),
    (11, 'GRP-PKG-BAG', 'أكياس وشرائط',         'Bags & Tapes',          2, 2, '1231', '3112', None, '1236-01', 'FIFO', 1),
    
    # تحت المنتجات التامة
    (12, 'GRP-FG-A',   'منتجات خط A',          'Product Line A',        4, 2, '1233', '3000', '4111', '1236-02', 'WEIGHTED_AVERAGE', 1),
    (13, 'GRP-FG-B',   'منتجات خط B',          'Product Line B',        4, 2, '1233', '3000', '4111', '1236-02', 'WEIGHTED_AVERAGE', 1),
    
    # تحت البضاعة التجارية
    (14, 'GRP-MER-ELC','أجهزة إلكترونية',       'Electronics',          5, 2, '1234', '3121', '4111', '1236-01', 'WEIGHTED_AVERAGE', 1),
    (15, 'GRP-MER-COS','مستحضرات تجميل',        'Cosmetics',            5, 2, '1234', '3121', '4111', '1236-01', 'WEIGHTED_AVERAGE', 1),
    
    # تحت المستلزمات
    (16, 'GRP-SUP-SPR','قطع غيار',              'Spare Parts',           6, 2, '1235', '3122', None, '1236-01', 'FIFO', 1),
    (17, 'GRP-SUP-OIL','زيوت وشحوم',            'Oils & Lubricants',     6, 2, '1235', '3122', None, '1236-01', 'FIFO', 5),
    (18, 'GRP-SUP-STA','قرطاسية ومطبوعات',      'Stationery',            6, 2, '1235', '3122', None, '1236-01', 'FIFO', 1),
]

for g in groups:
    conn.execute("""
        INSERT INTO item_groups 
        (id, code, name_ar, name_en, parent_id, level,
         inventory_account, cost_account, revenue_account, clearing_account,
         default_cost_method, default_uom_id, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, g)

conn.commit()
print(f"OK: Inserted {len(groups)} groups")
print()
print("=== Tree ===")
for r in conn.execute("SELECT id, code, name_ar, parent_id, level FROM item_groups ORDER BY id"):
    indent = "  " * (r[4]-1)
    print(f"{indent}{r[1]} | {r[2]}")
conn.close()
