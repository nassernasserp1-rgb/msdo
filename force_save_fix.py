#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إصلاح مشكلة عدم حفظ جميع المنتجات في قاعدة البيانات
"""

import sqlite3
import threading
import time
from optimized_scraper import OptimizedDatabase

class FixedOptimizedDatabase(OptimizedDatabase):
    """نسخة محسنة من قاعدة البيانات مع حفظ فوري"""
    
    def __init__(self, db_path: str = "products_optimized.db"):
        self.db_path = db_path
        self.batch_queue = []  # استخدام list بدلاً من queue
        self.batch_size = 100  # حجم أصغر للدفعات
        self.batch_lock = threading.Lock()  # حماية من race conditions
        self.stop_batch = False
        self._init_db()
        
        # تشغيل batch processor كل ثانية
        self.batch_timer = None
        self._start_batch_timer()
    
    def _start_batch_timer(self):
        """بدء مؤقت حفظ الدفعات"""
        if not self.stop_batch:
            self._process_batch()
            self.batch_timer = threading.Timer(1.0, self._start_batch_timer)
            self.batch_timer.daemon = True
            self.batch_timer.start()
    
    def _process_batch(self):
        """معالجة الدفعة الحالية"""
        with self.batch_lock:
            if self.batch_queue:
                batch_to_save = self.batch_queue.copy()
                self.batch_queue.clear()
                self._flush_batch(batch_to_save)
    
    def add_product(self, product):
        """إضافة منتج مع حفظ فوري للدفعات الصغيرة"""
        product_data = (
            product.asin, product.name, product.url, product.img,
            product.section, product.price, product.strike_price,
            product.discount_percent, product.last_updated.isoformat()
        )
        
        with self.batch_lock:
            self.batch_queue.append(product_data)
            
            # حفظ فوري إذا وصلت للحد الأقصى
            if len(self.batch_queue) >= self.batch_size:
                batch_to_save = self.batch_queue.copy()
                self.batch_queue.clear()
                self._flush_batch(batch_to_save)
    
    def force_save(self):
        """حفظ فوري لجميع البيانات المعلقة"""
        with self.batch_lock:
            if self.batch_queue:
                batch_to_save = self.batch_queue.copy()
                self.batch_queue.clear()
                self._flush_batch(batch_to_save)
                print(f"💾 تم حفظ {len(batch_to_save)} منتج معلق")
    
    def close(self):
        """إغلاق قاعدة البيانات مع حفظ جميع البيانات"""
        self.stop_batch = True
        
        if self.batch_timer:
            self.batch_timer.cancel()
        
        # حفظ أي بيانات متبقية
        self.force_save()
        
        print("✅ تم إغلاق قاعدة البيانات وحفظ جميع البيانات")

def fix_database_saving():
    """إصلاح مشكلة حفظ قاعدة البيانات"""
    
    print("🔧 إصلاح مشكلة حفظ قاعدة البيانات...")
    
    # فتح قاعدة البيانات الحالية
    db_path = "products_optimized.db"
    
    if not os.path.exists(db_path):
        print("❌ قاعدة البيانات غير موجودة")
        return
    
    # التحقق من عدد المنتجات المحفوظة
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM products')
    saved_count = cursor.fetchone()[0]
    
    print(f"📊 المنتجات المحفوظة حالياً: {saved_count:,}")
    
    # فرض حفظ أي بيانات معلقة
    try:
        # إنشاء instance جديد من قاعدة البيانات المحسنة
        fixed_db = FixedOptimizedDatabase(db_path)
        fixed_db.force_save()
        fixed_db.close()
        
        # التحقق مرة أخرى
        cursor.execute('SELECT COUNT(*) FROM products')
        new_count = cursor.fetchone()[0]
        
        print(f"📊 المنتجات بعد الإصلاح: {new_count:,}")
        print(f"➕ تم حفظ {new_count - saved_count} منتج إضافي")
        
    except Exception as e:
        print(f"❌ خطأ في الإصلاح: {e}")
    
    finally:
        conn.close()

def monitor_database_realtime():
    """مراقبة قاعدة البيانات في الوقت الفعلي"""
    
    print("👁️ مراقبة قاعدة البيانات في الوقت الفعلي...")
    print("اضغط Ctrl+C للتوقف")
    
    db_path = "products_optimized.db"
    last_count = 0
    
    try:
        while True:
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM products')
                current_count = cursor.fetchone()[0]
                
                if current_count != last_count:
                    added = current_count - last_count
                    print(f"📊 [{time.strftime('%H:%M:%S')}] المنتجات: {current_count:,} (+{added})")
                    last_count = current_count
                
                conn.close()
            
            time.sleep(2)  # فحص كل ثانيتين
            
    except KeyboardInterrupt:
        print("\n✅ تم إيقاف المراقبة")

if __name__ == "__main__":
    import os
    
    print("🔧 أداة إصلاح مشكلة حفظ قاعدة البيانات")
    print("=" * 50)
    
    choice = input("""
اختر العملية:
1. إصلاح قاعدة البيانات الحالية
2. مراقبة قاعدة البيانات في الوقت الفعلي
3. كلاهما

أدخل رقم الخيار (1-3): """).strip()
    
    if choice == "1":
        fix_database_saving()
    elif choice == "2":
        monitor_database_realtime()
    elif choice == "3":
        fix_database_saving()
        print("\n" + "="*30)
        monitor_database_realtime()
    else:
        print("❌ خيار غير صحيح")