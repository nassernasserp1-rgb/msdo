#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - النظام النهائي مع الاستخراج المتقدم من جوجل (مصحح)
المشروع الكامل الاحترافي مع جميع المميزات
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
advanced_google_enabled = [True]
auto_new_products_mode = [True]

ALERT_DISCOUNT = 25
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام الاستخراج المتقدم من جوجل (مصحح)
class AdvancedGoogleExtractor:
    """مستخرج متقدم للبيانات من صفحة جوجل - نسخة مصححة"""
    
    def __init__(self):
        self.stats = {
            'total_searches': 0,
            'successful_extractions': 0,
            'products_found': 0,
            'sites_detected': 0,
            'validated_deals': 0,
            'rejected_deals': 0,
            'cache_hits': 0,
            'extraction_errors': 0
        }
        self.cache = {}
        
        # المواقع المصرية المعروفة
        self.egyptian_sites_map = {
            'amazon.eg': 'أمازون مصر',
            'noon.com': 'نون',
            'jumia.com.eg': 'جوميا',
            'jumia.com': 'جوميا',
            'carrefouregypt.com': 'كارفور',
            'carrefour.eg': 'كارفور',
            'souq.com': 'سوق',
            'b-tech.com.eg': 'بي تك',
            'btech.com.eg': 'بي تك',
            'spinneys.com': 'سبينيز',
            'tradeline.com.eg': 'تريد لاين',
            'kanbkam.com': 'كانبكام',
            'aliexpress.com': 'علي اكسبرس'
        }
    
    def optimize_search_term(self, product_name: str) -> str:
        """تحسين مصطلح البحث للحصول على أفضل النتائج من جوجل"""
        
        # استخراج العلامة التجارية
        brands = {
            'samsung': 'سامسونج',
            'apple': 'ابل', 
            'iphone': 'ايفون',
            'xiaomi': 'شاومي',
            'sony': 'سوني',
            'lg': 'ال جي',
            'canon': 'كانون',
            'hp': 'اتش بي',
            'vaseline': 'فازلين',
            'nivea': 'نيفيا',
            'axe': 'اكس',
            'dove': 'دوف',
            'care': 'كير'
        }
        
        name_lower = product_name.lower()
        
        # البحث عن العلامة التجارية
        brand_found = ""
        for brand_en, brand_ar in brands.items():
            if brand_en in name_lower:
                brand_found = brand_ar
                break
        
        # استخراج أرقام مهمة
        important_numbers = re.findall(r'\b(\d+(?:gb|ml|mm|w|mah)?)\b', name_lower)
        
        # استخراج كلمات مهمة
        important_words = []
        for word in product_name.split():
            clean_word = re.sub(r'[^\w\u0600-\u06FF]', '', word)
            if (len(clean_word) > 3 and 
                clean_word.lower() not in ['amazon', 'choice', 'brand', 'original', 'with', 'from']):
                important_words.append(clean_word)
            if len(important_words) >= 4:
                break
        
        # بناء مصطلح البحث
        search_parts = []
        
        if brand_found:
            search_parts.append(brand_found)
        
        if important_numbers:
            search_parts.extend(important_numbers[:2])
        
        if important_words and not brand_found:
            search_parts.extend(important_words[:3])
        elif important_words:
            search_parts.extend(important_words[:2])
        
        search_term = ' '.join(search_parts) + " سعر مصر"
        return search_term.strip()
    
    async def extract_google_shopping_results(self, product_name: str, amazon_price: float) -> dict:
        """استخراج متقدم من نتائج جوجل للتسوق"""
        
        search_term = self.optimize_search_term(product_name)
        cache_key = f"advanced_extract_{search_term}_{amazon_price}"
        
        # فحص الكاش
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        print(f"🔍 استخراج متقدم: {product_name[:45]}...")
        print(f"   🔎 مصطلح محسن: '{search_term}'")
        
        result = {
            'amazon_price': amazon_price,
            'extracted_products': [],
            'market_data': {},
            'is_good_deal': False,
            'confidence_score': 0,
            'recommendation': 'لم يتم العثور على بيانات',
            'extraction_details': {
                'search_term': search_term,
                'extraction_method': 'none',
                'sites_found': 0,
                'prices_found': 0
            }
        }
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox', 
                        '--disable-dev-shm-usage',
                        '--disable-images',
                        '--window-size=1920,1080',
                        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    ]
                )
                
                context = await browser.new_context()
                page = await context.new_page()
                
                # تجربة عدة استراتيجيات بحث
                search_urls = [
                    f"https://www.google.com/search?q={search_term.replace(' ', '+')}&hl=ar&gl=EG",
                    f"https://www.google.com/search?q={search_term.replace(' ', '+')}&tbm=shop&hl=ar&gl=EG",
                    f"https://www.google.com.eg/search?q={search_term.replace(' ', '+')}&hl=ar"
                ]
                
                extraction_successful = False
                
                for strategy_idx, google_url in enumerate(search_urls):
                    try:
                        print(f"   📡 استراتيجية {strategy_idx + 1}: البحث في جوجل...")
                        
                        await page.goto(google_url, timeout=15000)
                        await page.wait_for_timeout(4000)
                        
                        # استخراج البيانات المهيكلة
                        extracted_data = await page.evaluate("""
                            () => {
                                const products = [];
                                
                                // المواقع المصرية
                                const egyptianSites = [
                                    'amazon.eg', 'noon.com', 'jumia.com.eg', 'jumia.com',
                                    'carrefouregypt.com', 'carrefour.eg', 'souq.com', 
                                    'b-tech.com.eg', 'btech.com.eg', 'spinneys.com',
                                    'tradeline.com.eg', 'kanbkam.com', 'aliexpress.com'
                                ];
                                
                                // أنماط الأسعار
                                const pricePatterns = [
                                    /‏?([0-9,]+(?:\\.[0-9]+)?)\\s*جنيه/g,
                                    /السعر الحالي هو[.\\s]*‏?([0-9,]+(?:\\.[0-9]+)?)\\s*جنيه/g,
                                    /([0-9,]+(?:\\.[0-9]+)?)\\s*(?:جنية مصرى|جنيه مصري|EGP)/g,
                                    /([0-9,]+(?:\\.[0-9]+)?)\\s*(?:ج\\.م\\.|جم|LE)/g
                                ];
                                
                                // أنواع العناصر
                                const resultSelectors = [
                                    '.g', '.yuRUbf', '.tF2Cxc', '.MjjYud',
                                    '.commercial-unit', '.pla-unit', '.shopping-carousel-item',
                                    '.sh-dgr__content', '.PLla-d'
                                ];
                                
                                for (const selector of resultSelectors) {
                                    const elements = document.querySelectorAll(selector);
                                    
                                    elements.forEach((element, index) => {
                                        if (index >= 20) return;
                                        
                                        try {
                                            const elementText = element.textContent || '';
                                            const elementHTML = element.innerHTML || '';
                                            
                                            if (elementText.length < 50) return;
                                            
                                            // استخراج الأسعار
                                            const foundPrices = new Set();
                                            for (const pattern of pricePatterns) {
                                                const matches = Array.from(elementText.matchAll(pattern));
                                                for (const match of matches) {
                                                    const price = parseFloat(match[1].replace(/,/g, ''));
                                                    if (price >= 20 && price <= 100000) {
                                                        foundPrices.add(price);
                                                    }
                                                }
                                            }
                                            
                                            // استخراج المواقع
                                            const foundSites = new Set();
                                            const foundLinks = new Set();
                                            
                                            for (const site of egyptianSites) {
                                                if (elementText.includes(site) || elementHTML.includes(site)) {
                                                    foundSites.add(site);
                                                }
                                            }
                                            
                                            // البحث في الروابط
                                            const links = element.querySelectorAll('a[href]');
                                            links.forEach(link => {
                                                const href = link.href || '';
                                                for (const site of egyptianSites) {
                                                    if (href.includes(site)) {
                                                        foundSites.add(site);
                                                        foundLinks.add(href);
                                                    }
                                                }
                                            });
                                            
                                            // استخراج العنوان
                                            const titleSelectors = ['h3', 'h2', '.LC20lb', '.DKV0Md'];
                                            let title = '';
                                            for (const titleSel of titleSelectors) {
                                                const titleEl = element.querySelector(titleSel);
                                                if (titleEl && titleEl.textContent.trim()) {
                                                    title = titleEl.textContent.trim();
                                                    break;
                                                }
                                            }
                                            
                                            // إذا وجدنا أسعار ومواقع مصرية
                                            if (foundPrices.size > 0 && foundSites.size > 0) {
                                                products.push({
                                                    prices: Array.from(foundPrices).sort((a, b) => a - b),
                                                    sites: Array.from(foundSites),
                                                    links: Array.from(foundLinks),
                                                    title: title || 'بدون عنوان',
                                                    description: elementText.slice(0, 150),
                                                    selector_used: selector
                                                });
                                            }
                                            
                                        } catch (e) {
                                            // تجاهل الأخطاء
                                        }
                                    });
                                    
                                    if (products.length >= 8) break;
                                }
                                
                                return products;
                            }
                        """)
                        
                        if extracted_data and len(extracted_data) > 0:
                            result['extracted_products'] = extracted_data
                            result['extraction_details']['extraction_method'] = f'strategy_{strategy_idx + 1}'
                            
                            print(f"      ✅ استخراج ناجح: {len(extracted_data)} منتجات")
                            extraction_successful = True
                            break  # نجح الاستخراج، نتوقف
                        else:
                            print(f"      ⚪ لا توجد منتجات مستخرجة")
                    
                    except Exception as e:
                        print(f"      ❌ خطأ في الاستراتيجية {strategy_idx + 1}: {e}")
                        continue
                
                await browser.close()
                
                # تحليل البيانات المستخرجة
                if extraction_successful and result['extracted_products']:
                    # تجميع جميع الأسعار والمواقع
                    all_prices = []
                    all_sites = []
                    site_prices = {}
                    
                    for product in result['extracted_products']:
                        all_prices.extend(product['prices'])
                        all_sites.extend(product['sites'])
                        
                        # ربط المواقع بالأسعار
                        for site in product['sites']:
                            if site not in site_prices:
                                site_prices[site] = []
                            site_prices[site].extend(product['prices'])
                    
                    # إزالة التكرار وفلترة
                    unique_prices = sorted(list(set(all_prices)))
                    unique_sites = list(set(all_sites))
                    
                    # فلترة الأسعار الشاذة
                    if len(unique_prices) > 4:
                        median_price = statistics.median(unique_prices)
                        filtered_prices = []
                        for price in unique_prices:
                            if 0.15 * median_price <= price <= 6 * median_price:
                                filtered_prices.append(price)
                        
                        if len(filtered_prices) >= 3:
                            unique_prices = filtered_prices
                    
                    # تحليل السوق
                    if len(unique_prices) >= 2:
                        avg_market_price = statistics.mean(unique_prices)
                        min_market_price = min(unique_prices)
                        max_market_price = max(unique_prices)
                        median_market_price = statistics.median(unique_prices)
                        
                        # حساب ترتيب أمازون
                        amazon_rank = sum(1 for price in unique_prices if price > amazon_price) + 1
                        total_competitors = len(unique_prices)
                        
                        # حساب الفروق
                        vs_avg_diff = ((avg_market_price - amazon_price) / avg_market_price) * 100
                        vs_min_diff = ((min_market_price - amazon_price) / min_market_price) * 100
                        vs_median_diff = ((median_market_price - amazon_price) / median_market_price) * 100
                        
                        result['market_data'] = {
                            'avg_price': avg_market_price,
                            'min_price': min_market_price,
                            'max_price': max_market_price,
                            'median_price': median_market_price,
                            'amazon_rank': amazon_rank,
                            'total_competitors': total_competitors,
                            'vs_avg_diff': vs_avg_diff,
                            'vs_min_diff': vs_min_diff,
                            'vs_median_diff': vs_median_diff,
                            'market_range': max_market_price - min_market_price,
                            'sites_count': len(unique_sites),
                            'site_prices': site_prices
                        }
                        
                        result['extraction_details']['sites_found'] = len(unique_sites)
                        result['extraction_details']['prices_found'] = len(unique_prices)
                        
                        # حساب نقاط الثقة
                        confidence_score = 40
                        confidence_reasons = []
                        
                        # عامل الترتيب
                        if amazon_rank == 1:
                            rank_points = 35
                            confidence_reasons.append(f"الأرخص في السوق ({total_competitors} منافس)")
                        elif amazon_rank == 2:
                            rank_points = 25
                            confidence_reasons.append(f"ثاني أرخص سعر ({total_competitors} منافس)")
                        elif amazon_rank <= 3:
                            rank_points = 15
                            confidence_reasons.append(f"ثالث أرخص سعر ({total_competitors} منافس)")
                        elif amazon_rank <= total_competitors * 0.5:
                            rank_points = 10
                            confidence_reasons.append(f"في النصف الأرخص ({amazon_rank}/{total_competitors})")
                        else:
                            rank_points = -10
                            confidence_reasons.append(f"ترتيب متأخر ({amazon_rank}/{total_competitors})")
                        
                        confidence_score += rank_points
                        
                        # عامل المتوسط
                        if vs_avg_diff > 20:
                            avg_points = 25
                            confidence_reasons.append(f"أرخص بـ {vs_avg_diff:.0f}% من المتوسط")
                        elif vs_avg_diff > 10:
                            avg_points = 15
                            confidence_reasons.append(f"أرخص بـ {vs_avg_diff:.0f}% من المتوسط")
                        elif vs_avg_diff > 0:
                            avg_points = 10
                            confidence_reasons.append(f"أرخص من المتوسط بـ {vs_avg_diff:.0f}%")
                        elif vs_avg_diff > -10:
                            avg_points = 5
                            confidence_reasons.append(f"قريب من المتوسط ({vs_avg_diff:+.0f}%)")
                        else:
                            avg_points = -15
                            confidence_reasons.append(f"أغلى من المتوسط بـ {abs(vs_avg_diff):.0f}%")
                        
                        confidence_score += avg_points
                        
                        # عامل عدد المواقع
                        sites_count = len(unique_sites)
                        if sites_count >= 5:
                            sites_points = 20
                        elif sites_count >= 4:
                            sites_points = 15
                        elif sites_count >= 3:
                            sites_points = 10
                        elif sites_count >= 2:
                            sites_points = 5
                        else:
                            sites_points = 0
                        
                        confidence_score += sites_points
                        
                        # عامل جودة الاستخراج
                        products_count = len(result['extracted_products'])
                        if products_count >= 5:
                            extraction_points = 15
                        elif products_count >= 3:
                            extraction_points = 10
                        else:
                            extraction_points = 5
                        
                        confidence_score += extraction_points
                        
                        # تحديد النقاط النهائية
                        result['confidence_score'] = max(0, min(100, confidence_score))
                        
                        # تحديد التوصية
                        if result['confidence_score'] >= 85:
                            result['is_good_deal'] = True
                            result['recommendation'] = f"🔥 عرض ممتاز! {confidence_reasons[0]}"
                        elif result['confidence_score'] >= 70:
                            result['is_good_deal'] = True
                            result['recommendation'] = f"✅ عرض جيد! {confidence_reasons[0]}"
                        elif result['confidence_score'] >= 55:
                            result['is_good_deal'] = True
                            result['recommendation'] = f"⚠️ عرض مقبول! {confidence_reasons[0]}"
                        else:
                            result['is_good_deal'] = False
                            result['recommendation'] = f"❌ عرض ضعيف! {confidence_reasons[0]}"
                        
                        # طباعة التحليل
                        print(f"   📊 تحليل السوق المتقدم:")
                        print(f"      💰 متوسط السوق: {avg_market_price:,.0f} EGP")
                        print(f"      📉 أقل سعر: {min_market_price:,.0f} EGP")
                        print(f"      📈 أعلى سعر: {max_market_price:,.0f} EGP")
                        print(f"      📊 الوسيط: {median_market_price:,.0f} EGP")
                        print(f"      🎯 أمازون: {amazon_price:,.0f} EGP (ترتيب {amazon_rank})")
                        print(f"      📈 الفرق عن المتوسط: {vs_avg_diff:+.1f}%")
                        print(f"      🏆 نقاط الثقة: {result['confidence_score']}/100")
                        print(f"      🌐 المواقع: {len(unique_sites)} موقع")
                        print(f"      📱 المنتجات: {len(result['extracted_products'])} منتج")
                        
                        # طباعة تفاصيل المواقع
                        print(f"   🏪 تفاصيل المواقع:")
                        for site, prices in site_prices.items():
                            site_name = self.egyptian_sites_map.get(site, site)
                            avg_site_price = sum(prices) / len(prices) if prices else 0
                            print(f"      🌐 {site_name}: {len(prices)} أسعار، متوسط {avg_site_price:.0f}")
                        
                        print(f"   🎯 التوصية: {result['recommendation']}")
                        
                        # إحصائيات النجاح
                        self.stats['successful_extractions'] += 1
                        self.stats['products_found'] += len(result['extracted_products'])
                        self.stats['sites_detected'] += len(unique_sites)
                
                # حفظ في الكاش
                if extraction_successful:
                    self.cache[cache_key] = result
                
        except Exception as e:
            print(f"   ❌ خطأ في الاستخراج المتقدم: {e}")
            self.stats['extraction_errors'] += 1
        
        finally:
            self.stats['total_searches'] += 1
        
        return result

