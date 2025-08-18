#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - المواقع الموثوقة فقط
نون، جوميا، كارفور، سبينيز - المواقع اللي بتشتغل فعلاً
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
reliable_sites_enabled = [True]
auto_new_products_mode = [True]

ALERT_DISCOUNT = 25
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام المواقع الموثوقة فقط
class ReliableSitesComparator:
    """مقارن الأسعار مع المواقع الموثوقة فقط - اللي بتشتغل فعلاً"""
    
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
        
        # المواقع الموثوقة فقط (بدون سوق، بي تك، تريد لاين، مترو)
        self.reliable_sites = {
            'noon': {
                'search_urls': [
                    'https://www.noon.com/egypt-en/search/?q={}',
                    'https://www.noon.com/egypt-ar/search/?q={}'
                ],
                'display_name': 'نون',
                'timeout': 10000,
                'priority': 1,
                'working': True
            },
            'jumia': {
                'search_urls': [
                    'https://www.jumia.com.eg/catalog/?q={}',
                    'https://www.jumia.com.eg/catalog/?q={}&sort=popularity'
                ],
                'display_name': 'جوميا',
                'timeout': 10000,
                'priority': 2,
                'working': True
            },
            'carrefour': {
                'search_urls': [
                    'https://www.carrefouregypt.com/mafegy/en/search/?q={}',
                    'https://www.carrefouregypt.com/mafegy/ar/search/?q={}'
                ],
                'display_name': 'كارفور',
                'timeout': 8000,
                'priority': 3,
                'working': True
            },
            'spinneys': {
                'search_urls': [
                    'https://spinneys.com/egypt/en/search?q={}',
                    'https://spinneys.com/egypt/ar/search?q={}'
                ],
                'display_name': 'سبينيز',
                'timeout': 8000,
                'priority': 4,
                'working': True
            }
        }
        
        # إحصائيات المواقع
        for site_name in self.reliable_sites:
            self.stats['sites_success'][site_name] = 0
            self.stats['sites_errors'][site_name] = 0
    
    def create_optimized_search_terms(self, product_name: str) -> list:
        """إنشاء مصطلحات بحث محسنة للمواقع الموثوقة"""
        
        # علامات تجارية موثوقة (اللي بتلاقي نتائج كويسة)
        reliable_brands = {
            'samsung': ['samsung', 'galaxy'],
            'apple': ['apple', 'iphone'],
            'xiaomi': ['xiaomi', 'redmi'],
            'sony': ['sony'],
            'lg': ['lg'],
            'canon': ['canon'],
            'hp': ['hp'],
            'anker': ['anker'],
            'vaseline': ['vaseline'],
            'nivea': ['nivea'],
            'palmers': ['palmers'],
            'axe': ['axe'],
            'dove': ['dove'],
            'loreal': ['loreal'],
            'garnier': ['garnier']
        }
        
        name_lower = product_name.lower()
        
        # البحث عن العلامة التجارية
        detected_brand = ""
        brand_variations = []
        
        for brand, variations in reliable_brands.items():
            for variation in variations:
                if variation in name_lower:
                    detected_brand = brand
                    brand_variations = variations
                    break
            if detected_brand:
                break
        
        # استخراج معلومات مهمة
        important_info = {
            'numbers': re.findall(r'\b(\d+(?:gb|mb|ml|w|mah|g)?)\b', name_lower),
            'colors': re.findall(r'\b(black|white|blue|red|green|orange|pink|gold|silver|أسود|أبيض|أزرق|أحمر)\b', name_lower),
            'types': re.findall(r'\b(cream|lotion|spray|gel|shampoo|soap|كريم|لوشن|صابون|شامبو)\b', name_lower)
        }
        
        # إنشاء مصطلحات بحث محسنة
        search_terms = []
        
        # البحث الأساسي بالعلامة التجارية
        if detected_brand:
            if important_info['numbers']:
                search_terms.append(f"{detected_brand} {' '.join(important_info['numbers'][:2])}")
            if important_info['types']:
                search_terms.append(f"{detected_brand} {important_info['types'][0]}")
            search_terms.append(detected_brand)
        
        # البحث بالكلمات المهمة
        important_words = []
        for word in product_name.split():
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if (len(clean_word) > 3 and 
                clean_word not in ['amazon', 'choice', 'original', 'brand', 'authentic', 'genuine', 'with', 'from']):
                important_words.append(clean_word)
            if len(important_words) >= 3:
                break
        
        if important_words:
            search_terms.append(' '.join(important_words[:2]))
        
        # البحث بالنوع والحجم (للمنتجات التجميلية)
        if important_info['types'] and important_info['numbers']:
            search_terms.append(f"{important_info['types'][0]} {important_info['numbers'][0]}")
        
        # إزالة التكرار وأخذ أفضل 2 مصطلحات
        unique_terms = []
        for term in search_terms:
            if term and term not in unique_terms and len(term.strip()) > 2:
                unique_terms.append(term.strip())
        
        return unique_terms[:2]  # أفضل 2 مصطلحات فقط للسرعة
    
    async def reliable_site_search(self, site_name: str, site_config: dict, search_terms: list) -> list:
        """بحث موثوق في موقع واحد"""
        
        all_prices = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-images',
                        '--disable-javascript',
                        '--window-size=1280,720',
                        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    ]
                )
                
                context = await browser.new_context()
                page = await context.new_page()
                
                # جرب كل مصطلح بحث
                for term_idx, search_term in enumerate(search_terms):
                    if len(all_prices) >= 8:  # إذا وجدنا أسعار كافية
                        break
                    
                    # جرب أول رابط بحث فقط (للسرعة)
                    try:
                        search_url = site_config['search_urls'][0].format(search_term.replace(' ', '+'))
                        
                        await page.goto(search_url, timeout=site_config['timeout'])
                        await page.wait_for_timeout(2500)
                        
                        # استخراج الأسعار بطريقة مبسطة
                        site_prices = await page.evaluate("""
                            () => {
                                const prices = new Set();
                                
                                // أنماط الأسعار البسيطة والفعالة
                                const pricePatterns = [
                                    /([0-9,]+(?:\\.[0-9]+)?)\\s*(?:جنيه|ج\\.م\\.|EGP)/gi,
                                    /([0-9,]+)\\s*ج/gi
                                ];
                                
                                // البحث في النص الكامل
                                const bodyText = document.body.innerText || '';
                                
                                for (const pattern of pricePatterns) {
                                    const matches = Array.from(bodyText.matchAll(pattern));
                                    for (const match of matches) {
                                        const price = parseFloat(match[1].replace(/,/g, ''));
                                        if (price >= 25 && price <= 50000) {
                                            prices.add(price);
                                        }
                                    }
                                }
                                
                                // تحويل إلى array مرتب
                                const sortedPrices = Array.from(prices).sort((a, b) => a - b);
                                return sortedPrices.slice(0, 10); // أول 10 أسعار
                            }
                        """)
                        
                        if site_prices and len(site_prices) > 0:
                            all_prices.extend(site_prices)
                            print(f"      ✅ {search_term}: {len(site_prices)} أسعار")
                            break  # إذا وجدنا أسعار، ننتقل للموقع التالي
                            
                    except Exception as e:
                        print(f"      ⚠️ {search_term}: خطأ")
                        continue
                
                await context.close()
                await browser.close()
                
                # إزالة التكرار
                unique_prices = sorted(list(set(all_prices)))
                
                if unique_prices:
                    self.stats['sites_success'][site_name] += 1
                    print(f"   ✅ {site_config['display_name']}: {len(unique_prices)} أسعار إجمالية")
                else:
                    print(f"   ⚪ {site_config['display_name']}: لا توجد أسعار")
                
                return unique_prices
        
        except Exception as e:
            print(f"   ❌ {site_config['display_name']}: خطأ عام")
            self.stats['sites_errors'][site_name] += 1
            return []
    
    async def reliable_comparison(self, product_name: str, amazon_price: float) -> dict:
        """مقارنة موثوقة مع المواقع المختارة"""
        
        search_terms = self.create_optimized_search_terms(product_name)
        cache_key = f"reliable_{'-'.join(search_terms)}_{amazon_price}"
        
        # فحص الكاش
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        print(f"🏪 مقارنة موثوقة: {search_terms}")
        
        result = {
            'found_prices': [],
            'sites_data': {},
            'amazon_price': amazon_price,
            'is_good_deal': False,
            'confidence': 30,
            'reason': 'لم يتم العثور على أسعار',
            'sites_checked': 0,
            'sites_found': 0,
            'search_terms': search_terms
        }
        
        all_prices = []
        sites_with_prices = []
        
        # البحث في المواقع الموثوقة فقط (تسلسلي للاستقرار)
        for site_name, site_config in self.reliable_sites.items():
            if not site_config['working']:
                continue
                
            try:
                # البحث في الموقع
                prices = await asyncio.wait_for(
                    self.reliable_site_search(site_name, site_config, search_terms),
                    timeout=15
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
            # إزالة التكرار وفلترة بسيطة
            unique_prices = sorted(list(set(all_prices)))
            
            # فلترة الأسعار الشاذة (بسيطة وسريعة)
            if len(unique_prices) > 4:
                # إزالة الأسعار البعيدة جداً عن المتوسط
                avg_price = sum(unique_prices) / len(unique_prices)
                filtered_prices = []
                for price in unique_prices:
                    if 0.2 * avg_price <= price <= 5 * avg_price:
                        filtered_prices.append(price)
                
                if len(filtered_prices) >= 3:
                    unique_prices = filtered_prices
            
            result['found_prices'] = unique_prices
            
            if len(unique_prices) >= 2:
                # تحليل بسيط وسريع
                avg_price = sum(unique_prices) / len(unique_prices)
                min_price = min(unique_prices)
                max_price = max(unique_prices)
                
                # حساب ترتيب أمازون
                cheaper_count = sum(1 for p in unique_prices if p > amazon_price)
                total_competitors = len(unique_prices)
                amazon_rank = total_competitors - cheaper_count + 1
                
                # حساب الفرق عن المتوسط
                vs_avg_diff = ((avg_price - amazon_price) / avg_price) * 100
                
                # تحديد جودة العرض (مبسط وسريع)
                confidence = 40
                
                if amazon_rank == 1 and vs_avg_diff > 15:
                    confidence = 85
                    result['reason'] = f"🔥 الأرخص من {total_competitors} أسعار بفارق كبير!"
                    result['is_good_deal'] = True
                elif amazon_rank == 1:
                    confidence = 75
                    result['reason'] = f"✅ الأرخص من {total_competitors} أسعار"
                    result['is_good_deal'] = True
                elif amazon_rank == 2:
                    confidence = 70
                    result['reason'] = f"⚡ ثاني أرخص من {total_competitors} أسعار"
                    result['is_good_deal'] = True
                elif vs_avg_diff > 10:
                    confidence = 65
                    result['reason'] = f"💰 أرخص بـ {vs_avg_diff:.0f}% من المتوسط"
                    result['is_good_deal'] = True
                elif vs_avg_diff > 0:
                    confidence = 55
                    result['reason'] = f"✅ أرخص من المتوسط بـ {vs_avg_diff:.0f}%"
                    result['is_good_deal'] = True
                elif amazon_rank <= total_competitors * 0.6:
                    confidence = 50
                    result['reason'] = f"⚠️ ترتيب {amazon_rank} من {total_competitors}"
                    result['is_good_deal'] = True
                else:
                    confidence = 40
                    result['reason'] = f"❌ ترتيب {amazon_rank} من {total_competitors}"
                    result['is_good_deal'] = False
                
                result['confidence'] = confidence
                
                # طباعة النتائج
                print(f"   📊 {total_competitors} أسعار من {result['sites_found']} مواقع موثوقة")
                print(f"   💰 المتوسط: {avg_price:.0f} | الأقل: {min_price:.0f} | الأعلى: {max_price:.0f}")
                print(f"   🎯 أمازون: {amazon_price:.0f} (ترتيب {amazon_rank})")
                print(f"   🏪 المواقع: {', '.join(sites_with_prices)}")
                print(f"   {result['reason']}")
                
                self.stats['successful_finds'] += 1
                
            else:
                result['confidence'] = 60
                result['reason'] = f"⚪ سعر واحد ({unique_prices[0]:.0f}) من {sites_with_prices[0]}"
                result['is_good_deal'] = True
        
        self.stats['total_searches'] += 1
        
        # حفظ في الكاش
        self.cache[cache_key] = result
        
        return result

# إنشاء مقارن المواقع الموثوقة
reliable_sites_comparator = ReliableSitesComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع المقارنة الموثوقة"""
    
    def reliable_compare_and_send():
        """مقارنة موثوقة وإرسال"""
        
        if reliable_sites_enabled[0]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                comparison_result = loop.run_until_complete(
                    reliable_sites_comparator.reliable_comparison(item.get('name', ''), new_price)
                )
                
                # قبول العروض بثقة 45% فأكثر
                if not comparison_result['is_good_deal'] and comparison_result['confidence'] < 45:
                    print(f"🚫 رفض موثوق: {item.get('name', '')[:35]}... - {comparison_result['reason']}")
                    reliable_sites_comparator.stats['rejected_deals'] += 1
                    return
                
                # إضافة معلومات المقارنة الموثوقة
                item['reliable_analysis'] = comparison_result
                item['reliable_confidence'] = comparison_result['confidence']
                item['reliable_reason'] = comparison_result['reason']
                item['found_prices'] = comparison_result['found_prices']
                item['sites_checked'] = comparison_result['sites_checked']
                item['sites_found'] = comparison_result['sites_found']
                item['search_terms'] = comparison_result['search_terms']
                
                reliable_sites_comparator.stats['validated_deals'] += 1
                
            except Exception as e:
                print(f"⚠️ خطأ في المقارنة الموثوقة: {e}")
                # في حالة الخطأ، نسمح بالإرسال للعروض الكبيرة
                if discount_percent >= 30:
                    item['reliable_confidence'] = 65
                    item['reliable_reason'] = "خصم كبير - قبول مباشر"
                    reliable_sites_comparator.stats['validated_deals'] += 1
                else:
                    return
            finally:
                loop.close()
        
        # إرسال الرسالة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=reliable_compare_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع معلومات المقارنة الموثوقة"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات المقارنة الموثوقة
        reliable_reason = item.get('reliable_reason', '')
        reliable_confidence = item.get('reliable_confidence', 0)
        found_prices = item.get('found_prices', [])
        sites_checked = item.get('sites_checked', 0)
        sites_found = item.get('sites_found', 0)
        search_terms = item.get('search_terms', [])

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان بناءً على الثقة
        if reliable_confidence >= 80:
            headline = "🏪 <b>RELIABLE SITES BEST DEAL!</b> 🏪"
        elif reliable_confidence >= 70:
            headline = "✅ <b>RELIABLE CONFIRMED!</b>"
        elif reliable_confidence >= 60:
            headline = "⚡ <b>RELIABLE DEAL!</b>"
        elif reliable_confidence >= 50:
            headline = "💸 <b>Deal Alert!</b>"
        else:
            headline = "🛍️ <b>Price Drop!</b>"

        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
        
        # معلومات السوق
        market_info = ""
        if found_prices and len(found_prices) >= 2:
            avg_market = sum(found_prices) / len(found_prices)
            min_market = min(found_prices)
            max_market = max(found_prices)
            market_info = f"\n📊 <b>Market:</b> Avg {avg_market:,.0f} | Min {min_market:,.0f} | Max {max_market:,.0f}"
        
        # معلومات المواقع
        sites_info = ""
        if sites_checked > 0:
            sites_info = f"\n🏪 <b>Reliable Sites:</b> {sites_found} found from {sites_checked} checked"
        
        # معلومات البحث
        search_info = ""
        if search_terms:
            terms_text = ', '.join(search_terms)
            search_info = f"\n🔍 <b>Search Terms:</b> {terms_text}"
        
        # معلومات التحليل
        analysis_info = ""
        if reliable_reason:
            analysis_info = f"\n🏪 <b>Reliable Analysis:</b> {reliable_reason}"
        
        confidence_row = f"\n📈 <b>Confidence:</b> {reliable_confidence}%" if reliable_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{confidence_row}{market_info}{sites_info}{search_info}{analysis_info}

🏪 <b>Reliable Egyptian Sites Only</b>
"""

        # أزرار للمواقع الموثوقة فقط
        main_term = search_terms[0] if search_terms else product_name.replace(' ', '+').replace('&', 'and')
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Buy on Amazon", "url": url}],
                [
                    {"text": "🌙 Noon", "url": f"https://www.noon.com/egypt-en/search/?q={main_term}"},
                    {"text": "🛒 Jumia", "url": f"https://www.jumia.com.eg/catalog/?q={main_term}"}
                ],
                [
                    {"text": "🛒 Carrefour", "url": f"https://www.carrefouregypt.com/mafegy/en/search/?q={main_term}"},
                    {"text": "🏬 Spinneys", "url": f"https://spinneys.com/egypt/en/search?q={main_term}"}
                ]
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
            sites_text = f"{sites_found}/{sites_checked} مواقع موثوقة" if sites_checked > 0 else "مقارنة أساسية"
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
    """إضافة بيانات التنبيه مع المقارنة الموثوقة"""
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
    
    # إرسال مع المقارنة الموثوقة
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
            reliable_mode = "[RELIABLE]" if reliable_sites_enabled[0] else ""
            log_fn(f"🏪 {mode}{reliable_mode} Reliable: {section}, page {page_num}")
        
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
            log_fn(f"[Page {page_num}] 🏪 {new_count} NEW products")
        
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
    
    reliable_mode = "RELIABLE ON" if reliable_sites_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🏪 Reliable Start - New Products: {auto_mode}, Reliable Sites: {reliable_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Reliable scraping {sec_name}...", "🏪")
                        for page_num in range(1, pages + 1):
                            if stop_flag.get("stop"):
                                break
                            await scrape_single_page(
                                sec_name, sec_url, page_num, db,
                                log_fn=lambda m: log(m, "🏪"),
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
                            log_fn=lambda m: log(m, "🏪"),
                            discount_alert_cb=add_alert_data,
                            discount_threshold=ALERT_DISCOUNT
                        )
                        update_progress(page_num / pages)
            
            loop.run_until_complete(scrape_all())
            
        except Exception as e:
            log(f"❌ Scraper error: {e}")
        finally:
            save_db()
            log("✅ Reliable Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Reliable Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    # إحصائيات المواقع الموثوقة
    if reliable_sites_enabled[0]:
        stats = reliable_sites_comparator.stats
        log(f"🏪 Reliable Sites Stats:")
        log(f"   📊 Total Searches: {stats['total_searches']}")
        log(f"   ✅ Successful Finds: {stats['successful_finds']}")
        log(f"   📱 Validated: {stats['validated_deals']}")
        log(f"   🚫 Rejected: {stats['rejected_deals']}")
        log(f"   🧠 Cache Hits: {stats['cache_hits']}")
        
        # إحصائيات المواقع الفردية
        for site_name, site_config in reliable_sites_comparator.reliable_sites.items():
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

def toggle_reliable_sites():
    reliable_sites_enabled[0] = reliable_sites_chk.get()
    status = "RELIABLE ON" if reliable_sites_enabled[0] else "OFF"
    log(f"🏪 Reliable Sites Comparison: {status}")

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
root.title("LAQTA - Reliable Sites Only")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA - RELIABLE SITES", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="🏪 المواقع الموثوقة فقط: نون، جوميا، كارفور، سبينيز - بدون أخطاء", 
                             font=("Arial", 18, "bold"), text_color="#ffaa44")
subtitle_label.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")

controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)

section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
    width=170, font=("Arial", 15), button_color="#54fac8")
