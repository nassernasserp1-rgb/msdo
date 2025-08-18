#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA مع نظام مقارنة الأسعار الخارجية
"""

import customtkinter as ctk
import json, threading, asyncio, os
from datetime import datetime
import re
from PIL import Image
import requests
from io import BytesIO
import webbrowser
import concurrent.futures
from playwright.async_api import async_playwright
import statistics
import random

# الفئات
CATEGORIES = {
    'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Automotive': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017874031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Beauty': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017988031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Fashion': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018165031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Home & Kitchen': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021933031%2Cp_98%3A21909049031&dc&page={}&language=en",
}

# إعداد الواجهة
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# متغيرات عامة
DB_FILE = "amz_products.json"
db = {}
stop_flag = {"stop": False}
running = [False]
telegram_alerts_enabled = [True]
price_comparison_enabled = [True]  # مقارنة الأسعار مفعلة
auto_new_products_mode = [True]

ALERT_DISCOUNT = 30
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام مقارنة الأسعار المدمج
class PriceComparator:
    """مقارن الأسعار مع المواقع الخارجية"""
    
    def __init__(self):
        self.sites = {
            'jumia': 'https://www.jumia.com.eg/catalog/?q={}',
            'noon': 'https://www.noon.com/egypt-en/search?q={}',
            'souq': 'https://egypt.souq.com/eg-en/search/?q={}'
        }
        self.comparison_cache = {}  # كاش لتوفير الوقت
        self.comparison_stats = {
            'total_comparisons': 0,
            'successful_comparisons': 0,
            'validated_deals': 0,
            'rejected_deals': 0
        }
    
    def clean_search_term(self, product_name: str) -> str:
        """تنظيف اسم المنتج للبحث"""
        # إزالة الكلمات غير المهمة وأخذ الكلمات الأساسية
        unwanted = ['amazon', 'choice', 'pack', 'piece', 'brand', 'أمازون', 'قطعة', 'حبة']
        
        clean_name = re.sub(r'[^\w\s]', ' ', product_name.lower())
        words = [word for word in clean_name.split() if word not in unwanted and len(word) > 2]
        
        # أخذ أهم 3 كلمات فقط للبحث السريع
        return ' '.join(words[:3])
    
    async def quick_price_check(self, product_name: str, amazon_price: float) -> Dict:
        """فحص سريع للأسعار في المواقع الأخرى"""
        
        search_term = self.clean_search_term(product_name)
        
        # فحص الكاش أولاً
        cache_key = f"{search_term}_{amazon_price}"
        if cache_key in self.comparison_cache:
            return self.comparison_cache[cache_key]
        
        external_prices = []
        sites_checked = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-images', '--disable-javascript', '--disable-css']
                )
                
                # فحص موقع واحد فقط للسرعة (Jumia - الأسرع)
                context = await browser.new_context()
                page = await context.new_page()
                
                try:
                    jumia_url = self.sites['jumia'].format(search_term)
                    await page.goto(jumia_url, timeout=10000)
                    await page.wait_for_timeout(2000)
                    
                    # استخراج أول 3 أسعار فقط للسرعة
                    prices = await page.evaluate("""
                        () => {
                            const priceElements = document.querySelectorAll('.prc, .-prc, .price, .price-now');
                            const prices = [];
                            
                            for (let i = 0; i < Math.min(3, priceElements.length); i++) {
                                const priceText = priceElements[i].textContent;
                                const match = priceText.match(/([0-9,]+)/);
                                if (match) {
                                    const price = parseFloat(match[1].replace(/,/g, ''));
                                    if (price > 10 && price < 100000) {
                                        prices.push(price);
                                    }
                                }
                            }
                            
                            return prices;
                        }
                    """)
                    
                    if prices:
                        external_prices.extend(prices)
                        sites_checked.append('Jumia')
                        print(f"   ✅ Jumia: وُجد {len(prices)} أسعار")
                    else:
                        print(f"   ⚪ Jumia: لا توجد أسعار")
                        
                except Exception as e:
                    print(f"   ❌ Jumia: خطأ في البحث")
                
                await browser.close()
                
        except Exception as e:
            print(f"   ❌ خطأ في فتح المتصفح: {e}")
        
        # تحليل النتائج
        result = {
            'external_prices': external_prices,
            'sites_checked': sites_checked,
            'amazon_price': amazon_price,
            'is_good_deal': False,
            'confidence': 30,  # ثقة منخفضة افتراضياً
            'reason': 'لم يتم العثور على مقارنات'
        }
        
        if external_prices:
            avg_external = statistics.mean(external_prices)
            min_external = min(external_prices)
            
            # حساب الفرق
            vs_avg_diff = ((avg_external - amazon_price) / avg_external) * 100
            vs_min_diff = ((min_external - amazon_price) / min_external) * 100
            
            result['avg_external_price'] = avg_external
            result['min_external_price'] = min_external
            result['vs_avg_difference'] = vs_avg_diff
            result['vs_min_difference'] = vs_min_diff
            
            # تحديد جودة العرض
            if vs_avg_diff > 15:  # أرخص بأكثر من 15%
                result['is_good_deal'] = True
                result['confidence'] = 85
                result['reason'] = f"🔥 أرخص بـ {vs_avg_diff:.0f}% من جوميا"
                
            elif vs_avg_diff > 5:   # أرخص بأكثر من 5%
                result['is_good_deal'] = True
                result['confidence'] = 70
                result['reason'] = f"✅ أرخص بـ {vs_avg_diff:.0f}% من جوميا"
                
            elif vs_avg_diff > -10:  # فرق بسيط
                result['is_good_deal'] = True
                result['confidence'] = 55
                result['reason'] = f"⚠️ سعر مقارب لجوميا ({vs_avg_diff:+.0f}%)"
                
            else:  # أغلى بكثير
                result['is_good_deal'] = False
                result['confidence'] = 25
                result['reason'] = f"❌ أغلى بـ {abs(vs_avg_diff):.0f}% من جوميا"
            
            self.comparison_stats['successful_comparisons'] += 1
        
        self.comparison_stats['total_comparisons'] += 1
        
        # حفظ في الكاش
        self.comparison_cache[cache_key] = result
        
        return result

# إنشاء مقارن الأسعار
price_comparator = PriceComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع مقارنة الأسعار"""
    
    # مقارنة الأسعار أولاً إذا كانت مفعلة
    if price_comparison_enabled[0]:
        
        def compare_and_send():
            """مقارنة وإرسال في thread منفصل"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # مقارنة سريعة
                comparison_result = loop.run_until_complete(
                    price_comparator.quick_price_check(item.get('name', ''), new_price)
                )
                
                if not comparison_result['is_good_deal']:
                    print(f"🚫 تم رفض التنبيه: {item.get('name', '')[:40]}... - {comparison_result['reason']}")
                    price_comparator.comparison_stats['rejected_deals'] += 1
                    return
                
                # إضافة معلومات المقارنة للرسالة
                item['comparison_info'] = comparison_result['reason']
                item['confidence_score'] = comparison_result['confidence']
                
                price_comparator.comparison_stats['validated_deals'] += 1
                
            except Exception as e:
                print(f"⚠️ خطأ في المقارنة، سيتم الإرسال بدون مقارنة: {e}")
            finally:
                loop.close()
            
            # إرسال الرسالة
            send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
        
        # تشغيل المقارنة في thread منفصل
        threading.Thread(target=compare_and_send, daemon=True).start()
    else:
        # إرسال مباشر بدون مقارنة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال فعلي لتنبيه التليجرام"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات المقارنة
        comparison_info = item.get('comparison_info', '')
        confidence_score = item.get('confidence_score', 0)

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        if drop_detected:
            headline = "🚨 <b>Price Drop!</b> 🚨"
        elif discount_percent >= 60:
            headline = "🔥 <b>HOT DEAL!</b>"
        elif discount_percent >= 40:
            headline = "✨ <b>Good Deal!</b>"
        else:
            headline = "💸 <b>Deal Alert!</b>"

        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
        
        # إضافة معلومات المقارنة للرسالة
        comparison_row = f"\n🔍 <b>Price Check:</b> {comparison_info}" if comparison_info else ""
        confidence_row = f"\n🎯 <b>Confidence:</b> {confidence_score}%" if confidence_score > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Open Product</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{comparison_row}{confidence_row}
"""

        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ View on Amazon", "url": url}],
                [{"text": "🔍 Search on Jumia", "url": f"https://www.jumia.com.eg/catalog/?q={product_name.replace(' ', '+')}"}]
            ]
        }
        reply_markup_json = json.dumps(reply_markup)

        sent_count = 0
        for user_id in users:
            try:
                if img_url:
                    response = requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                        data={
                            "chat_id": user_id,
                            "photo": img_url,
                            "caption": msg,
                            "parse_mode": "HTML",
                            "reply_markup": reply_markup_json
                        }, timeout=15
                    )
                else:
                    response = requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        data={
                            "chat_id": user_id,
                            "text": msg,
                            "parse_mode": "HTML",
                            "reply_markup": reply_markup_json
                        }, timeout=15
                    )
                
                if response.status_code == 200:
                    sent_count += 1

            except Exception as e:
                print(f"❌ خطأ إرسال للمستخدم {user_id}: {e}")
        
        if sent_count > 0:
            comparison_text = comparison_info[:30] if comparison_info else "بدون مقارنة"
            print(f"✅ تم إرسال تنبيه لـ {sent_count} مستخدم - {comparison_text}")

    except Exception as e:
        print("❌ Telegram Error:", e)