# إنشاء مستخرج جوجل المتقدم
advanced_extractor = AdvancedGoogleExtractor()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع الاستخراج المتقدم من جوجل"""
    
    def advanced_google_extract_and_send():
        """استخراج متقدم من جوجل وإرسال"""
        
        if advanced_google_enabled[0]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                extraction_result = loop.run_until_complete(
                    advanced_extractor.extract_google_shopping_results(item.get('name', ''), new_price)
                )
                
                # قبول العروض بثقة 50% فأكثر
                if not extraction_result['is_good_deal'] and extraction_result['confidence_score'] < 50:
                    print(f"🚫 رفض متقدم: {item.get('name', '')[:35]}... - {extraction_result['recommendation']}")
                    advanced_extractor.stats['rejected_deals'] += 1
                    return
                
                # إضافة معلومات الاستخراج المتقدم
                item['google_extraction'] = extraction_result
                item['google_confidence'] = extraction_result['confidence_score']
                item['google_recommendation'] = extraction_result['recommendation']
                item['market_data'] = extraction_result['market_data']
                item['extracted_products'] = extraction_result['extracted_products']
                item['extraction_details'] = extraction_result['extraction_details']
                
                advanced_extractor.stats['validated_deals'] += 1
                
            except Exception as e:
                print(f"⚠️ خطأ في الاستخراج المتقدم: {e}")
                # في حالة الخطأ، نسمح بالإرسال للعروض الكبيرة
                if discount_percent >= 35:
                    item['google_confidence'] = 60
                    item['google_recommendation'] = "خصم كبير - قبول مباشر"
                    advanced_extractor.stats['validated_deals'] += 1
                else:
                    return
            finally:
                loop.close()
        
        # إرسال الرسالة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=advanced_google_extract_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع معلومات الاستخراج المتقدم"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات الاستخراج المتقدم
        google_recommendation = item.get('google_recommendation', '')
        google_confidence = item.get('google_confidence', 0)
        market_data = item.get('market_data', {})
        extracted_products = item.get('extracted_products', [])
        extraction_details = item.get('extraction_details', {})

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان بناءً على الثقة
        if google_confidence >= 85:
            headline = "🔥 <b>GOOGLE ADVANCED VERIFIED!</b> 🔥"
        elif google_confidence >= 75:
            headline = "✅ <b>GOOGLE ADVANCED CONFIRMED!</b>"
        elif google_confidence >= 65:
            headline = "⚡ <b>GOOGLE ADVANCED DEAL!</b>"
        elif google_confidence >= 55:
            headline = "💸 <b>Deal Alert!</b>"
        else:
            headline = "🛍️ <b>Price Drop!</b>"

        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
        
        # معلومات السوق
        market_info = ""
        if market_data:
            avg_price = market_data.get('avg_price', 0)
            min_price = market_data.get('min_price', 0)
            max_price = market_data.get('max_price', 0)
            amazon_rank = market_data.get('amazon_rank', 0)
            total_competitors = market_data.get('total_competitors', 0)
            sites_count = market_data.get('sites_count', 0)
            
            if avg_price > 0:
                market_info = f"\n📊 <b>Market:</b> Avg {avg_price:,.0f} | Min {min_price:,.0f} | Max {max_price:,.0f}"
            if amazon_rank > 0 and total_competitors > 0:
                market_info += f"\n🏆 <b>Rank:</b> {amazon_rank} of {total_competitors} prices from {sites_count} sites"
        
        # معلومات الاستخراج
        extraction_info = ""
        if extraction_details:
            method = extraction_details.get('extraction_method', 'unknown')
            sites_found = extraction_details.get('sites_found', 0)
            prices_found = extraction_details.get('prices_found', 0)
            
            extraction_info = f"\n🔍 <b>Extraction:</b> {method} - {prices_found} prices from {sites_found} sites"
        
        # معلومات التوصية
        recommendation_info = ""
        if google_recommendation:
            recommendation_info = f"\n🎯 <b>Google Advanced:</b> {google_recommendation}"
        
        confidence_row = f"\n📈 <b>Confidence:</b> {google_confidence}%" if google_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{confidence_row}{market_info}{extraction_info}{recommendation_info}

🔍 <b>Google Advanced Extraction System</b>
"""

        # أزرار ذكية
        search_term = extraction_details.get('search_term', product_name)
        clean_search = search_term.replace(' سعر مصر', '').replace(' ', '+').replace('&', 'and')
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Buy on Amazon", "url": url}],
                [
                    {"text": "🔍 Google Search", "url": f"https://www.google.com/search?q={clean_search}&hl=ar&gl=EG"},
                    {"text": "🛒 Google Shopping", "url": f"https://www.google.com/search?q={clean_search}&tbm=shop&hl=ar&gl=EG"}
                ],
                [
                    {"text": "🌙 Noon", "url": f"https://www.noon.com/egypt-en/search/?q={clean_search}"},
                    {"text": "🛒 Jumia", "url": f"https://www.jumia.com.eg/catalog/?q={clean_search}"}
                ],
                [{"text": "🛒 Carrefour", "url": f"https://www.carrefouregypt.com/mafegy/en/search/?q={clean_search}"}]
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
                        }, timeout=25
                    )
                else:
                    response = requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        data={
                            "chat_id": user_id,
                            "text": msg,
                            "parse_mode": "HTML",
                            "reply_markup": reply_markup_json
                        }, timeout=20
                    )
                
                if response.status_code == 200:
                    sent_count += 1

            except Exception as e:
                print(f"❌ خطأ إرسال للمستخدم {user_id}: {e}")
        
        if sent_count > 0:
            confidence_text = f"ثقة {google_confidence}%" if google_confidence > 0 else "استخراج أساسي"
            method_text = extraction_details.get('extraction_method', 'unknown')
            print(f"✅ تم إرسال تنبيه لـ {sent_count} مستخدم - {confidence_text} ({method_text})")

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
    """إضافة بيانات التنبيه مع الاستخراج المتقدم"""
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
    
    # إرسال مع الاستخراج المتقدم
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=25):
    """سكرابة صفحة واحدة مع الاستخراج المتقدم"""
    
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
            google_mode = "[ADVANCED GOOGLE]" if advanced_google_enabled[0] else ""
            log_fn(f"🔍 {mode}{google_mode} Advanced: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(1500)
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:8]:  # 8 منتجات للتركيز على الجودة
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
                    
                    if discount_percent >= discount_threshold and discount_percent <= 75 and price >= 35:
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
            log_fn(f"[Page {page_num}] 🔍 {new_count} NEW products")
        
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
    
    google_mode = "ADVANCED ON" if advanced_google_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🔍 Advanced Start - New Products: {auto_mode}, Advanced Google: {google_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Advanced scraping {sec_name}...", "🔍")
                        for page_num in range(1, pages + 1):
                            if stop_flag.get("stop"):
                                break
                            await scrape_single_page(
                                sec_name, sec_url, page_num, db,
                                log_fn=lambda m: log(m, "🔍"),
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
                            log_fn=lambda m: log(m, "🔍"),
                            discount_alert_cb=add_alert_data,
                            discount_threshold=ALERT_DISCOUNT
                        )
                        update_progress(page_num / pages)
            
            loop.run_until_complete(scrape_all())
            
        except Exception as e:
            log(f"❌ Scraper error: {e}")
        finally:
            save_db()
            log("✅ Advanced Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Advanced Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    # إحصائيات الاستخراج المتقدم
    if advanced_google_enabled[0]:
        stats = advanced_extractor.stats
        log(f"🔍 Advanced Google Stats:")
        log(f"   📊 Total Searches: {stats['total_searches']}")
        log(f"   ✅ Successful Extractions: {stats['successful_extractions']}")
        log(f"   📱 Validated Deals: {stats['validated_deals']}")
        log(f"   🚫 Rejected Deals: {stats['rejected_deals']}")
        log(f"   🧠 Cache Hits: {stats['cache_hits']}")
        log(f"   ❌ Extraction Errors: {stats['extraction_errors']}")
        log(f"   📱 Products Found: {stats['products_found']}")
        log(f"   🌐 Sites Detected: {stats['sites_detected']}")
        
        if stats['total_searches'] > 0:
            success_rate = (stats['successful_extractions'] / stats['total_searches']) * 100
            validation_rate = (stats['validated_deals'] / stats['total_searches']) * 100
            avg_products = stats['products_found'] / stats['total_searches']
            avg_sites = stats['sites_detected'] / stats['total_searches']
            
            log(f"   📈 Success Rate: {success_rate:.1f}%")
            log(f"   📈 Validation Rate: {validation_rate:.1f}%")
            log(f"   📊 Avg Products/Search: {avg_products:.1f}")
            log(f"   🏪 Avg Sites/Search: {avg_sites:.1f}")

def toggle_advanced_google():
    advanced_google_enabled[0] = advanced_google_chk.get()
    status = "ADVANCED ON" if advanced_google_enabled[0] else "OFF"
    log(f"🔍 Advanced Google Extraction: {status}")

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
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Last Price", "Google Confidence", "Market Analysis"])
        for asin, item in db.items():
            google_conf = item.get('google_confidence', 0)
            market_data = item.get('market_data', {})
            market_summary = f"Rank {market_data.get('amazon_rank', 'N/A')} of {market_data.get('total_competitors', 'N/A')}" if market_data else "No Analysis"
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], item["price"], google_conf, market_summary])
    log("Exported to CSV with Google analysis.", "📁")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

