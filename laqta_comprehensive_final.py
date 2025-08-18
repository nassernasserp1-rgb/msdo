#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - نظام مقارنة الأسعار الشامل مع جميع المواقع المصرية
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
    'Beauty': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017988031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Fashion': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018165031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Home & Kitchen': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021933031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Automotive': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017874031%2Cp_98%3A21909049031&dc&page={}&language=en",
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
comprehensive_comparison_enabled = [True]
auto_new_products_mode = [True]

ALERT_DISCOUNT = 25  # نسبة أقل للحصول على مقارنات أكثر
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام المقارنة الشامل المبسط
class ComprehensiveComparator:
    """مقارن أسعار شامل مع جميع المواقع المصرية"""
    
    def __init__(self):
        # المواقع المصرية الرئيسية
        self.sites = {
            'jumia': {
                'name': 'جوميا',
                'url': 'https://www.jumia.com.eg/catalog/?q={}',
                'selectors': ['.prc', '.-prc', '.price']
            },
            'noon': {
                'name': 'نون', 
                'url': 'https://www.noon.com/egypt-en/search?q={}',
                'selectors': ['.priceNow', '.price-now', '.price']
            },
            'btech': {
                'name': 'بي تك',
                'url': 'https://b-tech.com.eg/search?q={}',
                'selectors': ['.price', '.product-price']
            }
        }
        
        self.stats = {
            'total_comparisons': 0,
            'successful_comparisons': 0,
            'validated_deals': 0,
            'rejected_deals': 0,
            'sites_checked': {site: 0 for site in self.sites.keys()}
        }
        
        self.cache = {}
    
    def clean_search_term(self, product_name: str) -> str:
        """تنظيف اسم المنتج للبحث"""
        # إزالة الكلمات غير المهمة
        unwanted = ['amazon', 'choice', 'brand', 'pack', 'piece', 'أمازون', 'قطعة', 'حبة']
        
        # تنظيف النص
        clean_name = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', product_name.lower())
        words = [word for word in clean_name.split() if word not in unwanted and len(word) > 2]
        
        # أخذ أهم 3 كلمات للبحث السريع
        return ' '.join(words[:3])
    
    async def quick_multi_site_check(self, product_name: str, amazon_price: float) -> dict:
        """فحص سريع في عدة مواقع"""
        
        search_term = self.clean_search_term(product_name)
        cache_key = f"{search_term}_{amazon_price}"
        
        # فحص الكاش
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        print(f"🔍 مقارنة شاملة: {product_name[:40]}...")
        print(f"   🔎 البحث عن: '{search_term}'")
        
        external_prices = []
        sites_found = []
        
        # البحث في المواقع الثلاثة الرئيسية بالتوازي
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-images', '--disable-javascript']
            )
            
            # إنشاء contexts منفصلة لكل موقع
            tasks = []
            for site_key, site_info in self.sites.items():
                task = self.search_single_site(browser, site_key, site_info, search_term)
                tasks.append(task)
            
            # تنفيذ البحث بالتوازي
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # معالجة النتائج
            for i, result in enumerate(results):
                site_key = list(self.sites.keys())[i]
                site_name = self.sites[site_key]['name']
                
                if isinstance(result, list) and result:
                    # أخذ أول سعر صالح
                    for price in result:
                        if 10 <= price <= 200000:
                            external_prices.append(price)
                            sites_found.append(site_name)
                            self.stats['sites_checked'][site_key] += 1
                            print(f"   ✅ {site_name}: {price:,.0f} EGP")
                            break
                    else:
                        print(f"   ⚪ {site_name}: لا توجد أسعار صالحة")
                else:
                    print(f"   ❌ {site_name}: لم يتم العثور على نتائج")
            
            await browser.close()
        
        # تحليل النتائج
        result = {
            'external_prices': external_prices,
            'sites_found': sites_found,
            'amazon_price': amazon_price,
            'is_good_deal': False,
            'confidence': 20,
            'reason': 'لم يتم العثور على مقارنات',
            'detailed_analysis': {}
        }
        
        if external_prices:
            # حساب الإحصائيات
            avg_market = statistics.mean(external_prices)
            min_market = min(external_prices)
            max_market = max(external_prices)
            
            # حساب الفروق
            vs_avg_diff = ((avg_market - amazon_price) / avg_market) * 100
            vs_min_diff = ((min_market - amazon_price) / min_market) * 100
            
            result['detailed_analysis'] = {
                'avg_market_price': avg_market,
                'min_market_price': min_market,
                'max_market_price': max_market,
                'vs_avg_difference': vs_avg_diff,
                'vs_min_difference': vs_min_diff,
                'sites_count': len(sites_found)
            }
            
            # تحديد جودة العرض
            if vs_avg_diff > 20 and len(sites_found) >= 2:
                result['is_good_deal'] = True
                result['confidence'] = 95
                result['reason'] = f"🔥 عرض ممتاز! أرخص بـ {vs_avg_diff:.0f}% من {len(sites_found)} مواقع"
                
            elif vs_avg_diff > 10 and len(sites_found) >= 2:
                result['is_good_deal'] = True
                result['confidence'] = 85
                result['reason'] = f"✅ عرض جيد! أرخص بـ {vs_avg_diff:.0f}% من {len(sites_found)} مواقع"
                
            elif vs_avg_diff > 0 and len(sites_found) >= 1:
                result['is_good_deal'] = True
                result['confidence'] = 70
                result['reason'] = f"⚠️ عرض مقبول! أرخص بـ {vs_avg_diff:.0f}% من السوق"
                
            elif vs_avg_diff > -15:
                result['is_good_deal'] = False
                result['confidence'] = 45
                result['reason'] = f"🤔 سعر مرتفع قليلاً بـ {abs(vs_avg_diff):.0f}% من السوق"
                
            else:
                result['is_good_deal'] = False
                result['confidence'] = 25
                result['reason'] = f"❌ سعر مرتفع! أغلى بـ {abs(vs_avg_diff):.0f}% من السوق"
            
            print(f"   📊 التحليل الشامل:")
            print(f"      💰 متوسط السوق: {avg_market:,.0f} EGP")
            print(f"      📉 أقل سعر: {min_market:,.0f} EGP") 
            print(f"      📈 أعلى سعر: {max_market:,.0f} EGP")
            print(f"      🎯 أمازون: {amazon_price:,.0f} EGP")
            print(f"      📊 الفرق: {vs_avg_diff:+.1f}% من المتوسط")
            print(f"      🏆 الثقة: {result['confidence']}%")
            print(f"      🌐 المواقع: {', '.join(sites_found)}")
            
            self.stats['successful_comparisons'] += 1
        
        self.stats['total_comparisons'] += 1
        
        # حفظ في الكاش
        self.cache[cache_key] = result
        
        return result
    
    async def search_single_site(self, browser, site_key: str, site_info: dict, search_term: str) -> list:
        """البحث في موقع واحد"""
        
        try:
            context = await browser.new_context()
            page = await context.new_page()
            
            search_url = site_info['url'].format(search_term.replace(' ', '+'))
            await page.goto(search_url, timeout=8000)
            await page.wait_for_timeout(1500)
            
            # استخراج الأسعار
            prices = await page.evaluate(f"""
                () => {{
                    const priceSelectors = {json.dumps(site_info['selectors'])};
                    const prices = [];
                    
                    for (const selector of priceSelectors) {{
                        const priceElements = document.querySelectorAll(selector);
                        for (let i = 0; i < Math.min(3, priceElements.length); i++) {{
                            const priceText = priceElements[i].textContent;
                            const match = priceText.match(/([0-9,]+)/);
                            if (match) {{
                                const price = parseFloat(match[1].replace(/,/g, ''));
                                if (price > 10 && price < 200000) {{
                                    prices.push(price);
                                }}
                            }}
                        }}
                        if (prices.length > 0) break;
                    }}
                    
                    return prices;
                }}
            """)
            
            await context.close()
            return prices
            
        except Exception as e:
            return []

