#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA Gemini - إصلاح endpoint وmodel name
"""

import customtkinter as ctk
import json, threading, asyncio, os
from datetime import datetime
import re
import requests
from playwright.async_api import async_playwright
import statistics
import time
import urllib.parse
from typing import Dict, List, Optional

# إعداد الواجهة
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# متغيرات عامة
DB_FILE = "amz_products.json"
db = {}
stop_flag = {"stop": False}
running = [False]
telegram_alerts_enabled = [True]
gemini_comparison_enabled = [True]

ALERT_DISCOUNT = 15
existing_asins = set()

def auto_setup_gemini():
    """إعداد تلقائي لـ Gemini"""
    
    # API key الخاص بك
    YOUR_GEMINI_API_KEY = "AIzaSyAS_qF5wf1OY_TAVBXaxPD0rZAX-8dt4S0"
    
    print("🔧 إعداد تلقائي لـ Gemini...")
    
    config = {
        "gemini_api_key": YOUR_GEMINI_API_KEY,
        "model": "gemini-1.5-flash",  # النموذج الصحيح
        "setup_date": datetime.now().isoformat(),
        "auto_created": True
    }
    
    try:
        with open('gemini_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        print("✅ تم إنشاء gemini_config.json مع النموذج الصحيح")
        return YOUR_GEMINI_API_KEY
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء الملف: {e}")
        return None

def auto_setup_telegram():
    """إعداد تلقائي لتليجرام"""
    
    telegram_config = {
        "bot_token": "8182350211:AAEHUVf3CpKi5wDUNpvipjURyGQ",
        "users": ["6613608451", "1712205938"],
        "auto_created": True,
        "setup_date": datetime.now().isoformat()
    }
    
    try:
        with open('telegram_config.json', 'w', encoding='utf-8') as f:
            json.dump(telegram_config, f, indent=4, ensure_ascii=False)
        
        print("✅ تم إنشاء telegram_config.json تلقائياً")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء ملف تليجرام: {e}")
        return False

class FixedGeminiComparator:
    """مقارن Gemini مع endpoint صحيح"""
    
    def __init__(self):
        # إنشاء الملفات تلقائياً
        if not os.path.exists('gemini_config.json'):
            auto_setup_gemini()
        
        if not os.path.exists('telegram_config.json'):
            auto_setup_telegram()
        
        self.api_key = self.load_api_key()
        self.ai_enabled = bool(self.api_key)
        
        self.stats = {
            'total_comparisons': 0,
            'gemini_comparisons': 0,
            'products_sent': 0
        }
        
        if self.ai_enabled:
            print("✅ Google Gemini مفعل - مع endpoint محسن")
            self.test_gemini_fixed()
        else:
            print("❌ Google Gemini فشل الإعداد")
    
    def load_api_key(self):
        """تحميل API key"""
        try:
            with open('gemini_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                api_key = config.get('gemini_api_key', '')
                
                if api_key and len(api_key) > 20:
                    print(f"✅ Gemini API key loaded: {api_key[:20]}...")
                    return api_key
                    
        except Exception as e:
            print(f"❌ خطأ في تحميل API: {e}")
        
        return None
    
    def test_gemini_fixed(self):
        """اختبار Gemini مع endpoints مختلفة"""
        print("🧪 اختبار Gemini مع endpoints محسنة...")
        
        # قائمة بـ endpoints مختلفة للاختبار
        endpoints_to_try = [
            {
                "name": "Gemini 1.5 Flash",
                "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            },
            {
                "name": "Gemini Pro",
                "url": f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={self.api_key}"
            },
            {
                "name": "Gemini Pro v1beta",
                "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.api_key}"
            }
        ]
        
        for endpoint in endpoints_to_try:
            print(f"   🧪 اختبار {endpoint['name']}...")
            
            try:
                data = {
                    "contents": [
                        {"parts": [{"text": "مرحبا"}]}
                    ]
                }
                
                response = requests.post(endpoint['url'], json=data, timeout=10)
                
                print(f"   📊 Response: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and len(result['candidates']) > 0:
                        content = result['candidates'][0]['content']['parts'][0]['text']
                        print(f"   ✅ {endpoint['name']} يعمل! الرد: {content[:30]}...")
                        
                        # حفظ الـ endpoint الناجح
                        self.working_url = endpoint['url'].replace(f"?key={self.api_key}", "")
                        self.working_model = endpoint['name']
                        
                        # اختبار مقارنة أسعار
                        return self.test_price_comparison()
                else:
                    print(f"   ❌ {endpoint['name']} فشل: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ {endpoint['name']} خطأ: {e}")
        
        print("❌ جميع endpoints فشلت")
        self.ai_enabled = False
        return False
    
    def test_price_comparison(self):
        """اختبار مقارنة أسعار"""
        print("   🧪 اختبار مقارنة أسعار...")
        
        test_prompt = """مقارنة سريعة:
