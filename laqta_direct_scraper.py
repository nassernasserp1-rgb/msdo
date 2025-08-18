#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA Direct Scraper - مقارنة مباشرة مع المواقع المصرية
سكرابة حقيقية للمواقع وعرض النتائج في الشكل المطلوب
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

def auto_setup_telegram():
    """إعداد تلقائي لتليجرام"""
    if not os.path.exists('telegram_config.json'):
        telegram_config = {
            "bot_token": "8182350211:AAEHUVf3CpKi5wDUNpvipjURyGQ",
            "users": ["6613608451", "1712205938"],
            "auto_created": True
        }
        
        with open('telegram_config.json', 'w', encoding='utf-8') as f:
            json.dump(telegram_config, f, indent=4, ensure_ascii=False)
        
        print("✅ تم إنشاء telegram_config.json تلقائياً")

class DirectEgyptianScraper:
    """سكرابة مباشرة للمواقع المصرية"""
    
    def __init__(self):
        self.stats = {
            'total_comparisons': 0,
            'sites_scraped': 0,
            'products_sent': 0
        }
        
        print("✅ Direct Egyptian Scraper مفعل")
        print("🌐 سكرابة مباشرة للمواقع المصرية")
        print("📊 نتائج حقيقية في الشكل المطلوب")
    
    async def scrape_noon_direct(self, search_term: str) -> Dict:
        """سكرابة نون مباشرة"""
        try:
            search_url = f"https://www.noon.com/egypt-en/search/?q={urllib.parse.quote(search_term)}"
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                await page.goto(search_url, timeout=15000)
                await page.wait_for_timeout(2000)
                
                # البحث عن الأسعار
                price_elements = await page.query_selector_all('[data-qa="product-price"]')
                prices = []
                
                for element in price_elements[:5]:
                    try:
                        price_text = await element.inner_text()
                        price_match = re.search(r'(\d{1,6}(?:,\d{3})*)', price_text)
                        if price_match:
                            price = float(price_match.group(1).replace(',', ''))
                            if 50 <= price <= 50000:
                                prices.append(price)
                    except:
                        continue
                
                await browser.close()
                
                if prices:
                    avg_price = statistics.mean(prices)
                    return {
                        'site': 'نون',
                        'prices': prices,
                        'average': avg_price,
                        'min_price': min(prices),
                        'max_price': max(prices),
                        'status': 'متوفر',
                        'count': len(prices)
                    }
                else:
                    return {'site': 'نون', 'status': 'غير متوفر', 'prices': []}
                    
        except Exception as e:
            print(f"   ❌ نون: {e}")
            return {'site': 'نون', 'status': 'خطأ في الوصول', 'prices': []}
    
    async def scrape_jumia_direct(self, search_term: str) -> Dict:
        """سكرابة جوميا مباشرة"""
        try:
            search_url = f"https://www.jumia.com.eg/catalog/?q={urllib.parse.quote(search_term)}"
            
            response = requests.get(search_url, timeout=8, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                content = response.text
                
                # البحث عن أسعار جوميا
                price_matches = re.findall(r'(\d{1,6}(?:,\d{3})*)\s*(?:EGP|جنيه)', content)
                prices = []
                
                for match in price_matches[:8]:
                    try:
                        price = float(match.replace(',', ''))
                        if 50 <= price <= 50000:
                            prices.append(price)
                    except:
                        continue
                
                if prices:
                    unique_prices = sorted(list(set(prices)))[:5]
                    avg_price = statistics.mean(unique_prices)
                    return {
                        'site': 'جوميا',
                        'prices': unique_prices,
                        'average': avg_price,
                        'min_price': min(unique_prices),
                        'max_price': max(unique_prices),
                        'status': 'متوفر',
                        'count': len(unique_prices)
                    }
                else:
                    return {'site': 'جوميا', 'status': 'غير متوفر', 'prices': []}
            else:
                return {'site': 'جوميا', 'status': 'خطأ في الوصول', 'prices': []}
                
        except Exception as e:
            print(f"   ❌ جوميا: {e}")
            return {'site': 'جوميا', 'status': 'خطأ في الوصول', 'prices': []}
    
    async def scrape_kanbkam_direct(self, search_term: str) -> Dict:
        """سكرابة كان بكام مباشرة"""
        try:
            search_url = f"https://www.kanbkam.com/search?q={urllib.parse.quote(search_term)}"
            
            response = requests.get(search_url, timeout=6, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                content = response.text
                
                # البحث عن أسعار
                price_matches = re.findall(r'(\d{1,6}(?:,\d{3})*)\s*(?:جنيه|EGP)', content)
                prices = []
                
                for match in price_matches[:5]:
                    try:
                        price = float(match.replace(',', ''))
                        if 50 <= price <= 50000:
                            prices.append(price)
                    except:
                        continue
                
                if prices:
                    unique_prices = sorted(list(set(prices)))
                    if unique_prices:
                        avg_price = statistics.mean(unique_prices)
                        return {
                            'site': 'كان بكام',
                            'prices': unique_prices,
                            'average': avg_price,
                            'status': 'متوفر',
                            'count': len(unique_prices)
                        }
                
            return {'site': 'كان بكام', 'status': 'غير متوفر', 'prices': []}
                
        except Exception as e:
            print(f"   ❌ كان بكام: {e}")
            return {'site': 'كان بكام', 'status': 'خطأ في الوصول', 'prices': []}
    
    async def get_comprehensive_comparison(self, product_name: str, amazon_price: float) -> Dict:
        """مقارنة شاملة مباشرة مع المواقع المصرية"""
        
        print(f"🔍 مقارنة مباشرة: {product_name[:50]}...")
        
        # استخراج كلمات البحث
        search_keywords = []
        for word in product_name.split()[:4]:
            clean = re.sub(r'[^\w]', '', word.lower())
            if len(clean) > 2:
                search_keywords.append(clean)
        
        search_term = ' '.join(search_keywords[:3])
        print(f"   🔍 كلمات البحث: {search_term}")
        
        # سكرابة المواقع مباشرة
        print(f"   🌐 سكرابة المواقع المصرية...")
        
        tasks = [
            self.scrape_noon_direct(search_term),
            self.scrape_jumia_direct(search_term),
            self.scrape_kanbkam_direct(search_term)
        ]
        
        # تشغيل السكرابة بالتوازي
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # تجميع النتائج
        comparison_results = []
        all_prices = []
        
        for result in results:
            if isinstance(result, dict) and result.get('prices'):
                comparison_results.append(result)
                all_prices.extend(result['prices'])
                
                # طباعة النتيجة بالشكل المطلوب
                site_name = result['site']
                avg_price = result.get('average', 0)
                status = result.get('status', 'غير متوفر')
                
                if avg_price > 0:
                    print(f"      📊 {site_name} | {avg_price:,.0f} جنيه | {status}")
                else:
                    print(f"      📊 {site_name} | غير متوفر")
        
        # حساب متوسط السوق
        market_average = 0
        if all_prices:
            market_average = statistics.mean(all_prices)
            print(f"   📊 متوسط السوق: {market_average:,.0f} جنيه")
        
        # تحديد التوصية
        confidence = 70
        recommendation = "اشتري"
        
        if market_average > 0:
            vs_market = ((market_average - amazon_price) / market_average) * 100
            
            if vs_market > 20:
                confidence = 95
                recommendation = "اشتري فوراً"
                print(f"   🔥 سعر أمازون ممتاز - توفير {vs_market:.0f}%")
            elif vs_market > 10:
                confidence = 85
                recommendation = "اشتري"
                print(f"   ✅ سعر أمازون جيد - توفير {vs_market:.0f}%")
            elif vs_market < -10:
                confidence = 65
                recommendation = "فكر"
                print(f"   ⚠️ سعر أمازون مرتفع - زيادة {abs(vs_market):.0f}%")
            else:
                print(f"   💸 سعر أمازون قريب من السوق")
        
        self.stats['total_comparisons'] += 1
        self.stats['sites_scraped'] += len(comparison_results)
        
        return {
            'comparison_results': comparison_results,
            'market_average': market_average,
            'confidence': confidence,
            'recommendation': recommendation,
            'sites_count': len(comparison_results),
            'all_prices': all_prices,
            'direct_scraping': True
        }

# إنشاء السكرابر المباشر
direct_scraper = DirectEgyptianScraper()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected=False):
    """إرسال تنبيه مع مقارنة مباشرة"""
    
    def analyze_and_send():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # مقارنة مباشرة مع المواقع
            comparison = loop.run_until_complete(
                direct_scraper.get_comprehensive_comparison(
                    item.get('name', ''), new_price
                )
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
                'direct_scraping': comparison['direct_scraping']
            })
            
            direct_scraper.stats['products_sent'] += 1
            
            loop.close()
            
            # إرسال تليجرام
            send_actual_telegram(item, old_price, new_price, discount_percent)
            
        except Exception as e:
            print(f"❌ خطأ: {e}")
    
    threading.Thread(target=analyze_and_send, daemon=True).start()

