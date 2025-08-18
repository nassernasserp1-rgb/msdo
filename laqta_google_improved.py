#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - نظام المقارنة المحسن عن طريق جوجل (محسن ومطور)
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
google_comparison_enabled = [True]
auto_new_products_mode = [True]

ALERT_DISCOUNT = 25
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام مقارنة جوجل المحسن
class ImprovedGoogleComparator:
    """مقارن الأسعار عن طريق جوجل - نسخة محسنة ومطورة"""
    
    def __init__(self):
        self.stats = {
            'total_comparisons': 0,
            'successful_comparisons': 0,
            'validated_deals': 0,
            'rejected_deals': 0,
            'cache_hits': 0,
            'google_errors': 0
        }
        self.cache = {}
        
        # كلمات مفتاحية للمواقع المصرية
        self.egyptian_sites = {
            'jumia': ['jumia.com.eg', 'جوميا'],
            'noon': ['noon.com', 'نون'],
            'souq': ['souq.com', 'سوق'],
            'btech': ['b-tech.com.eg', 'بي تك', 'btech'],
            'tradeline': ['tradeline.com.eg', 'تريد لاين'],
            'cairosales': ['cairosales.com', 'كايرو سيلز'],
            'elnekhely': ['elnekhely.com', 'النخيلي'],
            'amazon': ['amazon.eg', 'أمازون مصر'],
            'carrefour': ['carrefour.eg', 'كارفور'],
            'spinneys': ['spinneys.com', 'سبينيز']
        }
    
    def extract_brand_and_model(self, product_name: str) -> tuple:
        """استخراج العلامة التجارية والموديل من اسم المنتج"""
        
        # علامات تجارية شائعة
        brands = [
            'samsung', 'apple', 'iphone', 'xiaomi', 'huawei', 'oppo', 'vivo', 'realme',
            'sony', 'lg', 'canon', 'nikon', 'hp', 'dell', 'lenovo', 'asus', 'acer',
            'nike', 'adidas', 'puma', 'anker', 'baseus', 'ugreen', 'joyroom',
            'samsung galaxy', 'iphone 15', 'iphone 14', 'redmi', 'mi', 'galaxy'
        ]
        
        name_lower = product_name.lower()
        found_brand = ""
        
        # البحث عن العلامة التجارية
        for brand in sorted(brands, key=len, reverse=True):  # الأطول أولاً
            if brand in name_lower:
                found_brand = brand
                break
        
        # استخراج الموديل (الأرقام والحروف بعد العلامة التجارية)
        model_pattern = r'([a-z0-9\-]+(?:\s+[a-z0-9\-]+){0,2})'
        if found_brand:
            # البحث بعد العلامة التجارية
            brand_pos = name_lower.find(found_brand)
            after_brand = name_lower[brand_pos + len(found_brand):].strip()
            model_match = re.search(model_pattern, after_brand)
            model = model_match.group(1) if model_match else ""
        else:
            # إذا لم نجد علامة تجارية، نأخذ أول كلمتين
            words = name_lower.split()[:2]
            found_brand = words[0] if words else ""
            model = words[1] if len(words) > 1 else ""
        
        return found_brand.strip(), model.strip()
    
    def create_smart_search_terms(self, product_name: str) -> list:
        """إنشاء مصطلحات بحث ذكية متعددة"""
        
        brand, model = self.extract_brand_and_model(product_name)
        
        search_terms = []
        
        # البحث الأساسي
        basic_search = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', product_name.lower())
        basic_words = [w for w in basic_search.split() if len(w) > 2][:4]
        if basic_words:
            search_terms.append(' '.join(basic_words) + " سعر مصر")
        
        # البحث بالعلامة التجارية والموديل
        if brand and model:
            search_terms.append(f"{brand} {model} price egypt")
            search_terms.append(f"{brand} {model} سعر")
        
        # البحث بالعلامة التجارية فقط إذا كانت مشهورة
        famous_brands = ['samsung', 'apple', 'iphone', 'xiaomi', 'sony', 'canon', 'hp']
        if brand in famous_brands:
            search_terms.append(f"{brand} سعر مصر")
        
        # إزالة التكرار
        unique_terms = []
        for term in search_terms:
            if term not in unique_terms and len(term) > 5:
                unique_terms.append(term)
        
        return unique_terms[:3]  # أفضل 3 مصطلحات بحث
    
    async def advanced_google_search(self, search_term: str) -> list:
        """بحث متقدم في جوجل مع تحسينات"""
        
        results = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-images',
                        '--disable-javascript',  # تعطيل JS للسرعة
                        '--window-size=1920,1080',
                        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    ]
                )
                
                context = await browser.new_context()
                page = await context.new_page()
                
                # تجربة عدة روابط جوجل مختلفة
                google_urls = [
                    f"https://www.google.com/search?q={search_term.replace(' ', '+')}&tbm=shop&hl=ar&gl=EG",
                    f"https://www.google.com.eg/search?q={search_term.replace(' ', '+')}&tbm=shop",
                    f"https://www.google.com/search?q={search_term.replace(' ', '+')}+price+egypt&tbm=shop"
                ]
                
                for google_url in google_urls:
                    try:
                        await page.goto(google_url, timeout=12000)
                        await page.wait_for_timeout(3000)
                        
                        # استخراج النتائج بطرق متعددة
                        products_data = await page.evaluate("""
                            () => {
                                const results = [];
                                
                                // محاولة عدة selectors مختلفة لجوجل شوبينج
                                const selectors = [
                                    '[data-docid]',
                                    '.sh-dgr__content',
                                    '.PLla-d',
                                    '.sh-dlr__list-result',
                                    '.mnr-c',
                                    '.sh-dlr__content',
                                    '[jscontroller="SC7lYd"]'
                                ];
                                
                                let productElements = [];
                                
                                for (const selector of selectors) {
                                    productElements = document.querySelectorAll(selector);
                                    if (productElements.length > 0) {
                                        console.log(`Found ${productElements.length} products with selector: ${selector}`);
                                        break;
                                    }
                                }
                                
                                // إذا لم نجد منتجات، نبحث في النتائج العادية
                                if (productElements.length === 0) {
                                    productElements = document.querySelectorAll('.g, .tF2Cxc, .MjjYud');
                                }
                                
                                Array.from(productElements).slice(0, 20).forEach((element, index) => {
                                    try {
                                        // البحث عن اسم المنتج
                                        const nameSelectors = [
                                            'h3', 'h4', '.sh-dlr__product-title', 
                                            '.translate-content', '[role="heading"]',
                                            '.LC20lb', '.DKV0Md'
                                        ];
                                        
                                        let productName = '';
                                        for (const selector of nameSelectors) {
                                            const nameEl = element.querySelector(selector);
                                            if (nameEl && nameEl.textContent.trim()) {
                                                productName = nameEl.textContent.trim();
                                                break;
                                            }
                                        }
                                        
                                        // البحث عن السعر بطرق متعددة
                                        const priceSelectors = [
                                            '.a30cxb', '.notranslate', '.sh-dlr__price',
                                            '.price', '.current-price', '.final-price',
                                            '.sh-osd__price', '.translate-content'
                                        ];
                                        
                                        let price = null;
                                        let priceText = '';
                                        
                                        // البحث في العناصر
                                        for (const selector of priceSelectors) {
                                            const priceEl = element.querySelector(selector);
                                            if (priceEl) {
                                                priceText = priceEl.textContent;
                                                break;
                                            }
                                        }
                                        
                                        // إذا لم نجد، نبحث في النص الكامل
                                        if (!priceText) {
                                            priceText = element.textContent || '';
                                        }
                                        
                                        // استخراج السعر من النص
                                        const pricePatterns = [
                                            /([0-9,]+(?:\.[0-9]+)?)\s*(?:جنيه|EGP|ج\.م|LE)/gi,
                                            /(?:EGP|جنيه|ج\.م|LE)\s*([0-9,]+(?:\.[0-9]+)?)/gi,
                                            /([0-9,]+)\s*(?:جنيه|EGP)/gi
                                        ];
                                        
                                        for (const pattern of pricePatterns) {
                                            const matches = Array.from(priceText.matchAll(pattern));
                                            if (matches.length > 0) {
                                                const extractedPrice = parseFloat(matches[0][1].replace(/,/g, ''));
                                                if (extractedPrice > 20 && extractedPrice < 500000) {
                                                    price = extractedPrice;
                                                    break;
                                                }
                                            }
                                        }
                                        
                                        // البحث عن اسم المتجر
                                        const storeSelectors = [
                                            '.sh-dlr__merchant', '.merchant', '.store-name',
                                            '.a25r0b', '.sh-dlr__merchant-name', '.cite'
                                        ];
                                        
                                        let storeName = '';
                                        for (const selector of storeSelectors) {
                                            const storeEl = element.querySelector(selector);
                                            if (storeEl && storeEl.textContent.trim()) {
                                                storeName = storeEl.textContent.trim();
                                                break;
                                            }
                                        }
                                        
                                        // إذا لم نجد متجر، نبحث في الروابط
                                        if (!storeName) {
                                            const linkEl = element.querySelector('a[href]');
                                            if (linkEl) {
                                                const href = linkEl.href;
                                                if (href.includes('jumia')) storeName = 'Jumia';
                                                else if (href.includes('noon')) storeName = 'Noon';
                                                else if (href.includes('souq')) storeName = 'Souq';
                                                else if (href.includes('btech') || href.includes('b-tech')) storeName = 'B-Tech';
                                                else if (href.includes('amazon.eg')) storeName = 'Amazon Egypt';
                                            }
                                        }
                                        
                                        // الرابط
                                        const linkEl = element.querySelector('a[href]');
                                        const productUrl = linkEl ? linkEl.href : '';
                                        
                                        if (productName && price && storeName) {
                                            results.push({
                                                name: productName,
                                                price: price,
                                                store: storeName,
                                                url: productUrl,
                                                source: 'google_shopping',
                                                priceText: priceText
                                            });
                                        }
                                        
                                    } catch (e) {
                                        console.log('Error processing element:', e);
                                    }
                                });
                                
                                console.log(`Total results found: ${results.length}`);
                                return results;
                            }
                        """)
                        
                        if products_data and len(products_data) > 0:
                            results.extend(products_data)
                            break  # إذا وجدنا نتائج، نتوقف عن تجربة URLs أخرى
                            
                    except Exception as e:
                        print(f"   ⚠️ خطأ في URL: {e}")
                        continue
                
                await browser.close()
                
        except Exception as e:
            print(f"   ❌ خطأ في البحث: {e}")
            self.stats['google_errors'] += 1
        
        return results
    
    def filter_egyptian_results(self, results: list) -> list:
        """فلترة النتائج للمواقع المصرية فقط"""
        
        egyptian_results = []
        
        for result in results:
            store_name = result['store'].lower()
            url = result.get('url', '').lower()
            
            is_egyptian = False
            detected_store = ""
            
            # فحص اسم المتجر والرابط
            for store_key, keywords in self.egyptian_sites.items():
                for keyword in keywords:
                    if keyword in store_name or keyword in url:
                        is_egyptian = True
                        detected_store = store_key
                        break
                if is_egyptian:
                    break
            
            # فلترة إضافية للأسعار المنطقية
            price = result['price']
            if is_egyptian and 20 <= price <= 200000:
                result['detected_store'] = detected_store
                egyptian_results.append(result)
        
        # إزالة التكرار بناءً على المتجر والسعر
        unique_results = []
        seen_combinations = set()
        
        for result in egyptian_results:
            combination = f"{result['detected_store']}_{result['price']}"
            if combination not in seen_combinations:
                seen_combinations.add(combination)
                unique_results.append(result)
        
        return unique_results
    
    async def comprehensive_price_check(self, product_name: str, amazon_price: float) -> dict:
        """فحص شامل للأسعار مع تحسينات متقدمة"""
        
        cache_key = f"improved_{product_name[:30]}_{amazon_price}"
        
        # فحص الكاش
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        print(f"🔍 بحث محسن: {product_name[:45]}...")
        
        result = {
            'market_prices': [],
            'stores': [],
            'detailed_results': [],
            'amazon_price': amazon_price,
            'is_good_deal': False,
            'confidence': 20,
            'reason': 'لم يتم العثور على أسعار',
            'search_terms_used': [],
            'total_competitors': 0
        }
        
        try:
            # إنشاء مصطلحات بحث ذكية
            search_terms = self.create_smart_search_terms(product_name)
            result['search_terms_used'] = search_terms
            
            all_results = []
            
            # البحث بكل مصطلح
            for i, term in enumerate(search_terms):
                print(f"   🔎 [{i+1}/{len(search_terms)}] {term}")
                
                search_results = await self.advanced_google_search(term)
                
                if search_results:
                    egyptian_results = self.filter_egyptian_results(search_results)
                    all_results.extend(egyptian_results)
                    
                    if egyptian_results:
                        print(f"      ✅ {len(egyptian_results)} نتيجة مصرية")
                        break  # إذا وجدنا نتائج جيدة، نتوقف
                    else:
                        print(f"      ⚪ لا توجد نتائج مصرية")
                else:
                    print(f"      ❌ لا توجد نتائج")
                
                # توقف قصير بين البحثات
                await asyncio.sleep(1)
            
            if all_results:
                # معالجة النتائج
                prices = [r['price'] for r in all_results]
                stores = [r['detected_store'] for r in all_results]
                
                result['market_prices'] = prices
                result['stores'] = stores
                result['detailed_results'] = all_results
                result['total_competitors'] = len(all_results)
                
                # تحليل متقدم
                if len(prices) >= 2:  # نحتاج على الأقل منافسين
                    avg_price = statistics.mean(prices)
                    min_price = min(prices)
                    max_price = max(prices)
                    
                    # حساب موقع أمازون
                    cheaper_count = sum(1 for price in prices if price > amazon_price)
                    total_stores = len(prices)
                    amazon_rank = total_stores - cheaper_count + 1
                    
                    # حساب الفروق
                    vs_avg_diff = ((avg_price - amazon_price) / avg_price) * 100
                    vs_min_diff = ((min_price - amazon_price) / min_price) * 100
                    
                    # نظام تسجيل النقاط المحسن
                    confidence_score = 50  # نقطة البداية
                    
                    # عامل 1: موقع أمازون بين المنافسين
                    if amazon_rank == 1:
                        confidence_score += 40
                        rank_desc = "الأرخص في السوق!"
                    elif amazon_rank <= 2:
                        confidence_score += 30
                        rank_desc = f"ثاني أرخص سعر"
                    elif amazon_rank <= 3:
                        confidence_score += 20
                        rank_desc = f"ثالث أرخص سعر"
                    elif amazon_rank <= total_stores * 0.5:
                        confidence_score += 10
                        rank_desc = f"في النصف الأرخص"
                    else:
                        confidence_score -= 20
                        rank_desc = f"ترتيب {amazon_rank} من {total_stores}"
                    
                    # عامل 2: الفرق عن المتوسط
                    if vs_avg_diff > 20:
                        confidence_score += 25
                    elif vs_avg_diff > 10:
                        confidence_score += 15
                    elif vs_avg_diff > 0:
                        confidence_score += 10
                    elif vs_avg_diff > -10:
                        confidence_score += 5
                    else:
                        confidence_score -= 15
                    
                    # عامل 3: عدد المنافسين
                    if total_stores >= 5:
                        confidence_score += 15
                    elif total_stores >= 3:
                        confidence_score += 10
                    elif total_stores >= 2:
                        confidence_score += 5
                    
                    # عامل 4: نوعية المتاجر
                    premium_stores = ['jumia', 'noon', 'amazon', 'btech']
                    premium_count = sum(1 for store in stores if store in premium_stores)
                    if premium_count >= 3:
                        confidence_score += 10
                    elif premium_count >= 2:
                        confidence_score += 5
                    
                    # تحديد النقاط النهائية
                    result['confidence'] = max(0, min(100, confidence_score))
                    
                    # تحديد جودة العرض
                    if result['confidence'] >= 85:
                        result['is_good_deal'] = True
                        result['reason'] = f"🔥 {rank_desc} - ثقة عالية جداً"
                    elif result['confidence'] >= 70:
                        result['is_good_deal'] = True
                        result['reason'] = f"✅ {rank_desc} - ثقة عالية"
                    elif result['confidence'] >= 60:
                        result['is_good_deal'] = True
                        result['reason'] = f"⚠️ {rank_desc} - ثقة متوسطة"
                    else:
                        result['is_good_deal'] = False
                        result['reason'] = f"❌ {rank_desc} - ثقة منخفضة"
                    
                    # طباعة التفاصيل
                    print(f"   📊 تحليل محسن:")
                    print(f"      💰 متوسط السوق: {avg_price:,.0f} EGP")
                    print(f"      📉 أقل سعر: {min_price:,.0f} EGP")
                    print(f"      📈 أعلى سعر: {max_price:,.0f} EGP")
                    print(f"      🎯 أمازون: {amazon_price:,.0f} EGP (ترتيب {amazon_rank})")
                    print(f"      📊 الفرق عن المتوسط: {vs_avg_diff:+.1f}%")
                    print(f"      🏆 الثقة: {result['confidence']}/100")
                    print(f"      🌐 المنافسين: {total_stores} متجر")
                    print(f"   {result['reason']}")
                    
                    self.stats['successful_comparisons'] += 1
                    
                else:
                    result['reason'] = f"⚪ نتيجة واحدة فقط من {all_results[0]['detected_store']}"
                    result['confidence'] = 40
            
        except Exception as e:
            print(f"   ❌ خطأ في المقارنة المحسنة: {e}")
            self.stats['google_errors'] += 1
        
        self.stats['total_comparisons'] += 1
        
        # حفظ في الكاش
        self.cache[cache_key] = result
        
        return result