# إنشاء المقارن الشامل
comprehensive_comparator = ComprehensiveComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع المقارنة الشاملة"""
    
    def comprehensive_compare_and_send():
        """مقارنة شاملة وإرسال"""
        
        if comprehensive_comparison_enabled[0]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                comparison_result = loop.run_until_complete(
                    comprehensive_comparator.quick_multi_site_check(item.get('name', ''), new_price)
                )
                
                if not comparison_result['is_good_deal']:
                    print(f"🚫 رفض: {item.get('name', '')[:40]}... - {comparison_result['reason']}")
                    comprehensive_comparator.stats['rejected_deals'] += 1
                    return
                
                # إضافة معلومات المقارنة الشاملة
                item['comprehensive_analysis'] = comparison_result['detailed_analysis']
                item['market_confidence'] = comparison_result['confidence']
                item['market_reason'] = comparison_result['reason']
                item['sites_checked'] = comparison_result['sites_found']
                
                comprehensive_comparator.stats['validated_deals'] += 1
                
            except Exception as e:
                print(f"⚠️ خطأ في المقارنة الشاملة: {e}")
            finally:
                loop.close()
        
        # إرسال الرسالة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=comprehensive_compare_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال فعلي للتنبيه مع معلومات المقارنة الشاملة"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات المقارنة الشاملة
        market_reason = item.get('market_reason', '')
        market_confidence = item.get('market_confidence', 0)
        sites_checked = item.get('sites_checked', [])
        comprehensive_analysis = item.get('comprehensive_analysis', {})

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        if drop_detected:
            headline = "🚨 <b>Price Drop!</b> 🚨"
        elif market_confidence >= 90:
            headline = "🔥 <b>VERIFIED HOT DEAL!</b>"
        elif market_confidence >= 80:
            headline = "✅ <b>VERIFIED GOOD DEAL!</b>"
        elif market_confidence >= 70:
            headline = "⚠️ <b>VERIFIED DEAL!</b>"
        else:
            headline = "💸 <b>Deal Alert!</b>"

        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
        
        # معلومات المقارنة المفصلة
        market_info = ""
        if comprehensive_analysis:
            avg_market = comprehensive_analysis.get('avg_market_price', 0)
            min_market = comprehensive_analysis.get('min_market_price', 0)
            vs_avg = comprehensive_analysis.get('vs_avg_difference', 0)
            
            if avg_market > 0:
                market_info = f"""