# ==== MAIN ROOT ====
root = ctk.CTk()
root.title("LAQTA - Advanced Google Extraction System")
root.geometry("1600x1000")
root.minsize(1400, 800)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA - ADVANCED GOOGLE", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="🔍 الاستخراج المتقدم من جوجل - استخراج الأسعار والمواقع مباشرة من صفحة جوجل", 
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

# الاستخراج المتقدم من جوجل
advanced_google_chk = ctk.CTkCheckBox(controls_frame, text="🔍 Advanced Google", font=("Arial", 13, "bold"), 
                                     text_color="#4285f4", command=toggle_advanced_google)
advanced_google_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
advanced_google_chk.select()

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

log_textbox = ctk.CTkTextbox(root, font=("Consolas", 13), fg_color="#20242f", text_color="#c2ffe3", border_width=0, height=280)
log_textbox.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="nsew")
log_textbox.configure(state="disabled")

buttons_frame = ctk.CTkFrame(root, fg_color="transparent")
buttons_frame.grid(row=5, column=0, padx=10, pady=8, sticky="ew")
buttons_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)

btn_w, btn_h = 200, 50
btn_font = ("Arial", 16, "bold")

start_btn = ctk.CTkButton(buttons_frame, text="🔍 Advanced Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4285f4", hover_color="#1a73e8", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#ea4335", hover_color="#d93025", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#34a853", hover_color="#137333", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Advanced Stats", command=show_stats, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#fbbc04", hover_color="#f9ab00", text_color="#000000")
stats_btn.grid(row=0, column=3, padx=5, pady=6, sticky="ew")

export_btn = ctk.CTkButton(buttons_frame, text="📁 Export", command=export_csv, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#12dafb", hover_color="#59ff9d", text_color="#111927")
export_btn.grid(row=0, column=4, padx=5, pady=6, sticky="ew")

clear_btn = ctk.CTkButton(buttons_frame, text="🧹 Clear", command=clear_log, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
clear_btn.grid(row=0, column=5, padx=5, pady=6, sticky="ew")

exit_btn = ctk.CTkButton(root, text="Exit ❌", command=exit_app, width=350, height=50,
    font=("Arial Black", 18), fg_color="#232d3a", hover_color="#fa1a50", text_color="#59ff9d")
exit_btn.grid(row=6, column=0, pady=(8, 15))

load_db()

# رسائل ترحيب متقدمة
log("🔍 LAQTA Advanced Google Extraction started!", "🚀")
log("🎯 Advanced Method: استخراج العناصر المهيكلة من جوجل", "✨")
log("📊 Smart Analysis: تحليل متقدم للسوق والثقة", "💡")
log("🌐 Egyptian Sites: استخراج تلقائي للمواقع المصرية", "🇪🇬")
log("🆕 New Products: ON - منتجات جديدة فقط", "🎯")
log("📱 Expected: ADVANCED verified deals from Google!", "🏆")

root.mainloop()