# إنشاء مقارن جوجل المحسن
improved_google_comparator = ImprovedGoogleComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع مقارنة جوجل المحسنة"""
    
    def improved_google_compare_and_send():
        """مقارنة محسنة عن طريق جوجل وإرسال"""
        
        if google_comparison_enabled[0]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                comparison_result = loop.run_until_complete(
                    improved_google_comparator.comprehensive_price_check(item.get('name', ''), new_price)
                )
                
                if not comparison_result['is_good_deal']:
                    print(f"🚫 رفض محسن: {item.get('name', '')[:35]}... - {comparison_result['reason']}")
                    improved_google_comparator.stats['rejected_deals'] += 1
                    return
                
                # إضافة معلومات جوجل المحسنة
                item['google_analysis'] = comparison_result
                item['google_confidence'] = comparison_result['confidence']
                item['google_reason'] = comparison_result['reason']
                item['market_competitors'] = comparison_result['total_competitors']
                item['search_terms'] = comparison_result['search_terms_used']
                
                improved_google_comparator.stats['validated_deals'] += 1
                
            except Exception as e:
                print(f"⚠️ خطأ في جوجل المحسن: {e}")
            finally:
                loop.close()
        
        # إرسال الرسالة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=improved_google_compare_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع معلومات جوجل المحسنة"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات جوجل المحسنة
        google_reason = item.get('google_reason', '')
        google_confidence = item.get('google_confidence', 0)
        market_competitors = item.get('market_competitors', 0)
        search_terms = item.get('search_terms', [])

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان ذكي بناءً على الثقة
        if google_confidence >= 90:
            headline = "🔥 <b>VERIFIED BEST DEAL!</b> 🔥"
        elif google_confidence >= 80:
            headline = "✅ <b>GOOGLE CONFIRMED DEAL!</b>"
        elif google_confidence >= 70:
            headline = "⭐ <b>GOOD DEAL FOUND!</b>"
        else:
            headline = "💸 <b>Deal Alert!</b>"

        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
        
        # معلومات مقارنة جوجل المحسنة
        google_info = ""
        if google_reason:
            google_info = f"\n🧠 <b>Smart Analysis:</b> {google_reason}"
        
        if market_competitors > 0:
            google_info += f"\n🏪 <b>Compared with {market_competitors} stores</b>"
        
        confidence_row = f"\n🎯 <b>Confidence:</b> {google_confidence}%" if google_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Open on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{confidence_row}{google_info}

🤖 <b>AI-Powered Price Comparison</b>
"""

        # أزرار محسنة
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Buy on Amazon", "url": url}],
                [{"text": "🔍 Compare on Google", "url": f"https://www.google.com/search?q={product_name.replace(' ', '+')}&tbm=shop&hl=ar&gl=EG"}],
                [{"text": "🏪 Check Jumia", "url": f"https://www.jumia.com.eg/catalog/?q={product_name.replace(' ', '+')}"}],
                [{"text": "🌙 Check Noon", "url": f"https://www.noon.com/egypt-en/search/?q={product_name.replace(' ', '+')}"}]
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
            confidence_text = f"ثقة {google_confidence}%" if google_confidence > 0 else "مقارنة أساسية"
            print(f"✅ تم إرسال تنبيه لـ {sent_count} مستخدم - {confidence_text}")

    except Exception as e:
        print("❌ Telegram Error:", e)