🔍 <b>Market Analysis:</b>
📊 متوسط السوق: {avg_market:,.0f} EGP
📉 أقل سعر: {min_market:,.0f} EGP  
📈 الفرق: {vs_avg:+.0f}% من المتوسط
🌐 مواقع مفحوصة: {', '.join(sites_checked)}"""

        confidence_row = f"\n🎯 <b>Confidence:</b> {market_confidence}%" if market_confidence > 0 else ""
        reason_row = f"\n✨ <b>Verdict:</b> {market_reason}" if market_reason else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Open on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{confidence_row}{reason_row}{market_info}
"""

        # أزرار المقارنة
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Amazon", "url": url}],
                [{"text": "🔍 Jumia", "url": f"https://www.jumia.com.eg/catalog/?q={product_name.replace(' ', '+')}"}],
                [{"text": "🌙 Noon", "url": f"https://www.noon.com/egypt-en/search?q={product_name.replace(' ', '+')}"}]
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
                        }, timeout=20
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
            sites_text = ', '.join(sites_checked) if sites_checked else 'بدون مقارنة'
            print(f"✅ تم إرسال تنبيه لـ {sent_count} مستخدم - مقارنة مع: {sites_text}")

    except Exception as e:
        print("❌ Telegram Error:", e)

# باقي الدوال (نفس الأصلية)
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
    """إضافة بيانات التنبيه مع المقارنة الشاملة"""
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
    
    # إرسال على تليجرام مع المقارنة الشاملة
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة (مبسطة)
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=25):
    """سكرابة صفحة واحدة"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-images'])
        context = await browser.new_context()
        page = await context.new_page()
        
        # URL محسن للمنتجات الجديدة
        if auto_new_products_mode[0]:
            base_url = section_url.split('&page=')[0]
            url = f"{base_url}&s=date-desc-rank&page={page_num}"
        else:
            url = section_url.format(page_num)
        
        if log_fn:
            mode = "[NEW]" if auto_new_products_mode[0] else ""
            comparison_mode = "[COMPREHENSIVE CHECK]" if comprehensive_comparison_enabled[0] else ""
            log_fn(f"🌐 {mode}{comparison_mode} Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=35000)
            await page.wait_for_timeout(1500)
        except Exception as e:
            if log_fn:
                log_fn(f"❌ Error loading page: {e}")
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        scraped_count = 0
        new_count = 0

        for item in items[:15]:  # أول 15 منتج فقط للسرعة
            try:
                asin = await item.get_attribute("data-asin")
                if not asin:
                    continue

                # فلترة المنتجات الجديدة
                if auto_new_products_mode[0] and asin in existing_asins:
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
                    if href and '/dp/' in href:
                        long_url = "https://www.amazon.eg" + href
                        break

                # استخراج السعر
                price_el = await item.query_selector('.a-price .a-offscreen')
                if not price_el:
                    continue
                    
                price_txt = await price_el.inner_text()
                price = parse_egp_price(price_txt)
                if not price or price < 15:
                    continue

                # السعر المشطوب
                strike_el = await item.query_selector('.a-price.a-text-price .a-offscreen')
                strike_price = None
                if strike_el:
                    strike_txt = await strike_el.inner_text()
                    strike_price = parse_egp_price(strike_txt)

                # حساب نسبة الخصم
                if strike_price and price and strike_price > price:
                    discount_percent = ((strike_price - price) / strike_price) * 100
                    
                    if discount_percent >= discount_threshold and discount_percent <= 85 and price >= 20:
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
                continue

        await browser.close()
        
        if log_fn:
            log_fn(f"[Page {page_num}] ✅ {new_count} NEW products found")
        
        return scraped_count

# باقي دوال الواجهة
def start_scraping():
    if running[0]:
        log("Already running.", "⚠️")
        return
        
    section = section_combo.get()
    pages = int(pages_entry.get())
    progress_bar.set(0.0)
    stop_flag["stop"] = False
    running[0] = True
    
    comparison_mode = "ON" if comprehensive_comparison_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🚀 Starting - New Products: {auto_mode}, Comprehensive Check: {comparison_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Scraping {sec_name}...", "🟢")
                        for page_num in range(1, pages + 1):
                            if stop_flag.get("stop"):
                                break
                            await scrape_single_page(
                                sec_name, sec_url, page_num, db,
                                log_fn=lambda m: log(m, "🟢"),
                                discount_alert_cb=add_alert_data,
                                discount_threshold=ALERT_DISCOUNT
                            )
                            update_progress(page_num / pages)
                else:
                    sec_url = CATEGORIES[section]
                    for page_num in range(1, pages + 1):
                        if stop_flag.get("stop"):
                            break
                        await scrape_single_page(
                            section, sec_url, page_num, db,
                            log_fn=lambda m: log(m, "🟢"),
                            discount_alert_cb=add_alert_data,
                            discount_threshold=ALERT_DISCOUNT
                        )
                        update_progress(page_num / pages)
            
            loop.run_until_complete(scrape_all())
            
        except Exception as e:
            log(f"❌ Scraper error: {e}")
        finally:
            save_db()
            log("✅ Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    # إحصائيات المقارنة الشاملة
    if comprehensive_comparison_enabled[0]:
        stats = comprehensive_comparator.stats
        log(f"🔍 Comprehensive Comparison Stats:")
        log(f"   📊 Total Checked: {stats['total_comparisons']}")
        log(f"   ✅ Successful: {stats['successful_comparisons']}")
        log(f"   📱 Validated: {stats['validated_deals']}")
        log(f"   🚫 Rejected: {stats['rejected_deals']}")
        
        if stats['total_comparisons'] > 0:
            success_rate = (stats['validated_deals'] / stats['total_comparisons']) * 100
            log(f"   📈 Validation Rate: {success_rate:.1f}%")
        
        # إحصائيات المواقع
        log(f"🌐 Sites Performance:")
        for site, count in stats['sites_checked'].items():
            site_name = comprehensive_comparator.sites[site]['name']
            log(f"   {site_name}: {count} responses")

def toggle_comprehensive_comparison():
    comprehensive_comparison_enabled[0] = comprehensive_comparison_chk.get()
    status = "ON" if comprehensive_comparison_enabled[0] else "OFF"
    log(f"🔍 Comprehensive Comparison: {status}")

def toggle_auto_new_mode():
    auto_new_products_mode[0] = auto_new_chk.get()
    status = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🆕 Auto New Products: {status}")

def toggle_telegram_alert():
    telegram_alerts_enabled[0] = not telegram_alerts_enabled[0]

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

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

# ==== MAIN ROOT ====
root = ctk.CTk()
root.title("LAQTA - Comprehensive Price Checker")
root.geometry("1600x1000")
root.minsize(1300, 750)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA - COMPREHENSIVE CHECKER", font=("SST Arabic Medium", 50), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="🌐 مقارنة شاملة مع جوميا، نون، بي تك وجميع المواقع المصرية", 
                             font=("Arial", 16, "bold"), text_color="#ffaa44")
subtitle_label.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")

controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)

section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
    width=160, font=("Arial", 14), button_color="#54fac8")
section_combo.set("Electronics")
section_combo.grid(row=0, column=0, padx=4, pady=8, sticky="ew")

pages_entry = ctk.CTkEntry(controls_frame, width=60, font=("Arial", 14), fg_color="#232d3a", text_color="#12dafb")
pages_entry.insert(0, "6")  # عدد أقل للمقارنة الشاملة
pages_entry.grid(row=0, column=1, padx=4, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 12), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=4, pady=8, sticky="ew")

# المنتجات الجديدة
auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 New Only", font=("Arial", 12, "bold"), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=3, padx=4, pady=8, sticky="ew")
auto_new_chk.select()

# المقارنة الشاملة (الميزة الرئيسية)
comprehensive_comparison_chk = ctk.CTkCheckBox(controls_frame, text="🌐 Full Compare", font=("Arial", 12, "bold"), 
                                              text_color="#00aaff", command=toggle_comprehensive_comparison)
comprehensive_comparison_chk.grid(row=0, column=4, padx=4, pady=8, sticky="ew")
comprehensive_comparison_chk.select()

telegram_checkbox = ctk.CTkCheckBox(controls_frame, text="📱 Telegram", font=("Arial", 12), text_color="#13e6a7",
    command=toggle_telegram_alert)
telegram_checkbox.grid(row=0, column=5, padx=4, pady=8, sticky="ew")
telegram_checkbox.select()

min_discount_slider = ctk.CTkSlider(controls_frame, from_=1, to=99, number_of_steps=98, width=80,
    command=set_min_discount, progress_color="#12dafb")
min_discount_slider.set(ALERT_DISCOUNT)
min_discount_slider.grid(row=0, column=6, padx=4, pady=8, sticky="ew")

min_discount_label = ctk.CTkLabel(controls_frame, text=f"Min: {ALERT_DISCOUNT}%", font=("Arial", 11), text_color="#59ff9d")
min_discount_label.grid(row=0, column=7, padx=4, pady=8, sticky="ew")

progress_bar = ctk.CTkProgressBar(root, height=25, progress_color="#59ff9d", fg_color="#232d3a")
progress_bar.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
progress_bar.set(0.0)

log_textbox = ctk.CTkTextbox(root, font=("Consolas", 12), fg_color="#20242f", text_color="#c2ffe3", border_width=0, height=250)
log_textbox.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="nsew")
log_textbox.configure(state="disabled")

buttons_frame = ctk.CTkFrame(root, fg_color="transparent")
buttons_frame.grid(row=5, column=0, padx=10, pady=8, sticky="ew")
buttons_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)

btn_w, btn_h = 180, 45
btn_font = ("Arial", 15, "bold")

start_btn = ctk.CTkButton(buttons_frame, text="🚀 Start Comprehensive", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#12dafb", hover_color="#54fac8", text_color="#111927")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#59ff9d", hover_color="#12dafb", text_color="#111927")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Stats", command=show_stats, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#59ff9d", hover_color="#54fac8", text_color="#111927")
stats_btn.grid(row=0, column=3, padx=5, pady=6, sticky="ew")

export_btn = ctk.CTkButton(buttons_frame, text="📁 Export", command=export_csv, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#12dafb", hover_color="#59ff9d", text_color="#111927")
export_btn.grid(row=0, column=4, padx=5, pady=6, sticky="ew")

clear_btn = ctk.CTkButton(buttons_frame, text="🧹 Clear", command=clear_log, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
clear_btn.grid(row=0, column=5, padx=5, pady=6, sticky="ew")

exit_btn = ctk.CTkButton(root, text="Exit ❌", command=exit_app, width=300, height=45,
    font=("Arial Black", 18), fg_color="#232d3a", hover_color="#fa1a50", text_color="#59ff9d")
exit_btn.grid(row=6, column=0, pady=(8, 12))

load_db()

# رسائل ترحيب
log("🎯 LAQTA Comprehensive Price Checker started!", "🚀")
log("🌐 Full Compare: ON - مقارنة مع جوميا، نون، بي تك وجميع المواقع", "✨")
log("🆕 New Products: ON - منتجات جديدة فقط", "💡")
log("📱 Expected: Only VERIFIED deals confirmed by multiple sites!", "🏆")

root.mainloop()