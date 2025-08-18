#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - النظام النهائي بدون مواقع خارجية
الواجهة الأصلية + تحليل ذكي داخلي فقط + إرسال الصور
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

# جميع الفئات الأصلية
CATEGORIES = {
    'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Beauty': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017988031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Fashion': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018165031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Home & Kitchen': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021933031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Sports & Outdoors': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018038031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Automotive': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017874031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Baby Products': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017908031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Books': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017915031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Health & Personal Care': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017995031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Toys & Games': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018059031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Office Products': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018024031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Pet Supplies': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018031031%2Cp_98%3A21909049031&dc&page={}&language=en"
}

# إعداد الواجهة الأصلية
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# متغيرات عامة
DB_FILE = "amz_products.json"
db = {}
stop_flag = {"stop": False}
running = [False]
telegram_alerts_enabled = [True]
smart_analysis_enabled = [True]
auto_new_products_mode = [False]

ALERT_DISCOUNT = 25
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام التحليل الذكي الداخلي (بدون مواقع خارجية)
class SmartInternalAnalyzer:
    """محلل ذكي داخلي - بدون الحاجة لمواقع خارجية"""
    
    def __init__(self):
        self.stats = {
            'total_analyses': 0,
            'high_confidence_deals': 0,
            'medium_confidence_deals': 0,
            'low_confidence_deals': 0,
            'rejected_deals': 0,
            'brand_matches': 0,
            'category_matches': 0,
            'price_range_matches': 0
        }
        
        # قاعدة بيانات شاملة للعلامات التجارية والأسعار المتوقعة
        self.comprehensive_brand_guide = {
            # إلكترونيات - هواتف
            'samsung': {'min': 2000, 'max': 50000, 'category': 'electronics', 'quality': 'premium'},
            'xiaomi': {'min': 1500, 'max': 15000, 'category': 'electronics', 'quality': 'good'},
            'apple': {'min': 15000, 'max': 100000, 'category': 'electronics', 'quality': 'premium'},
            'iphone': {'min': 20000, 'max': 100000, 'category': 'electronics', 'quality': 'premium'},
            'huawei': {'min': 2000, 'max': 25000, 'category': 'electronics', 'quality': 'good'},
            'oppo': {'min': 1800, 'max': 20000, 'category': 'electronics', 'quality': 'good'},
            'vivo': {'min': 1800, 'max': 18000, 'category': 'electronics', 'quality': 'good'},
            'realme': {'min': 1500, 'max': 12000, 'category': 'electronics', 'quality': 'budget'},
            'redmi': {'min': 1200, 'max': 8000, 'category': 'electronics', 'quality': 'budget'},
            
            # إلكترونيات - إكسسوارات
            'anker': {'min': 200, 'max': 2000, 'category': 'accessories', 'quality': 'premium'},
            'joyroom': {'min': 50, 'max': 500, 'category': 'accessories', 'quality': 'budget'},
            'ugreen': {'min': 100, 'max': 1000, 'category': 'accessories', 'quality': 'good'},
            'baseus': {'min': 80, 'max': 800, 'category': 'accessories', 'quality': 'good'},
            'belkin': {'min': 300, 'max': 2500, 'category': 'accessories', 'quality': 'premium'},
            
            # إلكترونيات - أجهزة منزلية
            'sony': {'min': 1000, 'max': 30000, 'category': 'electronics', 'quality': 'premium'},
            'lg': {'min': 2000, 'max': 50000, 'category': 'electronics', 'quality': 'premium'},
            'philips': {'min': 500, 'max': 15000, 'category': 'electronics', 'quality': 'good'},
            'panasonic': {'min': 800, 'max': 20000, 'category': 'electronics', 'quality': 'good'},
            
            # كمبيوتر وطباعة
            'hp': {'min': 3000, 'max': 50000, 'category': 'computers', 'quality': 'good'},
            'dell': {'min': 4000, 'max': 60000, 'category': 'computers', 'quality': 'premium'},
            'lenovo': {'min': 3500, 'max': 45000, 'category': 'computers', 'quality': 'good'},
            'asus': {'min': 3000, 'max': 80000, 'category': 'computers', 'quality': 'premium'},
            'acer': {'min': 2500, 'max': 35000, 'category': 'computers', 'quality': 'budget'},
            'canon': {'min': 2000, 'max': 25000, 'category': 'computers', 'quality': 'premium'},
            'epson': {'min': 1500, 'max': 20000, 'category': 'computers', 'quality': 'good'},
            
            # منتجات العناية والتجميل
            'vaseline': {'min': 40, 'max': 200, 'category': 'beauty', 'quality': 'budget'},
            'nivea': {'min': 60, 'max': 300, 'category': 'beauty', 'quality': 'good'},
            'dove': {'min': 50, 'max': 250, 'category': 'beauty', 'quality': 'good'},
            'axe': {'min': 80, 'max': 400, 'category': 'beauty', 'quality': 'good'},
            'loreal': {'min': 100, 'max': 800, 'category': 'beauty', 'quality': 'premium'},
            'garnier': {'min': 80, 'max': 500, 'category': 'beauty', 'quality': 'good'},
            'pantene': {'min': 60, 'max': 300, 'category': 'beauty', 'quality': 'good'},
            'head': {'min': 80, 'max': 350, 'category': 'beauty', 'quality': 'good'},
            'shoulders': {'min': 80, 'max': 350, 'category': 'beauty', 'quality': 'good'},
            'tresemme': {'min': 70, 'max': 400, 'category': 'beauty', 'quality': 'good'},
            'schwarzkopf': {'min': 120, 'max': 600, 'category': 'beauty', 'quality': 'premium'},
            
            # منتجات العناية الشخصية
            'gillette': {'min': 100, 'max': 800, 'category': 'personal_care', 'quality': 'premium'},
            'oral': {'min': 50, 'max': 500, 'category': 'personal_care', 'quality': 'premium'},
            'colgate': {'min': 30, 'max': 200, 'category': 'personal_care', 'quality': 'good'},
            'listerine': {'min': 80, 'max': 400, 'category': 'personal_care', 'quality': 'good'},
            'johnson': {'min': 60, 'max': 400, 'category': 'personal_care', 'quality': 'good'},
            
            # أدوات منزلية ومطبخ
            'tefal': {'min': 200, 'max': 3000, 'category': 'kitchen', 'quality': 'premium'},
            'pyrex': {'min': 100, 'max': 1000, 'category': 'kitchen', 'quality': 'good'},
            'luminarc': {'min': 50, 'max': 500, 'category': 'kitchen', 'quality': 'good'},
            'lock': {'min': 30, 'max': 300, 'category': 'kitchen', 'quality': 'budget'},
            
            # ملابس وأزياء
            'nike': {'min': 500, 'max': 5000, 'category': 'fashion', 'quality': 'premium'},
            'adidas': {'min': 400, 'max': 4000, 'category': 'fashion', 'quality': 'premium'},
            'puma': {'min': 300, 'max': 2500, 'category': 'fashion', 'quality': 'good'},
            'under': {'min': 400, 'max': 3000, 'category': 'fashion', 'quality': 'premium'},
            'armour': {'min': 400, 'max': 3000, 'category': 'fashion', 'quality': 'premium'},
            
            # ألعاب وترفيه
            'lego': {'min': 200, 'max': 5000, 'category': 'toys', 'quality': 'premium'},
            'mattel': {'min': 100, 'max': 2000, 'category': 'toys', 'quality': 'good'},
            'hasbro': {'min': 150, 'max': 2500, 'category': 'toys', 'quality': 'good'},
            
            # منتجات أطفال
            'pampers': {'min': 100, 'max': 800, 'category': 'baby', 'quality': 'premium'},
            'huggies': {'min': 90, 'max': 700, 'category': 'baby', 'quality': 'premium'},
            'chicco': {'min': 200, 'max': 3000, 'category': 'baby', 'quality': 'premium'},
            
            # منتجات رياضية
            'decathlon': {'min': 100, 'max': 2000, 'category': 'sports', 'quality': 'budget'},
            'wilson': {'min': 300, 'max': 3000, 'category': 'sports', 'quality': 'good'},
            
            # منتجات السيارات
            'bosch': {'min': 200, 'max': 5000, 'category': 'automotive', 'quality': 'premium'},
            'castrol': {'min': 150, 'max': 1500, 'category': 'automotive', 'quality': 'premium'},
            'shell': {'min': 100, 'max': 1000, 'category': 'automotive', 'quality': 'premium'},
        }
        
        # كلمات مفتاحية للفئات
        self.category_keywords = {
            'electronics': ['phone', 'mobile', 'tablet', 'laptop', 'computer', 'tv', 'speaker', 'headphone', 'camera'],
            'beauty': ['cream', 'lotion', 'shampoo', 'conditioner', 'perfume', 'makeup', 'skincare'],
            'personal_care': ['toothbrush', 'toothpaste', 'razor', 'deodorant', 'soap'],
            'kitchen': ['pan', 'pot', 'plate', 'cup', 'knife', 'spoon', 'bowl'],
            'fashion': ['shirt', 'pants', 'shoes', 'dress', 'jacket', 'bag'],
            'toys': ['toy', 'game', 'puzzle', 'doll', 'car', 'block'],
            'baby': ['diaper', 'bottle', 'stroller', 'crib', 'baby'],
            'sports': ['ball', 'gym', 'fitness', 'exercise', 'sport'],
            'automotive': ['oil', 'filter', 'brake', 'tire', 'battery']
        }
    
    def extract_brand_and_category(self, product_name: str) -> dict:
        """استخراج العلامة التجارية والفئة من اسم المنتج"""
        
        name_lower = product_name.lower()
        result = {
            'brand': 'unknown',
            'category': 'general',
            'brand_info': None,
            'category_confidence': 0
        }
        
        # البحث عن العلامة التجارية
        for brand, info in self.comprehensive_brand_guide.items():
            if brand in name_lower:
                result['brand'] = brand
                result['brand_info'] = info
                result['category'] = info['category']
                result['category_confidence'] = 90
                self.stats['brand_matches'] += 1
                break
        
        # إذا لم نجد العلامة التجارية، نحاول تحديد الفئة من الكلمات
        if result['brand'] == 'unknown':
            for category, keywords in self.category_keywords.items():
                matches = sum(1 for keyword in keywords if keyword in name_lower)
                if matches > 0:
                    confidence = min(80, matches * 20)
                    if confidence > result['category_confidence']:
                        result['category'] = category
                        result['category_confidence'] = confidence
                        self.stats['category_matches'] += 1
        
        return result
    
    def smart_price_analysis(self, product_name: str, amazon_price: float, discount_percent: float) -> dict:
        """تحليل ذكي شامل للسعر بدون مواقع خارجية"""
        
        # استخراج معلومات المنتج
        product_info = self.extract_brand_and_category(product_name)
        brand = product_info['brand']
        category = product_info['category']
        brand_info = product_info['brand_info']
        
        result = {
            'is_good_deal': False,
            'confidence': 0,
            'reason': '',
            'analysis_details': {
                'discount_score': 0,
                'price_score': 0,
                'brand_score': 0,
                'category_score': 0,
                'final_score': 0
            },
            'brand': brand,
            'category': category,
            'assessment_type': 'smart_internal'
        }
        
        # 1. تقييم الخصم (40 نقطة)
        discount_score = 0
        discount_desc = ""
        
        if discount_percent >= 60:
            discount_score = 40
            discount_desc = "خصم هائل"
        elif discount_percent >= 50:
            discount_score = 35
            discount_desc = "خصم ضخم"
        elif discount_percent >= 40:
            discount_score = 30
            discount_desc = "خصم كبير جداً"
        elif discount_percent >= 30:
            discount_score = 25
            discount_desc = "خصم كبير"
        elif discount_percent >= 25:
            discount_score = 20
            discount_desc = "خصم جيد"
        elif discount_percent >= 20:
            discount_score = 15
            discount_desc = "خصم متوسط"
        elif discount_percent >= 15:
            discount_score = 10
            discount_desc = "خصم بسيط"
        else:
            discount_score = 5
            discount_desc = "خصم ضعيف"
        
        result['analysis_details']['discount_score'] = discount_score
        
        # 2. تقييم السعر والعلامة التجارية (35 نقطة)
        price_score = 0
        brand_desc = ""
        
        if brand_info:
            min_expected = brand_info['min']
            max_expected = brand_info['max']
            quality = brand_info['quality']
            
            # تقييم السعر بناءً على النطاق المتوقع
            if amazon_price <= min_expected * 0.8:  # أقل من الحد الأدنى بـ 20%
                price_score = 35
                brand_desc = f"سعر استثنائي لـ {brand} ({quality})"
                self.stats['price_range_matches'] += 1
            elif amazon_price <= min_expected:  # في النطاق المنخفض
                price_score = 30
                brand_desc = f"سعر ممتاز لـ {brand} ({quality})"
                self.stats['price_range_matches'] += 1
            elif amazon_price <= (min_expected + max_expected) / 2:  # في النطاق المتوسط
                price_score = 25
                brand_desc = f"سعر جيد لـ {brand} ({quality})"
                self.stats['price_range_matches'] += 1
            elif amazon_price <= max_expected:  # في النطاق العالي
                price_score = 15
                brand_desc = f"سعر مقبول لـ {brand} ({quality})"
            else:  # أعلى من المتوقع
                price_score = 5
                brand_desc = f"سعر مرتفع لـ {brand} ({quality})"
        else:
            # للعلامات غير المعروفة، تقييم عام
            if amazon_price <= 50:
                price_score = 25
                brand_desc = "منتج اقتصادي"
            elif amazon_price <= 200:
                price_score = 20
                brand_desc = "منتج متوسط السعر"
            elif amazon_price <= 1000:
                price_score = 15
                brand_desc = "منتج مرتفع السعر"
            elif amazon_price <= 5000:
                price_score = 10
                brand_desc = "منتج غالي"
            else:
                price_score = 5
                brand_desc = "منتج باهظ الثمن"
        
        result['analysis_details']['price_score'] = price_score
        result['analysis_details']['brand_score'] = price_score  # نفس النقاط للبساطة
        
        # 3. تقييم الفئة (15 نقطة)
        category_score = 0
        category_desc = ""
        
        # تقييم بناءً على الفئة والسعر
        category_ranges = {
            'electronics': {'low': 1000, 'high': 10000},
            'beauty': {'low': 50, 'high': 300},
            'personal_care': {'low': 30, 'high': 200},
            'kitchen': {'low': 100, 'high': 1000},
            'fashion': {'low': 200, 'high': 2000},
            'toys': {'low': 100, 'high': 1000},
            'baby': {'low': 80, 'high': 500},
            'sports': {'low': 150, 'high': 1500},
            'automotive': {'low': 100, 'high': 2000}
        }
        
        if category in category_ranges:
            cat_range = category_ranges[category]
            if amazon_price <= cat_range['low']:
                category_score = 15
                category_desc = f"سعر ممتاز للفئة ({category})"
            elif amazon_price <= cat_range['high']:
                category_score = 10
                category_desc = f"سعر مناسب للفئة ({category})"
            else:
                category_score = 5
                category_desc = f"سعر مرتفع للفئة ({category})"
        else:
            category_score = 8
            category_desc = "فئة عامة"
        
        result['analysis_details']['category_score'] = category_score
        
        # 4. حساب النقاط النهائية
        base_score = 10  # نقاط أساسية
        final_score = base_score + discount_score + price_score + category_score
        result['analysis_details']['final_score'] = final_score
        result['confidence'] = min(100, final_score)
        
        # 5. تحديد القبول أو الرفض
        if result['confidence'] >= 80:
            result['is_good_deal'] = True
            result['reason'] = f"🔥 {discount_desc} + {brand_desc}"
            self.stats['high_confidence_deals'] += 1
        elif result['confidence'] >= 65:
            result['is_good_deal'] = True
            result['reason'] = f"✅ {discount_desc} + {brand_desc}"
            self.stats['medium_confidence_deals'] += 1
        elif result['confidence'] >= 50:
            result['is_good_deal'] = True
            result['reason'] = f"⚡ {discount_desc} + {brand_desc}"
            self.stats['low_confidence_deals'] += 1
        else:
            result['is_good_deal'] = False
            result['reason'] = f"❌ {discount_desc} + {brand_desc}"
            self.stats['rejected_deals'] += 1
        
        # إضافة وصف الفئة
        if category_desc:
            result['reason'] += f" ({category_desc})"
        
        self.stats['total_analyses'] += 1
        
        return result

