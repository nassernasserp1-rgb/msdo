#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA AI - نسخة تشخيصية مفصلة
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
    """تحميل Groq API key مع تفاصيل"""
    print("🔍 فحص Groq API key...")
    try:
        if os.path.exists('groq_config.json'):
            with open('groq_config.json', 'r') as f:
                config = json.load(f)
                api_key = config.get('groq_api_key', '')
                
                if not api_key:
                    print("❌ API key فارغ")
                    return None
                elif 'YOUR_' in api_key:
                    print("❌ API key مازال placeholder")
                    return None
                elif len(api_key) < 20:
                    print("❌ API key قصير جداً")
                    return None
                else:
                    print(f"✅ API key موجود: {api_key[:15]}...{api_key[-6:]}")
                    return api_key
        else:
            print("❌ ملف groq_config.json غير موجود")
            return None
    except Exception as e:
        print(f"❌ خطأ في تحميل API key: {e}")
        return None

class VerboseAIComparator:
    """مقارن AI مع تفاصيل كاملة"""
    
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
        
        if self.ai_enabled:
            print("✅ Groq AI مفعل - سيتم اختباره")
            self.test_ai_connection()
        else:
            print("⚠️ Groq AI غير مفعل - smart mode only")
    
    def test_ai_connection(self):
        """اختبار اتصال AI"""
        print("🧪 اختبار اتصال AI...")
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": "llama-3.1-70b-versatile",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=10
            )
            
            print(f"📡 AI Test Response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print(f"✅ AI يعمل! الرد: {content}")
                return True
            else:
                print(f"❌ AI فشل: {response.status_code}")
                print(f"📄 Error: {response.text[:150]}")
                self.ai_enabled = False
                return False
                
        except Exception as e:
            print(f"❌ AI Exception: {e}")
            self.ai_enabled = False
            return False
    
    def call_groq_ai_verbose(self, prompt: str) -> Optional[str]:
        """استدعاء AI مع تفاصيل كاملة"""
        if not self.ai_enabled:
            print("   ⚠️ AI غير مفعل - تخطي")
            return None
        
        self.ai_calls += 1
        print(f"   🤖 AI Call #{self.ai_calls}: {prompt[:40]}...")
        
        try:
            # تنظيف الـ prompt
            clean_prompt = prompt.strip()[:100]
            clean_prompt = re.sub(r'[^\w\s\-:.,]', '', clean_prompt)
            
            print(f"   🧹 Clean prompt: {clean_prompt}")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": "llama-3.1-70b-versatile",
                "messages": [
                    {"role": "user", "content": clean_prompt}
                ],
                "max_tokens": 25,
                "temperature": 0.1
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=8
            )
            
            print(f"   📡 AI Response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                self.ai_success += 1
                print(f"   ✅ AI Success: {content}")
                return content
            else:
                self.ai_errors += 1
                print(f"   ❌ AI Error {response.status_code}: {response.text[:100]}")
                return None
                
        except Exception as e:
            self.ai_errors += 1
            print(f"   ❌ AI Exception: {e}")
            return None
    
    def analyze_product_verbose(self, product_name: str, amazon_price: float) -> Dict:
        """تحليل مفصل للمنتج"""
        
        print(f"\n🔍 تحليل مفصل: {product_name[:50]}...")
        print(f"💰 السعر: {amazon_price:,} EGP")
        
        # تحليل ذكي أولاً
        name_lower = product_name.lower()
        
        # علامات موثوقة
        trusted_brands = {
            'samsung': {'quality': 'ممتاز', 'confidence': 85},
            'apple': {'quality': 'ممتاز', 'confidence': 90},
            'anker': {'quality': 'ممتاز', 'confidence': 85},
            'xiaomi': {'quality': 'جيد', 'confidence': 75},
            'lg': {'quality': 'جيد', 'confidence': 75}
        }
        
        brand = 'unknown'
        confidence = 65
        brand_quality = 'متوسط'
        
        for b, info in trusted_brands.items():
            if b in name_lower:
                brand = b
                confidence = info['confidence']
                brand_quality = info['quality']
                print(f"   🏷️ العلامة المكتشفة: {brand} ({brand_quality})")
                break
        
        if brand == 'unknown':
            print(f"   ❓ علامة غير معروفة")
        
        print(f"   📈 الثقة الأولية: {confidence}%")
        
        # كلمات البحث
        words = []
        for word in product_name.split()[:4]:
            clean = re.sub(r'[^\w]', '', word.lower())
            if len(clean) > 2:
                words.append(clean)
        
        search_keywords = words[:3]
        print(f"   🔍 كلمات البحث: {search_keywords}")
        
        result = {
            'brand': brand,
            'brand_quality': brand_quality,
            'search_keywords': search_keywords,
            'confidence': confidence,
            'ai_used': False
        }
        
        # محاولة تحسين بـ AI
        if self.ai_enabled and self.ai_calls < 5:  # حد أقصى 5 محاولات للاختبار
            
            clean_name = product_name[:30]
            clean_name = re.sub(r'[^\w\s]', '', clean_name)
            
            ai_prompt = f"Brand of {clean_name}?"
            print(f"   🤖 محاولة AI...")
            
            ai_response = self.call_groq_ai_verbose(ai_prompt)
            if ai_response and len(ai_response) > 3:
                print(f"   🤖 AI نجح: {ai_response}")
                
                # تحسين بناءً على AI
                ai_lower = ai_response.lower()
                for ai_brand in trusted_brands.keys():
                    if ai_brand in ai_lower:
                        if result['brand'] == 'unknown':
                            result['brand'] = ai_brand
                            result['confidence'] = min(result['confidence'] + 10, 95)
                            print(f"   🤖 AI اكتشف علامة جديدة: {ai_brand}")
                        elif result['brand'] == ai_brand:
                            result['confidence'] = min(result['confidence'] + 5, 95)
                            print(f"   🤖 AI أكد العلامة: {ai_brand}")
                        break
                
                result['ai_used'] = True
                self.stats['ai_analyses'] += 1
            else:
                print(f"   ❌ AI فشل أو رد فارغ")
        else:
            if not self.ai_enabled:
                print(f"   ⚠️ AI غير مفعل")
            else:
                print(f"   ⚠️ تم الوصول للحد الأقصى من AI calls")
        
        print(f"   📊 النتيجة النهائية:")
        print(f"      🏷️ العلامة: {result['brand']}")
        print(f"      📈 الثقة: {result['confidence']}%")
        print(f"      🤖 AI مستخدم: {'نعم' if result['ai_used'] else 'لا'}")
        
        self.stats['total_analyses'] += 1
        return result
    
    def should_send_alert(self, analysis: Dict, amazon_price: float) -> bool:
        """قرار إرسال التنبيه مع تفاصيل"""
        
        confidence = analysis['confidence']
        brand = analysis['brand']
        ai_used = analysis['ai_used']
        
        print(f"   🎯 تقييم إرسال التنبيه:")
        print(f"      📈 الثقة: {confidence}%")
        print(f"      🏷️ العلامة: {brand}")
        print(f"      🤖 AI: {'نعم' if ai_used else 'لا'}")
        
        # شروط مخففة للاختبار
        if confidence >= 60:  # حد منخفض
            print(f"   ✅ قبول: ثقة كافية ({confidence}% >= 60%)")
            return True
        else:
            print(f"   🚫 رفض: ثقة ضعيفة ({confidence}% < 60%)")
            return False

# إنشاء المقارن
market_comparator = VerboseAIComparator()

def send_telegram_alert_verbose(item, old_price, new_price, discount_percent):
    """إرسال تنبيه تليجرام مع تفاصيل"""
    
    print(f"\n📱 محاولة إرسال تنبيه تليجرام...")
    
    def analyze_and_send():
        try:
            # تحليل المنتج
            product_analysis = market_comparator.analyze_product_verbose(
                item.get('name', ''), new_price
            )
            
            # قرار الإرسال
            should_send = market_comparator.should_send_alert(product_analysis, new_price)
            
            if not should_send:
                print(f"🚫 تم رفض الإرسال")
                market_comparator.stats['products_rejected'] += 1
                return
            
            # محاولة إرسال فعلي
            print(f"📱 محاولة الإرسال الفعلي...")
            
            # فحص إعدادات تليجرام
            try:
                with open("telegram_config.json", "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                bot_token = cfg.get("bot_token", "")
                users = cfg.get("users", [])
                
                print(f"📱 Bot Token: {bot_token[:20]}...{bot_token[-10:] if len(bot_token) > 10 else bot_token}")
                print(f"📱 Users: {len(users)} مستخدم")
                
                if not bot_token or 'YOUR_' in bot_token:
                    print("❌ Bot token غير صحيح")
                    return
                
                if not users or users[0] == 'YOUR_CHAT_ID_HERE':
                    print("❌ Chat IDs غير صحيحة")
                    return
                
                # رسالة مبسطة للاختبار
                product_name = item.get('name', 'Test Product')
                ai_status = "🤖 AI" if product_analysis['ai_used'] else "🧠 Smart"
                
                msg = f"""🔥 TEST ALERT 🔥

{product_name[:50]}...

💰 Price: {int(new_price):,} EGP
📈 Confidence: {product_analysis['confidence']}%
🏷️ Brand: {product_analysis['brand']}
{ai_status} Analysis

🧪 This is a test message"""
                
                # إرسال للمستخدم الأول فقط للاختبار
                user_id = users[0]
                
                response = requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    data={
                        "chat_id": user_id,
                        "text": msg,
                        "parse_mode": "HTML"
                    }, timeout=10
                )
                
                print(f"📡 Telegram Response: {response.status_code}")
                
                if response.status_code == 200:
                    print("✅ تم إرسال التنبيه بنجاح!")
                    market_comparator.stats['products_sent'] += 1
                else:
                    print(f"❌ فشل الإرسال: {response.text[:100]}")
                
            except FileNotFoundError:
                print("❌ ملف telegram_config.json غير موجود")
            except Exception as e:
                print(f"❌ خطأ في إعدادات تليجرام: {e}")
                
        except Exception as e:
            print(f"❌ خطأ عام في الإرسال: {e}")
    
    # تشغيل في thread منفصل
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

def test_single_product():
    """اختبار منتج واحد"""
    log("🧪 اختبار منتج واحد...")
    
    # منتج تجريبي
    test_item = {
        "name": "Samsung Galaxy A06 Dual Sim 6GB RAM 128GB Storage",
        "asin": "TEST123",
        "url": "https://amazon.eg/test",
        "img": "",
        "section": "Electronics"
    }
    
    test_price = 2500
    
    # إرسال تنبيه تجريبي
    send_telegram_alert_verbose(test_item, None, test_price, 0)

def show_detailed_stats():
    """عرض إحصائيات مفصلة"""
    total = len(db)
    stats = market_comparator.stats
    
    log(f"📊 إحصائيات مفصلة:")
    log(f"   🔢 المنتجات: {total:,}")
    log(f"   📊 تحليلات كلية: {stats['total_analyses']}")
    log(f"   🤖 تحليلات AI: {stats['ai_analyses']}")
    log(f"   📱 منتجات مرسلة: {stats['products_sent']}")
    log(f"   🚫 منتجات مرفوضة: {stats['products_rejected']}")
    
    # إحصائيات AI
    if market_comparator.ai_calls > 0:
        success_rate = (market_comparator.ai_success / market_comparator.ai_calls) * 100
        error_rate = (market_comparator.ai_errors / market_comparator.ai_calls) * 100
        log(f"   🎯 AI Success Rate: {success_rate:.1f}%")
        log(f"   ❌ AI Error Rate: {error_rate:.1f}%")
        log(f"   📞 AI Calls: {market_comparator.ai_calls}")
    
    log(f"   🤖 AI Status: {'مفعل' if market_comparator.ai_enabled else 'معطل'}")

def test_telegram():
    """اختبار تليجرام"""
    log("📱 اختبار إعدادات تليجرام...")
    
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        
        bot_token = cfg.get("bot_token", "")
        users = cfg.get("users", [])
        
        if not bot_token or 'YOUR_' in bot_token:
            log("❌ Bot token غير صحيح", "📱")
            return
        
        if not users or users[0] == 'YOUR_CHAT_ID_HERE':
            log("❌ Chat IDs غير صحيحة", "📱")
            return
        
        log(f"✅ Bot token: {bot_token[:15]}...", "📱")
        log(f"✅ Users: {len(users)} مستخدم", "📱")
        
        # اختبار إرسال
        test_msg = "🧪 Test message from LAQTA AI Debug"
        
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={
                "chat_id": users[0],
                "text": test_msg
            }, timeout=10
        )
        
        if response.status_code == 200:
            log("✅ تم إرسال رسالة اختبار!", "📱")
        else:
            log(f"❌ فشل الإرسال: {response.status_code}", "📱")
            
    except FileNotFoundError:
        log("❌ ملف telegram_config.json غير موجود", "📱")
    except Exception as e:
        log(f"❌ خطأ: {e}", "📱")