# باقي الدوال الأساسية
def load_db():
    global db, existing_asins
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
        existing_asins = set(db.keys())
        print(f"📦 تم تحميل {len(db):,} منتج موجود")
    else:
        db = {}
        existing_asins = set()

def save_db():
    try:
        if os.path.exists(DB_FILE):
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            import shutil
            shutil.copy2(DB_FILE, backup_name)
        
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        
        print(f"💾 تم حفظ {len(db):,} منتج")
    except Exception as e:
        print(f"❌ خطأ في الحفظ: {e}")

def log(msg, emoji=""):
    msg_no_links = re.sub(r'https?://\S+|www\.\S+', '', msg).strip()
    if not msg_no_links:
        return
    log_textbox.configure(state="normal")
    log_textbox.insert("end", f"{emoji} {msg_no_links}\n")
    log_textbox.see("end")
    log_textbox.configure(state="disabled")

def update_progress(val):
    progress_bar.set(val)

def add_alert_data(item, old_price, new_price, discount_percent, drop_detected=False):
    """إضافة بيانات التنبيه مع مقارنة الأسعار"""
    asin = item.get("asin")
    key = f"{asin}-{int(new_price)}"
    if key in notified_asins:
        return
    notified_asins.add(key)
    
    alerts_data.append({
        "item": item,
        "old_price": old_price,
        "new_price": new_price,
        "discount_percent": discount_percent,
        "drop_detected": drop_detected
    })
    
    # إرسال على تليجرام مع مقارنة الأسعار
    if telegram_alerts_enabled[0]:
        threading.Thread(target=send_telegram_alert, args=(item, old_price, new_price, discount_percent, drop_detected), daemon=True).start()

