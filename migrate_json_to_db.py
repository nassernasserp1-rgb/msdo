#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
أداة تحويل ملف JSON القديم إلى قاعدة بيانات SQLite الجديدة
"""

import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path
import sys

def create_optimized_database(db_path="products_optimized.db"):
    """إنشاء قاعدة البيانات المحسنة"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # إنشاء جدول المنتجات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            asin TEXT PRIMARY KEY,
            name TEXT,
            url TEXT,
            img TEXT,
            section TEXT,
            price REAL,
            strike_price REAL,
            discount_percent REAL,
            last_updated TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # إنشاء جدول تاريخ الأسعار
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asin TEXT,
            price REAL,
            date TEXT,
            time TEXT,
            FOREIGN KEY (asin) REFERENCES products (asin)
        )
    ''')
    
    # إنشاء الفهارس
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_asin ON products(asin)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_section ON products(section)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_discount ON products(discount_percent)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_history_asin ON price_history(asin)')
    
    conn.commit()
    conn.close()
    print(f"✅ تم إنشاء قاعدة البيانات: {db_path}")

def migrate_json_to_sqlite(json_file_path, db_path="products_optimized.db"):
    """تحويل ملف JSON إلى قاعدة بيانات SQLite"""
    
    if not os.path.exists(json_file_path):
        print(f"❌ لم يتم العثور على الملف: {json_file_path}")
        return False
    
    print(f"📖 قراءة ملف JSON: {json_file_path}")
    
    try:
        # قراءة ملف JSON
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📊 تم العثور على {len(data)} منتج في الملف")
        
        # إنشاء قاعدة البيانات
        create_optimized_database(db_path)
        
        # الاتصال بقاعدة البيانات
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # إحصائيات التحويل
        converted_products = 0
        converted_history = 0
        errors = 0
        
        current_time = datetime.now().isoformat()
        
        print("🔄 بدء عملية التحويل...")
        
        for asin, product_data in data.items():
            try:
                # استخراج البيانات الأساسية
                name = product_data.get('name', '')
                url = product_data.get('url', '')
                img = product_data.get('img', '')
                section = product_data.get('section', '')
                price = product_data.get('price')
                strike_price = product_data.get('strike_price')
                discount_percent = product_data.get('discount_percent')
                
                # تحويل الأسعار للأرقام
                if price is not None:
                    try:
                        price = float(price)
                    except (ValueError, TypeError):
                        price = None
                
                if strike_price is not None:
                    try:
                        strike_price = float(strike_price)
                    except (ValueError, TypeError):
                        strike_price = None
                
                if discount_percent is not None:
                    try:
                        discount_percent = float(discount_percent)
                    except (ValueError, TypeError):
                        discount_percent = None
                
                # إدراج المنتج في قاعدة البيانات
                cursor.execute('''
                    INSERT OR REPLACE INTO products 
                    (asin, name, url, img, section, price, strike_price, discount_percent, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (asin, name, url, img, section, price, strike_price, discount_percent, current_time))
                
                converted_products += 1
                
                # تحويل تاريخ الأسعار إذا كان موجود
                price_history = product_data.get('price_history', [])
                if isinstance(price_history, list):
                    for history_entry in price_history:
                        try:
                            hist_date = history_entry.get('date', '')
                            hist_time = history_entry.get('time', '')
                            hist_price = history_entry.get('price')
                            
                            if hist_price is not None:
                                try:
                                    hist_price = float(hist_price)
                                except (ValueError, TypeError):
                                    continue
                                
                                cursor.execute('''
                                    INSERT INTO price_history (asin, price, date, time)
                                    VALUES (?, ?, ?, ?)
                                ''', (asin, hist_price, hist_date, hist_time))
                                
                                converted_history += 1
                        except Exception as e:
                            print(f"⚠️ خطأ في تاريخ السعر للمنتج {asin}: {e}")
                
                # عرض التقدم كل 1000 منتج
                if converted_products % 1000 == 0:
                    print(f"📊 تم تحويل {converted_products} منتج...")
                    
            except Exception as e:
                errors += 1
                print(f"❌ خطأ في المنتج {asin}: {e}")
                continue
        
        # حفظ التغييرات
        conn.commit()
        conn.close()
        
        # عرض النتائج
        print(f"\n🎉 تمت عملية التحويل بنجاح!")
        print(f"📊 الإحصائيات:")
        print(f"   ✅ المنتجات المحولة: {converted_products:,}")
        print(f"   📈 سجلات الأسعار: {converted_history:,}")
        print(f"   ❌ الأخطاء: {errors}")
        print(f"   💾 قاعدة البيانات: {db_path}")
        
        # حساب حجم قاعدة البيانات
        db_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
        print(f"   📏 حجم قاعدة البيانات: {db_size:.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في قراءة ملف JSON: {e}")
        return False

