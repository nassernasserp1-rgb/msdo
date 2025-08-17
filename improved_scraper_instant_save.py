#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكرابر محسن مع حفظ فوري للبيانات
"""

import asyncio
import json
import sqlite3
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
from playwright.async_api import async_playwright
import threading

class InstantSaveDatabase:
    """قاعدة بيانات مع حفظ فوري"""
    
    def __init__(self, db_path: str = "products_instant.db"):
        self.db_path = db_path
        self.connection_lock = threading.Lock()
        self._init_db()
        
    def _init_db(self):
        """إنشاء جداول قاعدة البيانات"""
        with self.connection_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
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
            
            # إنشاء فهارس
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_asin ON products(asin)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_section ON products(section)')
            
            conn.commit()
            conn.close()
            
        print(f"✅ قاعدة البيانات جاهزة: {self.db_path}")
    
    def add_product_instant(self, asin: str, name: str, url: str, img: str, 
                           section: str, price: float, strike_price: float, 
                           discount_percent: float):
        """إضافة منتج مع حفظ فوري"""
        
        with self.connection_lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO products 
                    (asin, name, url, img, section, price, strike_price, discount_percent, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (asin, name, url, img, section, price, strike_price, 
                      discount_percent, datetime.now().isoformat()))
                
                conn.commit()
                conn.close()
                return True
                
            except Exception as e:
                print(f"❌ خطأ في حفظ المنتج {asin}: {e}")
                return False
    
    def get_stats(self) -> dict:
        """الحصول على إحصائيات فورية"""
        with self.connection_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM products')
            total_products = cursor.fetchone()[0]
            
            cursor.execute('SELECT section, COUNT(*) FROM products GROUP BY section')
            sections = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                'total_products': total_products,
                'sections': sections
            }

class InstantSaveScraper:
    """سكرابر مع حفظ فوري"""
    
    def __init__(self, concurrency: int = 10):
        self.concurrency = concurrency
        self.db = InstantSaveDatabase()
        self.session_stats = {
            'pages_scraped': 0,
            'products_found': 0,
            'products_saved': 0,
            'start_time': time.time()
        }
        
        # إعدادات متحفظة للمتصفح
        self.browser_config = {
            'headless': True,
            'args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-images',
                '--disable-javascript',
                '--window-size=1280,720',
            ]
        }
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(**self.browser_config)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'browser'):
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    async def scrape_page_instant(self, context, section: str, url: str, page_num: int,
                                 alert_callback: Optional[Callable] = None,
                                 discount_threshold: float = 30.0) -> int:
        """سكرابة صفحة مع حفظ فوري"""
        
        page = await context.new_page()
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=25000)
            await page.wait_for_timeout(500)
            
            # استخراج المنتجات
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
                        
                        if (name && price) {
                            products.push({
                                asin, name, img, url, price, strikePrice
                            });
                        }
                    });
                    
                    return products;
                }
            """)
            
            saved_count = 0
            
            # معالجة وحفظ كل منتج فوراً
            for product_data in products_data:
                try:
                    asin = product_data['asin']
                    name = product_data['name']
                    url = product_data['url']
                    img = product_data['img']
                    price = product_data['price']
                    strike_price = product_data['strikePrice']
                    
                    # حساب نسبة الخصم
                    discount_percent = 0
                    if strike_price and price and strike_price > price:
                        discount_percent = ((strike_price - price) / strike_price) * 100
                    
                    # حفظ فوري في قاعدة البيانات
                    success = self.db.add_product_instant(
                        asin, name, url, img, section, price, 
                        strike_price, discount_percent
                    )
                    
                    if success:
                        saved_count += 1
                        self.session_stats['products_saved'] += 1
                    
                    self.session_stats['products_found'] += 1
                    
                    # التحقق من التنبيهات
                    if (discount_percent >= discount_threshold and 
                        discount_percent <= 98 and price >= 4):
                        if alert_callback:
                            await alert_callback(asin, name, price, strike_price, discount_percent)
                    
                except Exception as e:
                    print(f"⚠️ خطأ في معالجة المنتج: {e}")
                    continue
            
            self.session_stats['pages_scraped'] += 1
            
            # طباعة تقرير فوري
            elapsed = time.time() - self.session_stats['start_time']
            products_per_sec = self.session_stats['products_found'] / elapsed if elapsed > 0 else 0
            
            print(f"📄 صفحة {page_num}: {saved_count} منتج محفوظ | "
                  f"الإجمالي: {self.session_stats['products_saved']} | "
                  f"السرعة: {products_per_sec:.1f} منتج/ثانية")
            
            return saved_count
            
        except Exception as e:
            print(f"❌ خطأ في الصفحة {page_num}: {e}")
            return 0
        finally:
            await page.close()
    
    async def scrape_section_instant(self, section: str, base_url: str, 
                                   start_page: int, end_page: int,
                                   alert_callback: Optional[Callable] = None,
                                   discount_threshold: float = 30.0,
                                   stop_flag: Optional[dict] = None):
        """سكرابة قسم مع حفظ فوري"""
        
        print(f"🎯 بدء سكرابة القسم: {section}")
        print(f"📊 الصفحات: {start_page} إلى {end_page}")
        
        context = await self.browser.new_context()
        semaphore = asyncio.Semaphore(self.concurrency)
        
        async def scrape_page_with_semaphore(page_num: int):
            async with semaphore:
                if stop_flag and stop_flag.get("stop"):
                    return 0
                
                url = base_url.format(page_num)
                return await self.scrape_page_instant(
                    context, section, url, page_num, alert_callback, discount_threshold
                )
        
        # تنفيذ جميع الصفحات
        pages = range(start_page, end_page + 1)
        tasks = [scrape_page_with_semaphore(page_num) for page_num in pages]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_saved = sum(r for r in results if isinstance(r, int))
        errors = [r for r in results if isinstance(r, Exception)]
        
        await context.close()
        
        # تقرير نهائي
        elapsed = time.time() - self.session_stats['start_time']
        print(f"\n✅ اكتمل القسم '{section}':")
        print(f"   📦 المنتجات المحفوظة: {total_saved}")
        print(f"   ⏱️ الوقت المستغرق: {elapsed:.1f} ثانية")
        print(f"   ⚡ السرعة: {total_saved/elapsed:.1f} منتج/ثانية")
        
        if errors:
            print(f"   ⚠️ أخطاء: {len(errors)}")
        
        return total_saved
    
    def get_performance_stats(self) -> dict:
        """الحصول على إحصائيات الأداء"""
        elapsed = time.time() - self.session_stats['start_time']
        db_stats = self.db.get_stats()
        
        return {
            'session': self.session_stats,
            'performance': {
                'elapsed_time': elapsed,
                'products_per_second': self.session_stats['products_found'] / elapsed if elapsed > 0 else 0,
                'save_rate': (self.session_stats['products_saved'] / self.session_stats['products_found'] * 100) if self.session_stats['products_found'] > 0 else 0
            },
            'database': db_stats
        }

