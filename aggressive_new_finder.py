#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
باحث عدواني للمنتجات الجديدة - يجد منتجات جديدة بسرعة
"""

import asyncio
import sqlite3
import json
import time
import random
from datetime import datetime, timedelta
from typing import Set, List, Dict
from playwright.async_api import async_playwright

class AggressiveNewProductsFinder:
    """باحث عدواني للمنتجات الجديدة"""
    
    def __init__(self, db_path: str = "products_optimized.db"):
        self.db_path = db_path
        self.existing_asins: Set[str] = set()
        self.new_products_found = 0
        self.total_checked = 0
        self.session_new_products = {}
        
        # إعدادات عدوانية
        self.concurrency = 8  # تزامن أقل لتجنب الحظر
        self.delay_range = (0.5, 1.5)  # تأخير أقل
        self.max_retries = 2
        
        self.load_existing_products()
    
    def load_existing_products(self):
        """تحميل المنتجات الموجودة بسرعة"""
        try:
            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # تحميل فقط ASINs للسرعة
                cursor.execute('SELECT asin FROM products')
                self.existing_asins = {row[0] for row in cursor.fetchall()}
                conn.close()
                
                print(f"📦 تم تحميل {len(self.existing_asins):,} ASIN موجود")
            else:
                print("⚠️ قاعدة البيانات غير موجودة - سيتم البحث في كل شيء")
                
        except Exception as e:
            print(f"⚠️ خطأ في تحميل ASINs: {e}")
            self.existing_asins = set()
    
    def generate_aggressive_urls(self, base_url: str) -> List[str]:
        """توليد URLs عدوانية للبحث السريع"""
        
        urls = []
        base_clean = base_url.split('&page=')[0]
        
        # استراتيجية 1: الصفحات الأحدث (أول 50 صفحة)
        for page in range(1, 51):
            url = f"{base_clean}&s=date-desc-rank&page={page}"
            urls.append(url)
        
        # استراتيجية 2: صفحات عشوائية من مجال واسع
        random_pages = random.sample(range(51, 300), 30)
        for page in random_pages:
            url = f"{base_clean}&page={page}"
            urls.append(url)
        
        # استراتيجية 3: نطاقات سعرية متنوعة
        price_ranges = [
            (1, 100), (100, 300), (300, 500), (500, 1000), 
            (1000, 2000), (2000, 5000), (5000, 10000)
        ]
        for min_price, max_price in price_ranges:
            for page in range(1, 8):
                url = f"{base_clean}&low-price={min_price}&high-price={max_price}&page={page}"
                urls.append(url)
        
        # استراتيجية 4: فلاتر خاصة
        special_filters = [
            "&s=price-asc-rank",  # الأرخص أولاً
            "&s=price-desc-rank", # الأغلى أولاً
            "&s=review-rank",     # الأعلى تقييماً
            "&s=newest-arrivals", # الأحدث وصولاً
        ]
        for filter_param in special_filters:
            for page in range(1, 15):
                url = f"{base_clean}{filter_param}&page={page}"
                urls.append(url)
        
        # خلط القائمة للتنويع
        random.shuffle(urls)
        
        print(f"🎯 تم توليد {len(urls)} URL للبحث العدواني")
        return urls
    
    async def scan_page_aggressively(self, page, url: str, section: str) -> List[Dict]:
        """مسح صفحة بطريقة عدوانية للبحث عن الجديد"""
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(random.uniform(500, 1000))
            
            # استخراج جميع المنتجات بسرعة
            products_data = await page.evaluate("""
                () => {
                    const items = document.querySelectorAll('div.s-result-item[data-asin]');
                    const products = [];
                    
                    items.forEach(item => {
                        const asin = item.getAttribute('data-asin');
                        if (!asin || asin.length < 10) return;
                        
                        const titleEl = item.querySelector('h2 span, [data-cy="title-recipe-title"]');
                        const name = titleEl ? titleEl.textContent.trim() : '';
                        
                        const imgEl = item.querySelector('img');
                        const img = imgEl ? (imgEl.src || imgEl.getAttribute('data-src')) : '';
                        
                        const linkEl = item.querySelector('a[href*="/dp/"]');
                        let url = '';
                        if (linkEl) {
                            const href = linkEl.getAttribute('href');
                            url = href.startsWith('http') ? href : 'https://www.amazon.eg' + href;
                        }
                        
                        // البحث عن السعر بطرق متعددة
                        let price = null;
                        const priceSelectors = [
                            '.a-price .a-offscreen',
                            '.a-price-whole',
                            '[data-cy="price-recipe-price"]',
                            '.a-price-range .a-offscreen'
                        ];
                        
                        for (const selector of priceSelectors) {
                            const priceEl = item.querySelector(selector);
                            if (priceEl) {
                                const priceText = priceEl.textContent;
                                const match = priceText.match(/([0-9,]+)/);
                                if (match) {
                                    price = parseFloat(match[1].replace(/,/g, ''));
                                    break;
                                }
                            }
                        }
                        
                        // البحث عن السعر المشطوب
                        let strikePrice = null;
                        const strikeEl = item.querySelector('.a-price.a-text-price .a-offscreen, .a-price-was .a-offscreen');
                        if (strikeEl) {
                            const strikeText = strikeEl.textContent;
                            const match = strikeText.match(/([0-9,]+)/);
                            if (match) {
                                strikePrice = parseFloat(match[1].replace(/,/g, ''));
                            }
                        }
                        
                        // التحقق من التوفر بطريقة أسرع
                        const itemText = item.textContent.toLowerCase();
                        const isAvailable = !itemText.includes('غير متوفر') && 
                                          !itemText.includes('currently unavailable') &&
                                          !itemText.includes('out of stock');
                        
                        if (name && asin && isAvailable) {
                            products.push({
                                asin, name, img, url, price, strikePrice
                            });
                        }
                    });
                    
                    return products;
                }
            """)
            
            # فلترة المنتجات الجديدة فقط
            new_products = []
            for product in products_data:
                self.total_checked += 1
                asin = product['asin']
                
                # تحقق سريع من كونه جديد
                if asin not in self.existing_asins:
                    # إضافة معلومات إضافية
                    product['section'] = section
                    product['found_at'] = datetime.now().isoformat()
                    product['discovery_method'] = 'aggressive_search'
                    
                    # حساب الخصم
                    if product['strikePrice'] and product['price']:
                        if product['strikePrice'] > product['price']:
                            discount = ((product['strikePrice'] - product['price']) / product['strikePrice']) * 100
                            product['discount_percent'] = discount
                        else:
                            product['discount_percent'] = 0
                    else:
                        product['discount_percent'] = 0
                    
                    new_products.append(product)
                    self.existing_asins.add(asin)  # إضافة فورية لتجنب التكرار
                    self.new_products_found += 1
                    
                    # إضافة للجلسة الحالية
                    self.session_new_products[asin] = product
            
            return new_products
            
        except Exception as e:
            print(f"❌ خطأ في مسح الصفحة: {e}")
            return []
    
    async def aggressive_search(self, category_name: str, category_url: str, 
                              max_pages: int = 100, target_new_products: int = 1000) -> List[Dict]:
        """البحث العدواني عن المنتجات الجديدة"""
        
        print(f"🔥 بدء البحث العدواني في {category_name}")
        print(f"🎯 الهدف: {target_new_products} منتج جديد في {max_pages} صفحة كحد أقصى")
        
        start_time = time.time()
        all_new_products = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-images',  # تعطيل الصور للسرعة
                    '--disable-javascript',  # تعطيل JS غير الضروري
                    '--window-size=1280,720'
                ]
            )
            
            # إنشاء عدة contexts للتوازي
            contexts = []
            for i in range(self.concurrency):
                context = await browser.new_context()
                contexts.append(context)
            
            # توليد URLs عدوانية
            aggressive_urls = self.generate_aggressive_urls(category_url)
            
            # تقسيم URLs على contexts مختلفة
            url_chunks = [aggressive_urls[i::self.concurrency] for i in range(self.concurrency)]
            
            async def process_url_chunk(context, url_chunk, context_id):
                """معالجة مجموعة URLs في context واحد"""
                page = await context.new_page()
                chunk_new_products = []
                
                for i, url in enumerate(url_chunk):
                    if len(all_new_products) >= target_new_products:
                        break
                    
                    try:
                        new_products = await self.scan_page_aggressively(page, url, category_name)
                        
                        if new_products:
                            chunk_new_products.extend(new_products)
                            elapsed = time.time() - start_time
                            rate = len(all_new_products) / elapsed if elapsed > 0 else 0
                            print(f"🔥 Context {context_id}: +{len(new_products)} جديد | "
                                  f"الإجمالي: {len(all_new_products)} | "
                                  f"السرعة: {rate:.1f} جديد/ثانية")
                        
                        # تأخير عشوائي قصير
                        await asyncio.sleep(random.uniform(*self.delay_range))
                        
                    except Exception as e:
                        print(f"⚠️ Context {context_id} - خطأ في URL {i}: {e}")
                        continue
                
                await page.close()
                return chunk_new_products
            
            # تشغيل جميع contexts بالتوازي
            tasks = [
                process_url_chunk(contexts[i], url_chunks[i], i+1) 
                for i in range(len(contexts))
            ]
            
            # تجميع النتائج
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # دمج النتائج
            for result in results:
                if isinstance(result, list):
                    all_new_products.extend(result)
                elif isinstance(result, Exception):
                    print(f"⚠️ خطأ في معالجة chunk: {result}")
            
            # إغلاق contexts والمتصفح
            for context in contexts:
                await context.close()
            await browser.close()
        
        # إحصائيات النهائية
        elapsed = time.time() - start_time
        discovery_rate = (len(all_new_products) / self.total_checked * 100) if self.total_checked > 0 else 0
        
        print(f"\n🎉 انتهى البحث العدواني:")
        print(f"   ⏱️ الوقت: {elapsed:.1f} ثانية")
        print(f"   🔍 تم فحص: {self.total_checked:,} منتج")
        print(f"   ✨ تم اكتشاف: {len(all_new_products):,} منتج جديد")
        print(f"   📈 معدل الاكتشاف: {discovery_rate:.1f}%")
        print(f"   ⚡ السرعة: {len(all_new_products)/elapsed:.1f} منتج جديد/ثانية")
        
        return all_new_products
    
    def save_new_products_instantly(self, new_products: List[Dict], section: str):
        """حفظ فوري للمنتجات الجديدة"""
        
        if not new_products:
            return
        
        try:
            # حفظ في قاعدة البيانات
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # إنشاء الجدول إذا لم يكن موجود
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
            
            saved_count = 0
            for product in new_products:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO products 
                        (asin, name, url, img, section, price, strike_price, discount_percent, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        product['asin'],
                        product['name'],
                        product['url'],
                        product['img'],
                        section,
                        product['price'],
                        product['strikePrice'],
                        product.get('discount_percent', 0),
                        datetime.now().isoformat()
                    ))
                    saved_count += 1
                except Exception as e:
                    print(f"⚠️ خطأ في حفظ المنتج {product['asin']}: {e}")
            
            conn.commit()
            conn.close()
            
            print(f"💾 تم حفظ {saved_count} منتج جديد في قاعدة البيانات")
            
            # حفظ في JSON أيضاً
            self.save_to_json(new_products, section)
            
        except Exception as e:
            print(f"❌ خطأ في حفظ المنتجات: {e}")
    
    def save_to_json(self, new_products: List[Dict], section: str):
        """حفظ المنتجات الجديدة في JSON"""
        
        try:
            # اسم ملف JSON مع timestamp
            json_filename = f"new_products_{section}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # تحضير البيانات للحفظ
            json_data = {
                "metadata": {
                    "section": section,
                    "timestamp": datetime.now().isoformat(),
                    "total_new_products": len(new_products),
                    "search_method": "aggressive_finder",
                    "version": "2.0"
                },
                "products": {}
            }
            
            # تحويل البيانات لتنسيق JSON
            for product in new_products:
                asin = product['asin']
                json_data["products"][asin] = {
                    "name": product['name'],
                    "url": product['url'],
                    "img": product['img'],
                    "section": section,
                    "price": product['price'],
                    "strike_price": product['strikePrice'],
                    "discount_percent": product.get('discount_percent', 0),
                    "found_at": product.get('found_at', datetime.now().isoformat()),
                    "discovery_method": product.get('discovery_method', 'aggressive_search')
                }
            
            # حفظ الملف
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            print(f"📄 تم حفظ {len(new_products)} منتج في: {json_filename}")
            
            # حفظ في الملف الرئيسي أيضاً
            main_json = "amz_products_updated.json"
            if os.path.exists(main_json):
                with open(main_json, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            else:
                existing_data = {}
            
            # دمج البيانات الجديدة
            for asin, product_data in json_data["products"].items():
                existing_data[asin] = product_data
            
            # حفظ الملف المحدث
            with open(main_json, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            print(f"📄 تم تحديث الملف الرئيسي: {main_json} (الآن يحتوي على {len(existing_data):,} منتج)")
            
        except Exception as e:
            print(f"❌ خطأ في حفظ JSON: {e}")

# واجهة سريعة للاستخدام
async def quick_aggressive_search():
    """بحث عدواني سريع"""
    
    categories = {
        'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en",
        'Beauty': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017988031%2Cp_98%3A21909049031&dc&page={}&language=en",
        'Fashion': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018165031%2Cp_98%3A21909049031&dc&page={}&language=en"
    }
    
    finder = AggressiveNewProductsFinder()
    
    print("🔥 بدء البحث العدواني عن المنتجات الجديدة")
    print("🎯 الهدف: العثور على أكبر عدد من المنتجات الجديدة بأسرع وقت")
    print()
    
    total_new_found = 0
    
    for category_name, category_url in categories.items():
        print(f"🎯 البحث في قسم: {category_name}")
        
        new_products = await finder.aggressive_search(
            category_name, 
            category_url, 
            max_pages=50,  # 50 صفحة كحد أقصى
            target_new_products=500  # هدف 500 منتج جديد لكل قسم
        )
        
        if new_products:
            finder.save_new_products_instantly(new_products, category_name)
            total_new_found += len(new_products)
            
            print(f"🎉 تم العثور على {len(new_products)} منتج جديد في {category_name}")
        else:
            print(f"😔 لم يتم العثور على منتجات جديدة في {category_name}")
        
        print("-" * 50)
    
    print(f"\n🏆 النتيجة النهائية:")
    print(f"   ✨ إجمالي المنتجات الجديدة: {total_new_found:,}")
    print(f"   🔍 إجمالي المفحوص: {finder.total_checked:,}")
    print(f"   📈 معدل الاكتشاف: {(total_new_found/finder.total_checked*100):.1f}%")

if __name__ == "__main__":
    print("🔥 الباحث العدواني للمنتجات الجديدة")
    print("=" * 50)
    print("⚡ هذا النظام مصمم للعثور على أكبر عدد من المنتجات الجديدة بأسرع وقت")
    print("🎯 سيبحث في صفحات متنوعة ونطاقات سعرية مختلفة")
    print()
    
    asyncio.run(quick_aggressive_search())