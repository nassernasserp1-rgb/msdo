#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - نظام متعدد المواقع مع بحث ذكي محسن
مواقع أكثر + طريقة بحث أذكى
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
multi_sites_enabled = [True]
auto_new_products_mode = [True]

ALERT_DISCOUNT = 25
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام متعدد المواقع مع بحث ذكي
class MultiSitesSmartComparator:
    """مقارن الأسعار متعدد المواقع مع بحث ذكي محسن"""
    
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
        
        # مواقع مصرية متعددة مع استراتيجيات بحث مختلفة
        self.egyptian_sites = {
            'noon': {
                'search_urls': [
                    'https://www.noon.com/egypt-en/search/?q={}',
                    'https://www.noon.com/egypt-ar/search/?q={}'
                ],
                'display_name': 'نون',
                'timeout': 10000,
                'priority': 1,
                'price_selectors': ['.priceNow', '.price-now', '.final-price', '.current-price']
            },
            'jumia': {
                'search_urls': [
                    'https://www.jumia.com.eg/catalog/?q={}',
                    'https://www.jumia.com.eg/catalog/?q={}&sort=popularity'
                ],
                'display_name': 'جوميا',
                'timeout': 10000,
                'priority': 2,
                'price_selectors': ['.prc', '.price', '.current-price', '.sale-price']
            },
            'carrefour': {
                'search_urls': [
                    'https://www.carrefouregypt.com/mafegy/en/search/?q={}',
                    'https://www.carrefouregypt.com/mafegy/ar/search/?q={}'
                ],
                'display_name': 'كارفور',
                'timeout': 8000,
                'priority': 3,
                'price_selectors': ['.price', '.current-price', '.final-price']
            },
            'btech': {
                'search_urls': [
                    'https://b-tech.com.eg/en/catalogsearch/result/?q={}',
                    'https://b-tech.com.eg/ar/catalogsearch/result/?q={}'
                ],
                'display_name': 'بي تك',
                'timeout': 8000,
                'priority': 4,
                'price_selectors': ['.price', '.regular-price', '.special-price']
            },
            'souq': {
                'search_urls': [
                    'https://egypt.souq.com/eg-en/search?q={}',
                    'https://egypt.souq.com/eg-ar/search?q={}'
                ],
                'display_name': 'سوق',
                'timeout': 8000,
                'priority': 5,
                'price_selectors': ['.price', '.current-price', '.sale-price']
            },
            'tradeline': {
                'search_urls': [
                    'https://tradeline.com.eg/search?q={}',
                    'https://tradeline.com.eg/en/search?q={}'
                ],
                'display_name': 'تريد لاين',
                'timeout': 8000,
                'priority': 6,
                'price_selectors': ['.price', '.product-price', '.current-price']
            },
            'spinneys': {
                'search_urls': [
                    'https://spinneys.com/egypt/en/search?q={}',
                    'https://spinneys.com/egypt/ar/search?q={}'
                ],
                'display_name': 'سبينيز',
                'timeout': 8000,
                'priority': 7,
                'price_selectors': ['.price', '.current-price', '.product-price']
            },
            'metro': {
                'search_urls': [
                    'https://metro-online.com/en/search?q={}',
                    'https://metro-online.com/ar/search?q={}'
                ],
                'display_name': 'مترو',
                'timeout': 8000,
                'priority': 8,
                'price_selectors': ['.price', '.product-price', '.current-price']
            }
        }
        
        # إحصائيات المواقع
        for site_name in self.egyptian_sites:
            self.stats['sites_success'][site_name] = 0
            self.stats['sites_errors'][site_name] = 0
    
    def create_smart_search_terms(self, product_name: str) -> list:
        """إنشاء مصطلحات بحث ذكية متعددة"""
        
        # علامات تجارية مهمة مع تنويعاتها
        brands_variations = {
            'samsung': ['samsung', 'galaxy'],
            'apple': ['apple', 'iphone'],
            'xiaomi': ['xiaomi', 'redmi', 'mi'],
            'sony': ['sony'],
            'lg': ['lg'],
            'canon': ['canon', 'pixma'],
            'hp': ['hp'],
            'dell': ['dell'],
            'anker': ['anker'],
            'baseus': ['baseus'],
            'joyroom': ['joyroom'],
            'ugreen': ['ugreen'],
            'kemei': ['kemei'],
            'axe': ['axe'],
            'vaseline': ['vaseline'],
            'nivea': ['nivea'],
            'loreal': ['loreal', "l'oreal"]
        }
        
        name_lower = product_name.lower()
        
        # البحث عن العلامة التجارية
        detected_brand = ""
        brand_variations = []
        
        for brand, variations in brands_variations.items():
            for variation in variations:
                if variation in name_lower:
                    detected_brand = brand
                    brand_variations = variations
                    break
            if detected_brand:
                break
        
        # استخراج معلومات مهمة
        numbers = re.findall(r'\b(\d+(?:gb|mb|ml|w|mah|inch|inc)?)\b', name_lower)
        colors = re.findall(r'\b(black|white|blue|red|green|orange|pink|gold|silver|أسود|أبيض|أزرق|أحمر)\b', name_lower)
        sizes = re.findall(r'\b(\d+(?:ml|l|kg|g|inch|inc|cm))\b', name_lower)
        
        # إنشاء مصطلحات بحث متعددة
        search_terms = []
        
        # البحث الأساسي بالعلامة التجارية والأرقام
        if detected_brand:
            if numbers:
                search_terms.append(f"{detected_brand} {' '.join(numbers[:2])}")
            search_terms.append(detected_brand)
            
            # بحث بتنويعات العلامة التجارية
            for variation in brand_variations[:2]:
                if variation != detected_brand:
                    search_terms.append(variation)
        
        # البحث بالكلمات المفتاحية
        important_words = []
        for word in product_name.split():
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if (len(clean_word) > 3 and 
                clean_word not in ['amazon', 'choice', 'original', 'brand', 'authentic', 'genuine']):
                important_words.append(clean_word)
            if len(important_words) >= 4:
                break
        
        if important_words:
            search_terms.append(' '.join(important_words[:3]))
            search_terms.append(' '.join(important_words[:2]))
        
        # بحث بالأرقام المهمة
        if numbers:
            search_terms.append(' '.join(numbers[:2]))
        
        # بحث بالألوان والأحجام
        if colors:
            search_terms.append(f"{detected_brand} {colors[0]}" if detected_brand else colors[0])
        
        if sizes:
            search_terms.append(f"{detected_brand} {sizes[0]}" if detected_brand else sizes[0])
        
        # إزالة التكرار وأخذ أفضل 3 مصطلحات
        unique_terms = []
        for term in search_terms:
            if term and term not in unique_terms and len(term.strip()) > 2:
                unique_terms.append(term.strip())
        
        return unique_terms[:3]
    
    async def advanced_site_search(self, site_name: str, site_config: dict, search_terms: list) -> list:
        """بحث متقدم في موقع واحد بعدة مصطلحات"""
        
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
                        '--disable-css',
                        '--window-size=1280,720',
                        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    ]
                )
                
                try:
                    context = await browser.new_context()
                    page = await context.new_page()
                    
                    # جرب كل مصطلح بحث
                    for term_idx, search_term in enumerate(search_terms):
                        if len(all_prices) >= 8:  # إذا وجدنا أسعار كافية، نتوقف
                            break
                        
                        # جرب كل رابط بحث للموقع
                        for url_idx, search_url_template in enumerate(site_config['search_urls']):
                            try:
                                search_url = search_url_template.format(search_term.replace(' ', '+'))
                                
                                await page.goto(search_url, timeout=site_config['timeout'])
                                await page.wait_for_timeout(2000)
                                
                                # استخراج الأسعار
                                site_prices = await page.evaluate(f"""
                                    () => {{
                                        const prices = new Set();
                                        
                                        // أنماط الأسعار المتقدمة
                                        const pricePatterns = [
                                            /([0-9,]+(?:\\.[0-9]+)?)\\s*(?:جنيه|ج\\.م\\.|EGP|LE)/gi,
                                            /(?:EGP|جنيه|ج\\.م\\.|LE)\\s*([0-9,]+(?:\\.[0-9]+)?)/gi,
                                            /([0-9,]+)\\s*ج/gi,
                                            /([0-9,]+(?:\\.[0-9]+)?)\\s*(?:ج|جم|جنية)/gi
                                        ];
                                        
                                        // البحث في النص الكامل
                                        const bodyText = document.body.innerText || '';
                                        
                                        for (const pattern of pricePatterns) {{
                                            const matches = Array.from(bodyText.matchAll(pattern));
                                            for (const match of matches) {{
                                                const price = parseFloat(match[1].replace(/,/g, ''));
                                                if (price >= 25 && price <= 100000) {{
                                                    prices.add(price);
                                                }}
                                            }}
                                        }}
                                        
                                        // البحث في عناصر الأسعار المحددة
                                        const priceSelectors = {json.dumps(site_config['price_selectors']) + [
                                            '.price', '.current-price', '.final-price', '.sale-price',
                                            '.product-price', '.amount', '.cost', '[data-price]'
                                        ]};
                                        
                                        for (const selector of priceSelectors) {{
                                            try {{
                                                const elements = document.querySelectorAll(selector);
                                                elements.forEach(element => {{
                                                    const text = element.textContent || element.getAttribute('data-price') || '';
                                                    
                                                    for (const pattern of pricePatterns) {{
                                                        const matches = Array.from(text.matchAll(pattern));
                                                        for (const match of matches) {{
                                                            const price = parseFloat(match[1].replace(/,/g, ''));
                                                            if (price >= 25 && price <= 100000) {{
                                                                prices.add(price);
                                                            }}
                                                        }}
                                                    }}
                                                }});
                                            }} catch (e) {{
                                                // تجاهل أخطاء العناصر الفردية
                                            }}
                                        }}
                                        
                                        // تحويل إلى array مرتب
                                        const sortedPrices = Array.from(prices).sort((a, b) => a - b);
                                        return sortedPrices.slice(0, 12); // أول 12 سعر
                                    }}
                                """)
                                
                                if site_prices and len(site_prices) > 0:
                                    all_prices.extend(site_prices)
                                    print(f"      ✅ {search_term} ({url_idx+1}): {len(site_prices)} أسعار")
                                    break  # إذا وجدنا أسعار، ننتقل للمصطلح التالي
                                    
                            except Exception:
                                continue
                    
                    await context.close()
                    
                except Exception as inner_e:
                    print(f"   ❌ {site_config['display_name']}: خطأ في الصفحة")
                    self.stats['sites_errors'][site_name] += 1
                
                finally:
                    await browser.close()
        
        except Exception as e:
            print(f"   ❌ {site_config['display_name']}: خطأ عام")
            self.stats['sites_errors'][site_name] += 1
        
        # إزالة التكرار وترتيب
        unique_prices = sorted(list(set(all_prices)))
        
        if unique_prices:
            self.stats['sites_success'][site_name] += 1
            print(f"   ✅ {site_config['display_name']}: {len(unique_prices)} أسعار إجمالية")
        else:
            print(f"   ⚪ {site_config['display_name']}: لا توجد أسعار")
        
        return unique_prices
    
    async def multi_sites_comparison(self, product_name: str, amazon_price: float) -> dict:
        """مقارنة متعددة المواقع مع بحث ذكي"""
        
        search_terms = self.create_smart_search_terms(product_name)
        cache_key = f"multi_{'-'.join(search_terms)}_{amazon_price}"
        
        # فحص الكاش
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        print(f"🌐 مقارنة متعددة: {search_terms}")
        
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
        
        # البحث في المواقع بأولوية (أهم 5 مواقع أولاً)
        priority_sites = sorted(self.egyptian_sites.items(), key=lambda x: x[1]['priority'])[:5]
        
        for site_name, site_config in priority_sites:
            try:
                # البحث في الموقع مع timeout محدود
                prices = await asyncio.wait_for(
                    self.advanced_site_search(site_name, site_config, search_terms),
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
            # إزالة التكرار وفلترة الأسعار
            unique_prices = sorted(list(set(all_prices)))
            
            # فلترة الأسعار الشاذة بذكاء
            if len(unique_prices) > 5:
                # إزالة أعلى وأقل 10% من الأسعار
                remove_count = max(1, len(unique_prices) // 10)
                unique_prices = unique_prices[remove_count:-remove_count]
            
            result['found_prices'] = unique_prices
            
            if len(unique_prices) >= 2:
                # تحليل الأسعار
                avg_price = statistics.mean(unique_prices)
                min_price = min(unique_prices)
                max_price = max(unique_prices)
                median_price = statistics.median(unique_prices)
                
                # حساب ترتيب أمازون
                cheaper_count = sum(1 for p in unique_prices if p > amazon_price)
                total_competitors = len(unique_prices)
                amazon_rank = total_competitors - cheaper_count + 1
                
                # حساب الفروق
                vs_avg_diff = ((avg_price - amazon_price) / avg_price) * 100
                vs_median_diff = ((median_price - amazon_price) / median_price) * 100
                
                # تحديد جودة العرض بذكاء متقدم
                confidence = 30
                
                # عوامل الثقة المتعددة
                rank_factor = (total_competitors - amazon_rank + 1) / total_competitors * 40
                avg_factor = max(0, vs_avg_diff) * 0.8
                median_factor = max(0, vs_median_diff) * 0.6
                sites_factor = min(20, result['sites_found'] * 4)
                
                confidence = min(95, 30 + rank_factor + avg_factor + median_factor + sites_factor)
                
                # تحديد الرسالة والقبول
                if amazon_rank == 1 and vs_avg_diff > 15:
                    result['reason'] = f"🔥 الأرخص من {total_competitors} أسعار بفارق كبير!"
                    result['is_good_deal'] = True
                elif amazon_rank == 1:
                    result['reason'] = f"✅ الأرخص من {total_competitors} أسعار"
                    result['is_good_deal'] = True
                elif amazon_rank == 2 and vs_avg_diff > 10:
                    result['reason'] = f"⚡ ثاني أرخص + أرخص من المتوسط بـ {vs_avg_diff:.0f}%"
                    result['is_good_deal'] = True
                elif vs_avg_diff > 20:
                    result['reason'] = f"💰 أرخص بـ {vs_avg_diff:.0f}% من المتوسط"
                    result['is_good_deal'] = True
                elif vs_avg_diff > 10:
                    result['reason'] = f"✅ أرخص بـ {vs_avg_diff:.0f}% من المتوسط"
                    result['is_good_deal'] = True
                elif amazon_rank <= total_competitors * 0.5:
                    result['reason'] = f"⚠️ ترتيب {amazon_rank} من {total_competitors} (النصف الأرخص)"
                    result['is_good_deal'] = True
                elif confidence >= 50:
                    result['reason'] = f"💸 ترتيب {amazon_rank} من {total_competitors} (مقبول)"
                    result['is_good_deal'] = True
                else:
                    result['reason'] = f"❌ ترتيب {amazon_rank} من {total_competitors}"
                    result['is_good_deal'] = False
                
                result['confidence'] = int(confidence)
                
                # طباعة النتائج
                print(f"   📊 {total_competitors} أسعار من {result['sites_found']} مواقع")
                print(f"   💰 المتوسط: {avg_price:.0f} | الوسيط: {median_price:.0f} | الأقل: {min_price:.0f} | الأعلى: {max_price:.0f}")
                print(f"   🎯 أمازون: {amazon_price:.0f} (ترتيب {amazon_rank})")
                print(f"   🏪 المواقع: {', '.join(sites_with_prices)}")
                print(f"   {result['reason']}")
                
                self.stats['successful_finds'] += 1
                
            else:
                result['confidence'] = 60
                result['reason'] = f"⚪ سعر واحد ({unique_prices[0]:.0f}) من {sites_with_prices[0]}"
                result['is_good_deal'] = True  # نقبل لأن وجدنا مقارنة
        
        self.stats['total_searches'] += 1
        
        # حفظ في الكاش
        self.cache[cache_key] = result
        
        return result

# إنشاء مقارن متعدد المواقع
multi_sites_comparator = MultiSitesSmartComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع المقارنة متعددة المواقع"""
    
    def multi_sites_compare_and_send():
        """مقارنة متعددة المواقع وإرسال"""
        
        if multi_sites_enabled[0]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                comparison_result = loop.run_until_complete(
                    multi_sites_comparator.multi_sites_comparison(item.get('name', ''), new_price)
                )
                
                # قبول العروض بثقة 45% فأكثر
                if not comparison_result['is_good_deal'] and comparison_result['confidence'] < 45:
                    print(f"🚫 رفض متعدد: {item.get('name', '')[:35]}... - {comparison_result['reason']}")
                    multi_sites_comparator.stats['rejected_deals'] += 1
                    return
                
                # إضافة معلومات المقارنة متعددة المواقع
                item['multi_analysis'] = comparison_result
                item['multi_confidence'] = comparison_result['confidence']
                item['multi_reason'] = comparison_result['reason']
                item['found_prices'] = comparison_result['found_prices']
                item['sites_checked'] = comparison_result['sites_checked']
                item['sites_found'] = comparison_result['sites_found']
                item['search_terms'] = comparison_result['search_terms']
                
                multi_sites_comparator.stats['validated_deals'] += 1
                
            except Exception as e:
                print(f"⚠️ خطأ في المقارنة متعددة المواقع: {e}")
                # في حالة الخطأ، نسمح بالإرسال للعروض الكبيرة
                if discount_percent >= 30:
                    item['multi_confidence'] = 65
                    item['multi_reason'] = "خصم كبير - قبول مباشر"
                    multi_sites_comparator.stats['validated_deals'] += 1
                else:
                    return
            finally:
                loop.close()
        
        # إرسال الرسالة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=multi_sites_compare_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع معلومات المقارنة متعددة المواقع"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات المقارنة متعددة المواقع
        multi_reason = item.get('multi_reason', '')
        multi_confidence = item.get('multi_confidence', 0)
        found_prices = item.get('found_prices', [])
        sites_checked = item.get('sites_checked', 0)
        sites_found = item.get('sites_found', 0)
        search_terms = item.get('search_terms', [])

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان بناءً على الثقة
        if multi_confidence >= 85:
            headline = "🌐 <b>MULTI-SITES VERIFIED BEST!</b> 🌐"
        elif multi_confidence >= 75:
            headline = "✅ <b>MULTI-SITES CONFIRMED!</b>"
        elif multi_confidence >= 65:
            headline = "⚡ <b>MULTI-SITES DEAL!</b>"
        elif multi_confidence >= 55:
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
            median_market = statistics.median(found_prices)
            market_info = f"\n📊 <b>Market:</b> Avg {avg_market:,.0f} | Med {median_market:,.0f} | Min {min_market:,.0f}"
        
        # معلومات المواقع
        sites_info = ""
        if sites_checked > 0:
            sites_info = f"\n🌐 <b>Sites:</b> {sites_found} found prices from {sites_checked} checked"
        
        # معلومات البحث الذكي
        search_info = ""
        if search_terms:
            terms_text = ', '.join(search_terms[:2])
            search_info = f"\n🔍 <b>Smart Terms:</b> {terms_text}"
        
        # معلومات التحليل
        analysis_info = ""
        if multi_reason:
            analysis_info = f"\n🌐 <b>Multi Analysis:</b> {multi_reason}"
        
        confidence_row = f"\n📈 <b>Confidence:</b> {multi_confidence}%" if multi_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{confidence_row}{market_info}{sites_info}{search_info}{analysis_info}

🌐 <b>Multi Egyptian Sites Smart Comparison</b>
"""

        # أزرار متعددة المواقع مع بحث ذكي
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
                    {"text": "🔧 B-Tech", "url": f"https://b-tech.com.eg/en/catalogsearch/result/?q={main_term}"}
                ],
                [
                    {"text": "🏪 Souq", "url": f"https://egypt.souq.com/eg-en/search?q={main_term}"},
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
            sites_text = f"{sites_found}/{sites_checked} مواقع" if sites_checked > 0 else "مقارنة أساسية"
            terms_text = f"({len(search_terms)} terms)" if search_terms else ""
            print(f"✅ تم إرسال تنبيه لـ {sent_count} مستخدم - {sites_text} {terms_text}")

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
    """إضافة بيانات التنبيه مع المقارنة متعددة المواقع"""
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
    
    # إرسال مع المقارنة متعددة المواقع
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
            multi_mode = "[MULTI SITES]" if multi_sites_enabled[0] else ""
            log_fn(f"🌐 {mode}{multi_mode} Multi: {section}, page {page_num}")
        
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
            log_fn(f"[Page {page_num}] 🌐 {new_count} NEW products")
        
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
    
    multi_mode = "MULTI ON" if multi_sites_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🌐 Multi Start - New Products: {auto_mode}, Multi Sites: {multi_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Multi scraping {sec_name}...", "🌐")
                        for page_num in range(1, pages + 1):
                            if stop_flag.get("stop"):
                                break
                            await scrape_single_page(
                                sec_name, sec_url, page_num, db,
                                log_fn=lambda m: log(m, "🌐"),
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
                            log_fn=lambda m: log(m, "🌐"),
                            discount_alert_cb=add_alert_data,
                            discount_threshold=ALERT_DISCOUNT
                        )
                        update_progress(page_num / pages)
            
            loop.run_until_complete(scrape_all())
            
        except Exception as e:
            log(f"❌ Scraper error: {e}")
        finally:
            save_db()
            log("✅ Multi Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Multi Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    # إحصائيات المقارنة متعددة المواقع
    if multi_sites_enabled[0]:
        stats = multi_sites_comparator.stats
        log(f"🌐 Multi Sites Stats:")
        log(f"   📊 Total Searches: {stats['total_searches']}")
        log(f"   ✅ Successful Finds: {stats['successful_finds']}")
        log(f"   📱 Validated: {stats['validated_deals']}")
        log(f"   🚫 Rejected: {stats['rejected_deals']}")
        log(f"   🧠 Cache Hits: {stats['cache_hits']}")
        
        # إحصائيات المواقع الفردية
        for site_name, site_config in list(multi_sites_comparator.egyptian_sites.items())[:5]:
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

def toggle_multi_sites():
    multi_sites_enabled[0] = multi_sites_chk.get()
    status = "MULTI ON" if multi_sites_enabled[0] else "OFF"
    log(f"🌐 Multi Sites Comparison: {status}")

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
root.title("LAQTA - Multi Sites Smart Comparison")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA - MULTI SITES", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="🌐 مواقع أكثر + بحث ذكي: نون، جوميا، كارفور، بي تك، سوق، تريد لاين، سبينيز، مترو", 
                             font=("Arial", 18, "bold"), text_color="#ffaa44")
subtitle_label.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")

controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)

section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
    width=170, font=("Arial", 15), button_color="#54fac8")
section_combo.set("Beauty")  # نبدأ بـ Beauty للاختبار
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

# المقارنة متعددة المواقع
multi_sites_chk = ctk.CTkCheckBox(controls_frame, text="🌐 Multi Sites", font=("Arial", 13, "bold"), 
                                 text_color="#4285f4", command=toggle_multi_sites)
multi_sites_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
multi_sites_chk.select()

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

start_btn = ctk.CTkButton(buttons_frame, text="🌐 Multi Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4285f4", hover_color="#1a73e8", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#ea4335", hover_color="#d93025", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#34a853", hover_color="#137333", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Multi Stats", command=show_stats, width=btn_w, height=btn_h,
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

# رسائل ترحيب متعددة المواقع
log("🌐 LAQTA Multi Sites started!", "🚀")
log("🏪 8 Sites: نون، جوميا، كارفور، بي تك، سوق، تريد لاين، سبينيز، مترو", "✨")
log("🔍 Smart Search: مصطلحات متعددة لكل منتج", "💡")
log("🌐 Multi URLs: عدة روابط لكل موقع (عربي + إنجليزي)", "🔄")
log("🆕 New Products: ON - منتجات جديدة فقط", "🎯")
log("📱 Expected: MULTI-SITES verified deals!", "🏆")

root.mainloop()