# مثال على الاستخدام
async def test_instant_scraper():
    """اختبار السكرابر مع الحفظ الفوري"""
    
    categories = {
        'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en"
    }
    
    async def alert_callback(asin, name, price, old_price, discount):
        print(f"🚨 خصم {discount:.1f}%: {name[:50]}")
    
    async with InstantSaveScraper(concurrency=8) as scraper:
        for section_name, section_url in categories.items():
            await scraper.scrape_section_instant(
                section=section_name,
                base_url=section_url,
                start_page=1,
                end_page=5,  # اختبار بعدد قليل من الصفحات
                alert_callback=alert_callback,
                discount_threshold=25.0
            )
            
            # طباعة الإحصائيات
            stats = scraper.get_performance_stats()
            print(f"\n📊 الإحصائيات:")
            print(f"   المنتجات المكتشفة: {stats['session']['products_found']}")
            print(f"   المنتجات المحفوظة: {stats['session']['products_saved']}")
            print(f"   معدل الحفظ: {stats['performance']['save_rate']:.1f}%")
            print(f"   قاعدة البيانات: {stats['database']['total_products']} منتج")

if __name__ == "__main__":
    print("🚀 السكرابر المحسن مع الحفظ الفوري")
    print("=" * 40)
    asyncio.run(test_instant_scraper())