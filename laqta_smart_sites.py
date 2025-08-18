#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - مقارنة ذكية مع المواقع اللي بتشتغل فعلاً
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
import time

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
smart_comparison_enabled = [True]
auto_new_products_mode = [True]

ALERT_DISCOUNT = 25
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام المقارنة الذكية
class SmartSitesComparator:
    """مقارن الأسعار الذكي - يركز على المواقع اللي بتشتغل فعلاً"""
    
    def __init__(self):
        self.stats = {
            'total_searches': 0,
            'successful_finds': 0,
            'validated_deals': 0,
            'rejected_deals': 0,
            'cache_hits': 0,
            'sites_success': {},
            'sites_errors': {}
        }
        self.cache = {}
        
        # المواقع الذكية - مرتبة حسب الأولوية والموثوقية
        self.smart_sites = {
            'jumia': {
                'search_url': 'https://www.jumia.com.eg/catalog/?q={}',
                'display_name': 'جوميا',
                'timeout': 10000,
                'priority': 1,  # أولوية عالية
                'success_rate': 0.8
            },
            'btech': {
                'search_url': 'https://b-tech.com.eg/en/catalogsearch/result/?q={}',
                'display_name': 'بي تك',
                'timeout': 8000,
                'priority': 2,
                'success_rate': 0.7
            },
            'carrefour': {
                'search_url': 'https://www.carrefouregypt.com/mafegy/en/search/?q={}',
                'display_name': 'كارفور',
                'timeout': 8000,
                'priority': 3,
                'success_rate': 0.6
            }
        }
        
        # إحصائيات المواقع
        for site_name in self.smart_sites:
            self.stats['sites_success'][site_name] = 0
            self.stats['sites_errors'][site_name] = 0
    
    def extract_smart_keywords(self, product_name: str) -> str:
        """استخراج ذكي للكلمات المفتاحية"""
        
        # علامات تجارية مهمة مع أولوية
        priority_brands = {
            'samsung': 'samsung',
            'apple': 'apple', 
            'iphone': 'iphone',
            'xiaomi': 'xiaomi',
            'redmi': 'redmi',
            'sony': 'sony',
            'anker': 'anker',
            'joyroom': 'joyroom',
            'canon': 'canon',
            'hp': 'hp'
        }
        
        name_lower = product_name.lower()
        
        # البحث عن العلامة التجارية
        brand_found = ""
        for brand, clean_name in priority_brands.items():
            if brand in name_lower:
                brand_found = clean_name
                break
        
        # استخراج أرقام مهمة (موديل، ذاكرة، قوة)
        important_numbers = []
        
        # أرقام الذاكرة
        memory_match = re.findall(r'\b(\d+(?:gb|mb))\b', name_lower)
        if memory_match:
            important_numbers.extend(memory_match[:2])
        
        # أرقام القوة
        power_match = re.findall(r'\b(\d+w)\b', name_lower)
        if power_match:
            important_numbers.extend(power_match[:1])
        
        # أرقام الموديل
        model_match = re.findall(r'\b([a-z]*\d+[a-z]*)\b', name_lower)
        if model_match:
            important_numbers.extend([m for m in model_match[:2] if len(m) > 1])
        
        # إنشاء مصطلح البحث الذكي
        search_parts = []
        
        if brand_found:
            search_parts.append(brand_found)
        
        if important_numbers:
            search_parts.extend(important_numbers[:2])
        
        # إذا لم نجد علامة تجارية، نأخذ أهم الكلمات
        if not brand_found:
            words = []
            for word in product_name.split():
                clean_word = re.sub(r'[^\w]', '', word.lower())
                if (len(clean_word) > 3 and 
                    clean_word not in ['amazon', 'choice', 'original', 'brand', 'authentic']):
                    words.append(clean_word)
                if len(words) >= 2:
                    break
            search_parts.extend(words)
        
        # تحديد طول البحث حسب نوع المنتج
        if len(search_parts) > 3:
            search_parts = search_parts[:3]  # أقصى 3 كلمات
        elif len(search_parts) < 2:
            # إضافة كلمات إضافية إذا كان البحث قصير
            extra_words = [w for w in product_name.split() if len(w) > 4][:2]
            search_parts.extend([re.sub(r'[^\w]', '', w.lower()) for w in extra_words])
        
        search_term = ' '.join(search_parts[:3])
        return search_term.strip()
    
    async def safe_search_site(self, site_name: str, site_config: dict, search_term: str) -> list:
        """بحث آمن في موقع واحد مع معالجة محسنة للأخطاء"""
        
        prices = []
        
        try:
            # إنشاء browser منفصل لكل موقع لتجنب التداخل
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-images',
                        '--disable-javascript',  # تعطيل JS للسرعة
                        '--window-size=1280,720',
                        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    ]
                )
                
                try:
                    context = await browser.new_context()
                    page = await context.new_page()
                    
                    # إنشاء رابط البحث
                    search_url = site_config['search_url'].format(search_term.replace(' ', '+'))
                    
                    # الذهاب للصفحة مع timeout محدود
                    await page.goto(search_url, timeout=site_config['timeout'])
                    await page.wait_for_timeout(2500)  # انتظار قصير
                    
                    # استخراج الأسعار بطريقة محسنة
                    site_prices = await page.evaluate("""
                        () => {
                            const prices = new Set();
                            
                            // أنماط الأسعار المختلفة
                            const pricePatterns = [
                                /([0-9,]+(?:\\.[0-9]+)?)\\s*(?:جنيه|ج\\.م\\.|EGP|LE)/gi,
                                /(?:EGP|جنيه|ج\\.م\\.|LE)\\s*([0-9,]+(?:\\.[0-9]+)?)/gi,
                                /([0-9,]+)\\s*ج/gi
                            ];
                            
                            // البحث في النص الكامل
                            const bodyText = document.body.innerText || '';
                            
                            for (const pattern of pricePatterns) {
                                const matches = Array.from(bodyText.matchAll(pattern));
                                for (const match of matches) {
                                    const price = parseFloat(match[1].replace(/,/g, ''));
                                    if (price >= 30 && price <= 50000) {
                                        prices.add(price);
                                    }
                                }
                            }
                            
                            // البحث في عناصر الأسعار
                            const priceSelectors = [
                                '.price', '.current-price', '.final-price', '.sale-price',
                                '.prc', '.amount', '.cost', '[data-price]', '.product-price'
                            ];
                            
                            for (const selector of priceSelectors) {
                                try {
                                    const elements = document.querySelectorAll(selector);
                                    elements.forEach(element => {
                                        const text = element.textContent || element.getAttribute('data-price') || '';
                                        
                                        for (const pattern of pricePatterns) {
                                            const matches = Array.from(text.matchAll(pattern));
                                            for (const match of matches) {
                                                const price = parseFloat(match[1].replace(/,/g, ''));
                                                if (price >= 30 && price <= 50000) {
                                                    prices.add(price);
                                                }
                                            }
                                        }
                                    });
                                } catch (e) {
                                    // تجاهل أخطاء العناصر الفردية
                                }
                            }
                            
                            // تحويل إلى array مرتب
                            const sortedPrices = Array.from(prices).sort((a, b) => a - b);
                            return sortedPrices.slice(0, 10); // أول 10 أسعار
                        }
                    """)
                    
                    await context.close()
                    
                    if site_prices and len(site_prices) > 0:
                        prices = site_prices
                        self.stats['sites_success'][site_name] += 1
                        print(f"   ✅ {site_config['display_name']}: {len(prices)} أسعار")
                    else:
                        print(f"   ⚪ {site_config['display_name']}: لا توجد أسعار")
                        
                except Exception as inner_e:
                    print(f"   ❌ {site_config['display_name']}: خطأ في الصفحة")
                    self.stats['sites_errors'][site_name] += 1
                
                finally:
                    await browser.close()
                
        except Exception as e:
            print(f"   ❌ {site_config['display_name']}: خطأ عام")
            self.stats['sites_errors'][site_name] += 1
        
        return prices
    
    async def smart_comparison(self, product_name: str, amazon_price: float) -> dict:
        """مقارنة ذكية مع المواقع الموثوقة"""
        
        search_term = self.extract_smart_keywords(product_name)
        cache_key = f"smart_{search_term}_{amazon_price}"
        
        # فحص الكاش
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        print(f"🧠 مقارنة ذكية: {search_term}")
        
        result = {
            'found_prices': [],
            'sites_data': {},
            'amazon_price': amazon_price,
            'is_good_deal': False,
            'confidence': 30,
            'reason': 'لم يتم العثور على أسعار',
            'sites_checked': 0,
            'sites_found': 0,
            'search_term': search_term
        }
        
        all_prices = []
        sites_with_prices = []
        
        # البحث في المواقع بالتسلسل (أكثر استقرار من التوازي)
        for site_name, site_config in self.smart_sites.items():
            try:
                # البحث في الموقع مع timeout محدود
                prices = await asyncio.wait_for(
                    self.safe_search_site(site_name, site_config, search_term),
                    timeout=12
                )
                
                result['sites_checked'] += 1
                
                if prices:
                    all_prices.extend(prices)
                    sites_with_prices.append(site_config['display_name'])
                    result['sites_data'][site_name] = {
                        'prices': prices,
                        'display_name': site_config['display_name']
                    }
                    result['sites_found'] += 1
                    
            except asyncio.TimeoutError:
                print(f"   ⏱️ {site_config['display_name']}: انتهت المهلة")
                result['sites_checked'] += 1
            except Exception as e:
                print(f"   ❌ {site_config['display_name']}: خطأ")
                result['sites_checked'] += 1
        
        # معالجة النتائج
        if all_prices:
            # إزالة التكرار وفلترة الأسعار
            unique_prices = sorted(list(set(all_prices)))
            
            # فلترة الأسعار الشاذة
            if len(unique_prices) > 3:
                median_price = statistics.median(unique_prices)
                filtered_prices = []
                for price in unique_prices:
                    if 0.3 * median_price <= price <= 3 * median_price:
                        filtered_prices.append(price)
                
                if len(filtered_prices) >= 2:
                    unique_prices = filtered_prices
            
            result['found_prices'] = unique_prices
            
            if len(unique_prices) >= 2:
                # تحليل الأسعار
                avg_price = statistics.mean(unique_prices)
                min_price = min(unique_prices)
                max_price = max(unique_prices)
                
                # حساب ترتيب أمازون
                cheaper_count = sum(1 for p in unique_prices if p > amazon_price)
                total_competitors = len(unique_prices)
                amazon_rank = total_competitors - cheaper_count + 1
                
                # حساب الفرق عن المتوسط
                vs_avg_diff = ((avg_price - amazon_price) / avg_price) * 100
                
                # تحديد جودة العرض بذكاء
                confidence = 40
                
                if amazon_rank == 1 and vs_avg_diff > 10:
                    confidence = 85
                    result['reason'] = f"🔥 الأرخص من {total_competitors} أسعار!"
                    result['is_good_deal'] = True
                elif amazon_rank == 1:
                    confidence = 75
                    result['reason'] = f"✅ الأرخص من {total_competitors} أسعار"
                    result['is_good_deal'] = True
                elif amazon_rank == 2 and vs_avg_diff > 5:
                    confidence = 70
                    result['reason'] = f"⚡ ثاني أرخص + أرخص من المتوسط"
                    result['is_good_deal'] = True
                elif vs_avg_diff > 15:
                    confidence = 65
                    result['reason'] = f"💰 أرخص بـ {vs_avg_diff:.0f}% من المتوسط"
                    result['is_good_deal'] = True
                elif vs_avg_diff > 5:
                    confidence = 55
                    result['reason'] = f"✅ أرخص بـ {vs_avg_diff:.0f}% من المتوسط"
                    result['is_good_deal'] = True
                elif amazon_rank <= total_competitors * 0.6:
                    confidence = 50
                    result['reason'] = f"⚠️ ترتيب {amazon_rank} من {total_competitors}"
                    result['is_good_deal'] = True  # نقبل للمقارنة
                else:
                    confidence = 40
                    result['reason'] = f"❌ ترتيب {amazon_rank} من {total_competitors}"
                    result['is_good_deal'] = False
                
                result['confidence'] = confidence
                
                # طباعة النتائج
                print(f"   📊 {total_competitors} أسعار من {result['sites_found']} مواقع")
                print(f"   💰 المتوسط: {avg_price:.0f} | الأقل: {min_price:.0f} | الأعلى: {max_price:.0f}")
                print(f"   🎯 أمازون: {amazon_price:.0f} (ترتيب {amazon_rank})")
                print(f"   🏪 المواقع: {', '.join(sites_with_prices)}")
                print(f"   {result['reason']}")
                
                self.stats['successful_finds'] += 1
                
            else:
                result['confidence'] = 55
                result['reason'] = f"⚪ سعر واحد ({unique_prices[0]:.0f}) من {sites_with_prices[0]}"
                result['is_good_deal'] = True  # نقبل لأن وجدنا مقارنة
        
        self.stats['total_searches'] += 1
        
        # حفظ في الكاش
        self.cache[cache_key] = result
        
        return result

