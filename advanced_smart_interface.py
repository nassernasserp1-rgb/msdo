#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
واجهة متقدمة مع نظام البحث الذكي عن المنتجات الجديدة
"""

import customtkinter as ctk
import json
import threading
import asyncio
import os
from datetime import datetime
import webbrowser
from tkinter import messagebox
import time

# استيراد الباحث الذكي
from smart_new_products_finder import SmartNewProductsFinder

# استيراد السكرابر المتوافق مع JSON
from json_compatible_scraper import JSONCompatibleScraper, ProductData

# استيراد بوت التليجرام
from telegram_bot import send_telegram_alert

# إعداد الواجهة
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# الفئات المتاحة
CATEGORIES = {
    'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Automotive': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017874031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Beauty': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017988031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Fashion': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018165031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Grocery': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18020637031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Health & Household Products': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021875031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Home & Kitchen': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021933031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Tools & Home Improvement': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021990031%2Cp_98%3A21909049031&dc&page={}&language=en",
}

class AdvancedSmartInterface:
    def __init__(self):
        self.scraper = None
        self.smart_finder = None
        self.stop_flag = {"stop": False}
        self.running = False
        self.telegram_alerts_enabled = True
        self.alerts_data = []
        self.notified_asins = set()
        self.ALERT_DISCOUNT = 30
        self.json_file_path = ""
        
        # إعدادات البحث الذكي
        self.new_products_only = False
        self.search_strategy = "newest_first"
        
        self.setup_ui()
        
    def setup_ui(self):
        """إعداد واجهة المستخدم المتقدمة"""
        self.root = ctk.CTk()
        self.root.title("LAQTA - Advanced Smart Scraper")
        self.root.geometry("1700x1200")
        self.root.minsize(1400, 1000)
        self.root.rowconfigure(6, weight=1)
        self.root.columnconfigure(0, weight=1)

        # العنوان
        title_label = ctk.CTkLabel(
            self.root, 
            text="LAQTA - SMART FINDER", 
            font=("SST Arabic Medium", 50), 
            text_color="#54fac8"
        )
        title_label.grid(row=0, column=0, padx=8, pady=(18, 5), sticky="ew")

        # إطار ملف JSON
        self.setup_json_frame()
        
        # إطار التحكم الأساسي
        self.setup_basic_controls()
        
        # إطار البحث الذكي (الجديد)
        self.setup_smart_controls()
        
        # شريط التقدم
        self.progress_bar = ctk.CTkProgressBar(
            self.root, 
            height=25, 
            progress_color="#59ff9d", 
            fg_color="#232d3a"
        )
        self.progress_bar.grid(row=4, column=0, padx=10, pady=7, sticky="ew")
        self.progress_bar.set(0.0)

        # إطار الإحصائيات المتقدم
        self.setup_advanced_stats_frame()
        
        # صندوق السجل
        self.log_textbox = ctk.CTkTextbox(
            self.root, 
            font=("Consolas", 13), 
            fg_color="#20242f", 
            text_color="#c2ffe3", 
            border_width=0, 
            height=200
        )
        self.log_textbox.grid(row=6, column=0, padx=15, pady=(0, 12), sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # أزرار التحكم
        self.setup_buttons()

    def setup_json_frame(self):
        """إعداد إطار ملف JSON"""
        json_frame = ctk.CTkFrame(self.root, fg_color="#1a1f2b", height=60)
        json_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        json_frame.grid_columnconfigure(1, weight=1)
        
        json_label = ctk.CTkLabel(json_frame, text="📁 JSON File:", font=("Arial", 14, "bold"), text_color="#54fac8")
        json_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.json_path_label = ctk.CTkLabel(json_frame, text="No file selected", font=("Arial", 12), text_color="#ffffff")
        self.json_path_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        select_json_btn = ctk.CTkButton(json_frame, text="🔍 Select JSON", command=self.select_json_file,
                                       font=("Arial", 12, "bold"), fg_color="#12dafb", width=120, height=30)
        select_json_btn.grid(row=0, column=2, padx=10, pady=10)

    def setup_basic_controls(self):
        """إعداد عناصر التحكم الأساسية"""
        controls_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        controls_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)

        # العناصر الأساسية
        self.section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
                                           width=160, font=("Arial", 14), button_color="#54fac8")
        self.section_combo.set("Electronics")
        self.section_combo.grid(row=0, column=0, padx=4, pady=6, sticky="ew")

        self.pages_entry = ctk.CTkEntry(controls_frame, width=60, font=("Arial", 14), fg_color="#232d3a", text_color="#12dafb")
        self.pages_entry.insert(0, "20")
        self.pages_entry.grid(row=0, column=1, padx=4, pady=6, sticky="ew")

        pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 12), text_color="#12dafb")
        pages_label.grid(row=0, column=2, padx=4, pady=6, sticky="ew")

        self.all_pages_chk = ctk.CTkCheckBox(controls_frame, text="All Pages", font=("Arial", 12), text_color="#59ff9d")
        self.all_pages_chk.grid(row=0, column=3, padx=4, pady=6, sticky="ew")

        self.min_discount_slider = ctk.CTkSlider(controls_frame, from_=1, to=99, number_of_steps=98, width=90,
                                               command=self.set_min_discount, progress_color="#12dafb")
        self.min_discount_slider.set(self.ALERT_DISCOUNT)
        self.min_discount_slider.grid(row=0, column=4, padx=4, pady=6, sticky="ew")

        self.min_discount_label = ctk.CTkLabel(controls_frame, text=f"Min: {self.ALERT_DISCOUNT}%", 
                                             font=("Arial", 12), text_color="#59ff9d")
        self.min_discount_label.grid(row=0, column=5, padx=4, pady=6, sticky="ew")

        self.telegram_checkbox = ctk.CTkCheckBox(controls_frame, text="Telegram", font=("Arial", 12), 
                                               text_color="#13e6a7", command=self.toggle_telegram_alert)
        self.telegram_checkbox.grid(row=0, column=6, padx=4, pady=6, sticky="ew")
        self.telegram_checkbox.select()

        self.concurrency_entry = ctk.CTkEntry(controls_frame, width=50, font=("Arial", 12), 
                                            fg_color="#232d3a", text_color="#12dafb")
        self.concurrency_entry.insert(0, "15")
        self.concurrency_entry.grid(row=0, column=7, padx=4, pady=6, sticky="ew")

    def setup_smart_controls(self):
        """إعداد عناصر التحكم الذكية (الجديد)"""
        smart_frame = ctk.CTkFrame(self.root, fg_color="#1a2332", height=80)
        smart_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        smart_frame.grid_columnconfigure((1,3,5), weight=1)
        
        # عنوان القسم
        smart_title = ctk.CTkLabel(smart_frame, text="🧠 SMART SEARCH OPTIONS", 
                                 font=("Arial", 16, "bold"), text_color="#54fac8")
        smart_title.grid(row=0, column=0, columnspan=6, padx=10, pady=(5, 0), sticky="w")
        
        # خيار المنتجات الجديدة فقط
        self.new_products_checkbox = ctk.CTkCheckBox(
            smart_frame, 
            text="🆕 New Products Only", 
            font=("Arial", 14, "bold"), 
            text_color="#ff6b6b",
            command=self.toggle_new_products_only
        )
        self.new_products_checkbox.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        # استراتيجية البحث
        strategy_label = ctk.CTkLabel(smart_frame, text="Strategy:", font=("Arial", 12), text_color="#12dafb")
        strategy_label.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        self.strategy_combo = ctk.CTkComboBox(
            smart_frame,
            values=["newest_first", "random_pages", "price_ranges", "date_filters", "seller_rotation"],
            width=140,
            font=("Arial", 12),
            command=self.set_search_strategy
        )
        self.strategy_combo.set("newest_first")
        self.strategy_combo.grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        
        # حد التوقف
        stop_label = ctk.CTkLabel(smart_frame, text="Stop after:", font=("Arial", 12), text_color="#12dafb")
        stop_label.grid(row=1, column=3, padx=5, pady=5, sticky="w")
        
        self.stop_after_entry = ctk.CTkEntry(smart_frame, width=60, font=("Arial", 12), 
                                           fg_color="#232d3a", text_color="#12dafb")
        self.stop_after_entry.insert(0, "5")
        self.stop_after_entry.grid(row=1, column=4, padx=5, pady=5, sticky="ew")
        
        stop_pages_label = ctk.CTkLabel(smart_frame, text="empty pages", font=("Arial", 12), text_color="#12dafb")
        stop_pages_label.grid(row=1, column=5, padx=5, pady=5, sticky="w")

    def setup_advanced_stats_frame(self):
        """إعداد إطار الإحصائيات المتقدم"""
        self.stats_frame = ctk.CTkFrame(self.root, fg_color="#1a1f2b", height=90)
        self.stats_frame.grid(row=5, column=0, padx=10, pady=5, sticky="ew")
        self.stats_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)
        
        # تسميات الإحصائيات المتقدمة
        self.stats_labels = {}
        stats_names = [
            ("Total Checked", "total_checked"),
            ("New Found", "new_found"),
            ("Existing Skipped", "existing_skipped"),
            ("Discovery Rate", "discovery_rate"),
            ("Products/Sec", "products_per_second"),
            ("Alerts Sent", "alerts_sent"),
            ("Cache Size", "cache_size"),
            ("DB Size", "db_size")
        ]
        
        for i, (name, key) in enumerate(stats_names):
            frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
            frame.grid(row=0, column=i, padx=2, pady=8, sticky="ew")
            
            title = ctk.CTkLabel(frame, text=name, font=("Arial", 10, "bold"), text_color="#54fac8")
            title.pack()
            
            value = ctk.CTkLabel(frame, text="0", font=("Arial", 14, "bold"), text_color="#ffffff")
            value.pack()
            
            self.stats_labels[key] = value

    def setup_buttons(self):
        """إعداد الأزرار"""
        buttons_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        buttons_frame.grid(row=7, column=0, padx=10, pady=10, sticky="ew")
        buttons_frame.grid_columnconfigure((0,1,2,3,4,5,6), weight=1)

        btn_w, btn_h = 130, 38
        btn_font = ("Arial", 14, "bold")

        # أزرار التحكم
        self.start_btn = ctk.CTkButton(buttons_frame, text="🚀 Start Smart", command=self.start_smart_scraping,
                                     width=btn_w, height=btn_h, font=btn_font, fg_color="#54fac8", 
                                     hover_color="#12dafb", text_color="#111927")
        self.start_btn.grid(row=0, column=0, padx=4, pady=6, sticky="ew")

        self.stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=self.stop_scraping,
                                    width=btn_w, height=btn_h, font=btn_font, fg_color="#ff6b6b", 
                                    hover_color="#ff5252", text_color="#ffffff")
        self.stop_btn.grid(row=0, column=1, padx=4, pady=6, sticky="ew")

        self.new_only_btn = ctk.CTkButton(buttons_frame, text="🆕 New Only", command=self.start_new_products_only,
                                        width=btn_w, height=btn_h, font=btn_font, fg_color="#ff6b6b", 
                                        hover_color="#ff5252", text_color="#ffffff")
        self.new_only_btn.grid(row=0, column=2, padx=4, pady=6, sticky="ew")

        self.alerts_btn = ctk.CTkButton(buttons_frame, text="📢 Alerts", command=self.open_alerts_window,
                                      width=btn_w, height=btn_h, font=btn_font, fg_color="#59ff9d", 
                                      hover_color="#12dafb", text_color="#111927")
        self.alerts_btn.grid(row=0, column=3, padx=4, pady=6, sticky="ew")

        self.export_btn = ctk.CTkButton(buttons_frame, text="💾 Export", command=self.export_data,
                                      width=btn_w, height=btn_h, font=btn_font, fg_color="#12dafb", 
                                      hover_color="#59ff9d", text_color="#111927")
        self.export_btn.grid(row=0, column=4, padx=4, pady=6, sticky="ew")

        self.clear_btn = ctk.CTkButton(buttons_frame, text="🧹 Clear", command=self.clear_log,
                                     width=btn_w, height=btn_h, font=btn_font, fg_color="#9c27b0", 
                                     hover_color="#7b1fa2", text_color="#ffffff")
        self.clear_btn.grid(row=0, column=5, padx=4, pady=6, sticky="ew")

        self.exit_btn = ctk.CTkButton(buttons_frame, text="❌ Exit", command=self.exit_app,
                                    width=btn_w, height=btn_h, font=btn_font, fg_color="#232d3a", 
                                    hover_color="#fa1a50", text_color="#59ff9d")
        self.exit_btn.grid(row=0, column=6, padx=4, pady=6, sticky="ew")

    def select_json_file(self):
        """اختيار ملف JSON"""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            self.json_file_path = file_path
            file_name = os.path.basename(file_path)
            self.json_path_label.configure(text=file_name)
            self.log(f"✅ JSON file selected: {file_name}")

    def toggle_new_products_only(self):
        """تفعيل/إلغاء وضع المنتجات الجديدة فقط"""
        self.new_products_only = self.new_products_checkbox.get()
        status = "enabled" if self.new_products_only else "disabled"
        self.log(f"🆕 New products only mode: {status}")

    def set_search_strategy(self, strategy):
        """تحديد استراتيجية البحث"""
        self.search_strategy = strategy
        self.log(f"🧠 Search strategy set to: {strategy}")

    def start_new_products_only(self):
        """بدء البحث عن المنتجات الجديدة فقط"""
        self.new_products_checkbox.select()
        self.toggle_new_products_only()
        self.start_smart_scraping()

    def start_smart_scraping(self):
        """بدء السكرابة الذكية"""
        if self.running:
            self.log("⚠️ Already running!", "🚨")
            return

        # إعداد المتغيرات
        section = self.section_combo.get()
        all_pages = self.all_pages_chk.get()
        
        try:
            pages = int(self.pages_entry.get()) if not all_pages else 500
            concurrency = int(self.concurrency_entry.get())
            stop_after = int(self.stop_after_entry.get())
        except ValueError:
            self.log("❌ Invalid input values", "🚨")
            return

        self.progress_bar.set(0.0)
        self.stop_flag["stop"] = False
        self.running = True
        self.alerts_data.clear()
        self.notified_asins.clear()

        mode = "New Products Only" if self.new_products_only else "All Products"
        self.log(f"🚀 Starting smart scraping - Mode: {mode}, Strategy: {self.search_strategy}", "🎯")

        # تشغيل السكرابر في thread منفصل
        scraper_thread = threading.Thread(
            target=self.smart_scraper_wrapper, 
            args=(section, pages, concurrency, stop_after), 
            daemon=True
        )
        scraper_thread.start()

        # بدء تحديث الإحصائيات
        self.update_stats_periodically()

    def smart_scraper_wrapper(self, section, pages, concurrency, stop_after):
        """تشغيل السكرابر الذكي في حلقة async"""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            loop.run_until_complete(self.run_smart_scraper(section, pages, concurrency, stop_after))
        except Exception as e:
            self.log(f"❌ Smart scraper error: {e}", "🚨")
        finally:
            self.running = False
            self.log("✅ Smart scraping completed", "🎉")

    async def run_smart_scraper(self, section, pages, concurrency, stop_after):
        """تشغيل السكرابر الذكي"""
        
        if self.new_products_only:
            # وضع المنتجات الجديدة فقط
            self.smart_finder = SmartNewProductsFinder()
            
            if section == "All Sections":
                for sec_name, sec_url in CATEGORIES.items():
                    if self.stop_flag["stop"]:
                        break
                    
                    self.log(f"🔍 Smart search in: {sec_name}", "🎯")
                    
                    new_products = await self.smart_finder.smart_search_new_products(
                        sec_name, sec_url, self.search_strategy, pages, stop_after
                    )
                    
                    if new_products:
                        self.smart_finder.save_new_products(new_products, sec_name)
                        self.log(f"💾 Saved {len(new_products)} new products from {sec_name}")
                    
                    # تحديث الإحصائيات
                    self.root.after(0, self.update_smart_stats)
            else:
                section_url = CATEGORIES[section]
                new_products = await self.smart_finder.smart_search_new_products(
                    section, section_url, self.search_strategy, pages, stop_after
                )
                
                if new_products:
                    self.smart_finder.save_new_products(new_products, section)
                    self.log(f"💾 Saved {len(new_products)} new products")
                
                self.root.after(0, self.update_smart_stats)
        else:
            # الوضع العادي مع السكرابر المحسن
            json_file = self.json_file_path if self.json_file_path else "amz_products.json"
            
            async with JSONCompatibleScraper(concurrency=concurrency, json_file=json_file) as scraper:
                self.scraper = scraper
                
                # باقي الكود كما هو...
                # (يمكن إضافة المزيد هنا حسب الحاجة)

    def update_smart_stats(self):
        """تحديث الإحصائيات الذكية"""
        if self.smart_finder:
            stats = self.smart_finder.get_search_stats()
            
            self.stats_labels["total_checked"].configure(text=str(stats['total_checked']))
            self.stats_labels["new_found"].configure(text=str(stats['new_found']))
            self.stats_labels["existing_skipped"].configure(text=str(stats['skipped_existing']))
            self.stats_labels["discovery_rate"].configure(text=f"{stats['discovery_rate']:.1f}%")

    def update_stats_periodically(self):
        """تحديث الإحصائيات بشكل دوري"""
        if self.running:
            if self.new_products_only:
                self.update_smart_stats()
            else:
                # تحديث إحصائيات السكرابر العادي
                pass
            
            self.root.after(3000, self.update_stats_periodically)

    # باقي الوظائف المساعدة (مثل الأصلية)
    def log(self, msg, emoji=""):
        """إضافة رسالة للسجل"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"[{timestamp}] {emoji} {msg}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def set_min_discount(self, val):
        """تحديد نسبة الخصم الأدنى"""
        self.ALERT_DISCOUNT = int(float(val))
        self.min_discount_label.configure(text=f"Min: {self.ALERT_DISCOUNT}%")

    def toggle_telegram_alert(self):
        """تفعيل/إلغاء إشعارات التليجرام"""
        self.telegram_alerts_enabled = not self.telegram_alerts_enabled

    def stop_scraping(self):
        """إيقاف السكرابة"""
        self.stop_flag["stop"] = True
        self.log("🛑 Stopping smart scraper...", "⏹️")

    def open_alerts_window(self):
        """فتح نافذة التنبيهات"""
        if not self.alerts_data:
            self.log("📭 No alerts to show", "ℹ️")
            return
        self.log(f"📢 Found {len(self.alerts_data)} alerts", "🎉")

    def export_data(self):
        """تصدير البيانات"""
        filename = f"smart_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "mode": "new_products_only" if self.new_products_only else "all_products",
            "strategy": self.search_strategy,
            "alerts": self.alerts_data
        }
        
        if self.smart_finder:
            export_data["smart_stats"] = self.smart_finder.get_search_stats()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
            
        self.log(f"💾 Smart data exported to {filename}", "✅")

    def clear_log(self):
        """مسح السجل"""
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def exit_app(self):
        """إغلاق التطبيق"""
        self.stop_flag["stop"] = True
        self.root.destroy()

    def run(self):
        """تشغيل التطبيق"""
        self.log("🧠 Advanced Smart Scraper started!", "🚀")
        self.log("🆕 NEW FEATURE: Smart search for new products only!", "💡")
        self.log("📋 Strategies: newest_first, random_pages, price_ranges, date_filters, seller_rotation", "ℹ️")
        self.root.mainloop()

if __name__ == "__main__":
    app = AdvancedSmartInterface()
    app.run()