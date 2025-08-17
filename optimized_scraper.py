import asyncio
import aiohttp
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright
import time
from concurrent.futures import ThreadPoolExecutor
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# إعدادات محسنة
AMAZON_BASE = "https://www.amazon.eg"
DISCOUNT_THRESHOLD = 30.0
SUDDEN_DROP_THRESHOLD = 30.0
SUPER_DROP_PERCENT = 90.0
SUPER_DROP_PRICE = 20.0
ALLOW_SUPER_DROP = True

# إعدادات الأداء المحسنة
MAX_CONCURRENT_BROWSERS = 5  # تقليل عدد المتصفحات المتزامنة
PAGE_TIMEOUT = 30000  # تقليل وقت الانتظار
BATCH_SIZE = 20  # حجم الدفعة للمعالجة
CACHE_SIZE = 1000  # حجم الكاش للصور

class OptimizedScraper:
    def __init__(self):
        self.db = {}
        self.browser_pool = []
        self.session = None
        self.cache = {}
        self.stats = {
            'total_scraped': 0,
            'total_pages': 0,
            'start_time': None,
            'errors': 0
        }
    
    async def init_session(self):
        """تهيئة جلسة HTTP محسنة"""
        connector = aiohttp.TCPConnector(
            limit=100,  # زيادة حد الاتصالات
            limit_per_host=30,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
    
    async def create_browser_pool(self, size=MAX_CONCURRENT_BROWSERS):
        """إنشاء مجموعة من المتصفحات الجاهزة"""
        self.playwright = await async_playwright().start()
        
        for _ in range(size):
            browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images',  # تعطيل الصور لتسريع التحميل
                    '--disable-javascript',  # تعطيل JavaScript غير الضروري
                ]
            )
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            self.browser_pool.append((browser, context))
    
    async def get_browser(self):
        """الحصول على متصفح من المجموعة"""
        if not self.browser_pool:
            await self.create_browser_pool()
        return self.browser_pool.pop()
    
    async def return_browser(self, browser, context):
        """إعادة المتصفح للمجموعة"""
        self.browser_pool.append((browser, context))
    
    async def scrape_page_fast(self, section, section_url, page_num, log_fn=None):
        """نسخة محسنة من scraping صفحة واحدة"""
        browser, context = await self.get_browser()
        page = await context.new_page()
        
        try:
            url = section_url.format(page_num)
            if log_fn:
                log_fn(f"🌐 Scraping: {section} - Page {page_num}")
            
            # تحميل أسرع مع إعدادات محسنة
            await page.goto(url, timeout=PAGE_TIMEOUT, wait_until='domcontentloaded')
            await page.wait_for_timeout(1000)  # تقليل وقت الانتظار
            
            # استخراج البيانات بشكل أسرع
            items_data = await page.evaluate("""
                () => {
                    const items = document.querySelectorAll('div.s-result-item[data-asin][data-component-type="s-search-result"]');
                    const results = [];
                    
                    for (const item of items) {
                        const asin = item.getAttribute('data-asin');
                        if (!asin || asin.trim() === '') continue;
                        
                        const titleEl = item.querySelector('h2 span');
                        const name = titleEl ? titleEl.innerText : '?';
                        
                        const imgEl = item.querySelector('img.s-image');
                        const img = imgEl ? imgEl.src : '';
                        
                        const anchors = item.querySelectorAll('a.a-link-normal');
                        let longUrl = '';
                        for (const a of anchors) {
                            const href = a.href;
                            if (href && (href.includes('/dp/') || href.includes('/-/en/'))) {
                                longUrl = href;
                                break;
                            }
                        }
                        
                        const priceEl = item.querySelector('.a-price .a-offscreen');
                        let price = null;
                        if (priceEl) {
                            const priceText = priceEl.innerText;
                            const match = priceText.match(/(\\d[\\d,\\.]*)/);
                            price = match ? parseFloat(match[1].replace(',', '')) : null;
                        }
                        
                        const strikeEl = item.querySelector('.a-price.a-text-price .a-offscreen');
                        let strikePrice = null;
                        if (strikeEl) {
                            const strikeText = strikeEl.innerText;
                            const match = strikeText.match(/(\\d[\\d,\\.]*)/);
                            strikePrice = match ? parseFloat(match[1].replace(',', '')) : null;
                        }
                        
                        // التحقق من توفر المنتج
                        const cardText = item.innerText.toLowerCase();
                        const notAvailTexts = ['غير متوفر', 'غير متوفر حاليًا', 'no featured offers available', 'currently unavailable'];
                        const isAvailable = price !== null && !notAvailTexts.some(txt => cardText.includes(txt.toLowerCase()));
                        
                        if (isAvailable) {
                            results.push({
                                asin: asin,
                                name: name,
                                img: img,
                                url: longUrl,
                                price: price,
                                strike_price: strikePrice
                            });
                        }
                    }
                    return results;
                }
            """)
            
            scraped_count = 0
            for item_data in items_data:
                try:
                    asin = item_data['asin']
                    name = item_data['name']
                    img = item_data['img']
                    long_url = item_data['url']
                    price = item_data['price']
                    strike_price = item_data['strike_price']
                    
                    # حساب نسبة الخصم
                    discount_percent = None
                    if strike_price and price and strike_price > price:
                        discount_percent = ((strike_price - price) / strike_price) * 100
                    
                    # تحديث قاعدة البيانات
                    if asin not in self.db:
                        self.db[asin] = {
                            "name": name,
                            "url": long_url,
                            "img": img,
                            "section": section,
                            "price": price,
                            "strike_price": strike_price,
                            "discount_percent": discount_percent,
                            "price_history": []
                        }
                    
                    # تحديث البيانات
                    self.db[asin].update({
                        "name": name,
                        "url": long_url,
                        "img": img,
                        "section": section,
                        "price": price,
                        "strike_price": strike_price,
                        "discount_percent": discount_percent
                    })
                    
                    # إضافة تاريخ السعر
                    now = datetime.now()
                    date_str = now.strftime("%Y-%m-%d")
                    time_str = now.strftime("%H:%M")
                    
                    price_history = self.db[asin]["price_history"]
                    last_history = price_history[-1] if price_history else None
                    
                    is_new_history = (
                        not last_history or
                        last_history.get("date") != date_str or
                        last_history.get("price") != price
                    )
                    
                    if is_new_history:
                        price_history.append({
                            "date": date_str,
                            "time": time_str,
                            "price": price
                        })
                    
                    scraped_count += 1
                    
                except Exception as e:
                    if log_fn:
                        log_fn(f"⚠️ Error parsing item: {e}")
                    continue
            
            await page.close()
            await self.return_browser(browser, context)
            return scraped_count
            
        except Exception as e:
            await page.close()
            await self.return_browser(browser, context)
            if log_fn:
                log_fn(f"❌ Error scraping page {page_num}: {e}")
            return 0
    
    async def scrape_section_optimized(self, section, section_url, start_page, end_page, 
                                     log_fn=None, progress_fn=None, stop_flag=None,
                                     discount_alert_cb=None, discount_threshold=DISCOUNT_THRESHOLD):
        """نسخة محسنة من scraping القسم بأكمله"""
        self.stats['start_time'] = time.time()
        pages = list(range(start_page, end_page + 1))
        
        # تقسيم الصفحات إلى دفعات
        batches = [pages[i:i + BATCH_SIZE] for i in range(0, len(pages), BATCH_SIZE)]
        
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_BROWSERS)
        
        async def process_batch(batch):
            async with semaphore:
                tasks = []
                for page_num in batch:
                    if stop_flag and stop_flag.get("stop"):
                        return
                    task = self.scrape_page_fast(section, section_url, page_num, log_fn)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return results
        
        total_scraped = 0
        for i, batch in enumerate(batches):
            if stop_flag and stop_flag.get("stop"):
                if log_fn:
                    log_fn("⛔️ Stopped by user.")
                break
            
            if log_fn:
                log_fn(f"📦 Processing batch {i+1}/{len(batches)} ({len(batch)} pages)")
            
            batch_results = await process_batch(batch)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    self.stats['errors'] += 1
                    if log_fn:
                        log_fn(f"❌ Batch error: {result}")
                else:
                    total_scraped += result
            
            if progress_fn:
                progress_fn((i + 1) * BATCH_SIZE)
            
            # حفظ البيانات كل 100 صفحة
            if (i + 1) % 5 == 0:
                await self.save_db_async()
                if log_fn:
                    log_fn(f"💾 Saved progress: {total_scraped} products scraped")
        
        self.stats['total_scraped'] = total_scraped
        self.stats['total_pages'] = len(pages)
        
        if log_fn:
            elapsed_time = time.time() - self.stats['start_time']
            rate = total_scraped / elapsed_time if elapsed_time > 0 else 0
            log_fn(f"✅ Completed: {total_scraped} products in {elapsed_time:.1f}s ({rate:.1f} products/sec)")
        
        return total_scraped
    
    async def save_db_async(self):
        """حفظ قاعدة البيانات بشكل غير متزامن"""
        try:
            with open("amz_products_optimized.json", "w", encoding="utf-8") as f:
                json.dump(self.db, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving DB: {e}")
    
    async def cleanup(self):
        """تنظيف الموارد"""
        if self.session:
            await self.session.close()
        
        for browser, context in self.browser_pool:
            await context.close()
            await browser.close()
        
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

# دالة مساعدة لتحليل السعر
def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

def extract_any_number(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# مثال على الاستخدام
async def main():
    scraper = OptimizedScraper()
    await scraper.init_session()
    await scraper.create_browser_pool()
    
    # مثال على استخدام السكريبت المحسن
    section = "Electronics"
    section_url = "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en"
    
    def log_fn(msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    
    def progress_fn(page_num):
        print(f"Progress: {page_num} pages processed")
    
    try:
        await scraper.scrape_section_optimized(
            section=section,
            section_url=section_url,
            start_page=1,
            end_page=10,
            log_fn=log_fn,
            progress_fn=progress_fn,
            stop_flag={"stop": False}
        )
    finally:
        await scraper.cleanup()

if __name__ == "__main__":
    asyncio.run(main())