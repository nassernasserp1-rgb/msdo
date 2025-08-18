#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA Gemini + Web Scraping
نحن نسكرب المواقع، Gemini يحلل وينظم النتائج
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
telegram_alerts_enabled = [True]
existing_asins = set()

def auto_setup_configs():
    """إعداد تلقائي لجميع الملفات"""
    
    # إعداد Gemini
    if not os.path.exists('gemini_config.json'):
        gemini_config = {
            "gemini_api_key": "AIzaSyAS_qF5wf1OY_TAVBXaxPD0rZAX-8dt4S0",
            "model": "gemini-1.5-flash",
            "auto_created": True
        }
        
        with open('gemini_config.json', 'w', encoding='utf-8') as f:
            json.dump(gemini_config, f, indent=4, ensure_ascii=False)
        
        print("✅ تم إنشاء gemini_config.json تلقائياً")
    
    # إعداد تليجرام
    if not os.path.exists('telegram_config.json'):
        telegram_config = {
            "bot_token": "8182350211:AAEHUVf3CpKi5wDUNpvipjURyGQ",
            "users": ["6613608451", "1712205938"],
            "auto_created": True
        }
        
        with open('telegram_config.json', 'w', encoding='utf-8') as f:
            json.dump(telegram_config, f, indent=4, ensure_ascii=False)
        
        print("✅ تم إنشاء telegram_config.json تلقائياً")

