from app import create_app
app = create_app()
print("=== جميع المسارات المسجلة في السيرفر ===")
for rule in app.url_map.iter_rules():
    if 'income' in str(rule) or 'trial' in str(rule) or 'balance' in str(rule):
        print(f"المسار: {rule} | الدالة: {rule.endpoint}")