المنتج: Samsung Galaxy A06
سعر أمازون: 2500 جنيه

قارن مع نون وجوميا فقط.
النتيجة: اسم الموقع | السعر"""
        
        result = self.call_gemini_working(test_prompt)
        if result:
            print(f"   ✅ مقارنة الأسعار تعمل: {result[:60]}...")
            return True
        else:
            print("   ❌ مقارنة الأسعار فشلت")
            return False
    
    def call_gemini_working(self, prompt: str) -> Optional[str]:
        """استدعاء Gemini مع الـ endpoint الناجح"""
        if not self.ai_enabled or not hasattr(self, 'working_url'):
            return None
        
        try:
            url = f"{self.working_url}?key={self.api_key}"
            
            data = {
                "contents": [
                    {"parts": [{"text": prompt}]}
                ]
            }
            
            response = requests.post(url, json=data, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    return content.strip()
            
            return None
                
        except Exception:
            return None
    
    def get_comprehensive_comparison(self, product_name: str, amazon_price: float) -> Dict:
        """مقارنة شاملة"""
        
        if not self.ai_enabled:
            return self.get_smart_analysis(product_name, amazon_price)
        
        print(f"🔍 Gemini مقارنة شاملة: {product_name[:50]}...")
        
        # نفس الـ prompt اللي استخدمته
        comparison_prompt = f"""قم بمقارنة أسعار هذا المنتج في جميع المواقع المصرية المتاحة:

المنتج: {product_name}
سعر أمازون: {amazon_price} جنيه مصري

المطلوب مقارنة مع: نون، جوميا، سوق، كارفور، كان بكام، بي تك، سبينيز، اكسترا، أي موقع مصري آخر

أريد النتيجة في شكل منظم:
اسم الموقع | السعر بالجنيه المصري | حالة التوفر

