#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نسخة محسنة من السكرابر تدعم قراءة ملف JSON القديم
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
from optimized_scraper import OptimizedScraper, ProductData

class JSONCompatibleScraper(OptimizedScraper):
    """سكرابر محسن يدعم قراءة ملف JSON القديم"""
    
    def __init__(self, concurrency: int = 15, cache_duration: int = 3600, json_file: str = "amz_products.json"):
        super().__init__(concurrency, cache_duration)
        self.json_file = json_file
        self.json_data = {}
        self.json_loaded = False
        
    async def __aenter__(self):
        await super().__aenter__()
        # تحميل ملف JSON القديم إذا كان موجود
        self.load_json_data()
        return self
    
    def load_json_data(self):
        """تحميل بيانات ملف JSON القديم"""
        possible_files = [
            self.json_file,
            "amz_products.json",
            "products.json",
            "amazon_products.json",
            "data.json"
        ]
        
        for file_path in possible_files:
            if os.path.exists(file_path):
                try:
                    print(f"📖 تحميل ملف JSON: {file_path}")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.json_data = json.load(f)
                    
                    print(f"✅ تم تحميل {len(self.json_data):,} منتج من {file_path}")
                    self.json_loaded = True
                    self.json_file = file_path
                    
                    # إحصائيات سريعة
                    sections = {}
                    discounted = 0
                    
                    for asin, product in self.json_data.items():
                        section = product.get('section', 'Unknown')
                        sections[section] = sections.get(section, 0) + 1
                        
                        if product.get('discount_percent', 0) > 0:
                            discounted += 1
                    
                    print(f"📊 الإحصائيات:")
                    print(f"   🏷️ منتجات بخصومات: {discounted:,}")
                    print(f"   📂 عدد الأقسام: {len(sections)}")
                    
                    # عرض أكبر 5 أقسام
                    top_sections = sorted(sections.items(), key=lambda x: x[1], reverse=True)[:5]
                    for section, count in top_sections:
                        print(f"   • {section}: {count:,} منتج")
                    
                    return True
                    
                except Exception as e:
                    print(f"❌ خطأ في تحميل {file_path}: {e}")
                    continue
        
        print("⚠️ لم يتم العثور على ملف JSON صالح")
        return False
    
    def _is_product_in_json(self, asin: str) -> bool:
        """التحقق من وجود المنتج في ملف JSON"""
        return self.json_loaded and asin in self.json_data
    
    def _get_json_product_data(self, asin: str) -> Optional[ProductData]:
        """الحصول على بيانات المنتج من ملف JSON"""
        if not self._is_product_in_json(asin):
            return None
        
        try:
            json_product = self.json_data[asin]
            
            # تحويل البيانات من JSON إلى ProductData
            price = json_product.get('price')
            strike_price = json_product.get('strike_price')
            discount_percent = json_product.get('discount_percent')
            
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
            
            # إنشاء كائن ProductData
            product = ProductData(
                asin=asin,
                name=json_product.get('name', ''),
                url=json_product.get('url', ''),
                img=json_product.get('img', ''),
                section=json_product.get('section', ''),
                price=price,
                strike_price=strike_price,
                discount_percent=discount_percent,
                last_updated=datetime.now()
            )
            
            return product
            
        except Exception as e:
            print(f"❌ خطأ في تحويل بيانات المنتج {asin}: {e}")
            return None
    
    def _is_cached_valid(self, asin: str) -> bool:
        """التحقق من صحة الكاش (مع مراعاة JSON)"""
        # إذا كان المنتج موجود في JSON، استخدمه
        if self._is_product_in_json(asin):
            return False  # دائماً استخدم بيانات JSON الحديثة
        
        # وإلا استخدم منطق الكاش العادي
        return super()._is_cached_valid(asin)
    
    async def scrape_page_optimized(
        self, 
        context,
        section: str, 
        url: str, 
        page_num: int,
        alert_callback: Optional[Callable] = None,
        discount_threshold: float = 30.0
    ) -> int:
        """سكرابة صفحة واحدة مع دعم JSON"""
        
        # تشغيل السكرابة العادية أولاً
        scraped_count = await super().scrape_page_optimized(
            context, section, url, page_num, alert_callback, discount_threshold
        )
        
        # إذا كان لدينا بيانات JSON، نتحقق من المنتجات الإضافية
        if self.json_loaded:
            json_products_added = 0
            
            # البحث في JSON عن منتجات من نفس القسم
            for asin, json_product in self.json_data.items():
                try:
                    # التحقق من القسم
                    if json_product.get('section', '') != section:
                        continue
                    
                    # التحقق من الكاش
                    if self._is_cached_valid(asin):
                        continue
                    
                    # الحصول على بيانات المنتج
                    product = self._get_json_product_data(asin)
                    if not product:
                        continue
                    
                    # إضافة للكاش وقاعدة البيانات
                    self._add_to_cache(asin, product)
                    self.db.add_product(product)
                    
                    # التحقق من التنبيهات
                    if (product.discount_percent and product.discount_percent >= discount_threshold and 
                        product.discount_percent <= 98 and product.price and product.price >= 4):
                        if alert_callback:
                            await alert_callback(product, product.strike_price, 
                                               product.price, product.discount_percent)
                        self.session_stats['alerts_sent'] += 1
                    
                    json_products_added += 1
                    self.session_stats['products_found'] += 1
                    
                    # حد أقصى للمنتجات من JSON في كل صفحة
                    if json_products_added >= 50:
                        break
                        
                except Exception as e:
                    continue
            
            if json_products_added > 0:
                print(f"📦 تم إضافة {json_products_added} منتج من JSON للقسم {section}")
        
        return scraped_count
    
    def save_combined_data(self, output_file: str = "combined_products.json"):
        """حفظ البيانات المدمجة (JSON + قاعدة البيانات)"""
        try:
            # الحصول على البيانات من قاعدة البيانات
            db_stats = self.db.get_stats()
            
            # دمج البيانات
            combined_data = {}
            
            # إضافة بيانات JSON القديمة
            if self.json_loaded:
                combined_data.update(self.json_data)
                print(f"📖 تم إضافة {len(self.json_data):,} منتج من JSON")
            
            # إضافة بيانات جديدة من قاعدة البيانات
            # (هنا يمكن إضافة كود لاستخراج البيانات من SQLite إذا لزم الأمر)
            
            # حفظ البيانات المدمجة
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 تم حفظ البيانات المدمجة في: {output_file}")
            print(f"📊 إجمالي المنتجات: {len(combined_data):,}")
            
            return True
            
        except Exception as e:
            print(f"❌ خطأ في حفظ البيانات المدمجة: {e}")
            return False

