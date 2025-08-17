@echo off
echo 🚀 LAQTA Optimized - التثبيت التلقائي
echo =====================================

echo 📦 تثبيت المكتبات المطلوبة...
pip install -r requirements.txt

echo 🎭 تثبيت Playwright browser...
playwright install chromium

echo ✅ تم التثبيت بنجاح!
echo 💡 يمكنك الآن تشغيل:
echo    - python quick_test.py (للاختبار)
echo    - python integrated_app.py (للواجهة الرسومية)

pause