# إنشاء المحلل الذكي الداخلي
smart_analyzer = SmartInternalAnalyzer()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع التحليل الذكي الداخلي فقط"""
    
    def smart_analyze_and_send():
        """تحليل ذكي داخلي وإرسال"""
        
        if smart_analysis_enabled[0]:
            try:
                # تحليل ذكي داخلي فقط (بدون مواقع خارجية)
                analysis_result = smart_analyzer.smart_price_analysis(
                    item.get('name', ''), new_price, discount_percent
                )
                
                # رفض العروض الضعيفة
                if not analysis_result['is_good_deal']:
                    print(f"🚫 رفض ذكي: {item.get('name', '')[:35]}... - {analysis_result['reason']}")
                    return
                
                # إضافة معلومات التحليل الذكي
                item['smart_analysis'] = analysis_result
                item['smart_confidence'] = analysis_result['confidence']
                item['smart_reason'] = analysis_result['reason']
                item['brand'] = analysis_result['brand']
                item['category'] = analysis_result['category']
                item['analysis_details'] = analysis_result['analysis_details']
                
                print(f"✅ قبول ذكي: {item.get('name', '')[:35]}... - ثقة {analysis_result['confidence']}%")
                
            except Exception as e:
                print(f"⚠️ خطأ في التحليل الذكي: {e}")
                # في حالة الخطأ، نسمح بالإرسال للعروض الكبيرة فقط
                if discount_percent >= 35:
                    item['smart_confidence'] = 70
                    item['smart_reason'] = f"خصم كبير {discount_percent:.0f}% - قبول مباشر"
                else:
                    return
        
        # إرسال الرسالة مع الصورة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=smart_analyze_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع الصورة والتحليل الذكي الداخلي"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات التحليل الذكي
        smart_reason = item.get('smart_reason', '')
        smart_confidence = item.get('smart_confidence', 0)
        brand = item.get('brand', 'unknown')
        category = item.get('category', 'general')
        analysis_details = item.get('analysis_details', {})

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان بناءً على مستوى الثقة
        if smart_confidence >= 80:
            headline = "🔥 <b>EXCELLENT DEAL!</b> 🔥"
        elif smart_confidence >= 65:
            headline = "✅ <b>GOOD DEAL!</b>"
        elif smart_confidence >= 50:
            headline = "⚡ <b>Fair Deal</b>"
        else:
            headline = "🛍️ <b>Deal</b>"

        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
        
        # حساب المبلغ الموفر
        savings = old_price - new_price if old_price else 0
        savings_info = f"\n💵 <b>You Save:</b> {savings:,.0f} EGP" if savings > 0 else ""
        
        # معلومات العلامة التجارية والفئة
        brand_info = ""
        if brand and brand != 'unknown':
            brand_info = f"\n🏷️ <b>Brand:</b> {brand.title()}"
        
        category_info = ""
        if category and category != 'general':
            category_info = f"\n📂 <b>Category:</b> {category.title()}"
        
        # تفاصيل التحليل الذكي
        analysis_info = ""
        if analysis_details:
            discount_score = analysis_details.get('discount_score', 0)
            price_score = analysis_details.get('price_score', 0)
            final_score = analysis_details.get('final_score', 0)
            analysis_info = f"\n📊 <b>Analysis:</b> Discount({discount_score}) + Price({price_score}) = {final_score}"
        
        # معلومات التحليل
        reason_info = ""
        if smart_reason:
            reason_info = f"\n🎯 <b>Assessment:</b> {smart_reason}"
        
        confidence_row = f"\n📈 <b>Confidence:</b> {smart_confidence}%" if smart_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{savings_info}{confidence_row}{brand_info}{category_info}{reason_info}{analysis_info}

🧠 <b>Smart Internal Analysis - No External Sites</b>
"""

        # أزرار للبحث اليدوي (بدون مقارنة تلقائية)
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Buy on Amazon", "url": url}],
                [
                    {"text": "🔍 Search Jumia", "url": f"https://www.jumia.com.eg/catalog/?q={product_name.replace(' ', '+')}"},
                    {"text": "🔍 Search Noon", "url": f"https://www.noon.com/egypt-en/search/?q={product_name.replace(' ', '+')}"}
                ]
            ]
        }
        reply_markup_json = json.dumps(reply_markup)

        sent_count = 0
        for user_id in users:
            try:
                # إرسال مع الصورة (الميزة المطلوبة)
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
            confidence_level = "عالية" if smart_confidence >= 80 else "متوسطة" if smart_confidence >= 65 else "مقبولة"
            print(f"✅ تم إرسال تنبيه لـ {sent_count} مستخدم - ثقة {confidence_level} ({smart_confidence}%)")

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
    """إضافة بيانات التنبيه مع التحليل الذكي الداخلي"""
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
    
    # إرسال مع التحليل الذكي الداخلي فقط
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة السريعة
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=25):
    """سكرابة صفحة واحدة - سريعة ومحسنة"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-images', '--disable-javascript']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        # URL أصلي
        url = section_url.format(page_num)
        
        if log_fn:
            mode = "[SMART INTERNAL]" if smart_analysis_enabled[0] else ""
            log_fn(f"🧠 {mode} Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=25000)
            await page.wait_for_timeout(1000)  # انتظار قصير للسرعة
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:14]:  # 14 منتج للتوازن بين السرعة والجودة
            try:
                asin = await item.get_attribute("data-asin")
                if not asin:
                    continue

                # فلترة المنتجات الجديدة (إذا كان مفعل)
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
                if not price or price < 25:
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
                    
                    if discount_percent >= discount_threshold and discount_percent <= 80 and price >= 30:
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

# دوال الواجهة الأصلية
def start_scraping():
    if running[0]:
        log("Already running.", "⚠️")
        return
        
    section = section_combo.get()
    pages = int(pages_entry.get())
    progress_bar.set(0.0)
    stop_flag["stop"] = False
    running[0] = True
    
    smart_mode = "SMART INTERNAL ON" if smart_analysis_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🧠 Smart Internal Start - New Products: {auto_mode}, Smart Analysis: {smart_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Smart Internal scraping {sec_name}...", "🧠")
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
            log("✅ Smart Internal Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Smart Internal Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    # إحصائيات التحليل الذكي الداخلي
    if smart_analysis_enabled[0]:
        stats = smart_analyzer.stats
        log(f"🧠 Smart Internal Stats:")
        log(f"   📊 Total Analyses: {stats['total_analyses']}")
        log(f"   🔥 High Confidence (80%+): {stats['high_confidence_deals']}")
        log(f"   ✅ Medium Confidence (65-79%): {stats['medium_confidence_deals']}")
        log(f"   ⚡ Low Confidence (50-64%): {stats['low_confidence_deals']}")
        log(f"   🚫 Rejected (<50%): {stats['rejected_deals']}")
        log(f"   🏷️ Brand Matches: {stats['brand_matches']}")
        log(f"   📂 Category Matches: {stats['category_matches']}")
        log(f"   💰 Price Range Matches: {stats['price_range_matches']}")
        
        if stats['total_analyses'] > 0:
            acceptance_rate = ((stats['high_confidence_deals'] + stats['medium_confidence_deals'] + stats['low_confidence_deals']) / stats['total_analyses']) * 100
            brand_rate = (stats['brand_matches'] / stats['total_analyses']) * 100
            log(f"   📈 Acceptance Rate: {acceptance_rate:.1f}%")
            log(f"   📈 Brand Recognition Rate: {brand_rate:.1f}%")

def toggle_smart_analysis():
    smart_analysis_enabled[0] = not smart_analysis_enabled[0]
    status = "SMART INTERNAL ON" if smart_analysis_enabled[0] else "OFF"
    log(f"🧠 Smart Internal Analysis: {status}")

def toggle_auto_new_mode():
    auto_new_products_mode[0] = not auto_new_products_mode[0]
    status = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🆕 Auto New Products: {status}")

def toggle_telegram_alert():
    telegram_alerts_enabled[0] = not telegram_alerts_enabled[0]
    status = "ON" if telegram_alerts_enabled[0] else "OFF"
    log(f"📱 Telegram: {status}")

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
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Last Price", "Discount %", "Confidence", "Brand", "Category"])
        for asin, item in db.items():
            discount_pct = item.get('discount_percent', 0)
            confidence = item.get('smart_confidence', 0)
            brand = item.get('brand', 'unknown')
            category = item.get('category', 'general')
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], item["price"], discount_pct, confidence, brand, category])
    log("Exported to CSV with smart internal analysis.", "📁")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

# ==== الواجهة الأصلية ====
root = ctk.CTk()
root.title("LAQTA - Smart Internal System")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

# العنوان الأصلي
title_label = ctk.CTkLabel(root, text="LAQTA", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="Amazon Egypt Products Scraper - Smart Internal Analysis Only", 
                             font=("Arial", 18), text_color="#ffaa44")
subtitle_label.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")

# التحكمات الأصلية
controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)

section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
    width=170, font=("Arial", 15), button_color="#54fac8")
section_combo.set("Electronics")
section_combo.grid(row=0, column=0, padx=5, pady=8, sticky="ew")

pages_entry = ctk.CTkEntry(controls_frame, width=70, font=("Arial", 15), fg_color="#232d3a", text_color="#12dafb")
pages_entry.insert(0, "5")  # عدد صفحات معقول
pages_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 13), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=5, pady=8, sticky="ew")

# الخيارات الأصلية
auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 Auto New", font=("Arial", 13), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=3, padx=5, pady=8, sticky="ew")

smart_analysis_chk = ctk.CTkCheckBox(controls_frame, text="🧠 Smart Internal", font=("Arial", 13), 
                                    text_color="#4CAF50", command=toggle_smart_analysis)
smart_analysis_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
smart_analysis_chk.select()  # مفعل افتراضياً

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

# شريط التقدم الأصلي
progress_bar = ctk.CTkProgressBar(root, height=25, progress_color="#59ff9d", fg_color="#232d3a")
progress_bar.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
progress_bar.set(0.0)

# منطقة السجل الأصلية
log_textbox = ctk.CTkTextbox(root, font=("Consolas", 13), fg_color="#20242f", text_color="#c2ffe3", border_width=0, height=250)
log_textbox.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="nsew")
log_textbox.configure(state="disabled")

# الأزرار الأصلية
buttons_frame = ctk.CTkFrame(root, fg_color="transparent")
buttons_frame.grid(row=5, column=0, padx=10, pady=8, sticky="ew")
buttons_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)

btn_w, btn_h = 190, 45
btn_font = ("Arial", 16, "bold")

start_btn = ctk.CTkButton(buttons_frame, text="🧠 Smart Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4CAF50", hover_color="#45a049", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#f44336", hover_color="#da190b", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#2196F3", hover_color="#0b7dda", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Smart Stats", command=show_stats, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#FF9800", hover_color="#e68900", text_color="#ffffff")
stats_btn.grid(row=0, column=3, padx=5, pady=6, sticky="ew")

export_btn = ctk.CTkButton(buttons_frame, text="📁 Export", command=export_csv, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#9C27B0", hover_color="#7b1fa2", text_color="#ffffff")
export_btn.grid(row=0, column=4, padx=5, pady=6, sticky="ew")

clear_btn = ctk.CTkButton(buttons_frame, text="🧹 Clear", command=clear_log, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#607D8B", hover_color="#455a64", text_color="#ffffff")
clear_btn.grid(row=0, column=5, padx=5, pady=6, sticky="ew")

# زر الخروج الأصلي
exit_btn = ctk.CTkButton(root, text="Exit ❌", command=exit_app, width=300, height=45,
    font=("Arial Black", 18), fg_color="#232d3a", hover_color="#fa1a50", text_color="#59ff9d")
exit_btn.grid(row=6, column=0, pady=(8, 12))

load_db()

# رسائل ترحيب للنظام الداخلي
log("🧠 LAQTA Smart Internal System started!", "🚀")
log("🏷️ Brand Database: 50+ brands with price ranges loaded", "📊")
log("📂 Categories: 9 categories with smart price analysis", "🎯")
log("📸 Telegram: ON - with photos and smart internal analysis", "📱")
log("⚡ Speed: No external sites = super fast analysis!", "🏃")
log("🎯 Strategy: Smart scoring based on discount + brand + price + category", "💡")
log("📱 Expected: FAST and SMART internal analysis only!", "🏆")

root.mainloop()