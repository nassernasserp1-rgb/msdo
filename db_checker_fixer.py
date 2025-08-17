#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
أداة فحص وإصلاح قاعدة البيانات
"""

import sqlite3
import os
import json
from datetime import datetime

def check_database_status():
    """فحص حالة قاعدة البيانات"""
    
    print("🔍 فحص حالة قواعد البيانات...")
    print("=" * 50)
    
    # قواعد البيانات المحتملة
    db_files = [
        "products_optimized.db",
        "products_instant.db", 
        "amz_products.db",
        "products.db"
    ]
    
    found_databases = []
    
    for db_file in db_files:
        if os.path.exists(db_file):
            try:
                # فحص قاعدة البيانات
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                # التحقق من وجود جدول المنتجات
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
                table_exists = cursor.fetchone() is not None
                
                if table_exists:
                    # عدد المنتجات
                    cursor.execute('SELECT COUNT(*) FROM products')
                    product_count = cursor.fetchone()[0]
                    
                    # حجم الملف
                    file_size = os.path.getsize(db_file) / (1024 * 1024)  # MB
                    
                    # آخر تحديث
                    cursor.execute('SELECT MAX(last_updated) FROM products')
                    last_update = cursor.fetchone()[0]
                    
                    found_databases.append({
                        'file': db_file,
                        'products': product_count,
                        'size_mb': file_size,
                        'last_update': last_update
                    })
                    
                    print(f"✅ {db_file}:")
                    print(f"   📦 المنتجات: {product_count:,}")
                    print(f"   📏 الحجم: {file_size:.2f} MB")
                    print(f"   📅 آخر تحديث: {last_update or 'غير محدد'}")
                    print()
                
                conn.close()
                
            except Exception as e:
                print(f"❌ خطأ في فحص {db_file}: {e}")
        else:
            print(f"⚪ {db_file}: غير موجود")
    
    # فحص ملفات JSON
    print("\n📁 فحص ملفات JSON:")
    json_files = [
        "amz_products.json",
        "products.json",
        "amazon_products.json",
        "data.json"
    ]
    
    for json_file in json_files:
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                file_size = os.path.getsize(json_file) / (1024 * 1024)
                print(f"✅ {json_file}: {len(data):,} منتج ({file_size:.2f} MB)")
            except Exception as e:
                print(f"❌ خطأ في قراءة {json_file}: {e}")
        else:
            print(f"⚪ {json_file}: غير موجود")
    
    return found_databases

def fix_database_connection():
    """إصلاح اتصال قاعدة البيانات"""
    
    print("\n🔧 إصلاح اتصال قاعدة البيانات...")
    
    # إنشاء قاعدة بيانات جديدة إذا لم تكن موجودة
    db_path = "products_optimized.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # إنشاء الجداول إذا لم تكن موجودة
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
        
        conn.commit()
        
        # اختبار إدراج بيانات تجريبية
        test_asin = "TEST123456"
        cursor.execute('SELECT COUNT(*) FROM products WHERE asin = ?', (test_asin,))
        exists = cursor.fetchone()[0] > 0
        
        if not exists:
            cursor.execute('''
                INSERT INTO products 
                (asin, name, url, img, section, price, strike_price, discount_percent, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (test_asin, "Test Product", "http://test.com", "", "Test", 100.0, 120.0, 16.7, datetime.now().isoformat()))
            
            conn.commit()
            print("✅ تم إدراج بيانات اختبار")
        
        # التحقق من العدد النهائي
        cursor.execute('SELECT COUNT(*) FROM products')
        final_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✅ قاعدة البيانات تعمل بشكل صحيح")
        print(f"📦 العدد الحالي: {final_count:,} منتج")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في إصلاح قاعدة البيانات: {e}")
        return False

def create_test_database_with_sample_data():
    """إنشاء قاعدة بيانات اختبار مع بيانات عينة"""
    
    print("\n🧪 إنشاء قاعدة بيانات اختبار...")
    
    db_path = "products_test.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # إنشاء الجداول
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
        
        # إدراج بيانات عينة
        sample_products = [
            ("B08N5WRWNW", "Echo Dot (4th Gen)", "https://amazon.eg/echo-dot", "", "Electronics", 899.0, 1099.0, 18.2),
            ("B08N5WRXYZ", "Fire TV Stick", "https://amazon.eg/fire-tv", "", "Electronics", 699.0, 899.0, 22.2),
            ("B08N5WRABC", "Kindle Paperwhite", "https://amazon.eg/kindle", "", "Electronics", 1299.0, 1599.0, 18.8),
            ("B08N5WRDEF", "Ring Video Doorbell", "https://amazon.eg/ring", "", "Electronics", 2499.0, 2999.0, 16.7),
            ("B08N5WRGHI", "Blink Mini Camera", "https://amazon.eg/blink", "", "Electronics", 799.0, 999.0, 20.0)
        ]
        
        current_time = datetime.now().isoformat()
        
        for asin, name, url, img, section, price, strike_price, discount in sample_products:
            cursor.execute('''
                INSERT OR REPLACE INTO products 
                (asin, name, url, img, section, price, strike_price, discount_percent, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (asin, name, url, img, section, price, strike_price, discount, current_time))
        
        conn.commit()
        
        # التحقق من النتيجة
        cursor.execute('SELECT COUNT(*) FROM products')
        count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✅ تم إنشاء قاعدة بيانات اختبار: {db_path}")
        print(f"📦 تحتوي على {count} منتج عينة")
        
        return db_path
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء قاعدة البيانات الاختبارية: {e}")
        return None

def test_database_operations():
    """اختبار عمليات قاعدة البيانات"""
    
    print("\n🧪 اختبار عمليات قاعدة البيانات...")
    
    db_path = "products_optimized.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # اختبار الإدراج
        test_asin = f"TEST_{datetime.now().strftime('%H%M%S')}"
        cursor.execute('''
            INSERT OR REPLACE INTO products 
            (asin, name, url, img, section, price, strike_price, discount_percent, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (test_asin, "Test Product", "http://test.com", "", "Test", 100.0, 120.0, 16.7, datetime.now().isoformat()))
        
        # اختبار الاستعلام
        cursor.execute('SELECT COUNT(*) FROM products WHERE asin = ?', (test_asin,))
        inserted = cursor.fetchone()[0] > 0
        
        # اختبار التحديث
        cursor.execute('UPDATE products SET price = ? WHERE asin = ?', (110.0, test_asin))
        
        # اختبار الحذف
        cursor.execute('DELETE FROM products WHERE asin = ?', (test_asin,))
        
        conn.commit()
        conn.close()
        
        if inserted:
            print("✅ جميع عمليات قاعدة البيانات تعمل بشكل صحيح")
            return True
        else:
            print("❌ مشكلة في عمليات قاعدة البيانات")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في اختبار قاعدة البيانات: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    
    print("🔧 أداة فحص وإصلاح قاعدة البيانات")
    print("=" * 50)
    
    # فحص الحالة الحالية
    databases = check_database_status()
    
    if not databases:
        print("\n⚠️ لم يتم العثور على قواعد بيانات صالحة")
        print("🔧 سيتم إنشاء قاعدة بيانات جديدة...")
        
        # إصلاح قاعدة البيانات
        if fix_database_connection():
            print("✅ تم إصلاح قاعدة البيانات بنجاح")
        else:
            print("❌ فشل في إصلاح قاعدة البيانات")
    else:
        print(f"\n✅ تم العثور على {len(databases)} قاعدة بيانات")
        
        # اختبار العمليات
        if test_database_operations():
            print("✅ قاعدة البيانات تعمل بشكل مثالي")
        else:
            print("⚠️ قد تحتاج قاعدة البيانات لإعادة إنشاء")
    
    # إنشاء قاعدة بيانات اختبار
    print("\n" + "="*30)
    choice = input("هل تريد إنشاء قاعدة بيانات اختبار؟ (y/n): ").strip().lower()
    
    if choice in ['y', 'yes', 'نعم', 'ن']:
        test_db = create_test_database_with_sample_data()
        if test_db:
            print(f"🎉 يمكنك الآن اختبار الواجهة مع قاعدة البيانات: {test_db}")
    
    print("\n💡 نصائح:")
    print("1. تأكد من تشغيل الواجهة في نفس المجلد")
    print("2. تحقق من وجود ملف products_optimized.db")
    print("3. استخدم force_save_fix.py لحفظ البيانات المعلقة")

if __name__ == "__main__":
    main()