class GeminiWebScrapingComparator:
    """مقارن يجمع بين Web Scraping + Gemini Analysis"""
    
    def __init__(self):
        # تحميل Gemini API
        self.api_key = self.load_gemini_api()
        self.ai_enabled = bool(self.api_key)
        
        self.stats = {
            'total_comparisons': 0,
            'gemini_analyses': 0,
            'sites_scraped': 0,
            'products_sent': 0
        }
        
        if self.ai_enabled:
            print("✅ Gemini + Web Scraping مفعل")
            self.test_gemini_connection()
        else:
            print("❌ Gemini غير متاح")
    
    def load_gemini_api(self):
        """تحميل Gemini API"""
        try:
            with open('gemini_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                api_key = config.get('gemini_api_key', '')
                
                if api_key and len(api_key) > 20:
                    print(f"✅ Gemini API loaded: {api_key[:20]}...")
                    return api_key
        except:
            pass
        return None
    
    def test_gemini_connection(self):
        """اختبار اتصال Gemini"""
        print("🧪 اختبار Gemini...")
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            
            data = {
                "contents": [
                    {"parts": [{"text": "مرحبا"}]}
                ]
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                content = result['candidates'][0]['content']['parts'][0]['text']
                print(f"✅ Gemini يعمل: {content[:40]}...")
                return True
            else:
                print(f"❌ Gemini فشل: {response.status_code}")
                self.ai_enabled = False
                return False
                
        except Exception as e:
            print(f"❌ Gemini خطأ: {e}")
            self.ai_enabled = False
            return False
    
    def call_gemini_ai(self, prompt: str) -> Optional[str]:
        """استدعاء Gemini"""
        if not self.ai_enabled:
            return None
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            
            data = {
                "contents": [
                    {"parts": [{"text": prompt}]}
                ]
            }
            
            response = requests.post(url, json=data, timeout=20)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    return content.strip()
            
            return None
                
        except Exception:
            return None
    
    async def scrape_egyptian_sites(self, search_term: str) -> List[Dict]:
        """سكرابة المواقع المصرية وجمع البيانات"""
        
        print(f"   🌐 سكرابة المواقع المصرية للبحث عن: {search_term}")
        
        scraped_data = []
        
        # سكرابة نون
        try:
            noon_data = await self.scrape_noon(search_term)
            if noon_data['prices']:
                scraped_data.append(noon_data)
                print(f"      ✅ نون: {len(noon_data['prices'])} أسعار")
        except Exception as e:
            print(f"      ❌ نون: خطأ")
        
        # سكرابة جوميا
        try:
            jumia_data = await self.scrape_jumia(search_term)
            if jumia_data['prices']:
                scraped_data.append(jumia_data)
                print(f"      ✅ جوميا: {len(jumia_data['prices'])} أسعار")
        except Exception as e:
            print(f"      ❌ جوميا: خطأ")
        
        # سكرابة كان بكام
        try:
            kanbkam_data = await self.scrape_kanbkam(search_term)
            if kanbkam_data['prices']:
                scraped_data.append(kanbkam_data)
                print(f"      ✅ كان بكام: {len(kanbkam_data['prices'])} أسعار")
        except Exception as e:
            print(f"      ❌ كان بكام: خطأ")
        
        self.stats['sites_scraped'] += len(scraped_data)
        return scraped_data
    
    async def scrape_noon(self, search_term: str) -> Dict:
        """سكرابة نون"""
        search_url = f"https://www.noon.com/egypt-en/search/?q={urllib.parse.quote(search_term)}"
        
        response = requests.get(search_url, timeout=8, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        prices = []
        if response.status_code == 200:
            price_matches = re.findall(r'(\d{2,6})\s*(?:جنيه|EGP)', response.text, re.IGNORECASE)
            
            for match in price_matches[:10]:
                try:
                    price = float(match.replace(',', ''))
                    if 50 <= price <= 50000:
                        prices.append(price)
                except:
                    continue
        
        unique_prices = sorted(list(set(prices)))[:5]
        return {
            'site': 'نون',
            'prices': unique_prices,
            'average': statistics.mean(unique_prices) if unique_prices else 0,
            'status': 'متوفر' if unique_prices else 'غير متوفر'
        }
    
    async def scrape_jumia(self, search_term: str) -> Dict:
        """سكرابة جوميا"""
        search_url = f"https://www.jumia.com.eg/catalog/?q={urllib.parse.quote(search_term)}"
        
        response = requests.get(search_url, timeout=8, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        prices = []
        if response.status_code == 200:
            price_matches = re.findall(r'(\d{2,6})\s*(?:EGP|جنيه)', response.text, re.IGNORECASE)
            
            for match in price_matches[:10]:
                try:
                    price = float(match.replace(',', ''))
                    if 50 <= price <= 50000:
                        prices.append(price)
                except:
                    continue
        
        unique_prices = sorted(list(set(prices)))[:5]
        return {
            'site': 'جوميا',
            'prices': unique_prices,
            'average': statistics.mean(unique_prices) if unique_prices else 0,
            'status': 'متوفر' if unique_prices else 'غير متوفر'
        }
    
    async def scrape_kanbkam(self, search_term: str) -> Dict:
        """سكرابة كان بكام"""
        search_url = f"https://www.kanbkam.com/search?q={urllib.parse.quote(search_term)}"
        
        response = requests.get(search_url, timeout=6, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        prices = []
        if response.status_code == 200:
            price_matches = re.findall(r'(\d{2,6})\s*(?:جنيه|EGP)', response.text, re.IGNORECASE)
            
            for match in price_matches[:8]:
                try:
                    price = float(match.replace(',', ''))
                    if 50 <= price <= 50000:
                        prices.append(price)
                except:
                    continue
        
        unique_prices = sorted(list(set(prices)))[:4]
        return {
            'site': 'كان بكام',
            'prices': unique_prices,
            'average': statistics.mean(unique_prices) if unique_prices else 0,
            'status': 'متوفر' if unique_prices else 'غير متوفر'
        }
    
    async def get_comprehensive_comparison_hybrid(self, product_name: str, amazon_price: float) -> Dict:
        """مقارنة هجينة: Web Scraping + Gemini Analysis"""
        
        print(f"🔍 مقارنة هجينة: {product_name[:50]}...")
        
        # 1. سكرابة المواقع أولاً
        search_keywords = []
        for word in product_name.split()[:4]:
            clean = re.sub(r'[^\w]', '', word.lower())
            if len(clean) > 2:
                search_keywords.append(clean)
        
        search_term = ' '.join(search_keywords[:3])
        
        # جمع البيانات من المواقع
        scraped_data = await self.scrape_egyptian_sites(search_term)
        
        if not scraped_data:
            print("   ❌ لم يتم العثور على بيانات من المواقع")
            return self.get_fallback_analysis(product_name, amazon_price)
        
        # 2. تحضير البيانات لـ Gemini
        sites_data = ""
        all_prices = []
        
        for site_data in scraped_data:
            site_name = site_data['site']
            avg_price = site_data.get('average', 0)
            status = site_data.get('status', 'غير متوفر')
            
            if avg_price > 0:
                sites_data += f"{site_name} | {avg_price:,.0f} جنيه | {status}\n"
                all_prices.extend(site_data['prices'])
            else:
                sites_data += f"{site_name} | غير متوفر\n"
        
        # 3. طلب Gemini لتحليل البيانات المجمعة
        if self.ai_enabled and sites_data:
            print("   🤖 إرسال البيانات لـ Gemini للتحليل...")
            
            gemini_prompt = f"""أنا جمعت بيانات أسعار حقيقية من المواقع المصرية للمنتج التالي:

المنتج: {product_name}
سعر أمازون: {amazon_price} جنيه مصري

البيانات المجمعة من المواقع:
{sites_data}

المطلوب تحليل احترافي:
1. نظم البيانات في شكل جدول منظم
2. احسب متوسط السعر في السوق
3. قارن سعر أمازون مع متوسط السوق
4. اعط توصية نهائية (اشتري فوراً/اشتري/فكر)
5. اذكر نسبة التوفير أو الزيادة

يرجى الرد بالعربية وبشكل منظم ومختصر."""
            
            gemini_analysis = self.call_gemini_ai(gemini_prompt)
            
            if gemini_analysis:
                print("   ✅ Gemini حلل البيانات بنجاح!")
                self.stats['gemini_analyses'] += 1
                
                # استخراج التوصية من تحليل Gemini
                recommendation = self.extract_recommendation(gemini_analysis)
                confidence = self.calculate_confidence(all_prices, amazon_price, recommendation)
                
                return {
                    'scraped_data': scraped_data,
                    'gemini_analysis': gemini_analysis,
                    'market_average': statistics.mean(all_prices) if all_prices else 0,
                    'confidence': confidence,
                    'recommendation': recommendation,
                    'sites_count': len(scraped_data),
                    'all_prices': all_prices,
                    'hybrid_used': True,
                    'organized_data': sites_data
                }
        
        # 4. تحليل أساسي إذا فشل Gemini
        return self.analyze_scraped_data(scraped_data, amazon_price)
    
    def extract_recommendation(self, gemini_text: str) -> str:
        """استخراج التوصية من نص Gemini"""
        text_lower = gemini_text.lower()
        
        if any(word in text_lower for word in ['اشتري فوراً', 'ممتاز', 'رائع']):
            return "اشتري فوراً"
        elif any(word in text_lower for word in ['اشتري', 'جيد', 'مناسب']):
            return "اشتري"
        elif any(word in text_lower for word in ['فكر', 'احذر', 'مرتفع']):
            return "فكر"
        else:
            return "اشتري"
    
    def calculate_confidence(self, all_prices: List[float], amazon_price: float, recommendation: str) -> int:
        """حساب الثقة بناءً على البيانات"""
        
        if not all_prices:
            return 70
        
        market_avg = statistics.mean(all_prices)
        vs_market = ((market_avg - amazon_price) / market_avg) * 100
        
        if recommendation == "اشتري فوراً":
            return 95
        elif recommendation == "اشتري" and vs_market > 0:
            return 85
        elif recommendation == "اشتري":
            return 75
        else:
            return 65
    
    def analyze_scraped_data(self, scraped_data: List[Dict], amazon_price: float) -> Dict:
        """تحليل البيانات المسكربة بدون Gemini"""
        
        all_prices = []
        for site_data in scraped_data:
            all_prices.extend(site_data.get('prices', []))
        
        if all_prices:
            market_avg = statistics.mean(all_prices)
            vs_market = ((market_avg - amazon_price) / market_avg) * 100
            
            if vs_market > 20:
                confidence = 95
                recommendation = "اشتري فوراً"
            elif vs_market > 10:
                confidence = 85
                recommendation = "اشتري"
            else:
                confidence = 75
                recommendation = "اشتري"
        else:
            market_avg = 0
            confidence = 70
            recommendation = "اشتري"
        
        return {
            'scraped_data': scraped_data,
            'gemini_analysis': "تحليل أساسي بناءً على البيانات المجمعة",
            'market_average': market_avg,
            'confidence': confidence,
            'recommendation': recommendation,
            'sites_count': len(scraped_data),
            'all_prices': all_prices,
            'hybrid_used': False
        }
    
    def get_fallback_analysis(self, product_name: str, amazon_price: float) -> Dict:
        """تحليل احتياطي"""
        return {
            'scraped_data': [],
            'gemini_analysis': "لم يتم العثور على بيانات من المواقع",
            'market_average': 0,
            'confidence': 70,
            'recommendation': "اشتري",
            'sites_count': 0,
            'all_prices': [],
            'hybrid_used': False
        }

# إنشاء المقارن الهجين
hybrid_comparator = GeminiWebScrapingComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected=False):
    """إرسال تنبيه مع مقارنة هجينة"""
    
    def analyze_and_send():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # مقارنة هجينة
            comparison = loop.run_until_complete(
                hybrid_comparator.get_comprehensive_comparison_hybrid(
                    item.get('name', ''), new_price
                )
            )
            
            # تحديث البيانات
            item.update({
                'comparison': comparison,
                'final_confidence': comparison['confidence'],
                'recommendation': comparison['recommendation'],
                'market_average': comparison['market_average'],
                'hybrid_used': comparison['hybrid_used']
            })
            
            hybrid_comparator.stats['products_sent'] += 1
            
            loop.close()
            
            # إرسال تليجرام
            send_actual_telegram(item, old_price, new_price, discount_percent)
            
        except Exception as e:
            print(f"❌ خطأ: {e}")
    
    threading.Thread(target=analyze_and_send, daemon=True).start()

def send_actual_telegram(item, old_price, new_price, discount_percent):
    """إرسال رسالة تليجرام مع تحليل هجين"""
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
        hybrid_used = item.get('hybrid_used', False)
        scraped_data = comparison.get('scraped_data', [])
        gemini_analysis = comparison.get('gemini_analysis', '')

        # عنوان
        if recommendation == "اشتري فوراً":
            headline = "🔥 <b>EXCELLENT DEAL!</b> 🔥"
        elif recommendation == "اشتري":
            headline = "✅ <b>GOOD DEAL!</b>"
        else:
            headline = "💸 <b>FAIR DEAL</b>"

        # مقارنة منظمة
        comparison_info = ""
        if scraped_data:
            comparison_info = f"\n🌐 <b>مقارنة مباشرة مع المواقع المصرية:</b>"
            
            for site_data in scraped_data:
                site_name = site_data['site']
                avg_price = site_data.get('average', 0)
                status = site_data.get('status', 'غير متوفر')
                
                if avg_price > 0:
                    comparison_info += f"\n📊 <b>{site_name}</b> | {avg_price:,.0f} جنيه | {status}"
                else:
                    comparison_info += f"\n📊 <b>{site_name}</b> | غير متوفر"
            
            if market_average > 0:
                vs_market = ((market_average - new_price) / market_average) * 100
                comparison_info += f"\n📊 <b>متوسط السوق:</b> {market_average:,.0f} جنيه"
                if vs_market > 0:
                    comparison_info += f"\n💰 <b>توفير:</b> {vs_market:.0f}% من متوسط السوق"
                elif vs_market < 0:
                    comparison_info += f"\n⚠️ <b>زيادة:</b> {abs(vs_market):.0f}% عن متوسط السوق"

        # تحليل Gemini
        gemini_info = ""
        if hybrid_used and gemini_analysis:
            gemini_info = f"\n🤖 <b>Gemini Analysis:</b>\n{gemini_analysis[:200]}..."

        # رسالة
        msg = f"""{headline}

<b>{product_name}</b>

💰 <b>أمازون:</b> {int(new_price):,} جنيه
📈 <b>Confidence:</b> {final_confidence}%
🎯 <b>Recommendation:</b> {recommendation}

{comparison_info}

{gemini_info}

🔗 <a href="{url}">Buy on Amazon</a>

{'🤖 <b>Hybrid: Web Scraping + Gemini AI</b>' if hybrid_used else '🌐 <b>Direct Web Scraping</b>'}
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
            method = "🤖 Hybrid" if hybrid_used else "🌐 Direct"
            print(f"✅ {method} تنبيه إرسال لـ {sent_count} مستخدم")

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

def test_babyliss_product():
    """اختبار منتج بيبي ليس"""
    log("🧪 اختبار مقارنة منتج بيبي ليس...")
    
    test_item = {
        "name": "ماكينة حلاقة متعددة الاستخدامات 10 في 1 للرجال من بيبي ليس، مجموعة أدوات تهذيب وحلاقة لاسلكية من التيتانيوم الكربوني مع شفرات بعرض 34 ملم، مرفقات للأنف/الأذن/الجسم ورؤوس قابلة للغسيل",
        "asin": "BABYLISS123",
        "url": "https://amazon.eg/babyliss-test",
        "img": "",
        "section": "Beauty"
    }
    
    test_price = 1500
    
    send_telegram_alert(test_item, None, test_price, 0)

def show_stats():
    """عرض الإحصائيات"""
    stats = hybrid_comparator.stats
    
    log(f"📊 إحصائيات الهجين:")
    log(f"   📊 مقارنات كلية: {stats['total_comparisons']}")
    log(f"   🤖 تحليلات Gemini: {stats['gemini_analyses']}")
    log(f"   🌐 مواقع مسكربة: {stats['sites_scraped']}")
    log(f"   📱 منتجات مرسلة: {stats['products_sent']}")
    
    if stats['total_comparisons'] > 0:
        gemini_rate = (stats['gemini_analyses'] / stats['total_comparisons']) * 100
        log(f"   🎯 Gemini Usage Rate: {gemini_rate:.1f}%")

# الواجهة
root = ctk.CTk()
root.title("LAQTA Hybrid - Web Scraping + Gemini AI")
root.geometry("1200x700")

title_label = ctk.CTkLabel(root, text="LAQTA Hybrid", font=("Arial", 35), text_color="#54fac8")
title_label.pack(pady=20)

subtitle_label = ctk.CTkLabel(root, text="🌐 Web Scraping + 🤖 Gemini AI Analysis", 
                             font=("Arial", 16), text_color="#ffaa44")
subtitle_label.pack(pady=5)

# Log
log_textbox = ctk.CTkTextbox(root, height=350, font=("Consolas", 11))
log_textbox.pack(pady=20, padx=20, fill="both", expand=True)

# Buttons
buttons_frame = ctk.CTkFrame(root)
buttons_frame.pack(pady=10, fill="x")

test_babyliss_btn = ctk.CTkButton(buttons_frame, text="🧪 Test Babyliss Product", 
                                 command=test_babyliss_product, fg_color="#4CAF50")
test_babyliss_btn.pack(side="left", padx=10)

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Stats", 
                         command=show_stats, fg_color="#FF9800")
stats_btn.pack(side="left", padx=10)

exit_btn = ctk.CTkButton(buttons_frame, text="❌ Exit", 
                        command=root.destroy, fg_color="#607D8B")
exit_btn.pack(side="right", padx=10)

# إعداد تلقائي
auto_setup_configs()
load_db()

# رسائل البداية
if hybrid_comparator.ai_enabled:
    log("🤖 LAQTA Hybrid System Ready!", "🚀")
    log("✅ Web Scraping + Gemini AI Analysis", "🤖")
    log("🌐 نسكرب المواقع المصرية ونرسل البيانات لـ Gemini", "🌐")
    log("📊 Gemini ينظم النتائج في الشكل المطلوب", "📊")
else:
    log("🌐 LAQTA Direct Scraping Only", "🚀")
    log("⚠️ Gemini غير متاح - استخدام تحليل مباشر", "⚠️")

log("🧪 اضغط 'Test Babyliss Product' لاختبار المنتج المطلوب", "🎯")

root.mainloop()