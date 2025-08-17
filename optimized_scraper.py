import asyncio
import aiohttp
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import sqlite3
from contextlib import asynccontextmanager
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading
import queue

# إعداد اللوجينج
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ProductData:
    asin: str
    name: str
    url: str
    img: str
    section: str
    price: Optional[float]
    strike_price: Optional[float]
    discount_percent: Optional[float]
    last_updated: datetime
    
    def to_dict(self) -> dict:
        return {
            'asin': self.asin,
            'name': self.name,
            'url': self.url,
            'img': self.img,
            'section': self.section,
            'price': self.price,
            'strike_price': self.strike_price,
            'discount_percent': self.discount_percent,
            'last_updated': self.last_updated.isoformat()
        }

class OptimizedDatabase:
    """قاعدة بيانات محسنة باستخدام SQLite مع batch operations"""
    
    def __init__(self, db_path: str = "products_optimized.db"):
        self.db_path = db_path
        self.batch_queue = queue.Queue()
        self.batch_size = 1000
        self.batch_thread = None
        self.stop_batch = False
        self._init_db()
        self._start_batch_processor()
    
    def _init_db(self):
        """إنشاء جداول قاعدة البيانات"""
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
        
        # إنشاء فهارس لتسريع البحث
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_asin ON products(asin)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_section ON products(section)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_discount ON products(discount_percent)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_history_asin ON price_history(asin)')
        
        conn.commit()
        conn.close()
    
    def _start_batch_processor(self):
        """بدء معالج الدفعات في thread منفصل"""
        self.batch_thread = threading.Thread(target=self._batch_processor, daemon=True)
        self.batch_thread.start()
    
    def _batch_processor(self):
        """معالج الدفعات للكتابة السريعة"""
        batch = []
        while not self.stop_batch:
            try:
                # انتظار عنصر جديد لمدة ثانية واحدة
                item = self.batch_queue.get(timeout=1.0)
                batch.append(item)
                
                # إذا وصلت الدفعة للحد المطلوب أو انتهت المهلة
                if len(batch) >= self.batch_size:
                    self._flush_batch(batch)
                    batch = []
                    
            except queue.Empty:
                # إذا لم تكن هناك عناصر، اكتب ما هو موجود
                if batch:
                    self._flush_batch(batch)
                    batch = []
                continue
    
    def _flush_batch(self, batch: List[Tuple]):
        """كتابة دفعة من البيانات"""
        if not batch:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.executemany('''
                INSERT OR REPLACE INTO products 
                (asin, name, url, img, section, price, strike_price, discount_percent, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', batch)
            conn.commit()
            logger.info(f"✅ Saved batch of {len(batch)} products to database")
        except Exception as e:
            logger.error(f"❌ Error saving batch: {e}")
        finally:
            conn.close()
    
    def add_product(self, product: ProductData):
        """إضافة منتج للدفعة"""
        self.batch_queue.put((
            product.asin, product.name, product.url, product.img,
            product.section, product.price, product.strike_price,
            product.discount_percent, product.last_updated.isoformat()
        ))
    
    def get_product(self, asin: str) -> Optional[ProductData]:
        """الحصول على منتج من قاعدة البيانات"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM products WHERE asin = ?', (asin,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return ProductData(
                asin=row[0], name=row[1], url=row[2], img=row[3],
                section=row[4], price=row[5], strike_price=row[6],
                discount_percent=row[7],
                last_updated=datetime.fromisoformat(row[8])
            )
        return None
    
    def get_stats(self) -> dict:
        """الحصول على إحصائيات قاعدة البيانات"""
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
    
    def close(self):
        """إغلاق قاعدة البيانات وحفظ البيانات المتبقية"""
        self.stop_batch = True
        if self.batch_thread:
            self.batch_thread.join(timeout=5)
        
        # حفظ أي بيانات متبقية
        remaining_batch = []
        while not self.batch_queue.empty():
            try:
                remaining_batch.append(self.batch_queue.get_nowait())
            except queue.Empty:
                break
        
        if remaining_batch:
            self._flush_batch(remaining_batch)

class OptimizedScraper:
    """سكرابر محسن مع تحسينات الأداء"""
    
    def __init__(self, concurrency: int = 15, cache_duration: int = 3600):
        self.concurrency = concurrency
        self.cache_duration = cache_duration  # مدة الكاش بالثواني
        self.db = OptimizedDatabase()
        self.cache = {}  # كاش في الذاكرة
        self.session_stats = {
            'pages_scraped': 0,
            'products_found': 0,
            'products_updated': 0,
            'alerts_sent': 0,
            'start_time': None
        }
        
        # إعدادات Playwright محسنة
        self.browser_config = {
            'headless': True,
            'args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920,1080',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # تعطيل الصور لتوفير bandwidth
                '--disable-javascript',  # تعطيل JS إذا لم يكن ضروري
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
        self.db.close()
    
    def _is_cached_valid(self, asin: str) -> bool:
        """التحقق من صحة الكاش"""
        if asin not in self.cache:
            return False
        
        cached_time = self.cache[asin].get('timestamp', 0)
        return (time.time() - cached_time) < self.cache_duration
    
    def _add_to_cache(self, asin: str, product: ProductData):
        """إضافة منتج للكاش"""
        self.cache[asin] = {
            'product': product,
            'timestamp': time.time()
        }
    
    async def scrape_page_optimized(
        self, 
        context: BrowserContext,
        section: str, 
        url: str, 
        page_num: int,
        alert_callback: Optional[Callable] = None,
        discount_threshold: float = 30.0
    ) -> int:
        """سكرابة صفحة واحدة بطريقة محسنة"""
        page = await context.new_page()
        
        # تحسينات إضافية للصفحة
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # تعطيل الموارد غير الضرورية
        await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", lambda route: route.abort())
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(1000)  # تقليل وقت الانتظار
            
            # استخراج المنتجات بطريقة أسرع
            products_data = await page.evaluate("""
                () => {
                    const items = document.querySelectorAll('div.s-result-item[data-asin][data-component-type="s-search-result"]');
                    const products = [];
                    
                    items.forEach(item => {
                        const asin = item.getAttribute('data-asin');
                        if (!asin) return;
                        
                        // استخراج البيانات بـ JavaScript أسرع من Playwright selectors
                        const titleEl = item.querySelector('h2 span');
                        const name = titleEl ? titleEl.textContent.trim() : '';
                        
                        const imgEl = item.querySelector('img.s-image');
                        const img = imgEl ? imgEl.src : '';
                        
                        const linkEl = item.querySelector('a.a-link-normal[href*="/dp/"]');
                        const url = linkEl ? 'https://www.amazon.eg' + linkEl.href : '';
                        
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
                        
                        // التحقق من التوفر
                        const itemText = item.textContent.toLowerCase();
                        const unavailableTexts = ['غير متوفر', 'currently unavailable', 'no featured offers'];
                        const isAvailable = !unavailableTexts.some(text => itemText.includes(text));
                        
                        if (name && price && isAvailable) {
                            products.push({
                                asin, name, img, url, price, strikePrice
                            });
                        }
                    });
                    
                    return products;
                }
            """)
            
            scraped_count = 0
            current_time = datetime.now()
            
            # معالجة المنتجات
            for product_data in products_data:
                try:
                    asin = product_data['asin']
                    
                    # التحقق من الكاش أولاً
                    if self._is_cached_valid(asin):
                        continue
                    
                    # حساب نسبة الخصم
                    discount_percent = None
                    if product_data['strikePrice'] and product_data['price']:
                        strike_price = product_data['strikePrice']
                        price = product_data['price']
                        if strike_price > price:
                            discount_percent = ((strike_price - price) / strike_price) * 100
                    
                    # إنشاء كائن المنتج
                    product = ProductData(
                        asin=asin,
                        name=product_data['name'],
                        url=product_data['url'],
                        img=product_data['img'],
                        section=section,
                        price=product_data['price'],
                        strike_price=product_data['strikePrice'],
                        discount_percent=discount_percent,
                        last_updated=current_time
                    )
                    
                    # إضافة للكاش وقاعدة البيانات
                    self._add_to_cache(asin, product)
                    self.db.add_product(product)
                    
                    # التحقق من التنبيهات
                    if (discount_percent and discount_percent >= discount_threshold and 
                        discount_percent <= 98 and product_data['price'] >= 4):
                        if alert_callback:
                            await alert_callback(product, product_data['strikePrice'], 
                                               product_data['price'], discount_percent)
                        self.session_stats['alerts_sent'] += 1
                    
                    scraped_count += 1
                    self.session_stats['products_found'] += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error processing product {product_data.get('asin', 'unknown')}: {e}")
                    continue
            
            self.session_stats['pages_scraped'] += 1
            return scraped_count
            
        except Exception as e:
            logger.error(f"❌ Error scraping page {page_num}: {e}")
            return 0
        finally:
            await page.close()
    
    async def scrape_section_optimized(
        self,
        section: str,
        base_url: str,
        start_page: int,
        end_page: int,
        alert_callback: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None,
        log_callback: Optional[Callable] = None,
        discount_threshold: float = 30.0,
        stop_flag: Optional[dict] = None
    ):
        """سكرابة قسم كامل بطريقة محسنة"""
        
        if not self.session_stats['start_time']:
            self.session_stats['start_time'] = time.time()
        
        # إنشاء context واحد لكل المهام
        context = await self.browser.new_context()
        
        # إنشاء semaphore للتحكم في عدد المهام المتزامنة
        semaphore = asyncio.Semaphore(self.concurrency)
        
        async def scrape_page_with_semaphore(page_num: int):
            async with semaphore:
                if stop_flag and stop_flag.get("stop"):
                    return 0
                
                url = base_url.format(page_num)
                count = await self.scrape_page_optimized(
                    context, section, url, page_num, alert_callback, discount_threshold
                )
                
                if progress_callback:
                    progress_callback(page_num)
                
                if log_callback:
                    log_callback(f"📄 Page {page_num}: {count} products scraped")
                
                return count
        
        # تنفيذ جميع الصفحات بشكل متزامن
        pages = range(start_page, end_page + 1)
        tasks = [scrape_page_with_semaphore(page_num) for page_num in pages]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # حساب النتائج
        total_scraped = sum(r for r in results if isinstance(r, int))
        errors = [r for r in results if isinstance(r, Exception)]
        
        if errors and log_callback:
            log_callback(f"⚠️ {len(errors)} pages had errors")
        
        if log_callback:
            elapsed_time = time.time() - self.session_stats['start_time']
            log_callback(f"✅ Section '{section}' completed: {total_scraped} products in {elapsed_time:.1f}s")
        
        await context.close()
        return total_scraped
    
    def get_performance_stats(self) -> dict:
        """الحصول على إحصائيات الأداء"""
        if self.session_stats['start_time']:
            elapsed = time.time() - self.session_stats['start_time']
            products_per_second = self.session_stats['products_found'] / elapsed if elapsed > 0 else 0
            pages_per_minute = (self.session_stats['pages_scraped'] * 60) / elapsed if elapsed > 0 else 0
        else:
            elapsed = 0
            products_per_second = 0
            pages_per_minute = 0
        
        db_stats = self.db.get_stats()
        
        return {
            'session': self.session_stats,
            'performance': {
                'elapsed_time': elapsed,
                'products_per_second': products_per_second,
                'pages_per_minute': pages_per_minute,
                'cache_size': len(self.cache)
            },
            'database': db_stats
        }

# مثال على الاستخدام
async def main():
    """مثال على استخدام السكرابر المحسن"""
    
    categories = {
        'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en",
        'Fashion': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018165031%2Cp_98%3A21909049031&dc&page={}&language=en"
    }
    
    async def alert_callback(product, old_price, new_price, discount):
        print(f"🚨 ALERT: {product.name} - {discount:.1f}% OFF!")
    
    def progress_callback(page):
        print(f"📊 Progress: Page {page} completed")
    
    def log_callback(message):
        print(f"📝 {message}")
    
    async with OptimizedScraper(concurrency=20) as scraper:
        for section_name, section_url in categories.items():
            print(f"\n🎯 Starting section: {section_name}")
            
            await scraper.scrape_section_optimized(
                section=section_name,
                base_url=section_url,
                start_page=1,
                end_page=10,  # ابدأ بعدد صفحات قليل للاختبار
                alert_callback=alert_callback,
                progress_callback=progress_callback,
                log_callback=log_callback,
                discount_threshold=30.0
            )
            
            # طباعة الإحصائيات
            stats = scraper.get_performance_stats()
            print(f"\n📊 Performance Stats:")
            print(f"   Products found: {stats['session']['products_found']}")
            print(f"   Products/second: {stats['performance']['products_per_second']:.2f}")
            print(f"   Pages/minute: {stats['performance']['pages_per_minute']:.2f}")
            print(f"   Total products in DB: {stats['database']['total_products']}")

if __name__ == "__main__":
    asyncio.run(main())