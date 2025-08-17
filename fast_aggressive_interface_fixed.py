#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
واجهة سريعة للبحث العدواني عن المنتجات الجديدة - مُصلحة
"""

import customtkinter as ctk
import json
import threading
import asyncio
import os
from datetime import datetime
import time

# استيراد الباحث العدواني
from aggressive_new_finder import AggressiveNewProductsFinder

# إعداد الواجهة (إصلاح مشكلة اللون)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")  # استخدام لون متاح

# الفئات المتاحة
CATEGORIES = {
    'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Beauty': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017988031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Fashion': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018165031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Automotive': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017874031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Home & Kitchen': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021933031%2Cp_98%3A21909049031&dc&page={}&language=en",
}

class FastAggressiveInterface:
    def __init__(self):
        self.finder = None
        self.stop_flag = {"stop": False}
        self.running = False
        self.telegram_alerts_enabled = True
        self.ALERT_DISCOUNT = 25
        
        # إحصائيات الجلسة
        self.session_stats = {
            'start_time': None,
            'new_products_found': 0,
            'total_checked': 0,
            'alerts_sent': 0,
            'json_files_created': 0
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        """إعداد واجهة المستخدم السريعة"""
        self.root = ctk.CTk()
        self.root.title("LAQTA - AGGRESSIVE NEW FINDER")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)
        self.root.rowconfigure(4, weight=1)
        self.root.columnconfigure(0, weight=1)

        # العنوان العدواني
        title_label = ctk.CTkLabel(
            self.root, 
            text="🔥 AGGRESSIVE NEW FINDER 🔥", 
            font=("Arial", 40, "bold"), 
            text_color="#ff4444"
        )
        title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

        # شعار
        subtitle_label = ctk.CTkLabel(
            self.root, 
            text="⚡ أسرع طريقة للعثور على منتجات جديدة ⚡", 
            font=("Arial", 18, "bold"), 
            text_color="#ffaa44"
        )
        subtitle_label.grid(row=1, column=0, padx=8, pady=(0, 10), sticky="ew")
        
        # إطار التحكم السريع
        self.setup_fast_controls()
        
        # إطار الإحصائيات المباشرة
        self.setup_live_stats()
        
        # صندوق السجل المحسن
        self.log_textbox = ctk.CTkTextbox(
            self.root, 
            font=("Consolas", 13), 
            fg_color="#1a1a1a", 
            text_color="#00ff88", 
            border_width=2,
            border_color="#ff4444",
            height=250
        )
        self.log_textbox.grid(row=4, column=0, padx=15, pady=(0, 12), sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # أزرار عدوانية
        self.setup_aggressive_buttons()

    def setup_fast_controls(self):
        """إعداد عناصر التحكم السريعة"""
        controls_frame = ctk.CTkFrame(self.root, fg_color="#2a1a1a", border_width=2, border_color="#ff4444")
        controls_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        controls_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)

        # اختيار القسم
        self.section_combo = ctk.CTkComboBox(
            controls_frame, 
            values=["All Sections"] + list(CATEGORIES.keys()),
            width=180, 
            font=("Arial", 16, "bold"), 
            button_color="#ff4444",
            fg_color="#1a1a1a",
            text_color="#ffffff"
        )
        self.section_combo.set("Electronics")
        self.section_combo.grid(row=0, column=0, padx=8, pady=12, sticky="ew")

        # هدف المنتجات الجديدة
        target_label = ctk.CTkLabel(controls_frame, text="🎯 Target New:", 
                                   font=("Arial", 14, "bold"), text_color="#ffaa44")
        target_label.grid(row=0, column=1, padx=5, pady=12, sticky="ew")
        
        self.target_entry = ctk.CTkEntry(
            controls_frame, 
            width=100, 
            font=("Arial", 16, "bold"), 
            fg_color="#1a1a1a", 
            text_color="#00ff88",
            border_color="#ff4444"
        )
        self.target_entry.insert(0, "500")
        self.target_entry.grid(row=0, column=2, padx=5, pady=12, sticky="ew")

        # حد أقصى للصفحات
        pages_label = ctk.CTkLabel(controls_frame, text="📄 Max Pages:", 
                                  font=("Arial", 14, "bold"), text_color="#ffaa44")
        pages_label.grid(row=0, column=3, padx=5, pady=12, sticky="ew")
        
        self.max_pages_entry = ctk.CTkEntry(
            controls_frame, 
            width=80, 
            font=("Arial", 16, "bold"), 
            fg_color="#1a1a1a", 
            text_color="#00ff88",
            border_color="#ff4444"
        )
        self.max_pages_entry.insert(0, "80")
        self.max_pages_entry.grid(row=0, column=4, padx=5, pady=12, sticky="ew")

        # تفعيل التليجرام
        self.telegram_checkbox = ctk.CTkCheckBox(
            controls_frame, 
            text="📱 Telegram", 
            font=("Arial", 14, "bold"), 
            text_color="#00ff88",
            command=self.toggle_telegram_alert
        )
        self.telegram_checkbox.grid(row=0, column=5, padx=8, pady=12, sticky="ew")
        self.telegram_checkbox.select()

    def setup_live_stats(self):
        """إعداد إحصائيات مباشرة"""
        self.stats_frame = ctk.CTkFrame(self.root, fg_color="#1a2a1a", border_width=2, border_color="#00ff88", height=100)
        self.stats_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        self.stats_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)
        
        # عنوان الإحصائيات
        stats_title = ctk.CTkLabel(self.stats_frame, text="📊 LIVE AGGRESSIVE STATS", 
                                  font=("Arial", 16, "bold"), text_color="#00ff88")
        stats_title.grid(row=0, column=0, columnspan=6, pady=(5, 0))
        
        # تسميات الإحصائيات
        self.stats_labels = {}
        stats_names = [
            ("🔍 Checked", "checked"),
            ("✨ New Found", "new_found"),
            ("📈 Discovery %", "discovery_rate"),
            ("⚡ New/Min", "new_per_minute"),
            ("🚨 Alerts", "alerts"),
            ("📄 JSON Files", "json_files")
        ]
        
        for i, (name, key) in enumerate(stats_names):
            frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
            frame.grid(row=1, column=i, padx=5, pady=8, sticky="ew")
            
            title = ctk.CTkLabel(frame, text=name, font=("Arial", 11, "bold"), text_color="#ffaa44")
            title.pack()
            
            value = ctk.CTkLabel(frame, text="0", font=("Arial", 16, "bold"), text_color="#ffffff")
            value.pack()
            
            self.stats_labels[key] = value

    def setup_aggressive_buttons(self):
        """إعداد أزرار عدوانية"""
        buttons_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        buttons_frame.grid(row=5, column=0, padx=10, pady=15, sticky="ew")
        buttons_frame.grid_columnconfigure((0,1,2,3,4), weight=1)

        btn_w, btn_h = 200, 55
        btn_font = ("Arial", 18, "bold")

        # زر البحث العدواني الرئيسي
        self.aggressive_btn = ctk.CTkButton(
            buttons_frame, 
            text="🔥 START AGGRESSIVE", 
            command=self.start_aggressive_search,
            width=btn_w, height=btn_h, font=btn_font, 
            fg_color="#ff4444", hover_color="#ff6666", text_color="#ffffff"
        )
        self.aggressive_btn.grid(row=0, column=0, padx=8, pady=8, sticky="ew")

        # زر الإيقاف
        self.stop_btn = ctk.CTkButton(
            buttons_frame, 
            text="⏹️ STOP", 
            command=self.stop_search,
            width=btn_w, height=btn_h, font=btn_font, 
            fg_color="#666666", hover_color="#888888", text_color="#ffffff"
        )
        self.stop_btn.grid(row=0, column=1, padx=8, pady=8, sticky="ew")

        # زر اختبار التليجرام
        self.test_telegram_btn = ctk.CTkButton(
            buttons_frame, 
            text="📱 TEST TELEGRAM", 
            command=self.test_telegram,
            width=btn_w, height=btn_h, font=btn_font, 
            fg_color="#00aa44", hover_color="#00cc55", text_color="#ffffff"
        )
        self.test_telegram_btn.grid(row=0, column=2, padx=8, pady=8, sticky="ew")

        # زر عرض النتائج
        self.results_btn = ctk.CTkButton(
            buttons_frame, 
            text="📊 SHOW RESULTS", 
            command=self.show_results,
            width=btn_w, height=btn_h, font=btn_font, 
            fg_color="#0088ff", hover_color="#00aaff", text_color="#ffffff"
        )
        self.results_btn.grid(row=0, column=3, padx=8, pady=8, sticky="ew")

        # زر الخروج
        self.exit_btn = ctk.CTkButton(
            buttons_frame, 
            text="❌ EXIT", 
            command=self.exit_app,
            width=btn_w, height=btn_h, font=btn_font, 
            fg_color="#333333", hover_color="#555555", text_color="#ff4444"
        )
        self.exit_btn.grid(row=0, column=4, padx=8, pady=8, sticky="ew")

    def log(self, msg, color="#00ff88"):
        """إضافة رسالة للسجل"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"[{timestamp}] {msg}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def toggle_telegram_alert(self):
        """تفعيل/إلغاء إشعارات التليجرام"""
        self.telegram_alerts_enabled = self.telegram_checkbox.get()
        status = "enabled" if self.telegram_alerts_enabled else "disabled"
        self.log(f"📱 Telegram alerts: {status}")

    def test_telegram(self):
        """اختبار التليجرام"""
        def test_thread():
            try:
                self.log("🧪 Testing Telegram connection...")
                
                # اختبار بسيط
                test_item = {
                    "name": "🧪 اختبار LAQTA العدواني",
                    "url": "https://amazon.eg/test",
                    "section": "اختبار",
                    "img": ""
                }
                
                # محاولة الاستيراد والاختبار
                try:
                    from telegram_bot_fixed import send_telegram_alert
                    success = send_telegram_alert(test_item, 100, 70, 30.0, False)
                except ImportError:
                    # استخدام النسخة الأصلية
                    from telegram_bot import send_telegram_alert
                    success = send_telegram_alert(test_item, 100, 70, 30.0, False)
                
                if success:
                    self.log("✅ Telegram test successful!")
                else:
                    self.log("❌ Telegram test failed!")
                    
            except Exception as e:
                self.log(f"❌ Telegram test error: {e}")
        
        threading.Thread(target=test_thread, daemon=True).start()

    def start_aggressive_search(self):
        """بدء البحث العدواني"""
        if self.running:
            self.log("⚠️ Already running!")
            return

        section = self.section_combo.get()
        
        try:
            target = int(self.target_entry.get())
            max_pages = int(self.max_pages_entry.get())
        except ValueError:
            self.log("❌ Invalid numbers in target or pages!")
            return

        self.stop_flag["stop"] = False
        self.running = True
        
        # إعادة تعيين الإحصائيات
        self.session_stats = {
            'start_time': time.time(),
            'new_products_found': 0,
            'total_checked': 0,
            'alerts_sent': 0,
            'json_files_created': 0
        }

        self.log(f"🔥 Starting AGGRESSIVE search - Target: {target} new products")
        self.log(f"🎯 Section: {section}, Max pages: {max_pages}")

        # تشغيل البحث في thread منفصل
        search_thread = threading.Thread(
            target=self.aggressive_search_wrapper, 
            args=(section, target, max_pages), 
            daemon=True
        )
        search_thread.start()

        # بدء تحديث الإحصائيات
        self.update_stats_periodically()

    def aggressive_search_wrapper(self, section, target, max_pages):
        """تشغيل البحث العدواني في حلقة async"""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            loop.run_until_complete(self.run_aggressive_search(section, target, max_pages))
        except Exception as e:
            self.log(f"❌ Aggressive search error: {e}")
        finally:
            self.running = False
            self.log("🎉 Aggressive search completed!")

    async def run_aggressive_search(self, section, target, max_pages):
        """تشغيل البحث العدواني"""
        
        self.finder = AggressiveNewProductsFinder()
        
        if section == "All Sections":
            # البحث في جميع الأقسام
            total_found = 0
            
            for sec_name, sec_url in CATEGORIES.items():
                if self.stop_flag["stop"]:
                    break
                
                self.log(f"🔥 Aggressive search in: {sec_name}")
                
                # هدف لكل قسم
                section_target = target // len(CATEGORIES)
                section_max_pages = max_pages // len(CATEGORIES)
                
                new_products = await self.finder.aggressive_search(
                    sec_name, sec_url, 
                    max_pages=section_max_pages, 
                    target_new_products=section_target
                )
                
                if new_products:
                    # حفظ فوري
                    self.finder.save_new_products_instantly(new_products, sec_name)
                    
                    # إرسال تنبيهات
                    await self.send_alerts_for_new_products(new_products)
                    
                    total_found += len(new_products)
                    self.session_stats['new_products_found'] = total_found
                    self.session_stats['json_files_created'] += 1
                    
                    self.log(f"💾 Found {len(new_products)} new products in {sec_name}")
                
                # تحديث الإحصائيات
                self.session_stats['total_checked'] = self.finder.total_checked
                self.root.after(0, self.update_live_stats)
        else:
            # البحث في قسم واحد
            section_url = CATEGORIES[section]
            
            self.log(f"🔥 Aggressive search in: {section}")
            
            new_products = await self.finder.aggressive_search(
                section, section_url, 
                max_pages=max_pages, 
                target_new_products=target
            )
            
            if new_products:
                self.finder.save_new_products_instantly(new_products, section)
                await self.send_alerts_for_new_products(new_products)
                
                self.session_stats['new_products_found'] = len(new_products)
                self.session_stats['json_files_created'] = 1
                
                self.log(f"💾 Found {len(new_products)} new products in {section}")
            
            self.session_stats['total_checked'] = self.finder.total_checked
            self.root.after(0, self.update_live_stats)

    async def send_alerts_for_new_products(self, new_products):
        """إرسال تنبيهات للمنتجات الجديدة ذات الخصومات"""
        
        if not self.telegram_alerts_enabled:
            return
        
        for product in new_products:
            discount = product.get('discount_percent', 0)
            
            if discount >= self.ALERT_DISCOUNT and product.get('price', 0) >= 10:
                try:
                    # محاولة استيراد النسخة المُصلحة أولاً
                    try:
                        from telegram_bot_fixed import send_telegram_alert
                    except ImportError:
                        from telegram_bot import send_telegram_alert
                    
                    success = send_telegram_alert(
                        product, 
                        product.get('strikePrice', 0), 
                        product.get('price', 0), 
                        discount, 
                        False
                    )
                    
                    if success:
                        self.session_stats['alerts_sent'] += 1
                        self.log(f"📱 Alert sent: {product['name'][:40]}... ({discount:.1f}% OFF)")
                    
                except Exception as e:
                    self.log(f"❌ Alert failed: {e}")

    def update_live_stats(self):
        """تحديث الإحصائيات المباشرة"""
        if self.session_stats['start_time']:
            elapsed = time.time() - self.session_stats['start_time']
            
            # تحديث الإحصائيات
            self.stats_labels["checked"].configure(text=str(self.session_stats['total_checked']))
            self.stats_labels["new_found"].configure(text=str(self.session_stats['new_products_found']))
            
            discovery_rate = (self.session_stats['new_products_found'] / max(self.session_stats['total_checked'], 1)) * 100
            self.stats_labels["discovery_rate"].configure(text=f"{discovery_rate:.1f}%")
            
            new_per_minute = (self.session_stats['new_products_found'] / max(elapsed, 1)) * 60
            self.stats_labels["new_per_minute"].configure(text=f"{new_per_minute:.1f}")
            
            self.stats_labels["alerts"].configure(text=str(self.session_stats['alerts_sent']))
            self.stats_labels["json_files"].configure(text=str(self.session_stats['json_files_created']))

    def update_stats_periodically(self):
        """تحديث الإحصائيات بشكل دوري"""
        if self.running:
            self.update_live_stats()
            self.root.after(2000, self.update_stats_periodically)  # كل ثانيتين

    def stop_search(self):
        """إيقاف البحث"""
        self.stop_flag["stop"] = True
        self.log("🛑 Stopping aggressive search...")

    def show_results(self):
        """عرض النتائج"""
        if self.finder and hasattr(self.finder, 'session_new_products'):
            stats = self.finder.session_new_products
            self.log(f"📊 Session results: {len(stats)} new products found")
            
            # عرض أفضل 5 منتجات
            sorted_products = sorted(
                stats.values(), 
                key=lambda x: x.get('discount_percent', 0), 
                reverse=True
            )[:5]
            
            if sorted_products:
                self.log("🏆 Top 5 deals found:")
                for i, product in enumerate(sorted_products, 1):
                    discount = product.get('discount_percent', 0)
                    price = product.get('price', 0)
                    name = product.get('name', 'Unknown')[:35]
                    self.log(f"   {i}. {name}... - {discount:.1f}% OFF ({price} EGP)")
            else:
                self.log("📭 No products with discounts found yet")
        else:
            self.log("📭 No search results yet")

    def exit_app(self):
        """إغلاق التطبيق"""
        self.stop_flag["stop"] = True
        self.root.destroy()

    def run(self):
        """تشغيل التطبيق"""
        self.log("🔥 AGGRESSIVE NEW FINDER STARTED!")
        self.log("⚡ This mode finds NEW products FAST!")
        self.log("🎯 Set your target and click START AGGRESSIVE!")
        self.log("📱 Don't forget to test Telegram first!")
        self.root.mainloop()

if __name__ == "__main__":
    app = FastAggressiveInterface()
    app.run()