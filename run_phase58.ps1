$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
chcp 65001 | Out-Null
Set-Location "E:\all downloads\Pharmacy_ERP"
python backend/phase5_8_full.py 2>&1 | Tee-Object -FilePath "E:\all downloads\Pharmacy_ERP\logs\phase5_8_run.log" -Append
