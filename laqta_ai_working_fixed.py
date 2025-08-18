#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA AI - نسخة محسنة مع AI يعمل فعلياً
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
ai_comparison_enabled = [True]

ALERT_DISCOUNT = 15
existing_asins = set()

def load_groq_api_key():
    """تحميل Groq API key محسن"""
    print("🔍 تحميل Groq API key...")
    
    try:
        # محاولة تحميل من الملف
        if os.path.exists('groq_config.json'):
            with open('groq_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                api_key = config.get('groq_api_key', '')
                
                print(f"📄 API key من الملف: {api_key[:20] if api_key else 'فارغ'}...")
                
                # فحص صحة API key
                if api_key and len(api_key) > 20 and api_key.startswith('gsk_'):
                    print(f"✅ API key صحيح: {api_key[:15]}...{api_key[-6:]}")
                    return api_key
                else:
                    print(f"❌ API key غير صحيح: طول={len(api_key)}, يبدأ بـgsk_={api_key.startswith('gsk_') if api_key else False}")
                    
        # محاولة تحميل من environment
        env_key = os.environ.get('GROQ_API_KEY', '')
        if env_key and len(env_key) > 20:
            print(f"✅ API key من Environment")
            return env_key
            
        print("❌ لم يتم العثور على API key صحيح")
        return None
        
    except Exception as e:
        print(f"❌ خطأ في تحميل API key: {e}")
        return None

class WorkingAIComparator:
    """مقارن AI يعمل فعلياً"""
    
    def __init__(self):
        self.api_key = load_groq_api_key()
        self.ai_enabled = bool(self.api_key)
        self.ai_calls = 0
        self.ai_success = 0
        self.ai_errors = 0
        
        self.stats = {
            'total_analyses': 0,
            'ai_analyses': 0,
            'products_sent': 0,
            'products_rejected': 0
        }
        
        # اختبار AI فوراً
        if self.ai_enabled:
            print("🧪 اختبار AI فوراً...")
            if self.test_ai_now():
                print("✅ Groq AI مفعل ويعمل!")
            else:
                print("❌ Groq AI معطل - فشل الاختبار")
                self.ai_enabled = False
        else:
            print("⚠️ Groq AI غير مفعل - لا يوجد API key")
    
    def test_ai_now(self) -> bool:
        """اختبار AI فوري"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": "llama-3.1-70b-versatile",
                "messages": [
                    {"role": "user", "content": "Hi"}
                ],
                "max_tokens": 5,
                "temperature": 0.1
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=8
            )
            
            print(f"📡 AI Test Response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print(f"✅ AI Test Success: {content}")
                return True
            else:
                print(f"❌ AI Test Failed: {response.status_code} - {response.text[:100]}")
                return False
                
        except Exception as e:
            print(f"❌ AI Test Exception: {e}")
            return False
    
    def call_groq_ai_working(self, prompt: str) -> Optional[str]:
        """استدعاء AI يعمل فعلياً"""
        if not self.ai_enabled:
            return None
        
        self.ai_calls += 1
        print(f"   🤖 AI Call #{self.ai_calls}: {prompt[:30]}...")
        
        try:
            # تنظيف بسيط
            clean_prompt = prompt.strip()[:80]
            clean_prompt = re.sub(r'[^\w\s\-:.,?]', '', clean_prompt)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": "llama-3.1-70b-versatile",
                "messages": [
                    {"role": "user", "content": clean_prompt}
                ],
                "max_tokens": 20,
                "temperature": 0.2
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                self.ai_success += 1
                print(f"   ✅ AI Success: {content}")
                return content
            else:
                self.ai_errors += 1
                print(f"   ❌ AI Error {response.status_code}")
                return None
                
        except Exception as e:
            self.ai_errors += 1
            print(f"   ❌ AI Exception: {e}")
            return None
    
    def analyze_product_with_ai(self, product_name: str, amazon_price: float) -> Dict:
        """تحليل مع AI فعال"""
        
        print(f"\n🔍 تحليل: {product_name[:50]}...")
        
        # تحليل ذكي أولاً
        name_lower = product_name.lower()
        
        trusted_brands = {
            'samsung': {'quality': 'ممتاز', 'confidence': 85},
            'apple': {'quality': 'ممتاز', 'confidence': 90},
            'anker': {'quality': 'ممتاز', 'confidence': 85},
            'xiaomi': {'quality': 'جيد', 'confidence': 75},
            'lg': {'quality': 'جيد', 'confidence': 75},
            'sony': {'quality': 'ممتاز', 'confidence': 85},
            'huawei': {'quality': 'جيد', 'confidence': 75}
        }
        
        brand = 'unknown'
        confidence = 65
        brand_quality = 'متوسط'
        
        for b, info in trusted_brands.items():
            if b in name_lower:
                brand = b
                confidence = info['confidence']
                brand_quality = info['quality']
                print(f"   🏷️ العلامة: {brand} ({brand_quality})")
                break
        
        # كلمات البحث
        words = []
        for word in product_name.split()[:4]:
            clean = re.sub(r'[^\w]', '', word.lower())
            if len(clean) > 2:
                words.append(clean)
        
        search_keywords = words[:3]
        
        result = {
            'brand': brand,
            'brand_quality': brand_quality,
            'search_keywords': search_keywords,
            'confidence': confidence,
            'ai_used': False
        }
        
        # محاولة AI (بدون حدود صارمة)
        if self.ai_enabled:
            clean_name = product_name[:40]
            clean_name = re.sub(r'[^\w\s]', '', clean_name)
            
            ai_prompt = f"What brand is {clean_name}?"
            
            ai_response = self.call_groq_ai_working(ai_prompt)
            if ai_response and len(ai_response) > 2:
                
                # البحث عن علامات في رد AI
                ai_lower = ai_response.lower()
                for ai_brand in trusted_brands.keys():
                    if ai_brand in ai_lower:
                        if result['brand'] == 'unknown':
                            result['brand'] = ai_brand
                            result['brand_quality'] = trusted_brands[ai_brand]['quality']
                            result['confidence'] = min(trusted_brands[ai_brand]['confidence'] + 10, 95)
                            print(f"   🤖 AI اكتشف: {ai_brand}")
                        elif result['brand'] == ai_brand:
                            result['confidence'] = min(result['confidence'] + 5, 95)
                            print(f"   🤖 AI أكد: {ai_brand}")
                        break
                
                result['ai_used'] = True
                self.stats['ai_analyses'] += 1
        
        print(f"   📊 النتيجة: {result['brand']} - ثقة {result['confidence']}% - AI: {'نعم' if result['ai_used'] else 'لا'}")
        
        self.stats['total_analyses'] += 1
        return result
    
    def should_send_alert(self, analysis: Dict) -> bool:
        """قرار الإرسال"""
        confidence = analysis['confidence']
        
        if confidence >= 60:  # حد منخفض للاختبار
            return True
        else:
            self.stats['products_rejected'] += 1
            return False

# إنشاء المقارن
market_comparator = WorkingAIComparator()

def send_telegram_alert_working(item, old_price, new_price, discount_percent):
    """إرسال تنبيه مع AI فعال"""
    
    def analyze_and_send():
        try:
            # تحليل المنتج
            product_analysis = market_comparator.analyze_product_with_ai(
                item.get('name', ''), new_price
            )
            
            # قرار الإرسال
            if not market_comparator.should_send_alert(product_analysis):
                print(f"🚫 رفض الإرسال")
                return
            
            # إرسال فعلي
            try:
                with open("telegram_config.json", "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                
                bot_token = cfg.get("bot_token", "")
                users = cfg.get("users", [])
                
                if not bot_token or not users:
                    print("❌ إعدادات تليجرام غير صحيحة")
                    return
                
                product_name = item.get('name', 'Test Product')
                ai_status = "🤖 AI Enhanced" if product_analysis['ai_used'] else "🧠 Smart Analysis"
                
                msg = f"""🔥 DEAL ALERT! 🔥

<b>{product_name[:80]}...</b>

💰 <b>Price:</b> {int(new_price):,} EGP
📈 <b>Confidence:</b> {product_analysis['confidence']}%
🏷️ <b>Brand:</b> {product_analysis['brand']} ({product_analysis['brand_quality']})
{ai_status}

🛍️ <a href="{item.get('url', '')}">Buy Now on Amazon</a>"""
                
                # إرسال للمستخدمين
                sent_count = 0
                for user_id in users:
                    try:
                        response = requests.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            data={
                                "chat_id": user_id,
                                "text": msg,
                                "parse_mode": "HTML"
                            }, timeout=10
                        )
                        
                        if response.status_code == 200:
                            sent_count += 1
                    except:
                        continue
                
                if sent_count > 0:
                    market_comparator.stats['products_sent'] += 1
                    ai_label = "🤖 AI" if product_analysis['ai_used'] else "🧠 Smart"
                    print(f"✅ {ai_label} تنبيه إرسال لـ {sent_count} مستخدم")
                
            except Exception as e:
                print(f"❌ خطأ تليجرام: {e}")
                
        except Exception as e:
            print(f"❌ خطأ عام: {e}")
    
    threading.Thread(target=analyze_and_send, daemon=True).start()

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

def test_ai_product():
    """اختبار AI مع منتج"""
    log("🧪 اختبار AI مع منتج...")
    
    test_item = {
        "name": "Samsung Galaxy A06 Dual Sim 6GB RAM 128GB Storage",
        "asin": "TEST123",
        "url": "https://amazon.eg/test",
        "img": "",
        "section": "Electronics"
    }
    
    test_price = 2500
    
    # إرسال تنبيه تجريبي
    send_telegram_alert_working(test_item, None, test_price, 0)

def show_ai_stats():
    """عرض إحصائيات AI"""
    stats = market_comparator.stats
    
    log(f"📊 إحصائيات AI:")
    log(f"   🤖 AI Status: {'مفعل' if market_comparator.ai_enabled else 'معطل'}")
    log(f"   📞 AI Calls: {market_comparator.ai_calls}")
    log(f"   ✅ AI Success: {market_comparator.ai_success}")
    log(f"   ❌ AI Errors: {market_comparator.ai_errors}")
    
    if market_comparator.ai_calls > 0:
        success_rate = (market_comparator.ai_success / market_comparator.ai_calls) * 100
        log(f"   🎯 Success Rate: {success_rate:.1f}%")
    
    log(f"   📊 Total Analyses: {stats['total_analyses']}")
    log(f"   🤖 AI Analyses: {stats['ai_analyses']}")
    log(f"   📱 Products Sent: {stats['products_sent']}")

def test_ai_connection():
    """اختبار اتصال AI"""
    if market_comparator.ai_enabled:
        log("🧪 اختبار اتصال AI...")
        if market_comparator.test_ai_now():
            log("✅ AI يعمل بشكل صحيح!", "🤖")
        else:
            log("❌ AI لا يعمل!", "🤖")
    else:
        log("⚠️ AI غير مفعل", "🤖")

# الواجهة
root = ctk.CTk()
root.title("LAQTA AI - Working Version")
root.geometry("1000x700")

title_label = ctk.CTkLabel(root, text="LAQTA AI - Working", font=("Arial", 30), text_color="#54fac8")
title_label.pack(pady=20)

ai_status = "🤖 AI WORKING" if market_comparator.ai_enabled else "🧠 Smart Only"
subtitle_label = ctk.CTkLabel(root, text=f"{ai_status} - Real AI Integration", 
                             font=("Arial", 16), text_color="#ffaa44")
subtitle_label.pack(pady=5)

# Log
log_textbox = ctk.CTkTextbox(root, height=350, font=("Consolas", 11))
log_textbox.pack(pady=20, padx=20, fill="both", expand=True)

# Buttons
buttons_frame = ctk.CTkFrame(root)
buttons_frame.pack(pady=10, fill="x")

test_ai_btn = ctk.CTkButton(buttons_frame, text="🧪 Test AI Connection", command=test_ai_connection,
                           fg_color="#4CAF50")
test_ai_btn.pack(side="left", padx=10)

test_product_btn = ctk.CTkButton(buttons_frame, text="🧪 Test AI Product", command=test_ai_product,
                                fg_color="#2196F3")
test_product_btn.pack(side="left", padx=10)

stats_btn = ctk.CTkButton(buttons_frame, text="📊 AI Stats", command=show_ai_stats,
                         fg_color="#FF9800")
stats_btn.pack(side="left", padx=10)

exit_btn = ctk.CTkButton(buttons_frame, text="❌ Exit", command=root.destroy,
                        fg_color="#607D8B")
exit_btn.pack(side="right", padx=10)

# تحميل البيانات
load_db()

# رسائل البداية
if market_comparator.ai_enabled:
    log("🤖 LAQTA AI Working System!", "🚀")
    log("✅ Groq AI تم اختباره وهو يعمل فعلياً", "🤖")
    log("📱 Telegram جاهز للإرسال", "📱")
else:
    log("🧠 LAQTA Smart System", "🚀")
    log("❌ AI غير متاح - تحقق من API key", "⚠️")

log("🧪 استخدم الأزرار لاختبار AI", "💡")

root.mainloop()