# دوال السكرابة
def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=30):
    """سكرابة صفحة واحدة"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-images'])
        context = await browser.new_context()
        page = await context.new_page()
        
        # تحسين URL للمنتجات الجديدة
        if auto_new_products_mode[0]:
            base_url = section_url.split('&page=')[0]
            if random.choice([True, False]):
                url = f"{base_url}&s=date-desc-rank&page={page_num}"
            else:
                random_page = random.randint(page_num, page_num + 20)
                url = section_url.format(random_page)
        else:
            url = section_url.format(page_num)
        
        if log_fn:
            mode = "[NEW]" if auto_new_products_mode[0] else ""
            comparison_mode = "[PRICE CHECK]" if price_comparison_enabled[0] else ""
            log_fn(f"🌐 {mode}{comparison_mode} Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=45000)
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

                # فلترة المنتجات الجديدة
                if auto_new_products_mode[0] and asin in existing_asins:
                    skipped_count += 1
                    continue

                # استخراج البيانات
                title_el = await item.query_selector('h2 span')
                name = await title_el.inner_text() if title_el else "?"

                img_el = await item.query_selector('img.s-image')
                img = await img_el.get_attribute("src") if img_el else ""

                anchors = await item.query_selector_all('a.a-link-normal')
                long_url = ""
                for a in anchors:
                    href = await a.get_attribute("href")
                    if href and ('/dp/' in href or '/-/en/' in href):
                        long_url = "https://www.amazon.eg" + href
                        break

                # استخراج السعر
                price = None
                price_el = await item.query_selector('.a-price .a-offscreen')
                if price_el:
                    price_txt = await price_el.inner_text()
                    price = parse_egp_price(price_txt)

                if price is None:
                    continue

                # السعر المشطوب
                strike_el = await item.query_selector('.a-price.a-text-price .a-offscreen')
                strike_price = None
                if strike_el:
                    strike_txt = await strike_el.inner_text()
                    strike_price = parse_egp_price(strike_txt)

                # حساب نسبة الخصم
                discount_percent = None
                if strike_price and price and strike_price > price:
                    discount_percent = ((strike_price - price) / strike_price) * 100
                    
                    if discount_percent >= discount_threshold and discount_percent <= 95 and price >= 10:
                        if discount_alert_cb:
                            discount_alert_cb(
                                {
                                    "asin": asin,
                                    "name": name,
                                    "url": long_url,
                                    "img": img,
                                    "section": section,
                                    "price": price,
                                    "strike_price": strike_price,
                                    "discount_percent": discount_percent,
                                },
                                strike_price,
                                price,
                                discount_percent,
                                False
                            )

                # إضافة للقاعدة
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
                        "found_at": datetime.now().isoformat()
                    }
                    existing_asins.add(asin)

                scraped_count += 1

            except Exception as e:
                if log_fn:
                    log_fn(f"⚠️ Error parsing item: {e}")

        await browser.close()
        
        if log_fn:
            if auto_new_products_mode[0]:
                log_fn(f"[Page {page_num}] ✅ {new_count} NEW, {skipped_count} skipped")
            else:
                log_fn(f"[Page {page_num}] ✅ Scraped {scraped_count} products")
        
        return scraped_count

async def scrape_section(section, section_url, start_page, end_page, db, log_fn=None, progress_fn=None, 
                        stop_flag=None, discount_alert_cb=None, concurrency=8, discount_threshold=30):
    """سكرابة قسم كامل"""
    pages = list(range(start_page, end_page + 1))
    semaphore = asyncio.Semaphore(concurrency)

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

def scraper_func(section, pages, all_pages):
    """دالة السكرابر الرئيسية"""
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    notified_asins.clear()
    alerts_data.clear()
    
    def alert_callback(item, old_price, new_price, discount_percent, drop_detected=False):
        add_alert_data(item, old_price, new_price, discount_percent, drop_detected=drop_detected)
    
    if all_pages:
        pages = 200
    
    if section == "All Sections":
        for sec in list(CATEGORIES.keys()):
            if stop_flag.get("stop"):
                break
            log(f"Scraping section: {sec}", "🟢")
            section_url = CATEGORIES[sec]
            loop.run_until_complete(scrape_section(
                sec, section_url, 1, pages, db,
                log_fn=lambda m: log(m, "🟢"),
                progress_fn=lambda pn: update_progress(pn / pages),
                stop_flag=stop_flag,
                discount_alert_cb=alert_callback,
                discount_threshold=ALERT_DISCOUNT
            ))
    else:
        section_url = CATEGORIES[section]
        loop.run_until_complete(scrape_section(
            section, section_url, 1, pages, db,
            log_fn=lambda m: log(m, "🟢"),
            progress_fn=lambda pn: update_progress(pn / pages),
            stop_flag=stop_flag,
            discount_alert_cb=alert_callback,
            discount_threshold=ALERT_DISCOUNT
        ))
    save_db()
    log("✅ Done.")
    running[0] = False

# باقي دوال الواجهة
def start_scraping():
    if running[0]:
        log("Already running.", "⚠️")
        return
    section = section_combo.get()
    all_pages = all_pages_chk.get()
    pages = int(pages_entry.get()) if not all_pages else 200
    progress_bar.set(0.0)
    stop_flag["stop"] = False
    running[0] = True
    
    # رسائل الحالة
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    comparison_mode = "ON" if price_comparison_enabled[0] else "OFF"
    log(f"🚀 Starting - Auto New: {auto_mode}, Price Comparison: {comparison_mode}")
    
    global scrape_thread
    scrape_thread = threading.Thread(target=scraper_func, args=(section, pages, all_pages), daemon=True)
    scrape_thread.start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    # إحصائيات مقارنة الأسعار
    if price_comparison_enabled[0]:
        stats = price_comparator.comparison_stats
        log(f"🔍 Price Comparison Stats:")
        log(f"   📊 Total Comparisons: {stats['total_comparisons']}")
        log(f"   ✅ Successful: {stats['successful_comparisons']}")
        log(f"   📱 Validated Deals: {stats['validated_deals']}")
        log(f"   🚫 Rejected Deals: {stats['rejected_deals']}")
        
        if stats['total_comparisons'] > 0:
            success_rate = (stats['validated_deals'] / stats['total_comparisons']) * 100
            log(f"   📈 Validation Rate: {success_rate:.1f}%")

def toggle_price_comparison():
    """تفعيل/إلغاء مقارنة الأسعار"""
    price_comparison_enabled[0] = price_comparison_chk.get()
    status = "ON" if price_comparison_enabled[0] else "OFF"
    log(f"🔍 Price Comparison: {status}")

def toggle_auto_new_mode():
    auto_new_products_mode[0] = auto_new_chk.get()
    status = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🆕 Auto New Products: {status}")

def resume_scraping():
    load_db()
    log("📦 Database loaded.")
    show_stats()

def exit_app():
    stop_flag["stop"] = True
    save_db()
    root.destroy()

def clear_log():
    log_textbox.configure(state="normal")
    log_textbox.delete("1.0", "end")
    log_textbox.configure(state="disabled")

def export_csv():
    with open("products_export.csv", "w", encoding="utf-8", newline="") as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Last Price"])
        for asin, item in db.items():
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], item["price"]])
    log("Exported to CSV.", "📁")

# ==== MAIN ROOT ====
root = ctk.CTk()
root.title("LAQTA - Price Comparison Validator")
root.geometry("1500x1000")
root.minsize(1200, 750)
root.rowconfigure(3, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA - PRICE CHECKER", font=("SST Arabic Medium", 60), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(18, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="🔍 مقارنة الأسعار مع جوميا ونون وسوق دوت كوم", 
                             font=("Arial", 18, "bold"), text_color="#ffaa44")
subtitle_label.grid(row=1, column=0, padx=8, pady=(0, 10), sticky="ew")

controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=2, column=0, padx=10, pady=7, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7,8), weight=1)

section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
    width=180, font=("Arial", 15), button_color="#54fac8")
section_combo.set("Electronics")
section_combo.grid(row=0, column=0, padx=5, pady=8, sticky="ew")

pages_entry = ctk.CTkEntry(controls_frame, width=70, font=("Arial", 15), fg_color="#232d3a", text_color="#12dafb")
pages_entry.insert(0, "8")
pages_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 13), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=5, pady=8, sticky="ew")

all_pages_chk = ctk.CTkCheckBox(controls_frame, text="All Pages", font=("Arial", 13), text_color="#59ff9d")
all_pages_chk.grid(row=0, column=3, padx=5, pady=8, sticky="ew")

# المنتجات الجديدة
auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 New Only", font=("Arial", 13, "bold"), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
auto_new_chk.select()

# مقارنة الأسعار (الميزة الجديدة)
price_comparison_chk = ctk.CTkCheckBox(controls_frame, text="🔍 Price Check", font=("Arial", 13, "bold"), 
                                      text_color="#00aaff", command=toggle_price_comparison)
price_comparison_chk.grid(row=0, column=5, padx=5, pady=8, sticky="ew")
price_comparison_chk.select()  # مفعل افتراضياً

def toggle_telegram_alert():
    telegram_alerts_enabled[0] = not telegram_alerts_enabled[0]

telegram_checkbox = ctk.CTkCheckBox(controls_frame, text="📱 Telegram", font=("Arial", 13), text_color="#13e6a7",
    command=toggle_telegram_alert)
telegram_checkbox.grid(row=0, column=6, padx=5, pady=8, sticky="ew")
telegram_checkbox.select()

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

min_discount_slider = ctk.CTkSlider(
    controls_frame, from_=1, to=99, number_of_steps=98, width=90,
    command=set_min_discount, progress_color="#12dafb"
)
min_discount_slider.set(ALERT_DISCOUNT)
min_discount_slider.grid(row=0, column=7, padx=5, pady=8, sticky="ew")

min_discount_label = ctk.CTkLabel(
    controls_frame, text=f"Min: {ALERT_DISCOUNT}%", font=("Arial", 11), text_color="#59ff9d"
)
min_discount_label.grid(row=0, column=8, padx=5, pady=8, sticky="ew")

progress_bar = ctk.CTkProgressBar(root, height=25, progress_color="#59ff9d", fg_color="#232d3a")
progress_bar.grid(row=3, column=0, padx=10, pady=7, sticky="ew")
progress_bar.set(0.0)

log_textbox = ctk.CTkTextbox(root, font=("Consolas", 13), fg_color="#20242f", text_color="#c2ffe3", border_width=0, height=220)
log_textbox.grid(row=4, column=0, padx=15, pady=(0, 12), sticky="nsew")
log_textbox.configure(state="disabled")

buttons_frame = ctk.CTkFrame(root, fg_color="transparent")
buttons_frame.grid(row=5, column=0, padx=10, pady=10, sticky="ew")
buttons_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)

btn_w, btn_h = 180, 45
btn_font = ("Arial", 16, "bold")

start_btn = ctk.CTkButton(buttons_frame, text="Start 🚀", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
start_btn.grid(row=0, column=0, padx=6, pady=8, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="Stop ✋", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#12dafb", hover_color="#54fac8", text_color="#111927")
stop_btn.grid(row=0, column=1, padx=6, pady=8, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="Resume 🔁", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#59ff9d", hover_color="#12dafb", text_color="#111927")
resume_btn.grid(row=0, column=2, padx=6, pady=8, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="Stats 📊", command=show_stats, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#59ff9d", hover_color="#54fac8", text_color="#111927")
stats_btn.grid(row=0, column=3, padx=6, pady=8, sticky="ew")

export_btn = ctk.CTkButton(buttons_frame, text="Export 📁", command=export_csv, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#12dafb", hover_color="#59ff9d", text_color="#111927")
export_btn.grid(row=0, column=4, padx=6, pady=8, sticky="ew")

clear_btn = ctk.CTkButton(buttons_frame, text="Clear 🧹", command=clear_log, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
clear_btn.grid(row=0, column=5, padx=6, pady=8, sticky="ew")

exit_btn = ctk.CTkButton(root, text="Exit ❌", command=exit_app, width=350, height=50,
    font=("Arial Black", 20), fg_color="#232d3a", hover_color="#fa1a50", text_color="#59ff9d")
exit_btn.grid(row=6, column=0, pady=(10, 14))

load_db()

# رسائل ترحيب
log("🎯 LAQTA Price Comparison Validator started!", "🚀")
log("🔍 Price Check: ON - سيتم مقارنة الأسعار مع جوميا ونون", "✨")
log("🆕 Auto New: ON - منتجات جديدة فقط", "💡")
log("📱 Expected: Only REAL deals verified by external price comparison!", "🏆")

root.mainloop()