def verify_migration(db_path="products_optimized.db"):
    """التحقق من نجاح عملية التحويل"""
    
    if not os.path.exists(db_path):
        print(f"❌ قاعدة البيانات غير موجودة: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # عدد المنتجات
    cursor.execute('SELECT COUNT(*) FROM products')
    products_count = cursor.fetchone()[0]
    
    # عدد سجلات الأسعار
    cursor.execute('SELECT COUNT(*) FROM price_history')
    history_count = cursor.fetchone()[0]
    
    # المنتجات مع الخصومات
    cursor.execute('SELECT COUNT(*) FROM products WHERE discount_percent IS NOT NULL AND discount_percent > 0')
    discounted_count = cursor.fetchone()[0]
    
    # الأقسام المختلفة
    cursor.execute('SELECT section, COUNT(*) FROM products GROUP BY section ORDER BY COUNT(*) DESC')
    sections = cursor.fetchall()
    
    conn.close()
    
    print(f"\n📊 إحصائيات قاعدة البيانات:")
    print(f"   📦 إجمالي المنتجات: {products_count:,}")
    print(f"   📈 سجلات الأسعار: {history_count:,}")
    print(f"   🏷️ منتجات بخصومات: {discounted_count:,}")
    print(f"\n📂 توزيع الأقسام:")
    
    for section, count in sections[:10]:  # أول 10 أقسام
        section_name = section if section else "غير محدد"
        print(f"   • {section_name}: {count:,} منتج")
    
    return True

def main():
    """الدالة الرئيسية"""
    
    print("🔄 أداة تحويل ملف JSON إلى قاعدة البيانات المحسنة")
    print("=" * 60)
    
    # البحث عن ملفات JSON المحتملة
    possible_files = [
        "amz_products.json",
        "products.json", 
        "amazon_products.json",
        "data.json"
    ]
    
    json_file = None
    
    # البحث التلقائي عن ملف JSON
    for file_name in possible_files:
        if os.path.exists(file_name):
            json_file = file_name
            break
    
    # إذا لم يتم العثور على ملف، اطلب من المستخدم
    if not json_file:
        print("🔍 لم يتم العثور على ملف JSON تلقائياً")
        print("📁 الملفات المتوقعة:", ", ".join(possible_files))
        
        if len(sys.argv) > 1:
            json_file = sys.argv[1]
        else:
            json_file = input("📝 أدخل مسار ملف JSON: ").strip()
    
    if not json_file:
        print("❌ لم يتم تحديد ملف JSON")
        return
    
    print(f"📂 سيتم تحويل الملف: {json_file}")
    
    # تأكيد العملية
    response = input("هل تريد المتابعة؟ (y/n): ").strip().lower()
    if response not in ['y', 'yes', 'نعم', 'ن']:
        print("❌ تم إلغاء العملية")
        return
    
    # تحديد اسم قاعدة البيانات
    db_name = "products_optimized.db"
    
    # إنشاء نسخة احتياطية إذا كانت قاعدة البيانات موجودة
    if os.path.exists(db_name):
        backup_name = f"products_optimized_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        os.rename(db_name, backup_name)
        print(f"💾 تم إنشاء نسخة احتياطية: {backup_name}")
    
    # تحويل البيانات
    success = migrate_json_to_sqlite(json_file, db_name)
    
    if success:
        # التحقق من النتائج
        verify_migration(db_name)
        
        print(f"\n✅ تمت العملية بنجاح!")
        print(f"💡 يمكنك الآن استخدام السكرابر المحسن:")
        print(f"   python quick_test.py")
        print(f"   python integrated_app.py")
        
    else:
        print(f"\n❌ فشلت عملية التحويل")

if __name__ == "__main__":
    main()