# باقي الدوال الأساسية (نفس الكود السابق)
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
    """إضافة بيانات التنبيه مع مقارنة جوجل المحسنة"""
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
    
    # إرسال مع مقارنة جوجل المحسنة
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة (نفس الكود السابق)
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=25):
    """سكرابة صفحة واحدة مع التركيز على الجودة"""
    
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
            google_mode = "[IMPROVED GOOGLE]" if google_comparison_enabled[0] else ""
            log_fn(f"🌐 {mode}{google_mode} Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(1500)
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:10]:  # أول 10 منتجات للتركيز على الجودة
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
                if not price or price < 20:
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
                    
                    if discount_percent >= discount_threshold and discount_percent <= 75 and price >= 25:
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
            log_fn(f"[Page {page_num}] ✅ {new_count} NEW products")
        
        return new_count

# دوال الواجهة (نفس الكود السابق مع تحديثات للمقارن المحسن)
def start_scraping():
    if running[0]:
        log("Already running.", "⚠️")
        return
        
    section = section_combo.get()
    pages = int(pages_entry.get())
    progress_bar.set(0.0)
    stop_flag["stop"] = False
    running[0] = True
    
    google_mode = "IMPROVED ON" if google_comparison_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🚀 Starting - New Products: {auto_mode}, Improved Google: {google_mode}")
    
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
    
    # إحصائيات جوجل المحسنة
    if google_comparison_enabled[0]:
        stats = improved_google_comparator.stats
        log(f"🧠 Improved Google Stats:")
        log(f"   📊 Total Searches: {stats['total_comparisons']}")
        log(f"   ✅ Successful: {stats['successful_comparisons']}")
        log(f"   📱 Validated: {stats['validated_deals']}")
        log(f"   🚫 Rejected: {stats['rejected_deals']}")
        log(f"   🧠 Cache Hits: {stats['cache_hits']}")
        log(f"   ❌ Errors: {stats['google_errors']}")
        
        if stats['total_comparisons'] > 0:
            success_rate = (stats['validated_deals'] / stats['total_comparisons']) * 100
            log(f"   📈 Success Rate: {success_rate:.1f}%")

