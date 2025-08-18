#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA Gemini - إعداد تلقائي مع API key
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

# جميع الفئات
CATEGORIES = {
    'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Beauty': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017988031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Fashion': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018165031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Home & Kitchen': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021933031%2Cp_98%3A21909049031&dc&page={}&language=en"
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
gemini_comparison_enabled = [True]

ALERT_DISCOUNT = 15
existing_asins = set()

def auto_setup_gemini():
    """إعداد تلقائي لـ Gemini مع API key الخاص بك"""
    
    # API key الخاص بك
    YOUR_GEMINI_API_KEY = "AIzaSyAS_qF5wf1OY_TAVBXaxPD0rZAX-8dt4S0"
    
    print("🔧 إعداد تلقائي لـ Gemini...")
    
    # إنشاء ملف الإعداد
    config = {
        "gemini_api_key": YOUR_GEMINI_API_KEY,
        "model": "gemini-pro",
        "setup_date": datetime.now().isoformat(),
        "auto_created": True
    }
    
    try:
        with open('gemini_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        print("✅ تم إنشاء gemini_config.json تلقائياً")
        print(f"🔑 API key: {YOUR_GEMINI_API_KEY[:20]}...")
        
        return YOUR_GEMINI_API_KEY
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء الملف: {e}")
        return None

def load_gemini_api_key():
    """تحميل أو إنشاء Gemini API key"""
    print("🔍 فحص Gemini API key...")
    
    # محاولة تحميل من الملف الموجود
    if os.path.exists('gemini_config.json'):
        try:
            print("✅ ملف gemini_config.json موجود")
            with open('gemini_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                api_key = config.get('gemini_api_key', '')
                
                if api_key and len(api_key) > 20:
                    print(f"✅ Gemini API key من الملف: {api_key[:20]}...")
                    return api_key
                else:
                    print("❌ API key في الملف غير صحيح")
        except Exception as e:
            print(f"❌ خطأ في قراءة الملف: {e}")
    
    # إنشاء الملف تلقائياً
    print("🔧 إنشاء ملف gemini_config.json تلقائياً...")
    return auto_setup_gemini()

class GeminiMarketComparator:
    """مقارن السوق المصري مع Google Gemini"""
    
    def __init__(self):
        self.api_key = load_gemini_api_key()
        self.ai_enabled = bool(self.api_key)
        
        self.stats = {
            'total_comparisons': 0,
            'gemini_comparisons': 0,
            'products_sent': 0,
            'products_rejected': 0
        }
        
        if self.ai_enabled:
            print("✅ Google Gemini مفعل - مقارنة شاملة مع السوق المصري")
            self.test_gemini()
        else:
            print("❌ Google Gemini فشل الإعداد")
    
    def test_gemini(self):
        """اختبار Gemini مع تفاصيل"""
        print("🧪 اختبار Gemini AI...")
        
        try:
            # اختبار بسيط
            result = self.call_gemini_ai("مرحبا")
            if result:
                print(f"✅ Gemini يعمل! الرد: {result[:50]}...")
                
                # اختبار مقارنة أسعار
                test_comparison = self.call_gemini_ai("""مقارنة سريعة:
المنتج: Samsung Galaxy A06
سعر أمازون: 2500 جنيه

قارن مع نون وجوميا فقط.
النتيجة: اسم الموقع | السعر""")
                
                if test_comparison:
                    print(f"✅ Gemini مقارنة الأسعار تعمل!")
                    print(f"🤖 مثال النتيجة: {test_comparison[:100]}...")
                    return True
                else:
                    print("❌ Gemini مقارنة الأسعار فشلت")
                    return False
            else:
                print("❌ Gemini فشل الاختبار الأساسي")
                return False
        except Exception as e:
            print(f"❌ Gemini خطأ: {e}")
            return False
    
    def call_gemini_ai(self, prompt: str) -> Optional[str]:
        """استدعاء Google Gemini AI مع تفاصيل"""
        if not self.ai_enabled:
            print("   ⚠️ Gemini غير مفعل")
            return None
        
        print(f"   🤖 Gemini Call: {prompt[:40]}...")
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.api_key}"
            
            data = {
                "contents": [
                    {"parts": [{"text": prompt}]}
                ]
            }
            
            print(f"   📡 إرسال طلب إلى Gemini...")
            
            response = requests.post(url, json=data, timeout=15)
            
            print(f"   📊 Gemini Response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    print(f"   ✅ Gemini Success: {content[:60]}...")
                    return content.strip()
                else:
                    print("   ❌ Gemini: لا توجد نتائج في الرد")
                    return None
            else:
                print(f"   ❌ Gemini Error {response.status_code}: {response.text[:100]}")
                return None
                
        except Exception as e:
            print(f"   ❌ Gemini Exception: {e}")
            return None
    
    def get_comprehensive_comparison(self, product_name: str, amazon_price: float) -> Dict:
        """مقارنة شاملة مع جميع المواقع المصرية"""
        
        if not self.ai_enabled:
            return self.get_smart_analysis(product_name, amazon_price)
        
        print(f"🔍 Gemini مقارنة شاملة: {product_name[:50]}...")
        
        # نفس الـ prompt اللي استخدمته مع Gemini
        comparison_prompt = f"""قم بمقارنة أسعار هذا المنتج في جميع المواقع المصرية المتاحة:

المنتج: {product_name}
سعر أمازون: {amazon_price} جنيه مصري

المطلوب مقارنة شاملة مع المواقع التالية (إذا متوفر):
- نون (noon.com)
- جوميا (jumia.com.eg)
- سوق (souq.com)
- كارفور (carrefour.com.eg)
- سبينيز (spinneys.com.eg)
- بي تك (b-tech.com.eg)
- كان بكام (kanbkam.com)
- اكسترا (extra.com)
- العربي جروب (elaraby.com)
- أي موقع مصري آخر يبيع المنتج

أريد النتيجة في شكل منظم:
اسم الموقع | السعر بالجنيه المصري | حالة التوفر

وفي النهاية:
- متوسط السعر في السوق
- هل سعر أمازون جيد؟
- نسبة التوفير/الزيادة
- التوصية النهائية

يرجى الاجابة بالعربية وبشكل مختصر ومنظم."""
        
        gemini_response = self.call_gemini_ai(comparison_prompt)
        
        if gemini_response:
            self.stats['gemini_comparisons'] += 1
            
            # تحليل النتيجة
            analysis = self.parse_gemini_response(gemini_response, amazon_price)
            analysis['gemini_used'] = True
            analysis['full_response'] = gemini_response
            
            print(f"   🤖 Gemini: مقارنة شاملة مع {analysis.get('sites_count', 0)} موقع")
            
            return analysis
        else:
            return self.get_smart_analysis(product_name, amazon_price)
    
    def parse_gemini_response(self, response: str, amazon_price: float) -> Dict:
        """تحليل رد Gemini"""
        
        # استخراج الأسعار
        prices = []
        sites = []
        
        # البحث عن أسعار في النص
        lines = response.split('\n')
        for line in lines:
            # البحث عن نمط: اسم الموقع | السعر
            price_match = re.search(r'(\d{1,6}(?:,\d{3})*)\s*(?:جنيه|EGP)', line)
            if price_match:
                try:
                    price = float(price_match.group(1).replace(',', ''))
                    if 50 <= price <= 50000 and price != amazon_price:
                        prices.append(price)
                        
                        # استخراج اسم الموقع
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
        """استخراج ملخص من رد Gemini"""
        
        lines = response.split('\n')
        summary_parts = []
        
        for line in lines:
            line = line.strip()
            if any(keyword in line for keyword in ['متوسط', 'توصية', 'توفير', 'سعر أمازون']):
                if len(line) < 80:
                    summary_parts.append(line)
        
        return ' • '.join(summary_parts[:3])
    
    def get_smart_analysis(self, product_name: str, amazon_price: float) -> Dict:
        """تحليل ذكي بدون Gemini"""
        
        name_lower = product_name.lower()
        trusted_brands = ['samsung', 'apple', 'anker', 'sony', 'xiaomi', 'lg']
        
        confidence = 70
        for brand in trusted_brands:
            if brand in name_lower:
                confidence = 85
                break
        
        return {
            'market_prices': [],
            'market_average': 0,
            'confidence': confidence,
            'recommendation': "اشتري",
            'sites_count': 0,
            'sites_found': [],
            'gemini_analysis': "تحليل ذكي محلي",
            'gemini_used': False
        }

# إنشاء ملف الإعداد تلقائياً
def create_gemini_config_auto():
    """إنشاء ملف إعداد Gemini تلقائياً"""
    
    # API key الخاص بك
    YOUR_API_KEY = "AIzaSyAS_qF5wf1OY_TAVBXaxPD0rZAX-8dt4S0"
    
    config = {
        "gemini_api_key": YOUR_API_KEY,
        "model": "gemini-pro",
        "setup_date": datetime.now().isoformat(),
        "auto_created": True,
        "note": "تم إنشاء هذا الملف تلقائياً مع API key الخاص بك"
    }
    
    try:
        with open('gemini_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        print("✅ تم إنشاء gemini_config.json تلقائياً مع API key الخاص بك")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء الملف: {e}")
        return False

# إنشاء الملف إذا لم يكن موجوداً
if not os.path.exists('gemini_config.json'):
    create_gemini_config_auto()

# إنشاء المقارن
gemini_comparator = GeminiMarketComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected=False):
    """إرسال تنبيه مع مقارنة Gemini"""
    
    def analyze_and_send():
        try:
            # مقارنة شاملة مع Gemini
            comparison = gemini_comparator.get_comprehensive_comparison(
                item.get('name', ''), new_price
            )
            
            # قرار الإرسال
            if comparison['confidence'] < 60:
                print(f"🚫 رفض: ثقة ضعيفة")
                gemini_comparator.stats['products_rejected'] += 1
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
    """إرسال رسالة تليجرام مع تحليل Gemini"""
    try:
        # إنشاء ملف telegram_config.json إذا لم يكن موجوداً
        if not os.path.exists('telegram_config.json'):
            telegram_config = {
                "bot_token": "8182350211:AAEHUVf3CpKi5wDUNpvipjURyGQ",
                "users": ["6613608451", "1712205938"],
                "auto_created": True,
                "note": "تم إنشاء هذا الملف تلقائياً مع إعداداتك"
            }
            
            with open('telegram_config.json', 'w', encoding='utf-8') as f:
                json.dump(telegram_config, f, indent=4, ensure_ascii=False)
            
            print("✅ تم إنشاء telegram_config.json تلقائياً")
        
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

def parse_egp_price(text):
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

def add_alert_data(item, old_price, new_price, discount_percent, drop_detected=False):
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

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
    log("🧪 اختبار مقارنة Gemini الشاملة...")
    
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
    total = len(db)
    stats = gemini_comparator.stats
    
    log(f"📊 إحصائيات:")
    log(f"   🔢 المنتجات: {total:,}")
    log(f"   📊 مقارنات كلية: {stats['total_comparisons']}")
    log(f"   🤖 مقارنات Gemini: {stats['gemini_comparisons']}")
    log(f"   📱 منتجات مرسلة: {stats['products_sent']}")
    log(f"   🚫 منتجات مرفوضة: {stats['products_rejected']}")
    
    if stats['total_comparisons'] > 0:
        gemini_rate = (stats['gemini_comparisons'] / stats['total_comparisons']) * 100
        log(f"   🎯 Gemini Usage Rate: {gemini_rate:.1f}%")

# الواجهة البسيطة
root = ctk.CTk()
root.title("LAQTA Gemini - Auto Setup")
root.geometry("1000x600")

title_label = ctk.CTkLabel(root, text="LAQTA Gemini", font=("Arial", 35), text_color="#54fac8")
title_label.pack(pady=20)

gemini_status = "🤖 Gemini Ready" if gemini_comparator.ai_enabled else "🧠 Smart Mode"
subtitle_label = ctk.CTkLabel(root, text=f"{gemini_status} - إعداد تلقائي", 
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
    log("🤖 LAQTA Gemini System Ready!", "🚀")
    log("✅ Google Gemini - مقارنة شاملة مع السوق المصري", "🤖")
    log("🌐 يقارن مع: نون، جوميا، سوق، كارفور، كان بكام، +المزيد", "🌐")
    log("📊 نتائج منظمة: اسم الموقع | السعر | حالة التوفر", "📊")
    log("💰 حساب متوسط السوق ونسبة التوفير", "💰")
    log("🧪 اضغط 'Test Gemini' لاختبار المقارنة الشاملة", "🎯")
else:
    log("❌ Gemini غير متاح - تحقق من API key", "⚠️")
    log("💡 تأكد من وجود gemini_config.json مع API key صحيح", "💡")

root.mainloop()