وفي النهاية:
- متوسط السعر في السوق
- هل سعر أمازون جيد؟
- التوصية النهائية"""
        
        gemini_response = self.call_gemini_working(comparison_prompt)
        
        if gemini_response:
            self.stats['gemini_comparisons'] += 1
            
            # تحليل النتيجة
            analysis = self.parse_gemini_response(gemini_response, amazon_price)
            analysis['gemini_used'] = True
            analysis['full_response'] = gemini_response
            
            # طباعة النتيجة المنظمة
            print(f"   🤖 Gemini نتيجة:")
            lines = gemini_response.split('\n')
            for line in lines[:10]:  # أول 10 أسطر
                if '|' in line or any(site in line for site in ['نون', 'جوميا', 'سوق', 'كارفور']):
                    print(f"      📊 {line.strip()}")
            
            return analysis
        else:
            print(f"   ❌ Gemini فشل - استخدام التحليل الذكي")
            return self.get_smart_analysis(product_name, amazon_price)
    
    def parse_gemini_response(self, response: str, amazon_price: float) -> Dict:
        """تحليل رد Gemini"""
        
        # استخراج الأسعار
        prices = []
        sites = []
        
        lines = response.split('\n')
        for line in lines:
            price_match = re.search(r'(\d{1,6}(?:,\d{3})*)\s*(?:جنيه|EGP)', line)
            if price_match:
                try:
                    price = float(price_match.group(1).replace(',', ''))
                    if 50 <= price <= 50000 and price != amazon_price:
                        prices.append(price)
                        
                        site_match = re.search(r'(نون|جوميا|سوق|كارفور|كان بكام|بي تك|سبينيز|اكسترا)', line)
                        if site_match:
                            sites.append(site_match.group(1))
                except:
                    continue
        
        # حساب المتوسط
        market_average = 0
        if prices:
            market_average = statistics.mean(prices)
        
        # تحديد التوصية
        confidence = 80
        recommendation = "اشتري"
        
        if market_average > 0:
            vs_market = ((market_average - amazon_price) / market_average) * 100
            
            if vs_market > 20:
                confidence = 95
                recommendation = "اشتري فوراً"
            elif vs_market > 10:
                confidence = 85
                recommendation = "اشتري"
            elif vs_market < -10:
                confidence = 65
                recommendation = "فكر"
        
        return {
            'market_prices': prices,
            'market_average': market_average,
            'confidence': confidence,
            'recommendation': recommendation,
            'sites_count': len(sites),
            'sites_found': sites,
            'gemini_analysis': self.extract_summary(response),
            'gemini_used': True
        }
    
    def extract_summary(self, response: str) -> str:
        """استخراج ملخص"""
        lines = response.split('\n')
        summary_parts = []
        
        for line in lines:
            line = line.strip()
            if any(keyword in line for keyword in ['متوسط', 'توصية', 'توفير', 'أمازون']):
                if len(line) < 80:
                    summary_parts.append(line)
        
        return ' • '.join(summary_parts[:3])
    
    def get_smart_analysis(self, product_name: str, amazon_price: float) -> Dict:
        """تحليل ذكي بدون Gemini"""
        
        name_lower = product_name.lower()
        trusted_brands = ['samsung', 'apple', 'anker', 'sony', 'xiaomi', 'lg']
        
        confidence = 70
        brand_found = False
        
        for brand in trusted_brands:
            if brand in name_lower:
                confidence = 85
                brand_found = True
                break
        
        return {
            'market_prices': [],
            'market_average': 0,
            'confidence': confidence,
            'recommendation': "اشتري" if brand_found else "فكر",
            'sites_count': 0,
            'sites_found': [],
            'gemini_analysis': f"تحليل ذكي - علامة {'موثوقة' if brand_found else 'غير معروفة'}",
            'gemini_used': False
        }

# إنشاء المقارن
gemini_comparator = FixedGeminiComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected=False):
    """إرسال تنبيه"""
    
    def analyze_and_send():
        try:
            # مقارنة مع Gemini
            comparison = gemini_comparator.get_comprehensive_comparison(
                item.get('name', ''), new_price
            )
            
            # قرار الإرسال
            if comparison['confidence'] < 60:
                print(f"🚫 رفض: ثقة ضعيفة")
                return
            
            # تحديث البيانات
            item.update({
                'comparison': comparison,
                'final_confidence': comparison['confidence'],
                'recommendation': comparison['recommendation'],
                'market_average': comparison['market_average'],
                'gemini_used': comparison['gemini_used']
            })
            
            gemini_comparator.stats['products_sent'] += 1
            
            # إرسال تليجرام
            send_actual_telegram(item, old_price, new_price, discount_percent)
            
        except Exception as e:
            print(f"❌ خطأ: {e}")
    
    threading.Thread(target=analyze_and_send, daemon=True).start()

def send_actual_telegram(item, old_price, new_price, discount_percent):
    """إرسال تليجرام"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        
        comparison = item.get('comparison', {})
        final_confidence = item.get('final_confidence', 0)
        recommendation = item.get('recommendation', '')
        market_average = item.get('market_average', 0)
        gemini_used = item.get('gemini_used', False)

        # عنوان
        if recommendation == "اشتري فوراً":
            headline = "🔥 <b>EXCELLENT DEAL!</b> 🔥"
        elif recommendation == "اشتري":
            headline = "✅ <b>GOOD DEAL!</b>"
        else:
            headline = "💸 <b>FAIR DEAL</b>"

        # تحليل Gemini
        gemini_info = ""
        if gemini_used:
            sites_count = comparison.get('sites_count', 0)
            analysis = comparison.get('gemini_analysis', '')
            
            if sites_count > 0:
                gemini_info = f"\n🤖 <b>Gemini Market Analysis:</b>"
                gemini_info += f"\n🌐 <b>مقارنة مع {sites_count} مواقع مصرية</b>"
                
                if analysis:
                    gemini_info += f"\n📊 {analysis}"
                
                if market_average > 0:
                    vs_market = ((market_average - new_price) / market_average) * 100
                    gemini_info += f"\n📊 <b>متوسط السوق:</b> {market_average:,.0f} جنيه"
                    if vs_market > 0:
                        gemini_info += f"\n💰 <b>توفير:</b> {vs_market:.0f}% من متوسط السوق"

        # رسالة
        msg = f"""{headline}

<b>{product_name}</b>

💰 <b>{int(new_price):,} EGP</b>
📈 <b>Confidence:</b> {final_confidence}%
🎯 <b>Recommendation:</b> {recommendation}

{gemini_info}

🔗 <a href="{url}">Buy on Amazon</a>

{'🤖 <b>Powered by Google Gemini AI</b>' if gemini_used else '🧠 <b>Smart Analysis</b>'}
"""

        # إرسال
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
                            "parse_mode": "HTML"
                        }, timeout=15
                    )
                else:
                    response = requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        data={
                            "chat_id": user_id,
                            "text": msg,
                            "parse_mode": "HTML"
                        }, timeout=15
                    )
                
                if response.status_code == 200:
                    sent_count += 1
            except:
                continue
        
        if sent_count > 0:
            ai_label = "🤖 Gemini" if gemini_used else "🧠 Smart"
            print(f"✅ {ai_label} تنبيه إرسال لـ {sent_count} مستخدم")

    except Exception as e:
        print("❌ Telegram Error:", e)