# إنشاء مقارن المواقع الذكي
smart_sites_comparator = SmartSitesComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع المقارنة الذكية"""
    
    def smart_compare_and_send():
        """مقارنة ذكية وإرسال"""
        
        if smart_comparison_enabled[0]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                comparison_result = loop.run_until_complete(
                    smart_sites_comparator.smart_comparison(item.get('name', ''), new_price)
                )
                
                # قبول العروض بثقة 45% فأكثر (تساهل أكثر)
                if not comparison_result['is_good_deal'] and comparison_result['confidence'] < 45:
                    print(f"🚫 رفض ذكي: {item.get('name', '')[:35]}... - {comparison_result['reason']}")
                    smart_sites_comparator.stats['rejected_deals'] += 1
                    return
                
                # إضافة معلومات المقارنة الذكية
                item['smart_analysis'] = comparison_result
                item['smart_confidence'] = comparison_result['confidence']
                item['smart_reason'] = comparison_result['reason']
                item['found_prices'] = comparison_result['found_prices']
                item['sites_checked'] = comparison_result['sites_checked']
                item['sites_found'] = comparison_result['sites_found']
                item['search_term'] = comparison_result['search_term']
                
                smart_sites_comparator.stats['validated_deals'] += 1
                
            except Exception as e:
                print(f"⚠️ خطأ في المقارنة الذكية: {e}")
                # في حالة الخطأ، نسمح بالإرسال للعروض الكبيرة
                if discount_percent >= 30:
                    item['smart_confidence'] = 60
                    item['smart_reason'] = "خصم كبير - قبول مباشر"
                    smart_sites_comparator.stats['validated_deals'] += 1
                else:
                    return
            finally:
                loop.close()
        
        # إرسال الرسالة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=smart_compare_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع معلومات المقارنة الذكية"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات المقارنة الذكية
        smart_reason = item.get('smart_reason', '')
        smart_confidence = item.get('smart_confidence', 0)
        found_prices = item.get('found_prices', [])
        sites_checked = item.get('sites_checked', 0)
        sites_found = item.get('sites_found', 0)
        search_term = item.get('search_term', '')

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان بناءً على الثقة
        if smart_confidence >= 80:
            headline = "🧠 <b>SMART VERIFIED BEST DEAL!</b> 🧠"
        elif smart_confidence >= 70:
            headline = "✅ <b>SMART CONFIRMED DEAL!</b>"
        elif smart_confidence >= 60:
            headline = "⚡ <b>SMART DEAL FOUND!</b>"
        elif smart_confidence >= 50:
            headline = "💸 <b>Deal Alert!</b>"
        else:
            headline = "🛍️ <b>Price Drop!</b>"

        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
        
        # معلومات السوق
        market_info = ""
        if found_prices:
            avg_market = sum(found_prices) / len(found_prices)
            min_market = min(found_prices)
            max_market = max(found_prices)
            market_info = f"\n📊 <b>Market:</b> Avg {avg_market:,.0f} | Min {min_market:,.0f} | Max {max_market:,.0f}"
        
        # معلومات المواقع
        sites_info = ""
        if sites_checked > 0:
            sites_info = f"\n🏪 <b>Sites:</b> {sites_found} found from {sites_checked} checked"
        
        # معلومات البحث الذكي
        search_info = ""
        if search_term:
            search_info = f"\n🔍 <b>Smart Search:</b> '{search_term}'"
        
        # معلومات التحليل
        analysis_info = ""
        if smart_reason:
            analysis_info = f"\n🧠 <b>Smart Analysis:</b> {smart_reason}"
        
        confidence_row = f"\n📈 <b>Confidence:</b> {smart_confidence}%" if smart_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{confidence_row}{market_info}{sites_info}{search_info}{analysis_info}

🧠 <b>Smart Egyptian Sites Comparison</b>
"""

        # أزرار ذكية مع لينكات مظبوطة
        search_query = search_term.replace(' ', '+') if search_term else product_name.replace(' ', '+')
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Buy on Amazon", "url": url}],
                [
                    {"text": "🛒 Jumia", "url": f"https://www.jumia.com.eg/catalog/?q={search_query}"},
                    {"text": "🔧 B-Tech", "url": f"https://b-tech.com.eg/en/catalogsearch/result/?q={search_query}"}
                ],
                [{"text": "🛒 Carrefour", "url": f"https://www.carrefouregypt.com/mafegy/en/search/?q={search_query}"}]
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
            sites_text = f"{sites_found}/{sites_checked} مواقع" if sites_checked > 0 else "مقارنة أساسية"
            print(f"✅ تم إرسال تنبيه لـ {sent_count} مستخدم - {sites_text}")

    except Exception as e:
        print("❌ Telegram Error:", e)

