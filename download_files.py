#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت لتحميل وإعداد جميع ملفات LAQTA Optimized
"""

import os
import shutil
import zipfile
from pathlib import Path

def create_project_structure():
    """إنشاء هيكل المشروع"""
    
    # إنشاء مجلد المشروع
    project_dir = Path("laqta_optimized")
    project_dir.mkdir(exist_ok=True)
    
    print(f"📁 تم إنشاء مجلد المشروع: {project_dir.absolute()}")
    
    # قائمة الملفات المطلوبة
    files_to_copy = [
        "optimized_scraper.py",
        "integrated_app.py", 
        "telegram_bot.py",
        "requirements.txt",
        "config.json",
        "telegram_config.json",
        "README.md",
        "QUICK_START.md",
        "quick_test.py",
        "setup.py"
    ]
    
    # نسخ الملفات
    current_dir = Path(".")
    copied_files = []
    
    for file_name in files_to_copy:
        source_file = current_dir / file_name
        dest_file = project_dir / file_name
        
        if source_file.exists():
            shutil.copy2(source_file, dest_file)
            copied_files.append(file_name)
            print(f"✅ تم نسخ: {file_name}")
        else:
            print(f"❌ لم يتم العثور على: {file_name}")
    
    # إنشاء ملف batch للتثبيت السريع (Windows)
    batch_content = """@echo off
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
"""
    
    with open(project_dir / "install.bat", "w", encoding="utf-8") as f:
        f.write(batch_content)
    
    # إنشاء ملف shell للتثبيت السريع (Linux/Mac)
    shell_content = """#!/bin/bash
echo "🚀 LAQTA Optimized - التثبيت التلقائي"
echo "====================================="

echo "📦 تثبيت المكتبات المطلوبة..."
pip install -r requirements.txt

echo "🎭 تثبيت Playwright browser..."
playwright install chromium

echo "✅ تم التثبيت بنجاح!"
echo "💡 يمكنك الآن تشغيل:"
echo "   - python quick_test.py (للاختبار)"
echo "   - python integrated_app.py (للواجهة الرسومية)"
"""
    
    install_sh = project_dir / "install.sh"
    with open(install_sh, "w", encoding="utf-8") as f:
        f.write(shell_content)
    
    # جعل الملف قابل للتنفيذ
    install_sh.chmod(0o755)
    
    print(f"\n📊 ملخص العملية:")
    print(f"   📁 مجلد المشروع: {project_dir.absolute()}")
    print(f"   📄 الملفات المنسوخة: {len(copied_files)}")
    print(f"   🔧 ملفات التثبيت: install.bat, install.sh")
    
    return project_dir, copied_files

def create_zip_archive():
    """إنشاء أرشيف ZIP"""
    
    zip_name = "laqta_optimized.zip"
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        
        # إضافة جميع الملفات للأرشيف
        files_to_zip = [
            "optimized_scraper.py",
            "integrated_app.py", 
            "telegram_bot.py",
            "requirements.txt",
            "config.json",
            "telegram_config.json",
            "README.md",
            "QUICK_START.md",
            "quick_test.py",
            "setup.py"
        ]
        
        for file_name in files_to_zip:
            if os.path.exists(file_name):
                zipf.write(file_name)
                print(f"📦 تمت إضافة: {file_name}")
    
    print(f"\n✅ تم إنشاء الأرشيف: {zip_name}")
    print(f"📏 حجم الملف: {os.path.getsize(zip_name) / 1024:.1f} KB")
    
    return zip_name

if __name__ == "__main__":
    print("🎯 LAQTA Optimized - أداة التحميل والإعداد")
    print("=" * 50)
    
    try:
        # إنشاء هيكل المشروع
        project_dir, files = create_project_structure()
        
        # إنشاء أرشيف ZIP
        zip_file = create_zip_archive()
        
        print(f"\n🎉 تمت العملية بنجاح!")
        print(f"📁 المجلد: {project_dir}")
        print(f"📦 الأرشيف: {zip_file}")
        print(f"\n💡 الخطوات التالية:")
        print(f"   1. حمل الملف {zip_file}")
        print(f"   2. فك الضغط في مجلد جديد")
        print(f"   3. شغل install.bat (Windows) أو install.sh (Linux/Mac)")
        print(f"   4. ابدأ بـ python quick_test.py")
        
    except Exception as e:
        print(f"❌ خطأ: {e}")