# دوال مساعدة
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

def log(msg, emoji=""):
    try:
        log_textbox.configure(state="normal")
        log_textbox.insert("end", f"{emoji} {msg}\n")
        log_textbox.see("end")
        log_textbox.configure(state="disabled")
    except:
        print(f"{emoji} {msg}")

def test_gemini_comparison():
    """اختبار مقارنة Gemini"""
    log("🧪 اختبار مقارنة Gemini مع endpoints محسنة...")
    
    test_item = {
        "name": "Samsung Galaxy A06 Dual Sim 6GB RAM 128GB Storage",
        "asin": "TEST123",
        "url": "https://amazon.eg/test",
        "img": "",
        "section": "Electronics"
    }
    
    test_price = 2500
    
    send_telegram_alert(test_item, None, test_price, 0)

def show_stats():
    """عرض الإحصائيات"""
    stats = gemini_comparator.stats
    
    log(f"📊 إحصائيات Gemini:")
    log(f"   🤖 Gemini Status: {'مفعل' if gemini_comparator.ai_enabled else 'معطل'}")
    log(f"   📊 Total Comparisons: {stats['total_comparisons']}")
    log(f"   🤖 Gemini Comparisons: {stats['gemini_comparisons']}")
    log(f"   📱 Products Sent: {stats['products_sent']}")
    
    if hasattr(gemini_comparator, 'working_model'):
        log(f"   ✅ Working Model: {gemini_comparator.working_model}")

# الواجهة
root = ctk.CTk()
root.title("LAQTA Gemini - Fixed Endpoints")
root.geometry("1000x600")

title_label = ctk.CTkLabel(root, text="LAQTA Gemini", font=("Arial", 35), text_color="#54fac8")
title_label.pack(pady=20)

gemini_status = "🤖 Gemini Fixed" if gemini_comparator.ai_enabled else "🧠 Smart Mode"
subtitle_label = ctk.CTkLabel(root, text=f"{gemini_status} - Fixed API Endpoints", 
                             font=("Arial", 16), text_color="#ffaa44")
subtitle_label.pack(pady=5)

# Log
log_textbox = ctk.CTkTextbox(root, height=300, font=("Consolas", 11))
log_textbox.pack(pady=20, padx=20, fill="both", expand=True)

# Buttons
buttons_frame = ctk.CTkFrame(root)
buttons_frame.pack(pady=10, fill="x")

test_btn = ctk.CTkButton(buttons_frame, text="🧪 Test Gemini", 
                        command=test_gemini_comparison, fg_color="#4CAF50")
test_btn.pack(side="left", padx=10)

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Stats", 
                         command=show_stats, fg_color="#FF9800")
stats_btn.pack(side="left", padx=10)

exit_btn = ctk.CTkButton(buttons_frame, text="❌ Exit", 
                        command=root.destroy, fg_color="#607D8B")
exit_btn.pack(side="right", padx=10)

# تحميل البيانات
load_db()

# رسائل البداية
if gemini_comparator.ai_enabled:
    log("🤖 LAQTA Gemini System - Fixed Endpoints!", "🚀")
    log("✅ Google Gemini - مقارنة شاملة مع السوق المصري", "🤖")
    log(f"🔧 Working Model: {getattr(gemini_comparator, 'working_model', 'تحديد تلقائي')}", "🔧")
    log("🧪 اضغط 'Test Gemini' لاختبار المقارنة الشاملة", "🎯")
else:
    log("❌ Gemini لا يعمل - جميع endpoints فشلت", "❌")
    log("🧠 استخدام Smart Analysis بدلاً من ذلك", "🧠")

root.mainloop()