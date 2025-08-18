#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام استخراج متقدم من صفحة جوجل للأسعار والمواقع
الطريقة المتقدمة - تحليل العناصر المهيكلة
"""

import asyncio
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright
import statistics

class GoogleAdvancedExtractor:
    """مستخرج متقدم للبيانات من صفحة جوجل"""
    
    def __init__(self):
        self.stats = {
            'total_searches': 0,
            'successful_extractions': 0,
            'products_found': 0,
            'sites_detected': 0,
            'extraction_errors': 0,
            'cache_hits': 0
        }
        self.cache = {}
        
        # المواقع المصرية المعروفة
        self.egyptian_sites = {
            'amazon.eg': 'أمازون مصر',
            'noon.com': 'نون',
            'jumia.com.eg': 'جوميا',
            'carrefouregypt.com': 'كارفور',
            'souq.com': 'سوق',
            'b-tech.com.eg': 'بي تك',
            'spinneys.com': 'سبينيز',
            'tradeline.com.eg': 'تريد لاين',
            'kanbkam.com': 'كانبكام',
            'aliexpress.com': 'علي اكسبرس'
        }
        
        # أنماط استخراج الأسعار المتقدمة
        self.price_patterns = [
            # النمط: "90.00 جنيه" أو "‏90.00 جنيه"
            r'‏?([0-9,]+(?:\.[0-9]+)?)\s*جنيه',
            # النمط: "السعر الحالي هو. ‏90.00 جنيه"
            r'السعر الحالي هو[.\s]*‏?([0-9,]+(?:\.[0-9]+)?)\s*جنيه',
            # النمط: "134.05 دلـع موبايلك"
            r'([0-9,]+(?:\.[0-9]+)?)\s*(?:جنية مصرى|جنيه مصري|EGP)',
            # النمط عام للأرقام مع العملة
            r'([0-9,]+(?:\.[0-9]+)?)\s*(?:ج\.م\.|جم|LE)'
        ]
        
        # أنماط استخراج المواقع المتقدمة
        self.site_patterns = [
            # النمط: "من www.amazon.eg"
            r'من\s+(www\.)?([a-zA-Z0-9\-\.]+)',
            # النمط: "https://www.noon.com"
            r'https?://(?:www\.)?([a-zA-Z0-9\-\.]+)',
            # النمط في الروابط
            r'href=["\']https?://(?:www\.)?([a-zA-Z0-9\-\.]+)'
        ]
    
    def clean_product_name_for_google(self, product_name: str) -> str:
        """تنظيف اسم المنتج للبحث في جوجل"""
        
        # إزالة الكلمات غير المهمة
        unwanted_words = [
            'amazon', 'choice', 'brand', 'original', 'authentic', 'genuine',
            'أمازون', 'أصلي', 'حقيقي', 'ماركة', 'من', 'في', 'مع', 'على'
        ]
        
        # تنظيف النص
        clean_name = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', product_name)
        
        # إزالة المواصفات التقنية المعقدة
        clean_name = re.sub(r'\b\d+\s*(gb|mb|ml|kg|gram|piece|pack)\b', '', clean_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'\b\d+\s*x\s*\d+\b', '', clean_name)  # إزالة أبعاد مثل "22 x 45"
        
        # فلترة الكلمات
        words = []
        for word in clean_name.split():
            if (len(word) > 2 and 
                word.lower() not in unwanted_words and 
                not word.isdigit()):
                words.append(word)
        
        # أخذ أهم 4-5 كلمات للبحث الدقيق
        search_terms = ' '.join(words[:5])
        
        # إضافة كلمة "سعر مصر" للحصول على نتائج أسعار مصرية
        search_terms += " سعر مصر"
        
        return search_terms.strip()
    
    async def extract_structured_results(self, page) -> List[Dict]:
        """استخراج النتائج المهيكلة من صفحة جوجل"""
        
        # استخراج البيانات بطريقة متقدمة
        extracted_data = await page.evaluate("""
            () => {
                const results = [];
                
                // البحث في أنواع مختلفة من النتائج
                const resultSelectors = [
                    '.g',                    // النتائج العادية
                    '.yuRUbf',              // النتائج الحديثة
                    '.tF2Cxc',              // نتائج البحث المهيكلة
                    '.MjjYud',              // نتائج جديدة
                    '.commercial-unit',      // النتائج التجارية
                    '.pla-unit',            // وحدات المنتجات
                    '.shopping-carousel-item' // عناصر التسوق
                ];
                
                const egyptianSites = [
                    'amazon.eg', 'noon.com', 'jumia.com.eg', 'carrefouregypt.com',
                    'souq.com', 'b-tech.com.eg', 'spinneys.com', 'tradeline.com.eg',
                    'kanbkam.com', 'aliexpress.com'
                ];
                
                const pricePatterns = [
                    /‏?([0-9,]+(?:\\.[0-9]+)?)\\s*جنيه/g,
                    /السعر الحالي هو[.\\s]*‏?([0-9,]+(?:\\.[0-9]+)?)\\s*جنيه/g,
                    /([0-9,]+(?:\\.[0-9]+)?)\\s*(?:جنية مصرى|جنيه مصري|EGP)/g,
                    /([0-9,]+(?:\\.[0-9]+)?)\\s*(?:ج\\.م\\.|جم|LE)/g
                ];
                
                // البحث في كل نوع من النتائج
                for (const selector of resultSelectors) {
                    const elements = document.querySelectorAll(selector);
                    
                    elements.forEach((element, index) => {
                        if (index >= 15) return; // أول 15 نتيجة فقط
                        
                        try {
                            const elementText = element.textContent || '';
                            const elementHTML = element.innerHTML || '';
                            
                            // استخراج الأسعار
                            const foundPrices = [];
                            for (const pattern of pricePatterns) {
                                const matches = Array.from(elementText.matchAll(pattern));
                                for (const match of matches) {
                                    const price = parseFloat(match[1].replace(/,/g, ''));
                                    if (price >= 20 && price <= 50000) {
                                        foundPrices.push(price);
                                    }
                                }
                            }
                            
                            // استخراج المواقع
                            const foundSites = [];
                            for (const site of egyptianSites) {
                                if (elementText.includes(site) || elementHTML.includes(site)) {
                                    foundSites.push(site);
                                }
                            }
                            
                            // استخراج الروابط
                            const links = element.querySelectorAll('a[href]');
                            const foundLinks = [];
                            links.forEach(link => {
                                const href = link.href;
                                for (const site of egyptianSites) {
                                    if (href.includes(site)) {
                                        foundLinks.push(href);
                                        if (!foundSites.includes(site)) {
                                            foundSites.push(site);
                                        }
                                    }
                                }
                            });
                            
                            // استخراج العنوان/الوصف
                            const titleSelectors = ['h3', 'h2', '.LC20lb', '.DKV0Md', '.yuRUbf h3'];
                            let title = '';
                            for (const titleSel of titleSelectors) {
                                const titleEl = element.querySelector(titleSel);
                                if (titleEl && titleEl.textContent.trim()) {
                                    title = titleEl.textContent.trim();
                                    break;
                                }
                            }
                            
                            // إذا وجدنا أسعار ومواقع، نحفظ النتيجة
                            if (foundPrices.length > 0 && foundSites.length > 0) {
                                results.push({
                                    prices: [...new Set(foundPrices)], // إزالة التكرار
                                    sites: [...new Set(foundSites)],   // إزالة التكرار
                                    links: [...new Set(foundLinks)],   // إزالة التكرار
                                    title: title,
                                    description: elementText.slice(0, 200),
                                    selector_used: selector
                                });
                            }
                            
                        } catch (e) {
                            // تجاهل الأخطاء والمتابعة
                        }
                    });
                    
                    // إذا وجدنا نتائج جيدة، نتوقف
                    if (results.length >= 5) break;
                }
                
                return results;
            }
        """)
        
        return extracted_data
    
    async def advanced_google_search(self, product_name: str, amazon_price: float) -> Dict:
        """بحث متقدم في جوجل مع استخراج مهيكل للبيانات"""
        
        search_term = self.clean_product_name_for_google(product_name)
        cache_key = f"advanced_{search_term}_{amazon_price}"
        
        # فحص الكاش
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        print(f"🔍 بحث متقدم: {product_name[:50]}...")
        print(f"   🔎 مصطلح البحث: '{search_term}'")
        
        result = {
            'amazon_price': amazon_price,
            'extracted_products': [],
            'market_analysis': {},
            'comparison_result': {},
            'is_good_deal': False,
            'confidence_score': 0,
            'recommendation': 'غير محدد',
            'extraction_method': 'none',
            'search_term': search_term
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
                        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    ]
                )
                
                context = await browser.new_context()
                page = await context.new_page()
                
                # تجربة عدة استراتيجيات بحث مختلفة
                search_strategies = [
                    f"https://www.google.com/search?q={search_term.replace(' ', '+')}&hl=ar&gl=EG",
                    f"https://www.google.com/search?q={search_term.replace(' ', '+')}&tbm=shop&hl=ar&gl=EG",
                    f"https://www.google.com.eg/search?q={search_term.replace(' ', '+')}&hl=ar"
                ]
                
                extracted_products = []
                
                for strategy_idx, google_url in enumerate(search_strategies):
                    try:
                        print(f"   📡 استراتيجية {strategy_idx + 1}: {google_url.split('?')[0]}")
                        
                        await page.goto(google_url, timeout=15000)
                        await page.wait_for_timeout(3000)
                        
                        # استخراج النتائج المهيكلة
                        structured_results = await self.extract_structured_results(page)
                        
                        if structured_results:
                            extracted_products.extend(structured_results)
                            result['extraction_method'] = f'strategy_{strategy_idx + 1}'
                            print(f"      ✅ وجدت {len(structured_results)} نتائج مهيكلة")
                            break  # إذا وجدنا نتائج، نتوقف
                        else:
                            print(f"      ⚪ لا توجد نتائج مهيكلة")
                    
                    except Exception as e:
                        print(f"      ❌ خطأ في الاستراتيجية {strategy_idx + 1}: {e}")
                        continue
                
                await browser.close()
                
                # معالجة النتائج المستخرجة
                if extracted_products:
                    result['extracted_products'] = extracted_products
                    
                    # تجميع جميع الأسعار والمواقع
                    all_prices = []
                    all_sites = []
                    site_price_map = {}
                    
                    for product in extracted_products:
                        all_prices.extend(product['prices'])
                        all_sites.extend(product['sites'])
                        
                        # ربط المواقع بالأسعار
                        for site in product['sites']:
                            if site not in site_price_map:
                                site_price_map[site] = []
                            site_price_map[site].extend(product['prices'])
                    
                    # إزالة التكرار وفلترة الأسعار
                    unique_prices = sorted(list(set(all_prices)))
                    unique_sites = list(set(all_sites))
                    
                    # فلترة الأسعار الشاذة
                    if len(unique_prices) > 4:
                        median_price = statistics.median(unique_prices)
                        filtered_prices = []
                        for price in unique_prices:
                            if 0.2 * median_price <= price <= 5 * median_price:
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
                        
                        result['market_analysis'] = {
                            'avg_market_price': avg_market_price,
                            'min_market_price': min_market_price,
                            'max_market_price': max_market_price,
                            'median_market_price': median_market_price,
                            'amazon_rank': amazon_rank,
                            'total_competitors': total_competitors,
                            'vs_avg_difference': vs_avg_diff,
                            'vs_min_difference': vs_min_diff,
                            'market_range': max_market_price - min_market_price,
                            'sites_found': len(unique_sites),
                            'site_price_map': site_price_map
                        }
                        
                        # تحديد جودة العرض
                        confidence_factors = []
                        base_confidence = 50
                        
                        # عامل 1: ترتيب أمازون
                        if amazon_rank == 1:
                            confidence_factors.append(('أفضل سعر', 35, f"الأرخص في السوق من {total_competitors} أسعار"))
                        elif amazon_rank == 2:
                            confidence_factors.append(('سعر ممتاز', 25, f"ثاني أرخص سعر من {total_competitors}"))
                        elif amazon_rank <= 3:
                            confidence_factors.append(('سعر جيد', 15, f"ثالث أرخص سعر من {total_competitors}"))
                        elif amazon_rank <= total_competitors * 0.5:
                            confidence_factors.append(('سعر مقبول', 10, f"في النصف الأرخص ({amazon_rank}/{total_competitors})"))
                        else:
                            confidence_factors.append(('سعر مرتفع', -20, f"ترتيب {amazon_rank} من {total_competitors}"))
                        
                        # عامل 2: مقارنة مع المتوسط
                        if vs_avg_diff > 25:
                            confidence_factors.append(('متوسط السوق', 30, f"أرخص بـ {vs_avg_diff:.0f}% من المتوسط"))
                        elif vs_avg_diff > 15:
                            confidence_factors.append(('متوسط السوق', 20, f"أرخص بـ {vs_avg_diff:.0f}% من المتوسط"))
                        elif vs_avg_diff > 5:
                            confidence_factors.append(('متوسط السوق', 10, f"أرخص بـ {vs_avg_diff:.0f}% من المتوسط"))
                        elif vs_avg_diff > -10:
                            confidence_factors.append(('متوسط السوق', 5, f"مقارب للمتوسط ({vs_avg_diff:+.0f}%)"))
                        else:
                            confidence_factors.append(('متوسط السوق', -15, f"أغلى بـ {abs(vs_avg_diff):.0f}% من المتوسط"))
                        
                        # عامل 3: عدد المواقع والمنافسين
                        sites_count = len(unique_sites)
                        if sites_count >= 4:
                            confidence_factors.append(('تنوع المواقع', 15, f"مقارنة مع {sites_count} مواقع مختلفة"))
                        elif sites_count >= 3:
                            confidence_factors.append(('تنوع المواقع', 10, f"مقارنة مع {sites_count} مواقع"))
                        elif sites_count >= 2:
                            confidence_factors.append(('تنوع المواقع', 5, f"مقارنة مع {sites_count} مواقع"))
                        
                        # عامل 4: جودة البيانات المستخرجة
                        extraction_quality = len(extracted_products)
                        if extraction_quality >= 5:
                            confidence_factors.append(('جودة البيانات', 10, f"استخراج {extraction_quality} منتجات"))
                        elif extraction_quality >= 3:
                            confidence_factors.append(('جودة البيانات', 5, f"استخراج {extraction_quality} منتجات"))
                        
                        # حساب النقاط النهائية
                        total_confidence = base_confidence
                        for factor_name, points, description in confidence_factors:
                            total_confidence += points
                        
                        result['confidence_score'] = max(0, min(100, total_confidence))
                        result['confidence_factors'] = confidence_factors
                        
                        # تحديد التوصية النهائية
                        if result['confidence_score'] >= 85:
                            result['is_good_deal'] = True
                            result['recommendation'] = f"🔥 عرض ممتاز! أمازون ترتيب {amazon_rank} من {total_competitors} مواقع"
                            
                        elif result['confidence_score'] >= 70:
                            result['is_good_deal'] = True
                            result['recommendation'] = f"✅ عرض جيد! أرخص من {total_competitors - amazon_rank} مواقع"
                            
                        elif result['confidence_score'] >= 55:
                            result['is_good_deal'] = True
                            result['recommendation'] = f"⚠️ عرض مقبول! ترتيب {amazon_rank} في السوق"
                            
                        else:
                            result['is_good_deal'] = False
                            result['recommendation'] = f"❌ عرض ضعيف! يوجد {amazon_rank-1} خيارات أرخص"
                        
                        # طباعة التفاصيل
                        print(f"   📊 تحليل متقدم:")
                        print(f"      💰 متوسط السوق: {avg_market_price:,.0f} EGP")
                        print(f"      📉 أقل سعر: {min_market_price:,.0f} EGP")
                        print(f"      📈 أعلى سعر: {max_market_price:,.0f} EGP")
                        print(f"      🎯 أمازون: {amazon_price:,.0f} EGP (ترتيب {amazon_rank})")
                        print(f"      📊 الفرق عن المتوسط: {vs_avg_diff:+.1f}%")
                        print(f"      🏆 الثقة: {result['confidence_score']}/100")
                        print(f"      🌐 المواقع: {len(unique_sites)} موقع")
                        print(f"      📱 المنتجات: {len(extracted_products)} منتج مستخرج")
                        print(f"   {result['recommendation']}")
                        
                        # إحصائيات النجاح
                        self.stats['successful_extractions'] += 1
                        self.stats['products_found'] += len(extracted_products)
                        self.stats['sites_detected'] += len(unique_sites)
                        
                        # حفظ في الكاش
                        self.cache[cache_key] = result
                        
                        return result
                
        except Exception as e:
            print(f"   ❌ خطأ في البحث المتقدم: {e}")
            self.stats['extraction_errors'] += 1
        
        finally:
            self.stats['total_searches'] += 1
        
        return result
    
    def get_extraction_stats(self) -> Dict:
        """الحصول على إحصائيات الاستخراج"""
        total = self.stats['total_searches']
        
        return {
            'total_searches': total,
            'successful_extractions': self.stats['successful_extractions'],
            'success_rate': (self.stats['successful_extractions'] / max(total, 1)) * 100,
            'products_found': self.stats['products_found'],
            'sites_detected': self.stats['sites_detected'],
            'avg_products_per_search': self.stats['products_found'] / max(total, 1),
            'avg_sites_per_search': self.stats['sites_detected'] / max(total, 1),
            'extraction_errors': self.stats['extraction_errors'],
            'cache_size': len(self.cache),
            'cache_hits': self.stats['cache_hits']
        }

# دالة للاختبار
async def test_advanced_extraction():
    """اختبار نظام الاستخراج المتقدم"""
    
    print("🧪 اختبار نظام الاستخراج المتقدم من جوجل")
    print("=" * 70)
    
    extractor = GoogleAdvancedExtractor()
    
    # منتجات للاختبار (من الأمثلة الحقيقية)
    test_products = [
        {
            'name': 'سوار سيليكون 22 ملم لساعة سامسونج جالاكسي 3 45 / 46 جير',
            'amazon_price': 90.0,
            'expected_sites': ['amazon.eg', 'noon.com', 'jumia.com.eg', 'kanbkam.com']
        },
        {
            'name': 'Vaseline Body Lotion Intensive Care 400ML',
            'amazon_price': 85.0,
            'expected_sites': ['amazon.eg', 'noon.com', 'jumia.com.eg', 'carrefouregypt.com']
        },
        {
            'name': 'Samsung Galaxy A06 Dual Sim 6GB RAM 128GB',
            'amazon_price': 2800.0,
            'expected_sites': ['amazon.eg', 'noon.com', 'jumia.com.eg']
        }
    ]
    
    successful_tests = 0
    
    for i, test_product in enumerate(test_products):
        print(f"\n🧪 اختبار {i+1}: {test_product['name']}")
        print(f"   💰 سعر أمازون: {test_product['amazon_price']:,.0f} EGP")
        
        try:
            result = await extractor.advanced_google_search(
                test_product['name'], 
                test_product['amazon_price']
            )
            
            if result['extracted_products']:
                print(f"   ✅ نجح الاستخراج!")
                print(f"      📱 منتجات مستخرجة: {len(result['extracted_products'])}")
                print(f"      🌐 مواقع مكتشفة: {result['market_analysis'].get('sites_found', 0)}")
                print(f"      🎯 توصية: {result['recommendation']}")
                successful_tests += 1
            else:
                print(f"   ❌ فشل الاستخراج")
        
        except Exception as e:
            print(f"   ❌ خطأ في الاختبار: {e}")
        
        print("-" * 50)
    
    # إحصائيات الاختبار
    stats = extractor.get_extraction_stats()
    print(f"\n📊 إحصائيات الاختبار:")
    print(f"   🧪 اختبارات ناجحة: {successful_tests}/{len(test_products)}")
    print(f"   📈 معدل النجاح: {(successful_tests / len(test_products)) * 100:.1f}%")
    print(f"   🔍 عمليات بحث: {stats['total_searches']}")
    print(f"   ✅ استخراجات ناجحة: {stats['successful_extractions']}")
    print(f"   📱 منتجات وجدت: {stats['products_found']}")
    print(f"   🌐 مواقع اكتشفت: {stats['sites_detected']}")
    print(f"   📊 متوسط المنتجات لكل بحث: {stats['avg_products_per_search']:.1f}")
    print(f"   🏪 متوسط المواقع لكل بحث: {stats['avg_sites_per_search']:.1f}")
    
    return successful_tests == len(test_products)

if __name__ == "__main__":
    print("🔍 نظام الاستخراج المتقدم من جوجل")
    print("💡 الفكرة: استخراج الأسعار والمواقع مباشرة من صفحة جوجل")
    print("🎯 الهدف: مقارنة سريعة ودقيقة بدون دخول المواقع الفردية")
    print()
    
    # تشغيل الاختبار
    success = asyncio.run(test_advanced_extraction())
    
    if success:
        print("\n🎉 جميع الاختبارات نجحت! النظام جاهز للتطبيق!")
    else:
        print("\n⚠️ بعض الاختبارات فشلت. يحتاج تحسين إضافي.")