# باقي الدوال الأساسية (مختصرة)
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
    """إضافة بيانات التنبيه مع المقارنة الذكية"""
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
    
    # إرسال مع المقارنة الذكية
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=25):
    """سكرابة صفحة واحدة"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-images'])
        context = await browser.new_context()
        page = await context.new_page()
        
        # URL محسن
        if auto_new_products_mode[0]:
            base_url = section_url.split('&page=')[0]
            url = f"{base_url}&s=date-desc-rank&page={page_num}"
        else:
            url = section_url.format(page_num)
        
        if log_fn:
            mode = "[NEW]" if auto_new_products_mode[0] else ""
            smart_mode = "[SMART]" if smart_comparison_enabled[0] else ""
            log_fn(f"🧠 {mode}{smart_mode} Smart: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(1500)
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:10]:  # 10 منتجات
            try:
                asin = await item.get_attribute("data-asin")
                if not asin:
                    continue

                # فلترة المنتجات الجديدة
                if auto_new_products_mode[0] and asin in existing_asins:
                    continue

                # استخراج البيانات الأساسية
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
                if not price or price < 30:
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
                    
                    if discount_percent >= discount_threshold and discount_percent <= 70 and price >= 35:
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

            except Exception:
                continue

        await browser.close()
        
        if log_fn:
            log_fn(f"[Page {page_num}] 🧠 {new_count} NEW products")
        
        return new_count

# دوال الواجهة
def start_scraping():
    if running[0]:
        log("Already running.", "⚠️")
        return
        
    section = section_combo.get()
    pages = int(pages_entry.get())
    progress_bar.set(0.0)
    stop_flag["stop"] = False
    running[0] = True
    
    smart_mode = "SMART ON" if smart_comparison_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🧠 Smart Start - New Products: {auto_mode}, Smart Sites: {smart_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Smart scraping {sec_name}...", "🧠")
                        for page_num in range(1, pages + 1):
                            if stop_flag.get("stop"):
                                break
                            await scrape_single_page(
                                sec_name, sec_url, page_num, db,
                                log_fn=lambda m: log(m, "🧠"),
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
                            log_fn=lambda m: log(m, "🧠"),
                            discount_alert_cb=add_alert_data,
                            discount_threshold=ALERT_DISCOUNT
                        )
                        update_progress(page_num / pages)
            
            loop.run_until_complete(scrape_all())
            
        except Exception as e:
            log(f"❌ Scraper error: {e}")
        finally:
            save_db()
            log("✅ Smart Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Smart Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    # إحصائيات المقارنة الذكية
    if smart_comparison_enabled[0]:
        stats = smart_sites_comparator.stats
        log(f"🧠 Smart Sites Stats:")
        log(f"   📊 Total Searches: {stats['total_searches']}")
        log(f"   ✅ Successful Finds: {stats['successful_finds']}")
        log(f"   📱 Validated: {stats['validated_deals']}")
        log(f"   🚫 Rejected: {stats['rejected_deals']}")
        log(f"   🧠 Cache Hits: {stats['cache_hits']}")
        
        # إحصائيات المواقع الفردية
        for site_name, site_config in smart_sites_comparator.smart_sites.items():
            success = stats['sites_success'].get(site_name, 0)
            errors = stats['sites_errors'].get(site_name, 0)
            total_attempts = success + errors
            success_rate = (success / max(total_attempts, 1)) * 100
            log(f"   🏪 {site_config['display_name']}: {success_rate:.0f}% success ({success}/{total_attempts})")
        
        if stats['total_searches'] > 0:
            find_rate = (stats['successful_finds'] / stats['total_searches']) * 100
            validation_rate = (stats['validated_deals'] / stats['total_searches']) * 100
            log(f"   📈 Find Rate: {find_rate:.1f}%")
            log(f"   📈 Validation Rate: {validation_rate:.1f}%")

def toggle_smart_comparison():
    smart_comparison_enabled[0] = smart_comparison_chk.get()
    status = "SMART ON" if smart_comparison_enabled[0] else "OFF"
    log(f"🧠 Smart Sites Comparison: {status}")

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
root.title("LAQTA - Smart Sites Comparison")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA - SMART SITES", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="🧠 مقارنة ذكية مع المواقع اللي بتشتغل فعلاً - بدون أخطاء", 
                             font=("Arial", 18, "bold"), text_color="#ffaa44")
subtitle_label.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")

controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)

section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
    width=170, font=("Arial", 15), button_color="#54fac8")
section_combo.set("Electronics")
section_combo.grid(row=0, column=0, padx=5, pady=8, sticky="ew")

pages_entry = ctk.CTkEntry(controls_frame, width=70, font=("Arial", 15), fg_color="#232d3a", text_color="#12dafb")
pages_entry.insert(0, "3")
pages_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 13), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=5, pady=8, sticky="ew")

# المنتجات الجديدة
auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 New Only", font=("Arial", 13, "bold"), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=3, padx=5, pady=8, sticky="ew")
auto_new_chk.select()

# المقارنة الذكية
smart_comparison_chk = ctk.CTkCheckBox(controls_frame, text="🧠 Smart Sites", font=("Arial", 13, "bold"), 
                                      text_color="#4285f4", command=toggle_smart_comparison)
smart_comparison_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
smart_comparison_chk.select()

telegram_checkbox = ctk.CTkCheckBox(controls_frame, text="📱 Telegram", font=("Arial", 13), text_color="#13e6a7",
    command=toggle_telegram_alert)
telegram_checkbox.grid(row=0, column=5, padx=5, pady=8, sticky="ew")
telegram_checkbox.select()

min_discount_slider = ctk.CTkSlider(controls_frame, from_=1, to=99, number_of_steps=98, width=90,
    command=set_min_discount, progress_color="#12dafb")
min_discount_slider.set(ALERT_DISCOUNT)
min_discount_slider.grid(row=0, column=6, padx=5, pady=8, sticky="ew")

min_discount_label = ctk.CTkLabel(controls_frame, text=f"Min: {ALERT_DISCOUNT}%", font=("Arial", 12), text_color="#59ff9d")
min_discount_label.grid(row=0, column=7, padx=5, pady=8, sticky="ew")

progress_bar = ctk.CTkProgressBar(root, height=25, progress_color="#59ff9d", fg_color="#232d3a")
progress_bar.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
progress_bar.set(0.0)

log_textbox = ctk.CTkTextbox(root, font=("Consolas", 13), fg_color="#20242f", text_color="#c2ffe3", border_width=0, height=250)
log_textbox.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="nsew")
log_textbox.configure(state="disabled")

buttons_frame = ctk.CTkFrame(root, fg_color="transparent")
buttons_frame.grid(row=5, column=0, padx=10, pady=8, sticky="ew")
buttons_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)

btn_w, btn_h = 190, 45
btn_font = ("Arial", 16, "bold")

start_btn = ctk.CTkButton(buttons_frame, text="🧠 Smart Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4285f4", hover_color="#1a73e8", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#ea4335", hover_color="#d93025", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#34a853", hover_color="#137333", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Smart Stats", command=show_stats, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#fbbc04", hover_color="#f9ab00", text_color="#000000")
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

# رسائل ترحيب ذكية
log("🧠 LAQTA Smart Sites started!", "🚀")
log("🏪 Smart Sites: جوميا، بي تك، كارفور (المواقع اللي بتشتغل)", "✨")
log("🧠 Smart Search: استخراج ذكي للكلمات المفتاحية", "💡")
log("🔧 Error Handling: معالجة محسنة للأخطاء", "🛡️")
log("🆕 New Products: ON - منتجات جديدة فقط", "🎯")
log("📱 Expected: SMART verified deals!", "🏆")

root.mainloop()