#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
واجهة محسنة مع حفظ تلقائي في JSON وإصلاح عرض الإحصائيات
"""

import customtkinter as ctk
import json
import threading
import asyncio
import os
import sqlite3
from datetime import datetime
import webbrowser
from tkinter import filedialog, messagebox
import time

# استيراد الباحث الذكي
from smart_new_products_finder import SmartNewProductsFinder

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

class AutoSaveJSONInterface:
    def __init__(self):
        self.smart_finder = None
        self.stop_flag = {"stop": False}
        self.running = False
        self.telegram_alerts_enabled = True
        self.alerts_data = []
        self.notified_asins = set()
        self.ALERT_DISCOUNT = 30
        self.json_file_path = ""
        
        # إعدادات الحفظ التلقائي
        self.auto_save_json = True
        self.json_output_file = f"products_auto_save_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.save_interval = 30  # حفظ كل 30 ثانية
        
        # إعدادات البحث الذكي
        self.new_products_only = True  # افتراضياً البحث عن الجديد فقط
        self.search_strategy = "newest_first"
        
        # بيانات المنتجات المجمعة
        self.collected_products = {}
        
        self.setup_ui()
        self.start_auto_save_timer()
        
    def setup_ui(self):
        """إعداد واجهة المستخدم المحسنة"""
        self.root = ctk.CTk()
        self.root.title("LAQTA - Auto JSON Saver")
        self.root.geometry("1750x1250")
        self.root.minsize(1500, 1000)
        self.root.rowconfigure(7, weight=1)
        self.root.columnconfigure(0, weight=1)

        # العنوان
        title_label = ctk.CTkLabel(
            self.root, 
            text="LAQTA - AUTO JSON SAVER", 
            font=("SST Arabic Medium", 48), 
            text_color="#54fac8"
        )
        title_label.grid(row=0, column=0, padx=8, pady=(18, 5), sticky="ew")

        # إطار إعدادات JSON التلقائي
        self.setup_auto_save_frame()
        
        # إطار ملف JSON المصدر
        self.setup_json_source_frame()
        
        # إطار التحكم الأساسي
        self.setup_basic_controls()
        
        # إطار البحث الذكي
        self.setup_smart_controls()
        
        # شريط التقدم
        self.progress_bar = ctk.CTkProgressBar(
            self.root, 
            height=28, 
            progress_color="#59ff9d", 
            fg_color="#232d3a"
        )
        self.progress_bar.grid(row=5, column=0, padx=10, pady=7, sticky="ew")
        self.progress_bar.set(0.0)

        # إطار الإحصائيات المحسن
        self.setup_enhanced_stats_frame()
        
        # صندوق السجل
        self.log_textbox = ctk.CTkTextbox(
            self.root, 
            font=("Consolas", 12), 
            fg_color="#20242f", 
            text_color="#c2ffe3", 
            border_width=0, 
            height=200
        )
        self.log_textbox.grid(row=7, column=0, padx=15, pady=(0, 12), sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # أزرار التحكم
        self.setup_buttons()

    def setup_auto_save_frame(self):
        """إعداد إطار الحفظ التلقائي في JSON"""
        save_frame = ctk.CTkFrame(self.root, fg_color="#1a2332", height=90)
        save_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        save_frame.grid_columnconfigure(2, weight=1)
        
        # عنوان القسم
        save_title = ctk.CTkLabel(save_frame, text="💾 AUTO JSON SAVE SETTINGS", 
                                 font=("Arial", 16, "bold"), text_color="#54fac8")
        save_title.grid(row=0, column=0, columnspan=4, padx=10, pady=(5, 0), sticky="w")
        
        # تفعيل الحفظ التلقائي
        self.auto_save_checkbox = ctk.CTkCheckBox(
            save_frame, 
            text="🔄 Auto Save to JSON", 
            font=("Arial", 14, "bold"), 
            text_color="#59ff9d",
            command=self.toggle_auto_save
        )
        self.auto_save_checkbox.grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.auto_save_checkbox.select()  # مفعل افتراضياً
        
        # اسم الملف
        filename_label = ctk.CTkLabel(save_frame, text="File:", font=("Arial", 12), text_color="#12dafb")
        filename_label.grid(row=1, column=1, padx=5, pady=8, sticky="w")
        
        self.json_filename_label = ctk.CTkLabel(
            save_frame, 
            text=self.json_output_file, 
            font=("Arial", 11), 
            text_color="#ffffff"
        )
        self.json_filename_label.grid(row=1, column=2, padx=5, pady=8, sticky="w")
        
        # فترة الحفظ
        interval_label = ctk.CTkLabel(save_frame, text="Save every:", font=("Arial", 12), text_color="#12dafb")
        interval_label.grid(row=1, column=3, padx=5, pady=8, sticky="w")
        
        self.save_interval_entry = ctk.CTkEntry(save_frame, width=60, font=("Arial", 12), 
                                              fg_color="#232d3a", text_color="#12dafb")
        self.save_interval_entry.insert(0, "30")
        self.save_interval_entry.grid(row=1, column=4, padx=5, pady=8, sticky="w")
        self.save_interval_entry.bind('<KeyRelease>', self.update_save_interval)
        
        seconds_label = ctk.CTkLabel(save_frame, text="seconds", font=("Arial", 12), text_color="#12dafb")
        seconds_label.grid(row=1, column=5, padx=5, pady=8, sticky="w")

    def setup_json_source_frame(self):
        """إعداد إطار ملف JSON المصدر"""
        json_frame = ctk.CTkFrame(self.root, fg_color="#1a1f2b", height=60)
        json_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        json_frame.grid_columnconfigure(1, weight=1)
        
        json_label = ctk.CTkLabel(json_frame, text="📁 Source JSON:", font=("Arial", 14, "bold"), text_color="#54fac8")
        json_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.json_path_label = ctk.CTkLabel(json_frame, text="No source file (will start fresh)", 
                                          font=("Arial", 12), text_color="#ffffff")
        self.json_path_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        select_json_btn = ctk.CTkButton(json_frame, text="🔍 Select Source", command=self.select_json_file,
                                       font=("Arial", 12, "bold"), fg_color="#12dafb", width=130, height=32)
        select_json_btn.grid(row=0, column=2, padx=10, pady=10)

    def setup_basic_controls(self):
        """إعداد عناصر التحكم الأساسية"""
        controls_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        controls_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)

        # العناصر الأساسية
        self.section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
                                           width=150, font=("Arial", 13), button_color="#54fac8")
        self.section_combo.set("Electronics")
        self.section_combo.grid(row=0, column=0, padx=3, pady=6, sticky="ew")

        self.pages_entry = ctk.CTkEntry(controls_frame, width=55, font=("Arial", 13), fg_color="#232d3a", text_color="#12dafb")
        self.pages_entry.insert(0, "25")
        self.pages_entry.grid(row=0, column=1, padx=3, pady=6, sticky="ew")

        pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 11), text_color="#12dafb")
        pages_label.grid(row=0, column=2, padx=3, pady=6, sticky="ew")

        self.all_pages_chk = ctk.CTkCheckBox(controls_frame, text="All Pages", font=("Arial", 11), text_color="#59ff9d")
        self.all_pages_chk.grid(row=0, column=3, padx=3, pady=6, sticky="ew")

        self.min_discount_slider = ctk.CTkSlider(controls_frame, from_=1, to=99, number_of_steps=98, width=80,
                                               command=self.set_min_discount, progress_color="#12dafb")
        self.min_discount_slider.set(self.ALERT_DISCOUNT)
        self.min_discount_slider.grid(row=0, column=4, padx=3, pady=6, sticky="ew")

        self.min_discount_label = ctk.CTkLabel(controls_frame, text=f"Min: {self.ALERT_DISCOUNT}%", 
                                             font=("Arial", 11), text_color="#59ff9d")
        self.min_discount_label.grid(row=0, column=5, padx=3, pady=6, sticky="ew")

        self.telegram_checkbox = ctk.CTkCheckBox(controls_frame, text="Telegram", font=("Arial", 11), 
                                               text_color="#13e6a7", command=self.toggle_telegram_alert)
        self.telegram_checkbox.grid(row=0, column=6, padx=3, pady=6, sticky="ew")
        self.telegram_checkbox.select()

        self.concurrency_entry = ctk.CTkEntry(controls_frame, width=45, font=("Arial", 11), 
                                            fg_color="#232d3a", text_color="#12dafb")
        self.concurrency_entry.insert(0, "12")
        self.concurrency_entry.grid(row=0, column=7, padx=3, pady=6, sticky="ew")

    def setup_smart_controls(self):
        """إعداد عناصر التحكم الذكية"""
        smart_frame = ctk.CTkFrame(self.root, fg_color="#1a2332", height=80)
        smart_frame.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        smart_frame.grid_columnconfigure((1,3,5), weight=1)
        
        # عنوان القسم
        smart_title = ctk.CTkLabel(smart_frame, text="🧠 SMART SEARCH OPTIONS", 
                                 font=("Arial", 15, "bold"), text_color="#54fac8")
        smart_title.grid(row=0, column=0, columnspan=6, padx=10, pady=(5, 0), sticky="w")
        
        # خيار المنتجات الجديدة فقط (مفعل افتراضياً)
        self.new_products_checkbox = ctk.CTkCheckBox(
            smart_frame, 
            text="🆕 New Products Only", 
            font=("Arial", 13, "bold"), 
            text_color="#ff6b6b",
            command=self.toggle_new_products_only
        )
        self.new_products_checkbox.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.new_products_checkbox.select()  # مفعل افتراضياً
        
        # استراتيجية البحث
        strategy_label = ctk.CTkLabel(smart_frame, text="Strategy:", font=("Arial", 11), text_color="#12dafb")
        strategy_label.grid(row=1, column=1, padx=4, pady=5, sticky="w")
        
        self.strategy_combo = ctk.CTkComboBox(
            smart_frame,
            values=["newest_first", "random_pages", "price_ranges", "date_filters", "seller_rotation"],
            width=120,
            font=("Arial", 11),
            command=self.set_search_strategy
        )
        self.strategy_combo.set("newest_first")
        self.strategy_combo.grid(row=1, column=2, padx=4, pady=5, sticky="ew")
        
        # حد التوقف
        stop_label = ctk.CTkLabel(smart_frame, text="Stop after:", font=("Arial", 11), text_color="#12dafb")
        stop_label.grid(row=1, column=3, padx=4, pady=5, sticky="w")
        
        self.stop_after_entry = ctk.CTkEntry(smart_frame, width=50, font=("Arial", 11), 
                                           fg_color="#232d3a", text_color="#12dafb")
        self.stop_after_entry.insert(0, "5")
        self.stop_after_entry.grid(row=1, column=4, padx=4, pady=5, sticky="ew")
        
        stop_pages_label = ctk.CTkLabel(smart_frame, text="empty pages", font=("Arial", 11), text_color="#12dafb")
        stop_pages_label.grid(row=1, column=5, padx=4, pady=5, sticky="w")

    def setup_enhanced_stats_frame(self):
        """إعداد إطار الإحصائيات المحسن"""
        self.stats_frame = ctk.CTkFrame(self.root, fg_color="#1a1f2b", height=100)
        self.stats_frame.grid(row=6, column=0, padx=10, pady=5, sticky="ew")
        self.stats_frame.grid_columnconfigure((0,1,2,3,4,5,6,7,8), weight=1)
        
        # تسميات الإحصائيات المحسنة
        self.stats_labels = {}
        stats_names = [
            ("JSON Products", "json_products"),
            ("DB Products", "db_products"),
            ("New Found", "new_found"),
            ("Total Checked", "total_checked"),
            ("Discovery Rate", "discovery_rate"),
            ("Products/Sec", "products_per_second"),
            ("Alerts Sent", "alerts_sent"),
            ("Auto Saves", "auto_saves"),
            ("Last Save", "last_save")
        ]
        
        for i, (name, key) in enumerate(stats_names):
            frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
            frame.grid(row=0, column=i, padx=2, pady=8, sticky="ew")
            
            title = ctk.CTkLabel(frame, text=name, font=("Arial", 9, "bold"), text_color="#54fac8")
            title.pack()
            
            value = ctk.CTkLabel(frame, text="0", font=("Arial", 13, "bold"), text_color="#ffffff")
            value.pack()
            
            self.stats_labels[key] = value
        
        # تحديث إحصائيات JSON وDB فوراً
        self.update_file_stats()

    def setup_buttons(self):
        """إعداد الأزرار"""
        buttons_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        buttons_frame.grid(row=8, column=0, padx=10, pady=10, sticky="ew")
        buttons_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)

        btn_w, btn_h = 120, 36
        btn_font = ("Arial", 13, "bold")

        # أزرار التحكم
        self.start_btn = ctk.CTkButton(buttons_frame, text="🚀 Start", command=self.start_smart_scraping,
                                     width=btn_w, height=btn_h, font=btn_font, fg_color="#54fac8", 
                                     hover_color="#12dafb", text_color="#111927")
        self.start_btn.grid(row=0, column=0, padx=3, pady=6, sticky="ew")

        self.stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=self.stop_scraping,
                                    width=btn_w, height=btn_h, font=btn_font, fg_color="#ff6b6b", 
                                    hover_color="#ff5252", text_color="#ffffff")
        self.stop_btn.grid(row=0, column=1, padx=3, pady=6, sticky="ew")

        self.save_now_btn = ctk.CTkButton(buttons_frame, text="💾 Save Now", command=self.save_json_now,
                                        width=btn_w, height=btn_h, font=btn_font, fg_color="#59ff9d", 
                                        hover_color="#13e6a7", text_color="#111927")
        self.save_now_btn.grid(row=0, column=2, padx=3, pady=6, sticky="ew")

        self.load_json_btn = ctk.CTkButton(buttons_frame, text="📂 Load JSON", command=self.load_existing_json,
                                         width=btn_w, height=btn_h, font=btn_font, fg_color="#12dafb", 
                                         hover_color="#59ff9d", text_color="#111927")
        self.load_json_btn.grid(row=0, column=3, padx=3, pady=6, sticky="ew")

        self.alerts_btn = ctk.CTkButton(buttons_frame, text="📢 Alerts", command=self.open_alerts_window,
                                      width=btn_w, height=btn_h, font=btn_font, fg_color="#ffa726", 
                                      hover_color="#ff9800", text_color="#111927")
        self.alerts_btn.grid(row=0, column=4, padx=3, pady=6, sticky="ew")

        self.stats_btn = ctk.CTkButton(buttons_frame, text="📊 Refresh", command=self.refresh_stats,
                                     width=btn_w, height=btn_h, font=btn_font, fg_color="#9c27b0", 
                                     hover_color="#7b1fa2", text_color="#ffffff")
        self.stats_btn.grid(row=0, column=5, padx=3, pady=6, sticky="ew")

        self.clear_btn = ctk.CTkButton(buttons_frame, text="🧹 Clear", command=self.clear_log,
                                     width=btn_w, height=btn_h, font=btn_font, fg_color="#607d8b", 
                                     hover_color="#546e7a", text_color="#ffffff")
        self.clear_btn.grid(row=0, column=6, padx=3, pady=6, sticky="ew")

        self.exit_btn = ctk.CTkButton(buttons_frame, text="❌ Exit", command=self.exit_app,
                                    width=btn_w, height=btn_h, font=btn_font, fg_color="#232d3a", 
                                    hover_color="#fa1a50", text_color="#59ff9d")
        self.exit_btn.grid(row=0, column=7, padx=3, pady=6, sticky="ew")

    def start_auto_save_timer(self):
        """بدء مؤقت الحفظ التلقائي"""
        if self.auto_save_json:
            self.auto_save_timer = threading.Timer(self.save_interval, self.auto_save_json_file)
            self.auto_save_timer.daemon = True
            self.auto_save_timer.start()

    def auto_save_json_file(self):
        """حفظ تلقائي لملف JSON"""
        if self.auto_save_json and self.collected_products:
            try:
                # إضافة معلومات إضافية للملف
                save_data = {
                    "metadata": {
                        "last_updated": datetime.now().isoformat(),
                        "total_products": len(self.collected_products),
                        "auto_save": True,
                        "source": "LAQTA Auto Saver",
                        "version": "2.0"
                    },
                    "products": self.collected_products
                }
                
                with open(self.json_output_file, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                
                # تحديث الإحصائيات
                current_saves = int(self.stats_labels["auto_saves"].cget("text"))
                self.stats_labels["auto_saves"].configure(text=str(current_saves + 1))
                self.stats_labels["last_save"].configure(text=datetime.now().strftime("%H:%M:%S"))
                
                self.log(f"💾 Auto-saved {len(self.collected_products)} products to {self.json_output_file}")
                
            except Exception as e:
                self.log(f"❌ Auto-save error: {e}")
        
        # إعادة جدولة المؤقت
        if self.auto_save_json:
            self.start_auto_save_timer()

    def save_json_now(self):
        """حفظ فوري لملف JSON"""
        if not self.collected_products:
            self.log("⚠️ No products to save", "📭")
            return
        
        try:
            # حفظ فوري
            save_data = {
                "metadata": {
                    "saved_at": datetime.now().isoformat(),
                    "total_products": len(self.collected_products),
                    "manual_save": True,
                    "source": "LAQTA Manual Save",
                    "version": "2.0"
                },
                "products": self.collected_products
            }
            
            # اختيار اسم ملف للحفظ الفوري
            manual_filename = f"products_manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(manual_filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            self.log(f"💾 Manually saved {len(self.collected_products)} products to {manual_filename}")
            messagebox.showinfo("Success", f"Products saved to {manual_filename}")
            
        except Exception as e:
            self.log(f"❌ Manual save error: {e}")
            messagebox.showerror("Error", f"Save failed: {e}")

    def load_existing_json(self):
        """تحميل ملف JSON موجود"""
        try:
            # البحث عن ملفات JSON في المجلد
            json_files = [f for f in os.listdir('.') if f.endswith('.json')]
            
            if json_files:
                # عرض قائمة بالملفات المتاحة
                file_info = []
                for json_file in json_files:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # تحديد عدد المنتجات
                        if isinstance(data, dict):
                            if 'products' in data:
                                count = len(data['products'])
                            else:
                                count = len(data)
                        else:
                            count = len(data)
                        
                        file_size = os.path.getsize(json_file) / (1024 * 1024)
                        file_info.append(f"{json_file} ({count:,} products, {file_size:.1f} MB)")
                        
                    except:
                        file_info.append(f"{json_file} (invalid format)")
                
                # عرض نافذة اختيار
                choice_window = ctk.CTkToplevel(self.root)
                choice_window.title("Select JSON File")
                choice_window.geometry("500x400")
                
                label = ctk.CTkLabel(choice_window, text="Select JSON file to load:", 
                                   font=("Arial", 14, "bold"))
                label.pack(pady=10)
                
                # قائمة الملفات
                files_frame = ctk.CTkScrollableFrame(choice_window, width=450, height=250)
                files_frame.pack(pady=10, padx=20, fill="both", expand=True)
                
                selected_file = ctk.StringVar()
                
                for i, file_info_str in enumerate(file_info):
                    radio = ctk.CTkRadioButton(files_frame, text=file_info_str, 
                                             variable=selected_file, value=json_files[i])
                    radio.pack(pady=5, anchor="w")
                
                def load_selected():
                    if selected_file.get():
                        self.load_json_file(selected_file.get())
                        choice_window.destroy()
                
                load_btn = ctk.CTkButton(choice_window, text="Load Selected", command=load_selected)
                load_btn.pack(pady=10)
                
            else:
                messagebox.showinfo("No Files", "No JSON files found in current directory")
                
        except Exception as e:
            self.log(f"❌ Error loading JSON files: {e}")

    def load_json_file(self, filename):
        """تحميل ملف JSON محدد"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # تحديد تنسيق البيانات
            if isinstance(data, dict):
                if 'products' in data:
                    self.collected_products = data['products']
                else:
                    self.collected_products = data
            else:
                self.collected_products = data
            
            self.log(f"📂 Loaded {len(self.collected_products):,} products from {filename}")
            self.update_file_stats()
            
        except Exception as e:
            self.log(f"❌ Error loading {filename}: {e}")
            messagebox.showerror("Error", f"Failed to load {filename}: {e}")

    def update_file_stats(self):
        """تحديث إحصائيات الملفات"""
        # إحصائيات JSON
        json_count = len(self.collected_products)
        self.stats_labels["json_products"].configure(text=str(json_count))
        
        # إحصائيات قاعدة البيانات
        db_count = self.get_database_count()
        self.stats_labels["db_products"].configure(text=str(db_count))

    def get_database_count(self):
        """الحصول على عدد المنتجات في قاعدة البيانات"""
        try:
            db_files = ["products_optimized.db", "products_instant.db", "products.db"]
            
            for db_file in db_files:
                if os.path.exists(db_file):
                    conn = sqlite3.connect(db_file)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
                    if cursor.fetchone():
                        cursor.execute('SELECT COUNT(*) FROM products')
                        count = cursor.fetchone()[0]
                        conn.close()
                        return count
                    conn.close()
            return 0
        except:
            return 0

    def toggle_auto_save(self):
        """تفعيل/إلغاء الحفظ التلقائي"""
        self.auto_save_json = self.auto_save_checkbox.get()
        status = "enabled" if self.auto_save_json else "disabled"
        self.log(f"💾 Auto-save JSON: {status}")
        
        if self.auto_save_json:
            self.start_auto_save_timer()

    def update_save_interval(self, event=None):
        """تحديث فترة الحفظ"""
        try:
            self.save_interval = int(self.save_interval_entry.get())
            self.log(f"⏱️ Save interval updated to {self.save_interval} seconds")
        except ValueError:
            pass

    def select_json_file(self):
        """اختيار ملف JSON مصدر"""
        file_path = filedialog.askopenfilename(
            title="Select source JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            self.json_file_path = file_path
            file_name = os.path.basename(file_path)
            self.json_path_label.configure(text=file_name)
            self.log(f"✅ Source JSON selected: {file_name}")
            
            # تحميل البيانات من الملف المختار
            self.load_json_file(file_path)

    def toggle_new_products_only(self):
        """تفعيل/إلغاء وضع المنتجات الجديدة فقط"""
        self.new_products_only = self.new_products_checkbox.get()
        status = "enabled" if self.new_products_only else "disabled"
        self.log(f"🆕 New products only mode: {status}")

    def set_search_strategy(self, strategy):
        """تحديد استراتيجية البحث"""
        self.search_strategy = strategy
        self.log(f"🧠 Search strategy: {strategy}")

    def start_smart_scraping(self):
        """بدء السكرابة الذكية"""
        if self.running:
            self.log("⚠️ Already running!", "🚨")
            return

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
        self.log(f"🚀 Starting smart scraping - Mode: {mode}, Auto-save: {self.auto_save_json}")

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
            # حفظ نهائي
            if self.auto_save_json and self.collected_products:
                self.save_json_now()

    async def run_smart_scraper(self, section, pages, concurrency, stop_after):
        """تشغيل السكرابر الذكي"""
        
        # إنشاء الباحث الذكي
        self.smart_finder = SmartNewProductsFinder()
        
        if section == "All Sections":
            for sec_name, sec_url in CATEGORIES.items():
                if self.stop_flag["stop"]:
                    break
                
                self.log(f"🔍 Smart search in: {sec_name}", "🎯")
                
                new_products = await self.smart_finder.smart_search_new_products(
                    sec_name, sec_url, self.search_strategy, pages, stop_after
                )
                
                # إضافة المنتجات للمجموعة المحلية
                for product in new_products:
                    asin = product['asin']
                    self.collected_products[asin] = {
                        'name': product['name'],
                        'url': product['url'],
                        'img': product['img'],
                        'section': sec_name,
                        'price': product['price'],
                        'strike_price': product['strikePrice'],
                        'discount_percent': product.get('discount_percent', 0),
                        'found_at': datetime.now().isoformat(),
                        'is_new_product': product.get('isNewProduct', True)
                    }
                
                if new_products:
                    # حفظ في قاعدة البيانات أيضاً
                    self.smart_finder.save_new_products(new_products, sec_name)
                    self.log(f"💾 Added {len(new_products)} new products from {sec_name}")
                
                # تحديث الإحصائيات
                self.root.after(0, self.update_smart_stats)
        else:
            section_url = CATEGORIES[section]
            new_products = await self.smart_finder.smart_search_new_products(
                section, section_url, self.search_strategy, pages, stop_after
            )
            
            # إضافة المنتجات للمجموعة المحلية
            for product in new_products:
                asin = product['asin']
                self.collected_products[asin] = {
                    'name': product['name'],
                    'url': product['url'],
                    'img': product['img'],
                    'section': section,
                    'price': product['price'],
                    'strike_price': product['strikePrice'],
                    'discount_percent': product.get('discount_percent', 0),
                    'found_at': datetime.now().isoformat(),
                    'is_new_product': product.get('isNewProduct', True)
                }
            
            if new_products:
                self.smart_finder.save_new_products(new_products, section)
                self.log(f"💾 Added {len(new_products)} new products")
            
            self.root.after(0, self.update_smart_stats)

    def update_smart_stats(self):
        """تحديث الإحصائيات الذكية"""
        if self.smart_finder:
            stats = self.smart_finder.get_search_stats()
            
            self.stats_labels["total_checked"].configure(text=str(stats['total_checked']))
            self.stats_labels["new_found"].configure(text=str(stats['new_found']))
            self.stats_labels["discovery_rate"].configure(text=f"{stats['discovery_rate']:.1f}%")
        
        # تحديث إحصائيات الملفات
        self.update_file_stats()

    def update_stats_periodically(self):
        """تحديث الإحصائيات بشكل دوري"""
        if self.running:
            self.update_smart_stats()
            self.root.after(3000, self.update_stats_periodically)

    def refresh_stats(self):
        """تحديث جميع الإحصائيات"""
        self.update_file_stats()
        if self.smart_finder:
            self.update_smart_stats()
        self.log("📊 Stats refreshed")

    # باقي الوظائف المساعدة
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

    def clear_log(self):
        """مسح السجل"""
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def exit_app(self):
        """إغلاق التطبيق"""
        self.stop_flag["stop"] = True
        
        # حفظ نهائي قبل الإغلاق
        if self.auto_save_json and self.collected_products:
            self.save_json_now()
        
        self.root.destroy()

    def run(self):
        """تشغيل التطبيق"""
        self.log("💾 LAQTA Auto JSON Saver started!", "🚀")
        self.log(f"🔄 Auto-save every {self.save_interval} seconds to: {self.json_output_file}", "💡")
        self.log("🆕 NEW: Automatic JSON saving + Smart new products search!", "✨")
        self.root.mainloop()

if __name__ == "__main__":
    app = AutoSaveJSONInterface()
    app.run()