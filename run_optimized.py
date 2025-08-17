#!/usr/bin/env python3
"""
تشغيل سريع للنسخة المحسنة من LAQTA
"""

import os
import sys
import subprocess

def check_dependencies():
    """التحقق من وجود المكتبات المطلوبة"""
    required_packages = [
        'playwright',
        'aiohttp', 
        'customtkinter',
        'Pillow',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ المكتبات التالية مفقودة:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 لتثبيت المكتبات المطلوبة:")
        print("   pip install -r requirements_optimized.txt")
        print("   playwright install chromium")
        return False
    
    return True

def check_files():
    """التحقق من وجود الملفات المطلوبة"""
    required_files = [
        'optimized_gui.py',
        'optimized_scraper.py',
        'categories.py',
        'telegram_bot.py',
        'telegram_config.json',
        'config.json'
    ]
    
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ الملفات التالية مفقودة:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    return True

def main():
    print("🚀 LAQTA - Amazon Product Hunter (Optimized)")
    print("=" * 50)
    
    # التحقق من المتطلبات
    print("🔍 التحقق من المتطلبات...")
    
    if not check_dependencies():
        sys.exit(1)
    
    if not check_files():
        print("\n❌ يرجى التأكد من وجود جميع الملفات المطلوبة")
        sys.exit(1)
    
    print("✅ جميع المتطلبات متوفرة")
    print("\n🎯 بدء تشغيل النسخة المحسنة...")
    
    try:
        # تشغيل النسخة المحسنة
        subprocess.run([sys.executable, 'optimized_gui.py'], check=True)
    except KeyboardInterrupt:
        print("\n⛔️ تم إيقاف البرنامج بواسطة المستخدم")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ خطأ في تشغيل البرنامج: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()