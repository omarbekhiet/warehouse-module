$file = "app\static\permissions.js"
$content = Get-Content $file -Raw -Encoding UTF8

# ضيف في STOREKEEPER
$content = $content -replace "('batches_report\.html')", "`$1,`n            'stock_movements.html'"

# ضيف في ACCOUNTANT
$content = $content -replace "('movements_journal\.html')", "`$1,`n            'stock_movements.html'"

$content | Out-File $file -Encoding UTF8

Write-Host "✅ تم التعديل"
Write-Host ""
Write-Host "التحقق:"
Select-String -Path $file -Pattern "stock_movements"
