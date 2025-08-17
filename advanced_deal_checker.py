#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام متقدم للتحقق من العروض الحقيقية باستخدام مصادر متعددة
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics
import re
import asyncio
from playwright.async_api import async_playwright

class AdvancedDealChecker:
    """محقق متقدم للعروض مع مصادر خارجية"""
    
    def __init__(self):
        self.price_sources = {
            'kanbkam': 'https://www.kanbkam.com/eg/ar/search/l?q=',
            'jumia': 'https://www.jumia.com.eg/catalog/?q=',
            'noon': 'https://www.noon.com/egypt-en/search?q='
        }
        
        self.validation_rules = {
            'min_price': 30,           # أقل سعر مقبول
            'max_discount': 80,        # أقصى خصم مقبول
            'min_original_price': 80,  # أقل سعر أصلي
            'price_jump_threshold': 2.5,  # حد القفزة السعرية المشبوهة
            'trust_score_threshold': 70   # حد نقاط الثقة
        }
        
        self.deal_patterns = {
            'fake_discount_indicators': [
                r'was.*now',  # كلمات خصم مزيف
                r'save.*%',
                r'limited.*time',
                r'flash.*sale'
            ],
            'quality_indicators': [
                r'amazon.*choice',
                r'best.*seller',
                r'highly.*rated',
                r'prime'
            ],
            'suspicious_names': [
                r'replica', r'copy', r'fake', r'imitation',
                r'نسخة', r'تقليد', r'مقلد'
            ]
        }
        
        self.validated_deals = []
        self.rejected_deals = []
        self.manual_review_deals = []
    
    async def check_price_on_kanbkam(self, asin: str) -> Optional[Dict]:
        """فحص السعر على كانبكام"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                url = f"https://www.kanbkam.com/eg/ar/product/{asin}"
                await page.goto(url, timeout=15000)
                await page.wait_for_timeout(2000)
                
                # البحث عن معلومات السعر
                price_info = await page.evaluate("""
                    () => {
                        // البحث عن السعر الحالي
                        const currentPriceEl = document.querySelector('.current-price, .price-now, .price');
                        const currentPrice = currentPriceEl ? currentPriceEl.textContent : null;
                        
                        // البحث عن السعر التاريخي
                        const avgPriceEl = document.querySelector('.avg-price, .historical-price');
                        const avgPrice = avgPriceEl ? avgPriceEl.textContent : null;
                        
                        // البحث عن أقل سعر
                        const lowestPriceEl = document.querySelector('.lowest-price, .min-price');
                        const lowestPrice = lowestPriceEl ? lowestPriceEl.textContent : null;
                        
                        return {
                            current_price: currentPrice,
                            avg_price: avgPrice,
                            lowest_price: lowestPrice,
                            available: !!currentPrice
                        };
                    }
                """)
                
                await browser.close()
                return price_info
                
        except Exception as e:
            print(f"⚠️ خطأ في فحص كانبكام: {e}")
            return None
    
    def extract_price_from_text(self, text: str) -> Optional[float]:
        """استخراج السعر من النص"""
        if not text:
            return None
        
        # البحث عن أرقام في النص
        numbers = re.findall(r'[\d,]+\.?\d*', text.replace(',', ''))
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                return None
        return None
    
    async def cross_validate_price(self, asin: str, amazon_price: float) -> Dict:
        """التحقق المتقاطع من السعر عبر مصادر متعددة"""
        
        validation_result = {
            'amazon_price': amazon_price,
            'external_prices': {},
            'price_difference': {},
            'is_reasonable': True,
            'confidence_score': 50
        }
        
        # فحص كانبكام
        kanbkam_data = await self.check_price_on_kanbkam(asin)
        if kanbkam_data and kanbkam_data.get('available'):
            current_price = self.extract_price_from_text(kanbkam_data.get('current_price', ''))
            avg_price = self.extract_price_from_text(kanbkam_data.get('avg_price', ''))
            
            if current_price:
                validation_result['external_prices']['kanbkam'] = current_price
                price_diff = abs(amazon_price - current_price) / current_price * 100
                validation_result['price_difference']['kanbkam'] = price_diff
                
                # إذا كان الفرق أقل من 20%، زيادة الثقة
                if price_diff < 20:
                    validation_result['confidence_score'] += 30
                elif price_diff < 50:
                    validation_result['confidence_score'] += 15
                else:
                    validation_result['confidence_score'] -= 20
            
            if avg_price:
                avg_diff = abs(amazon_price - avg_price) / avg_price * 100
                if avg_diff > 50:  # السعر أقل بكثير من المتوسط
                    validation_result['confidence_score'] += 20  # عرض جيد محتمل
        
        return validation_result
    
    def analyze_deal_quality(self, item: Dict, old_price: float, new_price: float, 
                           discount_percent: float) -> Dict:
        """تحليل جودة العرض بطريقة متقدمة"""
        
        analysis = {
            'quality_score': 0,
            'risk_factors': [],
            'positive_factors': [],
            'recommendation': 'unknown',
            'alert_priority': 'low'
        }
        
        product_name = item.get('name', '').lower()
        
        # عوامل إيجابية
        positive_checks = [
            (lambda: 50 <= new_price <= 5000, "سعر في النطاق المعقول", 15),
            (lambda: 25 <= discount_percent <= 70, "نسبة خصم معقولة", 20),
            (lambda: len(product_name) > 30, "وصف مفصل للمنتج", 10),
            (lambda: any(word in product_name for word in ['amazon', 'prime', 'choice']), "منتج أمازون معتمد", 25),
            (lambda: item.get('img', ''), "يحتوي على صورة", 5),
            (lambda: old_price > new_price * 1.2, "فرق سعر منطقي", 15),
            (lambda: not any(word in product_name for word in ['replica', 'copy', 'fake']), "اسم غير مشبوه", 10)
        ]
        
        for check, description, points in positive_checks:
            try:
                if check():
                    analysis['quality_score'] += points
                    analysis['positive_factors'].append(description)
            except:
                pass
        
        # عوامل خطر
        risk_checks = [
            (lambda: new_price < 20, "سعر منخفض جداً", -30),
            (lambda: discount_percent > 85, "خصم مشكوك فيه", -40),
            (lambda: old_price < 50, "سعر أصلي منخفض", -20),
            (lambda: any(word in product_name for word in ['fake', 'replica', 'copy']), "منتج مشبوه", -50),
            (lambda: new_price > 20000, "سعر عالي جداً", -25),
            (lambda: old_price / new_price > 5, "نسبة خصم غير واقعية", -35)
        ]
        
        for check, description, points in risk_checks:
            try:
                if check():
                    analysis['quality_score'] += points  # points سالبة
                    analysis['risk_factors'].append(description)
            except:
                pass
        
        # تحديد التوصية
        final_score = max(0, analysis['quality_score'])
        
        if final_score >= 80:
            analysis['recommendation'] = 'send_immediately'
            analysis['alert_priority'] = 'high'
        elif final_score >= 60:
            analysis['recommendation'] = 'send_with_caution'
            analysis['alert_priority'] = 'medium'
        elif final_score >= 40:
            analysis['recommendation'] = 'manual_review'
            analysis['alert_priority'] = 'low'
        else:
            analysis['recommendation'] = 'reject'
            analysis['alert_priority'] = 'none'
        
        analysis['final_score'] = final_score
        return analysis
    
    async def comprehensive_deal_validation(self, item: Dict, old_price: float, 
                                          new_price: float, discount_percent: float) -> Tuple[bool, str, Dict]:
        """تحقق شامل ومتقدم من العرض"""
        
        asin = item.get('asin', '')
        
        # التحليل الأساسي
        quality_analysis = self.analyze_deal_quality(item, old_price, new_price, discount_percent)
        
        # التحقق المتقاطع من الأسعار (إذا كان متاح)
        try:
            price_validation = await self.cross_validate_price(asin, new_price)
            quality_analysis['price_validation'] = price_validation
            
            # تعديل النقاط حسب التحقق الخارجي
            if price_validation['confidence_score'] > 70:
                quality_analysis['final_score'] += 20
            elif price_validation['confidence_score'] < 30:
                quality_analysis['final_score'] -= 15
                
        except Exception as e:
            print(f"⚠️ لم يتم التحقق الخارجي: {e}")
        
        # تحديد القرار النهائي
        should_send = quality_analysis['recommendation'] in ['send_immediately', 'send_with_caution']
        
        # إنشاء رسالة التوضيح
        if should_send:
            reason = f"✅ عرض موثوق ({quality_analysis['final_score']}/100) - {quality_analysis['alert_priority']} priority"
        else:
            reason = f"❌ عرض مرفوض ({quality_analysis['final_score']}/100) - {', '.join(quality_analysis['risk_factors'][:2])}"
        
        return should_send, reason, quality_analysis

# دالة للتكامل مع السكرابر الأصلي
advanced_checker = AdvancedDealChecker()

def advanced_alert_filter(item, old_price, new_price, discount_percent, drop_detected=False):
    """فلتر متقدم للتنبيهات"""
    
    async def validate():
        return await advanced_checker.comprehensive_deal_validation(
            item, old_price, new_price, discount_percent
        )
    
    # تشغيل التحقق في حلقة async جديدة
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        should_send, reason, analysis = loop.run_until_complete(validate())
        
        if should_send:
            # إضافة معلومات التحليل للمنتج
            item['analysis'] = analysis
            item['validation_reason'] = reason
            
            print(f"📱 تنبيه معتمد: {item.get('name', '')[:40]}... - {reason}")
            return True
        else:
            print(f"🚫 تنبيه مرفوض: {item.get('name', '')[:40]}... - {reason}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في التحقق المتقدم: {e}")
        return True  # في حالة الخطأ، أرسل التنبيه
    finally:
        loop.close()

if __name__ == "__main__":
    print("🧠 نظام التحقق المتقدم من العروض")
    print("=" * 50)
    
    # اختبار العرض
    test_item = {
        "asin": "B08N5WRWNW",
        "name": "Echo Dot (4th Gen) Smart speaker with Alexa",
        "section": "Electronics",
        "url": "https://amazon.eg/echo-dot",
        "img": "https://m.media-amazon.com/images/I/61SUj2aKoEL._AC_SL1000_.jpg"
    }
    
    print("🧪 اختبار عرض:")
    print(f"   📦 المنتج: {test_item['name']}")
    print(f"   💰 السعر: 1200 → 899 (25% OFF)")
    
    should_send = advanced_alert_filter(test_item, 1200, 899, 25.0, False)
    
    if should_send:
        print("✅ العرض معتمد للإرسال")
    else:
        print("❌ العرض مرفوض")