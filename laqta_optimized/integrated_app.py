#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import customtkinter as ctk
import json
import threading
import asyncio
import os
from datetime import datetime
import webbrowser
import concurrent.futures
from PIL import Image
import requests
from io import BytesIO
import time

# استيراد السكرابر المحسن
from optimized_scraper import OptimizedScraper, ProductData

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

class OptimizedApp:
    def __init__(self):
        self.scraper = None
        self.scraper_task = None
        self.stop_flag = {"stop": False}
        self.running = False
        self.telegram_alerts_enabled = True
        self.alerts_data = []
        self.notified_asins = set()
        self.ALERT_DISCOUNT = 30
        self.performance_stats = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        """إعداد واجهة المستخدم المحسنة"""
        self.root = ctk.CTk()
        self.root.title("LAQTA - Optimized Amazon Product Hunter")
        self.root.geometry("1500x1000")
        self.root.minsize(1200, 800)
        self.root.rowconfigure(4, weight=1)
        self.root.columnconfigure(0, weight=1)

        # العنوان
        title_label = ctk.CTkLabel(
            self.root, 
            text="LAQTA - OPTIMIZED", 
            font=("SST Arabic Medium", 60), 
            text_color="#54fac8"
        )
        title_label.grid(row=0, column=0, padx=8, pady=(18, 5), sticky="ew")

        # إطار التحكم
        self.setup_controls()
        
        # شريط التقدم
        self.progress_bar = ctk.CTkProgressBar(
            self.root, 
            height=25, 
            progress_color="#59ff9d", 
            fg_color="#232d3a"
        )
        self.progress_bar.grid(row=2, column=0, padx=10, pady=7, sticky="ew")
        self.progress_bar.set(0.0)

        # إطار الإحصائيات
        self.setup_stats_frame()
        
        # صندوق السجل
        self.log_textbox = ctk.CTkTextbox(
            self.root, 
            font=("Consolas", 14), 
            fg_color="#20242f", 
            text_color="#c2ffe3", 
            border_width=0, 
            height=200
        )
        self.log_textbox.grid(row=4, column=0, padx=15, pady=(0, 12), sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # أزرار التحكم
        self.setup_buttons()

    def setup_controls(self):
        """إعداد عناصر التحكم"""
        controls_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        controls_frame.grid(row=1, column=0, padx=10, pady=7, sticky="ew")
        controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)

        # اختيار القسم
        self.section_combo = ctk.CTkComboBox(
            controls_frame, 
            values=["All Sections"] + list(CATEGORIES.keys()),
            width=200, 
            font=("Arial", 16), 
            button_color="#54fac8"
        )
        self.section_combo.set("Electronics")
        self.section_combo.grid(row=0, column=0, padx=5, pady=8, sticky="ew")

        # عدد الصفحات
        self.pages_entry = ctk.CTkEntry(
            controls_frame, 
            width=80, 
            font=("Arial", 16), 
            fg_color="#232d3a", 
            text_color="#12dafb"
        )
        self.pages_entry.insert(0, "10")
        self.pages_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

        pages_label = ctk.CTkLabel(
            controls_frame, 
            text="Pages", 
            font=("Arial", 14), 
            text_color="#12dafb"
        )
        pages_label.grid(row=0, column=2, padx=5, pady=8, sticky="ew")

        # جميع الصفحات
        self.all_pages_chk = ctk.CTkCheckBox(
            controls_frame, 
            text="All Pages", 
            font=("Arial", 14), 
            text_color="#59ff9d"
        )
        self.all_pages_chk.grid(row=0, column=3, padx=5, pady=8, sticky="ew")

        # نسبة الخصم الأدنى
        self.min_discount_slider = ctk.CTkSlider(
            controls_frame, 
            from_=1, 
            to=99, 
            number_of_steps=98, 
            width=120,
            command=self.set_min_discount, 
            progress_color="#12dafb"
        )
        self.min_discount_slider.set(self.ALERT_DISCOUNT)
        self.min_discount_slider.grid(row=0, column=4, padx=5, pady=8, sticky="ew")

        self.min_discount_label = ctk.CTkLabel(
            controls_frame, 
            text=f"Min: {self.ALERT_DISCOUNT}%", 
            font=("Arial", 14), 
            text_color="#59ff9d"
        )
        self.min_discount_label.grid(row=0, column=5, padx=5, pady=8, sticky="ew")

        # إشعارات التليجرام
        self.telegram_checkbox = ctk.CTkCheckBox(
            controls_frame, 
            text="Telegram", 
            font=("Arial", 14), 
            text_color="#13e6a7",
            command=self.toggle_telegram_alert
        )
        self.telegram_checkbox.grid(row=0, column=6, padx=5, pady=8, sticky="ew")
        self.telegram_checkbox.select()

        # مستوى التزامن
        concurrency_label = ctk.CTkLabel(
            controls_frame, 
            text="Concurrency:", 
            font=("Arial", 12), 
            text_color="#12dafb"
        )
        concurrency_label.grid(row=0, column=7, padx=5, pady=8, sticky="ew")
        
        self.concurrency_entry = ctk.CTkEntry(
            controls_frame, 
            width=60, 
            font=("Arial", 14), 
            fg_color="#232d3a", 
            text_color="#12dafb"
        )
        self.concurrency_entry.insert(0, "20")
        self.concurrency_entry.grid(row=0, column=8, padx=5, pady=8, sticky="ew")

    def setup_stats_frame(self):
        """إعداد إطار الإحصائيات"""
        self.stats_frame = ctk.CTkFrame(self.root, fg_color="#1a1f2b", height=80)
        self.stats_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        self.stats_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)
        
        # تسميات الإحصائيات
        self.stats_labels = {}
        stats_names = [
            ("Products Found", "products_found"),
            ("Products/Sec", "products_per_second"),
            ("Pages/Min", "pages_per_minute"),
            ("Alerts Sent", "alerts_sent"),
            ("Cache Size", "cache_size"),
            ("DB Size", "db_size")
        ]
        
        for i, (name, key) in enumerate(stats_names):
            frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
            frame.grid(row=0, column=i, padx=5, pady=10, sticky="ew")
            
            title = ctk.CTkLabel(frame, text=name, font=("Arial", 12, "bold"), text_color="#54fac8")
            title.pack()
            
            value = ctk.CTkLabel(frame, text="0", font=("Arial", 16, "bold"), text_color="#ffffff")
            value.pack()
            
            self.stats_labels[key] = value

    def setup_buttons(self):
        """إعداد الأزرار"""
        buttons_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        buttons_frame.grid(row=5, column=0, padx=10, pady=10, sticky="ew")
        buttons_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)

        btn_w, btn_h = 160, 45
        btn_font = ("Arial", 16, "bold")

        # أزرار التحكم الرئيسية
        self.start_btn = ctk.CTkButton(
            buttons_frame, text="🚀 Start Optimized", command=self.start_scraping,
            width=btn_w, height=btn_h, font=btn_font, fg_color="#54fac8", 
            hover_color="#12dafb", text_color="#111927"
        )
        self.start_btn.grid(row=0, column=0, padx=8, pady=8, sticky="ew")

        self.stop_btn = ctk.CTkButton(
            buttons_frame, text="⏹️ Stop", command=self.stop_scraping,
            width=btn_w, height=btn_h, font=btn_font, fg_color="#ff6b6b", 
            hover_color="#ff5252", text_color="#ffffff"
        )
        self.stop_btn.grid(row=0, column=1, padx=8, pady=8, sticky="ew")

        self.alerts_btn = ctk.CTkButton(
            buttons_frame, text="📢 View Alerts", command=self.open_alerts_window,
            width=btn_w, height=btn_h, font=btn_font, fg_color="#59ff9d", 
            hover_color="#12dafb", text_color="#111927"
        )
        self.alerts_btn.grid(row=0, column=2, padx=8, pady=8, sticky="ew")

        self.export_btn = ctk.CTkButton(
            buttons_frame, text="💾 Export", command=self.export_data,
            width=btn_w, height=btn_h, font=btn_font, fg_color="#12dafb", 
            hover_color="#59ff9d", text_color="#111927"
        )
        self.export_btn.grid(row=0, column=3, padx=8, pady=8, sticky="ew")

        self.clear_btn = ctk.CTkButton(
            buttons_frame, text="🧹 Clear Log", command=self.clear_log,
            width=btn_w, height=btn_h, font=btn_font, fg_color="#ffa726", 
            hover_color="#ff9800", text_color="#111927"
        )
        self.clear_btn.grid(row=0, column=4, padx=8, pady=8, sticky="ew")

        self.exit_btn = ctk.CTkButton(
            buttons_frame, text="❌ Exit", command=self.exit_app,
            width=btn_w, height=btn_h, font=btn_font, fg_color="#232d3a", 
            hover_color="#fa1a50", text_color="#59ff9d"
        )
        self.exit_btn.grid(row=0, column=5, padx=8, pady=8, sticky="ew")

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

    def update_stats(self):
        """تحديث الإحصائيات"""
        if self.scraper:
            stats = self.scraper.get_performance_stats()
            
            # تحديث التسميات
            self.stats_labels["products_found"].configure(
                text=str(stats['session']['products_found'])
            )
            self.stats_labels["products_per_second"].configure(
                text=f"{stats['performance']['products_per_second']:.1f}"
            )
            self.stats_labels["pages_per_minute"].configure(
                text=f"{stats['performance']['pages_per_minute']:.1f}"
            )
            self.stats_labels["alerts_sent"].configure(
                text=str(stats['session']['alerts_sent'])
            )
            self.stats_labels["cache_size"].configure(
                text=str(stats['performance']['cache_size'])
            )
            self.stats_labels["db_size"].configure(
                text=str(stats['database']['total_products'])
            )

    async def alert_callback(self, product, old_price, new_price, discount_percent):
        """معالج التنبيهات"""
        asin = product.asin
        key = f"{asin}-{int(new_price)}"
        
        if key in self.notified_asins:
            return
            
        self.notified_asins.add(key)
        
        # إضافة للتنبيهات
        self.alerts_data.append({
            "item": product.to_dict(),
            "old_price": old_price,
            "new_price": new_price,
            "discount_percent": discount_percent,
            "drop_detected": False
        })
        
        # إرسال تليجرام إذا كان مفعل
        if self.telegram_alerts_enabled:
            threading.Thread(
                target=send_telegram_alert, 
                args=(product.to_dict(), old_price, new_price, discount_percent, False), 
                daemon=True
            ).start()

    def progress_callback(self, page):
        """معالج التقدم"""
        # تحديث شريط التقدم (تقدير تقريبي)
        self.progress_bar.set(min(page / 100, 1.0))

    def scraper_wrapper(self, section, pages, all_pages, concurrency):
        """تشغيل السكرابر في حلقة async"""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            loop.run_until_complete(self.run_scraper(section, pages, all_pages, concurrency))
        except Exception as e:
            self.log(f"❌ Scraper error: {e}", "🚨")
        finally:
            self.running = False
            self.log("✅ Scraping completed", "🎉")

    async def run_scraper(self, section, pages, all_pages, concurrency):
        """تشغيل السكرابر المحسن"""
        async with OptimizedScraper(concurrency=concurrency) as scraper:
            self.scraper = scraper
            
            if all_pages:
                pages = 500
                
            if section == "All Sections":
                for sec_name, sec_url in CATEGORIES.items():
                    if self.stop_flag["stop"]:
                        break
                        
                    self.log(f"🎯 Starting section: {sec_name}", "🔍")
                    
                    await scraper.scrape_section_optimized(
                        section=sec_name,
                        base_url=sec_url,
                        start_page=1,
                        end_page=pages,
                        alert_callback=self.alert_callback,
                        progress_callback=self.progress_callback,
                        log_callback=self.log,
                        discount_threshold=self.ALERT_DISCOUNT,
                        stop_flag=self.stop_flag
                    )
                    
                    # تحديث الإحصائيات
                    self.root.after(0, self.update_stats)
            else:
                section_url = CATEGORIES[section]
                await scraper.scrape_section_optimized(
                    section=section,
                    base_url=section_url,
                    start_page=1,
                    end_page=pages,
                    alert_callback=self.alert_callback,
                    progress_callback=self.progress_callback,
                    log_callback=self.log,
                    discount_threshold=self.ALERT_DISCOUNT,
                    stop_flag=self.stop_flag
                )
                
                # تحديث الإحصائيات النهائية
                self.root.after(0, self.update_stats)

    def start_scraping(self):
        """بدء السكرابة"""
        if self.running:
            self.log("⚠️ Already running!", "🚨")
            return

        section = self.section_combo.get()
        all_pages = self.all_pages_chk.get()
        
        try:
            pages = int(self.pages_entry.get()) if not all_pages else 500
            concurrency = int(self.concurrency_entry.get())
        except ValueError:
            self.log("❌ Invalid input values", "🚨")
            return

        self.progress_bar.set(0.0)
        self.stop_flag["stop"] = False
        self.running = True
        self.alerts_data.clear()
        self.notified_asins.clear()

        self.log(f"🚀 Starting optimized scraping - Section: {section}, Pages: {pages}, Concurrency: {concurrency}", "🎯")

        # تشغيل السكرابر في thread منفصل
        scraper_thread = threading.Thread(
            target=self.scraper_wrapper, 
            args=(section, pages, all_pages, concurrency), 
            daemon=True
        )
        scraper_thread.start()

        # بدء تحديث الإحصائيات
        self.update_stats_periodically()

    def update_stats_periodically(self):
        """تحديث الإحصائيات بشكل دوري"""
        if self.running:
            self.update_stats()
            self.root.after(2000, self.update_stats_periodically)  # كل ثانيتين

    def stop_scraping(self):
        """إيقاف السكرابة"""
        self.stop_flag["stop"] = True
        self.log("🛑 Stopping scraper...", "⏹️")

    def open_alerts_window(self):
        """فتح نافذة التنبيهات"""
        if not self.alerts_data:
            self.log("📭 No alerts to show", "ℹ️")
            return
            
        # يمكن استخدام نافذة التنبيهات من الملف الأصلي
        self.log(f"📢 Found {len(self.alerts_data)} alerts", "🎉")

    def export_data(self):
        """تصدير البيانات"""
        if self.scraper:
            stats = self.scraper.get_performance_stats()
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "stats": stats,
                "alerts": self.alerts_data
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
                
            self.log(f"💾 Data exported to {filename}", "✅")

    def clear_log(self):
        """مسح السجل"""
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def exit_app(self):
        """إغلاق التطبيق"""
        self.stop_flag["stop"] = True
        if self.scraper:
            self.scraper.db.close()
        self.root.destroy()

    def run(self):
        """تشغيل التطبيق"""
        self.log("🎯 Optimized LAQTA started!", "🚀")
        self.log("💡 Features: Advanced caching, batch processing, SQLite DB, concurrent scraping", "ℹ️")
        self.root.mainloop()

if __name__ == "__main__":
    app = OptimizedApp()
    app.run()