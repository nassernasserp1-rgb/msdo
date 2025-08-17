#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام ذكي للعثور على المنتجات الجديدة فقط
"""

import asyncio
import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Set, List, Dict
from playwright.async_api import async_playwright
import random

class SmartNewProductsFinder:
    """باحث ذكي عن المنتجات الجديدة"""
    
    def __init__(self, db_path: str = "products_optimized.db"):
        self.db_path = db_path
        self.existing_asins: Set[str] = set()
        self.new_products_found = 0
        self.total_checked = 0
        self.skip_count = 0
        
        # استراتيجيات البحث الذكي
        self.search_strategies = [
            "newest_first",      # الأحدث أولاً
            "random_pages",      # صفحات عشوائية
            "price_ranges",      # نطاقات سعرية مختلفة
            "date_filters",      # فلاتر تاريخية
            "seller_rotation"    # تنويع البائعين
        ]
        
        self.load_existing_products()
    
    def load_existing_products(self):
        """تحميل المنتجات الموجودة من قاعدة البيانات"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT asin FROM products')
            self.existing_asins = {row[0] for row in cursor.fetchall()}
            
            conn.close()
            print(f"📦 تم تحميل {len(self.existing_asins):,} منتج موجود")
            
        except Exception as e:
            print(f"⚠️ خطأ في تحميل المنتجات الموجودة: {e}")
            self.existing_asins = set()
    
    def is_new_product(self, asin: str) -> bool:
        """التحقق من كون المنتج جديد"""
        return asin not in self.existing_asins
    
    def mark_as_found(self, asin: str):
        """تسجيل المنتج كمنتج تم العثور عليه"""
        self.existing_asins.add(asin)
    
    def generate_smart_urls(self, base_category_url: str, strategy: str = "newest_first") -> List[str]:
        """توليد URLs ذكية للبحث عن المنتجات الجديدة"""
        
        urls = []
        base_url = base_category_url.split('&page=')[0]  # إزالة page parameter
        
        if strategy == "newest_first":
            # ترتيب حسب الأحدث (Amazon's newest arrivals)
            for page in range(1, 21):  # أول 20 صفحة من الأحدث
                url = f"{base_url}&s=date-desc-rank&page={page}"
                urls.append(url)
        
        elif strategy == "random_pages":
            # صفحات عشوائية من مجال واسع
            random_pages = random.sample(range(1, 200), 15)  # 15 صفحة عشوائية
            for page in random_pages:
                url = f"{base_url}&page={page}"
                urls.append(url)
        
        elif strategy == "price_ranges":
            # نطاقات سعرية مختلفة لاكتشاف منتجات جديدة
            price_ranges = [
                (1, 50), (50, 100), (100, 200), (200, 500), 
                (500, 1000), (1000, 2000), (2000, 5000)
            ]
            for min_price, max_price in price_ranges:
                for page in range(1, 6):  # 5 صفحات لكل نطاق سعري
                    url = f"{base_url}&low-price={min_price}&high-price={max_price}&page={page}"
                    urls.append(url)
        
        elif strategy == "date_filters":
            # فلاتر تاريخية (آخر 30 يوم، 90 يوم)
            date_filters = ["last-30", "last-90"]
            for date_filter in date_filters:
                for page in range(1, 11):  # 10 صفحات لكل فلتر
                    url = f"{base_url}&s=date-desc-rank&page={page}"
                    urls.append(url)
        
        elif strategy == "seller_rotation":
            # تنويع البائعين (إزالة قيد البائع أحياناً)
            for page in range(1, 26):  # 25 صفحة بدون قيد بائع
                clean_url = base_url.replace("me=A1ZVRGNO5AYLOV&", "")
                url = f"{clean_url}&page={page}"
                urls.append(url)
        
        return urls
    
    async def scan_page_for_new_products(self, page, url: str) -> List[Dict]:
        """مسح صفحة للبحث عن منتجات جديدة فقط"""
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(1000)
            
            # استخراج معلومات المنتجات
            products_data = await page.evaluate("""
                () => {
                    const items = document.querySelectorAll('div.s-result-item[data-asin][data-component-type="s-search-result"]');
                    const products = [];
                    
                    items.forEach(item => {
                        const asin = item.getAttribute('data-asin');
                        if (!asin) return;
                        
                        const titleEl = item.querySelector('h2 span');
                        const name = titleEl ? titleEl.textContent.trim() : '';
                        
                        const imgEl = item.querySelector('img.s-image');
                        const img = imgEl ? imgEl.src : '';
                        
                        const linkEl = item.querySelector('a.a-link-normal[href*="/dp/"]');
                        const url = linkEl ? 'https://www.amazon.eg' + linkEl.getAttribute('href') : '';
                        
                        const priceEl = item.querySelector('.a-price .a-offscreen');
                        let price = null;
                        if (priceEl) {
                            const priceText = priceEl.textContent;
                            const match = priceText.match(/([0-9,]+)/);
                            price = match ? parseFloat(match[1].replace(/,/g, '')) : null;
                        }
                        
                        const strikeEl = item.querySelector('.a-price.a-text-price .a-offscreen');
                        let strikePrice = null;
                        if (strikeEl) {
                            const strikeText = strikeEl.textContent;
                            const match = strikeText.match(/([0-9,]+)/);
                            strikePrice = match ? parseFloat(match[1].replace(/,/g, '')) : null;
                        }
                        
                        // البحث عن علامات "جديد"
                        const itemText = item.textContent.toLowerCase();
                        const isNewProduct = itemText.includes('new') || itemText.includes('جديد') || 
                                           itemText.includes('latest') || itemText.includes('recent');
                        
                        products.push({
                            asin, name, img, url, price, strikePrice, isNewProduct
                        });
                    });
                    
                    return products;
                }
            """)
            
            # فلترة المنتجات الجديدة فقط
            new_products = []
            for product in products_data:
                self.total_checked += 1
                
                if self.is_new_product(product['asin']):
                    new_products.append(product)
                    self.mark_as_found(product['asin'])
                    self.new_products_found += 1
                else:
                    self.skip_count += 1
            
            return new_products
            
        except Exception as e:
            print(f"❌ خطأ في مسح الصفحة: {e}")
            return []
    
    async def smart_search_new_products(self, category_name: str, category_url: str, 
                                      strategy: str = "newest_first", 
                                      max_pages: int = 50,
                                      stop_if_no_new: int = 5) -> List[Dict]:
        """البحث الذكي عن المنتجات الجديدة"""
        
        print(f"🔍 بدء البحث الذكي في {category_name} - استراتيجية: {strategy}")
        
        all_new_products = []
        pages_without_new = 0
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=[
                '--no-sandbox', '--disable-setuid-sandbox', '--disable-images'
            ])
            context = await browser.new_context()
            page = await context.new_page()
            
            # توليد URLs ذكية
            smart_urls = self.generate_smart_urls(category_url, strategy)
            
            for i, url in enumerate(smart_urls[:max_pages]):
                print(f"📄 مسح صفحة {i+1}/{min(max_pages, len(smart_urls))}: ", end="")
                
                new_products = await self.scan_page_for_new_products(page, url)
                
                if new_products:
                    all_new_products.extend(new_products)
                    pages_without_new = 0
                    print(f"✅ {len(new_products)} منتج جديد")
                else:
                    pages_without_new += 1
                    print("⚪ لا توجد منتجات جديدة")
                
                # إيقاف البحث إذا لم نجد منتجات جديدة لفترة
                if pages_without_new >= stop_if_no_new:
                    print(f"🛑 إيقاف البحث - لم يتم العثور على منتجات جديدة في آخر {stop_if_no_new} صفحات")
                    break
                
                # تأخير عشوائي لتجنب الحظر
                await asyncio.sleep(random.uniform(1, 3))
            
            await browser.close()
        
        return all_new_products
    
    def save_new_products(self, new_products: List[Dict], section: str):
        """حفظ المنتجات الجديدة في قاعدة البيانات"""
        
        if not new_products:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for product in new_products:
                # حساب نسبة الخصم
                discount_percent = 0
                if product['strikePrice'] and product['price']:
                    if product['strikePrice'] > product['price']:
                        discount_percent = ((product['strikePrice'] - product['price']) / product['strikePrice']) * 100
                
                cursor.execute('''
                    INSERT OR REPLACE INTO products 
                    (asin, name, url, img, section, price, strike_price, discount_percent, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    product['asin'], product['name'], product['url'], product['img'],
                    section, product['price'], product['strikePrice'],
                    discount_percent, datetime.now().isoformat()
                ))
            
            conn.commit()
            conn.close()
            
            print(f"💾 تم حفظ {len(new_products)} منتج جديد")
            
        except Exception as e:
            print(f"❌ خطأ في حفظ المنتجات الجديدة: {e}")
    
    def get_search_stats(self) -> Dict:
        """الحصول على إحصائيات البحث"""
        return {
            'total_checked': self.total_checked,
            'new_found': self.new_products_found,
            'skipped_existing': self.skip_count,
            'existing_products': len(self.existing_asins),
            'discovery_rate': (self.new_products_found / self.total_checked * 100) if self.total_checked > 0 else 0
        }

# مثال على الاستخدام
async def test_smart_finder():
    """اختبار الباحث الذكي"""
    
    categories = {
        'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en"
    }
    
    finder = SmartNewProductsFinder()
    
    for category_name, category_url in categories.items():
        print(f"\n🎯 البحث في قسم: {category_name}")
        
        # تجربة استراتيجيات مختلفة
        strategies = ["newest_first", "random_pages", "price_ranges"]
        
        for strategy in strategies:
            print(f"\n📋 الاستراتيجية: {strategy}")
            
            new_products = await finder.smart_search_new_products(
                category_name, category_url, strategy, max_pages=20
            )
            
            if new_products:
                finder.save_new_products(new_products, category_name)
            
            # طباعة الإحصائيات
            stats = finder.get_search_stats()
            print(f"📊 الإحصائيات:")
            print(f"   🔍 تم فحص: {stats['total_checked']} منتج")
            print(f"   ✨ جديد: {stats['new_found']} منتج")
            print(f"   ⏭️ تم تخطي: {stats['skipped_existing']} منتج موجود")
            print(f"   📈 معدل الاكتشاف: {stats['discovery_rate']:.1f}%")

if __name__ == "__main__":
    print("🔍 الباحث الذكي عن المنتجات الجديدة")
    print("=" * 50)
    asyncio.run(test_smart_finder())