# مثال على الاستخدام
async def main():
    """مثال على استخدام السكرابر المتوافق مع JSON"""
    
    categories = {
        'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en",
        'Beauty': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017988031%2Cp_98%3A21909049031&dc&page={}&language=en"
    }
    
    async def alert_callback(product, old_price, new_price, discount):
        print(f"🚨 ALERT: {product.name} - {discount:.1f}% OFF!")
    
    def log_callback(message):
        print(f"📝 {message}")
    
    # استخدام السكرابر المتوافق مع JSON
    async with JSONCompatibleScraper(concurrency=15, json_file="amz_products.json") as scraper:
        
        print(f"\n🎯 بدء السكرابة مع دعم JSON")
        
        for section_name, section_url in categories.items():
            print(f"\n🔍 معالجة القسم: {section_name}")
            
            await scraper.scrape_section_optimized(
                section=section_name,
                base_url=section_url,
                start_page=1,
                end_page=5,  # عدد قليل للاختبار
                alert_callback=alert_callback,
                log_callback=log_callback,
                discount_threshold=25.0
            )
        
        # طباعة الإحصائيات
        stats = scraper.get_performance_stats()
        print(f"\n📊 الإحصائيات النهائية:")
        print(f"   📦 المنتجات المكتشفة: {stats['session']['products_found']}")
        print(f"   ⚡ المنتجات/الثانية: {stats['performance']['products_per_second']:.2f}")
        print(f"   🚨 التنبيهات المرسلة: {stats['session']['alerts_sent']}")
        print(f"   💾 حجم قاعدة البيانات: {stats['database']['total_products']}")
        
        # حفظ البيانات المدمجة
        scraper.save_combined_data("updated_products.json")

if __name__ == "__main__":
    print("🔄 السكرابر المحسن مع دعم JSON")
    print("=" * 40)
    asyncio.run(main())