def send_actual_telegram(item, old_price, new_price, discount_percent):
    """إرسال رسالة تليجرام مع مقارنة مباشرة"""
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
        comparison_results = comparison.get('comparison_results', [])

        # عنوان
        if recommendation == "اشتري فوراً":
            headline = "🔥 <b>EXCELLENT DEAL!</b> 🔥"
        elif recommendation == "اشتري":
            headline = "✅ <b>GOOD DEAL!</b>"
        else:
            headline = "💸 <b>FAIR DEAL</b>"

        # مقارنة مباشرة بالشكل المطلوب
        comparison_info = ""
        if comparison_results:
            comparison_info = f"\n🌐 <b>مقارنة مباشرة مع المواقع المصرية:</b>"
            
            for result in comparison_results:
                site_name = result['site']
                if result.get('average', 0) > 0:
                    avg_price = result['average']
                    status = result.get('status', 'متوفر')
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

        # رسالة
        msg = f"""{headline}

<b>{product_name}</b>

💰 <b>أمازون:</b> {int(new_price):,} جنيه
📈 <b>Confidence:</b> {final_confidence}%
🎯 <b>Recommendation:</b> {recommendation}

{comparison_info}

🔗 <a href="{url}">Buy on Amazon</a>

🌐 <b>مقارنة مباشرة مع المواقع المصرية</b>
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
            print(f"✅ 🌐 Direct مقارنة إرسال لـ {sent_count} مستخدم")

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

def test_direct_comparison():
    """اختبار المقارنة المباشرة"""
    log("🧪 اختبار المقارنة المباشرة مع المواقع المصرية...")
    
    # المنتج اللي طلبته
    test_item = {
        "name": "ماكينة حلاقة متعددة الاستخدامات 10 في 1 للرجال من بيبي ليس، مجموعة أدوات تهذيب وحلاقة لاسلكية من التيتانيوم الكربوني مع شفرات بعرض 34 ملم، مرفقات للأنف/الأذن/الجسم ورؤوس قابلة للغسيل",
        "asin": "TEST123",
        "url": "https://amazon.eg/test",
        "img": "",
        "section": "Beauty"
    }
    
    test_price = 1500  # سعر تجريبي
    
    send_telegram_alert(test_item, None, test_price, 0)

def test_simple_product():
    """اختبار منتج بسيط"""
    log("🧪 اختبار منتج بسيط...")
    
    test_item = {
        "name": "Samsung Galaxy A06",
        "asin": "TEST456", 
        "url": "https://amazon.eg/test",
        "img": "",
        "section": "Electronics"
    }
    
    test_price = 2500
    
    send_telegram_alert(test_item, None, test_price, 0)

def show_stats():
    """عرض الإحصائيات"""
    stats = direct_scraper.stats
    
    log(f"📊 إحصائيات المقارنة المباشرة:")
    log(f"   📊 مقارنات كلية: {stats['total_comparisons']}")
    log(f"   🌐 مواقع تم سكرابتها: {stats['sites_scraped']}")
    log(f"   📱 منتجات مرسلة: {stats['products_sent']}")

# الواجهة
root = ctk.CTk()
root.title("LAQTA Direct Scraper - Real Egyptian Market Comparison")
root.geometry("1200x700")

title_label = ctk.CTkLabel(root, text="LAQTA Direct", font=("Arial", 35), text_color="#54fac8")
title_label.pack(pady=20)

subtitle_label = ctk.CTkLabel(root, text="🌐 مقارنة مباشرة مع المواقع المصرية - بدون AI", 
                             font=("Arial", 16), text_color="#ffaa44")
subtitle_label.pack(pady=5)

# Log
log_textbox = ctk.CTkTextbox(root, height=350, font=("Consolas", 11))
log_textbox.pack(pady=20, padx=20, fill="both", expand=True)

# Buttons
buttons_frame = ctk.CTkFrame(root)
buttons_frame.pack(pady=10, fill="x")

test_babyliss_btn = ctk.CTkButton(buttons_frame, text="🧪 Test Babyliss Product", 
                                 command=test_direct_comparison, fg_color="#4CAF50")
test_babyliss_btn.pack(side="left", padx=10)

test_samsung_btn = ctk.CTkButton(buttons_frame, text="🧪 Test Samsung", 
                                command=test_simple_product, fg_color="#2196F3")
test_samsung_btn.pack(side="left", padx=10)

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Stats", 
                         command=show_stats, fg_color="#FF9800")
stats_btn.pack(side="left", padx=10)

exit_btn = ctk.CTkButton(buttons_frame, text="❌ Exit", 
                        command=root.destroy, fg_color="#607D8B")
exit_btn.pack(side="right", padx=10)

# إعداد تلقائي
auto_setup_telegram()
load_db()

# رسائل البداية
log("🌐 LAQTA Direct Scraper System!", "🚀")
log("✅ سكرابة مباشرة للمواقع المصرية", "🌐")
log("📊 نتائج حقيقية: اسم الموقع | السعر | حالة التوفر", "📊")
log("🎯 مقارنة مع: نون، جوميا، كان بكام", "🎯")
log("💰 حساب متوسط السوق ونسبة التوفير", "💰")
log("🧪 اضغط 'Test Babyliss Product' لاختبار المنتج المطلوب", "🧪")

root.mainloop()