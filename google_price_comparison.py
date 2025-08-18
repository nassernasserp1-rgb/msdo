#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام مقارنة الأسعار عن طريق جوجل - أذكى طريقة للمقارنة
"""

import asyncio
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright
import statistics

class GooglePriceComparator:
    """مقارن الأسعار عن طريق جوجل - الطريقة الأذكى"""
    
    def __init__(self):
        # إعدادات البحث في جوجل
        self.google_settings = {
            'base_url': 'https://www.google.com/search?q={}&tbm=shop&hl=ar&gl=EG',
            'timeout': 12000,
            'max_results': 10,
            'min_price': 10,
            'max_price': 200000
        }
        
        # إحصائيات المقارنة
        self.comparison_stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'products_with_prices': 0,
            'validated_deals': 0,
            'rejected_deals': 0,
            'google_errors': 0
        }
        
        # كاش للبحثات السريعة
        self.search_cache = {}
        
    def clean_product_name_for_google(self, product_name: str) -> str:
        """تنظيف اسم المنتج للبحث في جوجل"""
        
        # إزالة الكلمات غير المهمة
        unwanted_words = [
            'amazon', 'choice', 'brand', 'original', 'authentic', 'genuine',
            'أمازون', 'أصلي', 'حقيقي', 'ماركة'
        ]
        
        # تنظيف النص
        clean_name = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', product_name)
        clean_name = re.sub(r'\b\d+\s*(piece|pack|ml|kg|gram|قطعة|حبة|لتر|كيلو)\b', '', clean_name, flags=re.IGNORECASE)
        
        # فلترة الكلمات
        words = []
        for word in clean_name.split():
            if (len(word) > 2 and 
                word.lower() not in unwanted_words and 
                not word.isdigit()):
                words.append(word)
        
        # أخذ أهم 4-5 كلمات للبحث الدقيق
        search_terms = ' '.join(words[:5])
        
        # إضافة كلمة "سعر" للحصول على نتائج أسعار أفضل
        search_terms += " سعر"
        
        return search_terms.strip()
    
    async def search_google_shopping(self, product_name: str) -> List[Dict]:
        """البحث في جوجل شوبينج للحصول على جميع الأسعار"""
        
        search_term = self.clean_product_name_for_google(product_name)
        cache_key = f"google_{search_term}"
        
        # فحص الكاش
        if cache_key in self.search_cache:
            cached_result = self.search_cache[cache_key]
            # استخدام الكاش إذا كان حديث (أقل من 10 دقائق)
            if time.time() - cached_result['timestamp'] < 600:
                return cached_result['data']
        
        print(f"🔍 البحث في جوجل: {product_name[:50]}...")
        print(f"   🔎 مصطلح البحث: '{search_term}'")
        
        search_url = self.google_settings['base_url'].format(search_term.replace(' ', '+'))
        
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
                
                # الذهاب لجوجل شوبينج
                await page.goto(search_url, timeout=self.google_settings['timeout'])
                await page.wait_for_timeout(3000)
                
                # استخراج بيانات الأسعار من جوجل
                price_data = await page.evaluate("""
                    () => {
                        const products = [];
                        
                        // البحث عن عناصر المنتجات في جوجل شوبينج
                        const productSelectors = [
                            '[data-docid]',
                            '.sh-dgr__content',
                            '.PLla-d',
                            '.sh-dlr__list-result',
                            '.mnr-c'
                        ];
                        
                        let productElements = [];
                        for (const selector of productSelectors) {
                            const elements = document.querySelectorAll(selector);
                            if (elements.length > 0) {
                                productElements = Array.from(elements).slice(0, 15);
                                break;
                            }
                        }
                        
                        productElements.forEach(element => {
                            try {
                                // البحث عن اسم المنتج
                                const nameSelectors = [
                                    'h3', 'h4', '.sh-dlr__product-title', 
                                    '.translate-content', '[role="heading"]'
                                ];
                                let productName = '';
                                for (const selector of nameSelectors) {
                                    const nameEl = element.querySelector(selector);
                                    if (nameEl && nameEl.textContent.trim()) {
                                        productName = nameEl.textContent.trim();
                                        break;
                                    }
                                }
                                
                                // البحث عن السعر
                                const priceSelectors = [
                                    '.a30cxb', '.notranslate', '.sh-dlr__price',
                                    '.price', '.current-price', '.final-price'
                                ];
                                let price = null;
                                for (const selector of priceSelectors) {
                                    const priceEl = element.querySelector(selector);
                                    if (priceEl) {
                                        const priceText = priceEl.textContent;
                                        // البحث عن أرقام مع "جنيه" أو "EGP"
                                        const match = priceText.match(/([0-9,]+)\\s*(جنيه|EGP|ج\\.م)/i);
                                        if (match) {
                                            const extractedPrice = parseFloat(match[1].replace(/,/g, ''));
                                            if (extractedPrice > 10 && extractedPrice < 500000) {
                                                price = extractedPrice;
                                                break;
                                            }
                                        }
                                    }
                                }
                                
                                // البحث عن اسم المتجر
                                const storeSelectors = [
                                    '.sh-dlr__merchant', '.merchant', '.store-name',
                                    '.a25r0b', '.sh-dlr__merchant-name'
                                ];
                                let storeName = '';
                                for (const selector of storeSelectors) {
                                    const storeEl = element.querySelector(selector);
                                    if (storeEl && storeEl.textContent.trim()) {
                                        storeName = storeEl.textContent.trim();
                                        break;
                                    }
                                }
                                
                                // البحث عن الرابط
                                const linkEl = element.querySelector('a[href]');
                                const productUrl = linkEl ? linkEl.href : '';
                                
                                if (productName && price && storeName) {
                                    products.push({
                                        name: productName,
                                        price: price,
                                        store: storeName,
                                        url: productUrl,
                                        source: 'google_shopping'
                                    });
                                }
                            } catch (e) {
                                // تجاهل الأخطاء والمتابعة
                            }
                        });
                        
                        return products;
                    }
                """)
                
                await browser.close()
                
                # تنظيف وفلترة النتائج
                cleaned_results = []
                seen_stores = set()
                
                for product in price_data:
                    store_name = product['store'].lower()
                    
                    # فلترة المتاجر المصرية المعروفة
                    egyptian_stores = [
                        'jumia', 'noon', 'souq', 'btech', 'b-tech', 'tradeline',
                        'cairosales', 'elnekhely', 'جوميا', 'نون', 'سوق'
                    ]
                    
                    is_egyptian_store = any(store in store_name for store in egyptian_stores)
                    
                    if (is_egyptian_store and 
                        store_name not in seen_stores and
                        self.google_settings['min_price'] <= product['price'] <= self.google_settings['max_price']):
                        
                        cleaned_results.append(product)
                        seen_stores.add(store_name)
                        
                        print(f"   ✅ {product['store']}: {product['price']:,.0f} EGP")
                
                # حفظ في الكاش
                self.search_cache[cache_key] = {
                    'data': cleaned_results,
                    'timestamp': time.time()
                }
                
                if cleaned_results:
                    self.comparison_stats['successful_searches'] += 1
                    self.comparison_stats['products_with_prices'] += len(cleaned_results)
                else:
                    print(f"   ⚪ لم يتم العثور على أسعار من متاجر مصرية")
                
                return cleaned_results
                
        except Exception as e:
            print(f"   ❌ خطأ في البحث في جوجل: {e}")
            self.comparison_stats['google_errors'] += 1
            return []
        
        finally:
            self.comparison_stats['total_searches'] += 1
    
    def calculate_name_similarity(self, amazon_name: str, google_name: str) -> float:
        """حساب تشابه أسماء المنتجات"""
        
        # تنظيف الأسماء
        amazon_clean = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', amazon_name.lower()).split()
        google_clean = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', google_name.lower()).split()
        
        # الكلمات المشتركة
        amazon_words = set(amazon_clean)
        google_words = set(google_clean)
        
        common_words = amazon_words & google_words
        total_words = amazon_words | google_words
        
        if not total_words:
            return 0.0
        
        # نسبة التشابه الأساسية
        basic_similarity = len(common_words) / len(total_words)
        
        # إضافة نقاط للعلامات التجارية
        important_brands = [
            'iphone', 'samsung', 'sony', 'lg', 'xiaomi', 'apple', 'nike', 'adidas'
        ]
        
        brand_bonus = 0
        for brand in important_brands:
            if brand in amazon_name.lower() and brand in google_name.lower():
                brand_bonus += 0.4
        
        return min(1.0, basic_similarity + brand_bonus)
    
    async def compare_with_google_prices(self, amazon_product: Dict, amazon_price: float) -> Dict:
        """مقارنة سعر أمازون مع أسعار جوجل"""
        
        product_name = amazon_product.get('name', '')
        
        # البحث في جوجل
        google_results = await self.search_google_shopping(product_name)
        
        comparison_result = {
            'amazon_price': amazon_price,
            'google_results': google_results,
            'market_analysis': {},
            'best_deals': [],
            'is_amazon_cheapest': False,
            'is_good_deal': False,
            'confidence_score': 0,
            'recommendation': 'غير محدد'
        }
        
        if google_results:
            # فلترة المنتجات المشابهة
            similar_products = []
            for result in google_results:
                similarity = self.calculate_name_similarity(product_name, result['name'])
                if similarity > 0.4:  # حد أدنى للتشابه
                    result['similarity'] = similarity
                    similar_products.append(result)
            
            if similar_products:
                # ترتيب حسب التشابه
                similar_products.sort(key=lambda x: x['similarity'], reverse=True)
                
                # أخذ أفضل 5 منتجات مشابهة
                top_matches = similar_products[:5]
                market_prices = [p['price'] for p in top_matches]
                
                # حساب إحصائيات السوق
                avg_market_price = statistics.mean(market_prices)
                min_market_price = min(market_prices)
                max_market_price = max(market_prices)
                median_market_price = statistics.median(market_prices)
                
                # تحليل موقع أمازون في السوق
                amazon_rank = sum(1 for price in market_prices if price > amazon_price) + 1
                total_competitors = len(market_prices)
                
                # حساب الفروق
                vs_avg_diff = ((avg_market_price - amazon_price) / avg_market_price) * 100
                vs_min_diff = ((min_market_price - amazon_price) / min_market_price) * 100
                
                comparison_result['market_analysis'] = {
                    'avg_market_price': avg_market_price,
                    'min_market_price': min_market_price,
                    'max_market_price': max_market_price,
                    'median_market_price': median_market_price,
                    'amazon_rank': amazon_rank,
                    'total_competitors': total_competitors,
                    'vs_avg_difference': vs_avg_diff,
                    'vs_min_difference': vs_min_diff,
                    'market_range': max_market_price - min_market_price
                }
                
                comparison_result['best_deals'] = [
                    {
                        'store': p['store'],
                        'price': p['price'],
                        'similarity': p['similarity']
                    } for p in top_matches
                ]
                
                # تحديد جودة العرض
                confidence_factors = []
                base_confidence = 50
                
                # عامل 1: مقارنة مع المتوسط
                if vs_avg_diff > 25:
                    confidence_factors.append(('متوسط السوق', 35, f"أرخص بـ {vs_avg_diff:.0f}% من المتوسط"))
                elif vs_avg_diff > 15:
                    confidence_factors.append(('متوسط السوق', 25, f"أرخص بـ {vs_avg_diff:.0f}% من المتوسط"))
                elif vs_avg_diff > 5:
                    confidence_factors.append(('متوسط السوق', 15, f"أرخص بـ {vs_avg_diff:.0f}% من المتوسط"))
                elif vs_avg_diff > -10:
                    confidence_factors.append(('متوسط السوق', 5, f"مقارب للمتوسط ({vs_avg_diff:+.0f}%)"))
                else:
                    confidence_factors.append(('متوسط السوق', -25, f"أغلى بـ {abs(vs_avg_diff):.0f}% من المتوسط"))
                
                # عامل 2: مقارنة مع أقل سعر
                if amazon_rank == 1:
                    confidence_factors.append(('ترتيب السعر', 30, f"الأرخص في السوق!"))
                elif amazon_rank <= 2:
                    confidence_factors.append(('ترتيب السعر', 20, f"ثاني أرخص سعر"))
                elif amazon_rank <= 3:
                    confidence_factors.append(('ترتيب السعر', 10, f"ثالث أرخص سعر"))
                else:
                    confidence_factors.append(('ترتيب السعر', -15, f"ترتيب {amazon_rank} من أصل {total_competitors}"))
                
                # عامل 3: عدد المنافسين
                competitors_bonus = min(20, len(top_matches) * 4)
                confidence_factors.append(('عدد المنافسين', competitors_bonus, f"مقارنة مع {len(top_matches)} متاجر"))
                
                # عامل 4: جودة التطابق
                avg_similarity = statistics.mean([p['similarity'] for p in top_matches])
                if avg_similarity > 0.8:
                    confidence_factors.append(('جودة التطابق', 15, 'تطابق عالي مع المنتجات'))
                elif avg_similarity > 0.6:
                    confidence_factors.append(('جودة التطابق', 10, 'تطابق جيد'))
                else:
                    confidence_factors.append(('جودة التطابق', 0, 'تطابق متوسط'))
                
                # حساب النقاط النهائية
                total_confidence = base_confidence
                for factor_name, points, description in confidence_factors:
                    total_confidence += points
                
                comparison_result['confidence_score'] = max(0, min(100, total_confidence))
                comparison_result['confidence_factors'] = confidence_factors
                
                # تحديد التوصية النهائية
                if comparison_result['confidence_score'] >= 85:
                    comparison_result['is_good_deal'] = True
                    comparison_result['is_amazon_cheapest'] = amazon_rank <= 2
                    comparison_result['recommendation'] = f"🔥 عرض ممتاز! ترتيب {amazon_rank} من {total_competitors} متاجر"
                    
                elif comparison_result['confidence_score'] >= 70:
                    comparison_result['is_good_deal'] = True
                    comparison_result['is_amazon_cheapest'] = amazon_rank <= 3
                    comparison_result['recommendation'] = f"✅ عرض جيد! أرخص من {total_competitors - amazon_rank} متاجر"
                    
                elif comparison_result['confidence_score'] >= 55:
                    comparison_result['is_good_deal'] = True
                    comparison_result['is_amazon_cheapest'] = False
                    comparison_result['recommendation'] = f"⚠️ عرض مقبول! ترتيب {amazon_rank} في السوق"
                    
                else:
                    comparison_result['is_good_deal'] = False
                    comparison_result['is_amazon_cheapest'] = False
                    comparison_result['recommendation'] = f"❌ عرض ضعيف! يوجد {amazon_rank-1} خيارات أرخص"
                
                # طباعة التفاصيل
                print(f"   📊 تحليل جوجل:")
                print(f"      💰 متوسط السوق: {avg_market_price:,.0f} EGP")
                print(f"      📉 أقل سعر: {min_market_price:,.0f} EGP")
                print(f"      📈 أعلى سعر: {max_market_price:,.0f} EGP")
                print(f"      🎯 أمازون: {amazon_price:,.0f} EGP (ترتيب {amazon_rank})")
                print(f"      📊 الفرق عن المتوسط: {vs_avg_diff:+.1f}%")
                print(f"      🏆 الثقة: {comparison_result['confidence_score']}/100")
                print(f"      🌐 المنافسين: {len(top_matches)} متجر")
                print(f"   {comparison_result['recommendation']}")
                
                # حفظ في الكاش
                self.search_cache[cache_key] = {
                    'data': google_results,
                    'timestamp': time.time()
                }
                
        return comparison_result
    
    def get_google_comparison_stats(self) -> Dict:
        """الحصول على إحصائيات مقارنة جوجل"""
        total = self.comparison_stats['total_searches']
        
        return {
            'total_searches': total,
            'successful_searches': self.comparison_stats['successful_searches'],
            'success_rate': (self.comparison_stats['successful_searches'] / max(total, 1)) * 100,
            'products_with_prices': self.comparison_stats['products_with_prices'],
            'validated_deals': self.comparison_stats['validated_deals'],
            'rejected_deals': self.comparison_stats['rejected_deals'],
            'validation_rate': (self.comparison_stats['validated_deals'] / max(total, 1)) * 100,
            'google_errors': self.comparison_stats['google_errors'],
            'cache_size': len(self.search_cache)
        }

# دالة للتكامل مع السكرابر
google_comparator = GooglePriceComparator()

async def validate_deal_with_google_comparison(item: Dict, old_price: float, 
                                             new_price: float, discount_percent: float) -> Tuple[bool, str]:
    """التحقق من العرض عن طريق مقارنة جوجل"""
    
    try:
        comparison_result = await google_comparator.compare_with_google_prices(item, new_price)
        
        should_send = comparison_result['is_good_deal']
        recommendation = comparison_result['recommendation']
        confidence = comparison_result['confidence_score']
        
        # إضافة معلومات جوجل للمنتج
        item['google_comparison'] = comparison_result
        item['google_confidence'] = confidence
        item['google_recommendation'] = recommendation
        
        if should_send:
            google_comparator.comparison_stats['validated_deals'] += 1
            return True, f"{recommendation} (ثقة: {confidence}%)"
        else:
            google_comparator.comparison_stats['rejected_deals'] += 1
            return False, f"{recommendation} (ثقة: {confidence}%)"
    
    except Exception as e:
        print(f"❌ خطأ في مقارنة جوجل: {e}")
        # في حالة الخطأ، استخدم فلترة أساسية
        if discount_percent <= 70 and new_price >= 30:
            return True, "⚠️ مقارنة جوجل فشلت - فلترة أساسية"
        else:
            return False, "❌ مقارنة جوجل فشلت + عرض مشبوه"

# اختبار النظام
async def test_google_comparison():
    """اختبار نظام مقارنة جوجل"""
    
    print("🧪 اختبار نظام مقارنة جوجل")
    print("=" * 60)
    
    test_products = [
        {
            'name': 'iPhone 15 Pro Max 256GB',
            'price': 42000,
            'section': 'Electronics',
            'asin': 'B0CHX1W1XY'
        },
        {
            'name': 'Samsung Galaxy Buds2 Pro',
            'price': 3200,
            'section': 'Electronics',
            'asin': 'B0B2SH4MQS'
        }
    ]
    
    for product in test_products:
        print(f"\n🧪 اختبار: {product['name']}")
        
        # محاكاة خصم
        old_price = product['price'] * 1.25
        new_price = product['price']
        discount = ((old_price - new_price) / old_price) * 100
        
        print(f"   💰 السعر: {old_price:,.0f} → {new_price:,.0f} ({discount:.1f}% OFF)")
        
        should_send, reason = await validate_deal_with_google_comparison(
            product, old_price, new_price, discount
        )
        
        if should_send:
            print(f"   ✅ {reason}")
        else:
            print(f"   ❌ {reason}")
        
        print("-" * 50)
    
    # إحصائيات النهائية
    stats = google_comparator.get_google_comparison_stats()
    print(f"\n📊 إحصائيات جوجل:")
    print(f"   🔍 عمليات بحث: {stats['total_searches']}")
    print(f"   ✅ بحثات ناجحة: {stats['successful_searches']}")
    print(f"   📱 عروض معتمدة: {stats['validated_deals']}")
    print(f"   🚫 عروض مرفوضة: {stats['rejected_deals']}")
    print(f"   📈 معدل النجاح: {stats['success_rate']:.1f}%")

if __name__ == "__main__":
    print("🔍 نظام مقارنة الأسعار عن طريق جوجل")
    print("💡 الفكرة: استخدام جوجل شوبينج للحصول على جميع الأسعار في مكان واحد")
    print()
    
    asyncio.run(test_google_comparison())