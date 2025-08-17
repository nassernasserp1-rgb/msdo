import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import requests
import json
import os

AMAZON_BASE = "https://www.amazon.eg"
DISCOUNT_THRESHOLD = 30.0
SUDDEN_DROP_THRESHOLD = 30.0
SUPER_DROP_PERCENT = 90.0
SUPER_DROP_PRICE = 20.0
ALLOW_SUPER_DROP = True

# متغير للتحكم في وضع المنتجات الجديدة
from original_interface_enhanced import auto_new_products_mode, existing_asins

def get_api_key():
    config_file = "config.json"
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("SCRAPER_API_KEY")
    return None

def fetch_product_from_api(asin):
    API_KEY = get_api_key()
    if not API_KEY:
        print("No API key found in config.json")
        return None
    try:
        url = f"https://api.scraperapi.com/?api_key={API_KEY}&url=https://www.amazon.eg/dp/{asin}"
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            data = r.json() if 'application/json' in r.headers.get('content-type', '') else None
            if data:
                return {
                    "name": data.get("name") or "?",
                    "img": data.get("img", ""),
                    "url": data.get("url", ""),
                    "price": data.get("price"),
                }
        return None
    except Exception as e:
        print(f"API error for {asin}: {e}")
        return None

async def scrape_single_page(
    section, section_url, page_num, db, log_fn=None, discount_alert_cb=None,
    discount_threshold=DISCOUNT_THRESHOLD
):
    """نفس دالة السكرابة الأصلية مع تحسين للمنتجات الجديدة"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # تحسين URL للمنتجات الجديدة
        if auto_new_products_mode[0]:
            # إضافة فلتر للأحدث أو صفحات عشوائية
            import random
            base_url = section_url.split('&page=')[0]
            
            if random.choice([True, False]):  # 50% احتمال
                url = f"{base_url}&s=date-desc-rank&page={page_num}"  # الأحدث أولاً
            else:
                # صفحة عشوائية من مجال أوسع
                random_page = random.randint(page_num, page_num + 50)
                url = section_url.format(random_page)
        else:
            url = section_url.format(page_num)
        
        if log_fn:
            mode = "[NEW MODE]" if auto_new_products_mode[0] else ""
            log_fn(f"🌐 {mode} Scraping section: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=70000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            if log_fn:
                log_fn(f"❌ Error loading page: {e}")
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        scraped_count = 0
        new_count = 0
        skipped_count = 0

        for item in items:
            try:
                asin = await item.get_attribute("data-asin")
                if not asin or asin.strip() == "":
                    continue

                # فلترة المنتجات الجديدة إذا كان الوضع مفعل
                if auto_new_products_mode[0] and asin in existing_asins:
                    skipped_count += 1
                    continue

                # --- الاسم ---
                title_el = await item.query_selector('h2 span')
                name = await title_el.inner_text() if title_el else "?"

                # --- الصورة ---
                img_el = await item.query_selector('img.s-image')
                img = await img_el.get_attribute("src") if img_el else ""

                # --- الرابط الطويل ---
                anchors = await item.query_selector_all('a.a-link-normal')
                long_url = ""
                for a in anchors:
                    href = await a.get_attribute("href")
                    if href and ('/dp/' in href or '/-/en/' in href):
                        long_url = AMAZON_BASE + href
                        break

                # --- السعر الحالي ---
                price = None
                price_el = await item.query_selector('.a-price .a-offscreen')
                if price_el:
                    price_txt = await price_el.inner_text()
                    price = parse_egp_price(price_txt)
                else:
                    price_txt = await item.inner_text()
                    price = extract_any_number(price_txt)
                price = float(price) if price else None

                # --- التحقق من توفر المنتج من نص الكارد مباشرة ---
                not_avail_texts = [
                    "غير متوفر", "غير متوفر حاليًا", "no featured offers available", "currently unavailable"
                ]
                card_text = (await item.inner_text()).lower()
                if price is None or any(txt.lower() in card_text for txt in not_avail_texts):
                    continue

                # --- السعر القديم (strike price) لو موجود ---
                strike_el = await item.query_selector('.a-price.a-text-price .a-offscreen')
                strike_price = None
                if strike_el:
                    strike_txt = await strike_el.inner_text()
                    strike_price = parse_egp_price(strike_txt)

                # --- حساب نسبة الخصم والفلترة ---
                discount_percent = None
                if strike_price and price and strike_price > price:
                    discount_percent = ((strike_price - price) / strike_price) * 100
                    is_super_drop = discount_percent > SUPER_DROP_PERCENT or price < SUPER_DROP_PRICE
                    flag = "⚠️ SUPER DROP" if is_super_drop else ""
                    
                    if discount_percent >= discount_threshold and discount_percent <= 98 and price >= 4:
                        if discount_alert_cb:
                            discount_alert_cb(
                                {
                                    "asin": asin,
                                    "name": name + (" " + flag if flag else ""),
                                    "url": long_url,
                                    "img": img,
                                    "section": section,
                                    "price": price,
                                    "strike_price": strike_price,
                                    "discount_percent": discount_percent,
                                    "drop_detected": False,
                                    "alert_flag": flag,
                                },
                                strike_price,
                                price,
                                discount_percent,
                                False
                            )

                # --- إضافة للقاعدة ---
                if asin not in db:
                    new_count += 1
                    db[asin] = {
                        "name": name,
                        "url": long_url,
                        "img": img,
                        "section": section,
                        "price": price,
                        "strike_price": strike_price,
                        "discount_percent": discount_percent,
                        "price_history": [],
                        "found_at": datetime.now().isoformat()  # إضافة وقت الاكتشاف
                    }
                    existing_asins.add(asin)  # إضافة للمجموعة الموجودة
                else:
                    # تحديث البيانات الموجودة
                    db[asin]["name"] = name
                    db[asin]["url"] = long_url
                    db[asin]["img"] = img
                    db[asin]["section"] = section
                    db[asin]["price"] = price
                    db[asin]["strike_price"] = strike_price
                    db[asin]["discount_percent"] = discount_percent

                # إضافة تاريخ السعر
                now = datetime.now()
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M")
                last_history = db[asin]["price_history"][-1] if db[asin]["price_history"] else None
                is_new_history = (
                    not last_history or
                    last_history.get("date") != date_str or
                    last_history.get("price") != price
                )
                if is_new_history:
                    db[asin]["price_history"].append({
                        "date": date_str,
                        "time": time_str,
                        "price": price
                    })

                scraped_count += 1

            except Exception as e:
                if log_fn:
                    log_fn(f"⚠️ Error parsing item: {e}")

        await browser.close()
        
        # تقرير مُحسن
        if log_fn:
            if auto_new_products_mode[0]:
                log_fn(f"[Page {page_num}] ✅ {new_count} NEW, {skipped_count} skipped, {scraped_count} total")
            else:
                log_fn(f"[Page {page_num}] ✅ Scraped {scraped_count} products")
        
        return scraped_count

async def scrape_section(
    section, section_url, start_page, end_page, db,
    log_fn=None, progress_fn=None, stop_flag=None, discount_alert_cb=None,
    concurrency=10, max_empty_retries=3, discount_threshold=DISCOUNT_THRESHOLD
):
    """نفس دالة scrape_section الأصلية"""
    pages = list(range(start_page, end_page + 1))
    semaphore = asyncio.Semaphore(concurrency)
    page_retries = {}
    empty_pages = []

    async def scrape_with_limit(page_num):
        async with semaphore:
            if stop_flag and stop_flag.get("stop"):
                return "stopped"
            count = await scrape_single_page(
                section, section_url, page_num, db, log_fn=log_fn,
                discount_alert_cb=discount_alert_cb, discount_threshold=discount_threshold
            )
            if progress_fn:
                progress_fn(page_num)
            return (page_num, count)

    tasks = [scrape_with_limit(page_num) for page_num in pages]
    for fut in asyncio.as_completed(tasks):
        res = await fut
        if res == "stopped":
            if log_fn:
                log_fn("⛔️ Stopped by user.")
            return
        page_num, scraped_count = res
        if log_fn:
            log_fn(f"[Page {page_num}] ✅ Scraped {scraped_count} products\n")
        if scraped_count == 0:
            page_retries[page_num] = 1
            empty_pages.append(page_num)

    # نفس منطق إعادة المحاولة الأصلي
    retry_num = 1
    while empty_pages and retry_num <= max_empty_retries:
        current_empty = empty_pages.copy()
        empty_pages = []
        if log_fn:
            log_fn(f"🔄 Retry {retry_num} for {len(current_empty)} empty pages...")
        retry_tasks = [scrape_with_limit(page_num) for page_num in current_empty]
        for fut in asyncio.as_completed(retry_tasks):
            res = await fut
            if res == "stopped":
                if log_fn:
                    log_fn("⛔️ Stopped by user during retry.")
                return
            page_num, scraped_count = res
            if scraped_count == 0:
                page_retries[page_num] += 1
                if page_retries[page_num] <= max_empty_retries:
                    empty_pages.append(page_num)
            else:
                if log_fn:
                    log_fn(f"🎉 Page {page_num} found products after {page_retries[page_num]} tries.")
        retry_num += 1

    failed_pages = [p for p, tries in page_retries.items() if tries > max_empty_retries]
    if failed_pages and log_fn:
        log_fn(f"⚠️ Pages with no products after {max_empty_retries} retries: {failed_pages}")

# --- Helpers (نفس الأصلية) ---
def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

def extract_any_number(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None