def toggle_google_comparison():
    google_comparison_enabled[0] = google_comparison_chk.get()
    status = "IMPROVED ON" if google_comparison_enabled[0] else "OFF"
    log(f"🧠 Improved Google Comparison: {status}")

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
root.title("LAQTA - Improved Google Price Checker")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA - IMPROVED GOOGLE", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="🧠 النسخة المحسنة: بحث ذكي متعدد + فلترة مصرية + تحليل متقدم", 
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
pages_entry.insert(0, "5")  # عدد أقل للجودة العالية
pages_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 13), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=5, pady=8, sticky="ew")

# المنتجات الجديدة
auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 New Only", font=("Arial", 13, "bold"), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=3, padx=5, pady=8, sticky="ew")
auto_new_chk.select()

# مقارنة جوجل المحسنة
google_comparison_chk = ctk.CTkCheckBox(controls_frame, text="🧠 Smart Google", font=("Arial", 13, "bold"), 
                                       text_color="#4285f4", command=toggle_google_comparison)
google_comparison_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
google_comparison_chk.select()

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

start_btn = ctk.CTkButton(buttons_frame, text="🚀 Start Smart Check", command=start_scraping, width=btn_w, height=btn_h,
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

# رسائل ترحيب محسنة
log("🧠 LAQTA Improved Google started!", "🚀")
log("🔍 Smart Google: ON - بحث ذكي متعدد المصطلحات", "✨")
log("🌍 Egyptian Filter: ON - فلترة المواقع المصرية", "🇪🇬")
log("🆕 New Products: ON - منتجات جديدة فقط", "💡")
log("📊 Advanced Analysis: ON - تحليل متقدم للثقة", "🎯")
log("📱 Expected: HIGH-QUALITY verified deals!", "🏆")

root.mainloop()