# الواجهة
root = ctk.CTk()
root.title("LAQTA AI - Debug Verbose")
root.geometry("1200x800")

title_label = ctk.CTkLabel(root, text="LAQTA AI - Debug Mode", font=("Arial", 30), text_color="#54fac8")
title_label.pack(pady=20)

ai_status = "🤖 AI Ready" if market_comparator.ai_enabled else "🧠 Smart Only"
subtitle_label = ctk.CTkLabel(root, text=f"{ai_status} - Verbose Logging", 
                             font=("Arial", 16), text_color="#ffaa44")
subtitle_label.pack(pady=5)

# Log
log_textbox = ctk.CTkTextbox(root, height=400, font=("Consolas", 11))
log_textbox.pack(pady=20, padx=20, fill="both", expand=True)

# Buttons
buttons_frame = ctk.CTkFrame(root)
buttons_frame.pack(pady=10, fill="x")

test_product_btn = ctk.CTkButton(buttons_frame, text="🧪 Test Product", command=test_single_product,
                                fg_color="#4CAF50")
test_product_btn.pack(side="left", padx=10)

test_telegram_btn = ctk.CTkButton(buttons_frame, text="📱 Test Telegram", command=test_telegram,
                                 fg_color="#2196F3")
test_telegram_btn.pack(side="left", padx=10)

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Detailed Stats", command=show_detailed_stats,
                         fg_color="#FF9800")
stats_btn.pack(side="left", padx=10)

exit_btn = ctk.CTkButton(buttons_frame, text="❌ Exit", command=root.destroy,
                        fg_color="#607D8B")
exit_btn.pack(side="right", padx=10)

# تحميل البيانات
load_db()

# رسائل البداية
if market_comparator.ai_enabled:
    log("🤖 LAQTA AI Debug System - AI Enabled!", "🚀")
    log("✨ AI تم اختباره وهو جاهز للاستخدام", "🤖")
else:
    log("🧠 LAQTA Smart Debug System!", "🚀")
    log("⚠️ AI غير متاح - smart mode only", "⚠️")

log("🔍 استخدم الأزرار لاختبار الوظائف", "💡")
log("📱 تأكد من إعداد telegram_config.json", "💡")

root.mainloop()