section_combo.set("Beauty")
section_combo.grid(row=0, column=0, padx=5, pady=8, sticky="ew")

pages_entry = ctk.CTkEntry(controls_frame, width=70, font=("Arial", 15), fg_color="#232d3a", text_color="#12dafb")
pages_entry.insert(0, "2")
pages_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 13), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=5, pady=8, sticky="ew")

# المنتجات الجديدة
auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 New Only", font=("Arial", 13, "bold"), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=3, padx=5, pady=8, sticky="ew")
auto_new_chk.select()

# المواقع الموثوقة
reliable_sites_chk = ctk.CTkCheckBox(controls_frame, text="🏪 Reliable Sites", font=("Arial", 13, "bold"), 
                                    text_color="#4285f4", command=toggle_reliable_sites)
reliable_sites_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
reliable_sites_chk.select()

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

start_btn = ctk.CTkButton(buttons_frame, text="🏪 Reliable Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4285f4", hover_color="#1a73e8", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#ea4335", hover_color="#d93025", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#34a853", hover_color="#137333", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Reliable Stats", command=show_stats, width=btn_w, height=btn_h,
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

# رسائل ترحيب موثوقة
log("🏪 LAQTA Reliable Sites started!", "🚀")
log("✅ Reliable Sites: نون، جوميا، كارفور، سبينيز (المواقع الموثوقة فقط)", "✨")
log("❌ Removed: سوق، بي تك، تريد لاين، مترو (مواقع بها مشاكل)", "🗑️")
log("🔍 Smart Search: مصطلحات محسنة للمواقع الموثوقة", "💡")
log("🆕 New Products: ON - منتجات جديدة فقط", "🎯")
log("📱 Expected: RELIABLE verified deals!", "🏆")

root.mainloop()