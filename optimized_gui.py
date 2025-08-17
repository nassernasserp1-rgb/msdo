import customtkinter as ctk
import json
import threading
import asyncio
import os
from datetime import datetime
from optimized_scraper import OptimizedScraper
from categories import CATEGORIES
import re
from PIL import Image
import requests
from io import BytesIO
import webbrowser
import concurrent.futures

# استيراد بوت التليجرام
from telegram_bot import send_telegram_alert

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

DB_FILE = "amz_products_optimized.json"
db = {}
stop_flag = {"stop": False}
scrape_thread = None
running = [False]
telegram_alerts_enabled = [True]
scraper_instance = None

ALERT_DISCOUNT = 30
alerts_data = []
notified_asins = set()

DISCOUNT_TAGS = [
    (90, "🔥", "#ff1a36"),
    (80, "💥", "#ff3e8a"),
    (70, "🎉", "#ff7f50"),
    (60, "✨", "#ffdf30"),
    (50, "⭐", "#00f7c2"),
    (40, "🔔", "#19c8fa"),
    (30, "⚡", "#77ff3b"),
]
DROP_TAG = ("🚨", "#ffbf00")

def load_db():
    global db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    else:
        db = {}

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def log(msg, emoji=""):
    msg_no_links = re.sub(r'https?://\S+|www\.\S+', '', msg).strip()
    if not msg_no_links:
        return
    log_textbox.configure(state="normal")
    log_textbox.insert("end", f"{emoji} {msg_no_links}\n")
    log_textbox.see("end")
    log_textbox.configure(state="disabled")

def export_csv():
    with open("products_export_optimized.csv", "w", encoding="utf-8", newline="") as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Last Price", "Discount %"])
        for asin, item in db.items():
            writer.writerow([
                asin, 
                item["name"], 
                item["section"], 
                item["url"], 
                item["img"], 
                item["price"],
                item.get("discount_percent", "")
            ])
    log("Exported to CSV.", "📁")

def update_progress(val):
    progress_bar.set(val)

def get_discount_tag(discount_percent):
    for level, icon, color in DISCOUNT_TAGS:
        if discount_percent >= level:
            return icon, color
    return "⚡", "#47ffd1"

def add_alert_data(item, old_price, new_price, discount_percent, drop_detected=False):
    asin = item.get("asin")
    key = f"{asin}-{int(new_price)}"
    if key in notified_asins:
        return
    notified_asins.add(key)
    alerts_data.append({
        "item": item,
        "old_price": old_price,
        "new_price": new_price,
        "discount_percent": discount_percent,
        "drop_detected": drop_detected
    })
    # إرسال على تليجرام لو متفعّل
    if telegram_alerts_enabled[0]:
        threading.Thread(target=send_telegram_alert, args=(item, old_price, new_price, discount_percent, drop_detected), daemon=True).start()

# ==== شاشة المنتجات المحسنة ====
class OptimizedAlertsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Optimized Alerts / Products")
        self.configure(bg="#232d3a")
        self.minsize(900, 450)
        self.geometry("1300x730")
        self.page = 0
        self._last_cols = None
        self._img_cache = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)

        self.outer_frame = ctk.CTkFrame(self, fg_color="#232d3a")
        self.outer_frame.pack(expand=True, fill="both", padx=16, pady=16)
        self.outer_frame.grid_rowconfigure(0, weight=1)
        self.outer_frame.grid_columnconfigure(0, weight=1)

        self.main_canvas = ctk.CTkCanvas(self.outer_frame, bg="#232d3a", highlightthickness=0)
        self.main_canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ctk.CTkScrollbar(self.outer_frame, orientation="vertical", command=self.main_canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.cards_frame = ctk.CTkFrame(self.main_canvas, fg_color="#232d3a")
        self.main_canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")

        # إضافة إحصائيات سريعة
        stats_frame = ctk.CTkFrame(self, fg_color="#232d3a")
        stats_frame.pack(side="top", fill="x", pady=(0, 10))
        
        self.stats_label = ctk.CTkLabel(
            stats_frame, 
            text=f"📊 Total Products: {len(db)} | 🚨 Alerts: {len(alerts_data)}", 
            font=("Arial", 16, "bold"), 
            text_color="#54fac8"
        )
        self.stats_label.pack(pady=5)

        pag_frame = ctk.CTkFrame(self, fg_color="#232d3a")
        pag_frame.pack(side="bottom", fill="x", pady=(0,16))
        self.prev_btn = ctk.CTkButton(pag_frame, text="⬅ Prev", font=("Arial", 17, "bold"),
                                      command=self.prev_page, width=120, fg_color="#54fac8", text_color="#232d3a")
        self.prev_btn.pack(side="left", padx=12, pady=5)
        self.page_lbl = ctk.CTkLabel(pag_frame, text="", font=("Arial", 18, "bold"), text_color="#6cfbc8")
        self.page_lbl.pack(side="left", padx=6)
        self.next_btn = ctk.CTkButton(pag_frame, text="Next ➡", font=("Arial", 17, "bold"),
                                      command=self.next_page, width=120, fg_color="#54fac8", text_color="#232d3a")
        self.next_btn.pack(side="left", padx=12, pady=5)

        self.bind("<Configure>", self._on_resize)
        self.after(100, self.refresh)

    def _on_resize(self, event=None):
        cols = self.get_dynamic_cols()
        if cols != self._last_cols:
            self._last_cols = cols
            self.after(10, self.refresh)
        self.cards_frame.update_idletasks()
        self.main_canvas.config(scrollregion=self.main_canvas.bbox("all"))

    def get_dynamic_cols(self):
        w = self.winfo_width()
        if w < 700:
            return 1
        elif w < 1050:
            return 2
        elif w < 1500:
            return 3
        else:
            return 4

    def render_alert_card(self, data, idx_in_page, cols, card_size):
        item = data["item"]
        old_price = data["old_price"]
        new_price = data["new_price"]
        discount_percent = data["discount_percent"]
        drop_detected = data["drop_detected"]

        if drop_detected:
            icon, color = DROP_TAG
            label_title = "Sudden Price Drop!"
        else:
            icon, color = get_discount_tag(discount_percent)
            label_title = f"{icon}  {discount_percent:.1f}% OFF"

        card = ctk.CTkFrame(
            self.cards_frame,
            fg_color="#222a34",
            border_width=3,
            border_color=color,
            corner_radius=18,
            width=card_size,
            height=card_size,
        )
        row, col = divmod(idx_in_page, cols)
        card.grid(row=row, column=col, padx=18, pady=16, sticky="nsew")

        img_side = min(110, card_size-30)
        img_frame = ctk.CTkFrame(card, fg_color="transparent", width=img_side, height=img_side)
        img_frame.pack(side="left", padx=(16, 8), pady=16)
        img_frame.pack_propagate(False)

        img_label = ctk.CTkLabel(img_frame, text="Loading...", font=("Arial", 10), width=img_side, height=img_side)
        img_label.pack(expand=True, fill="both")

        def load_img():
            url = item.get("img")
            if not url:
                img_label.after(0, lambda: img_label.configure(text="No Image", image=""))
                return
            if url in self._img_cache:
                ctk_img = self._img_cache[url]
                img_label.after(0, lambda: (img_label.configure(image=ctk_img, text=""), setattr(img_label, "image", ctk_img)))
                return
            try:
                r = requests.get(url, timeout=6)
                pil_img = Image.open(BytesIO(r.content)).resize((img_side, img_side))
                ctk_img = ctk.CTkImage(dark_image=pil_img, size=(img_side, img_side))
                self._img_cache[url] = ctk_img
                img_label.after(0, lambda: (img_label.configure(image=ctk_img, text=""), setattr(img_label, "image", ctk_img)))
            except Exception:
                img_label.after(0, lambda: img_label.configure(text="No Image", image=""))
        self._executor.submit(load_img)

        right_frame = ctk.CTkFrame(card, fg_color="transparent", width=card_size-img_side-40)
        right_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        right_frame.pack_propagate(False)

        title = item["name"][:58] + ("..." if len(item["name"]) > 58 else "")
        title_label = ctk.CTkLabel(
            right_frame, text=title,
            font=("Arial Black", 16, "bold"), text_color="#41ffe0",
            anchor="w", wraplength=card_size-img_side-60, justify="left"
        )
        title_label.pack(pady=(4, 2), anchor="w")

        price_row = ctk.CTkFrame(right_frame, fg_color="transparent")
        price_row.pack(anchor="w", pady=(2, 0), fill="x")
        old_label = ctk.CTkLabel(
            price_row,
            text=f"🔻 {int(old_price):,} EGP",
            font=("Arial", 16, "bold"),
            text_color="#fe8989"
        )
        old_label.pack(side="left", padx=(0, 9))
        new_label = ctk.CTkLabel(
            price_row,
            text=f"💰 {int(new_price):,} EGP",
            font=("Arial", 18, "bold"),
            text_color="#b9ffa3"
        )
        new_label.pack(side="left", padx=(0, 8))

        disc_label = ctk.CTkLabel(
            right_frame,
            text=label_title,
            font=("Arial Black", 17, "bold"),
            text_color=color,
            anchor="w"
        )
        disc_label.pack(pady=(2, 5), anchor="w")

        url = item.get("url")
        btn = ctk.CTkButton(
            right_frame,
            text="Open Product 🔗",
            fg_color=color,
            hover_color="#444",
            text_color="#232d3a",
            font=("Arial", 15, "bold"),
            width=140, height=36,
            command=lambda: webbrowser.open(url)
        )
        btn.pack(anchor="e", pady=(11, 6), padx=10, side="right")

    def refresh(self):
        for w in self.cards_frame.winfo_children():
            w.destroy()
        cols = self.get_dynamic_cols()
        card_size = int((self.winfo_width() - (cols+1)*40) / cols) if cols > 0 else 340
        PAGE_SIZE = cols * 3
        page = self.page
        total_pages = max(1, ((len(alerts_data) - 1) // PAGE_SIZE) + 1)
        self.page = max(0, min(page, total_pages - 1))
        start = self.page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_data = alerts_data[start:end]

        if not page_data:
            empty_lbl = ctk.CTkLabel(self.cards_frame, text="No alerts to show.", font=("Arial", 18), text_color="#54fac8")
            empty_lbl.pack(pady=60)
        else:
            for idx, alert in enumerate(page_data):
                self.render_alert_card(alert, idx, cols, card_size)

        self.page_lbl.configure(text=f"Page {self.page+1} of {total_pages}")
        self.prev_btn.configure(state="normal" if self.page > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.page < total_pages-1 else "disabled")
        
        # تحديث الإحصائيات
        self.stats_label.configure(text=f"📊 Total Products: {len(db)} | 🚨 Alerts: {len(alerts_data)}")
        
        self.cards_frame.update_idletasks()
        self.main_canvas.config(scrollregion=self.main_canvas.bbox("all"))

    def next_page(self):
        self.page += 1
        self.refresh()

    def prev_page(self):
        self.page -= 1
        self.refresh()

def open_alerts_window():
    OptimizedAlertsWindow(root)

# ----------------------------- سلايدر التحكم في نسبة الخصم -----------------------
def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min Discount: {ALERT_DISCOUNT}%")
    log(f"🔔 Minimum discount for alerts set to {ALERT_DISCOUNT}%", "⚡")

# ---------------------------------------------------------------------------------

async def optimized_scraper_func(section, pages, all_pages):
    global scraper_instance, db
    scraper_instance = OptimizedScraper()
    await scraper_instance.init_session()
    await scraper_instance.create_browser_pool()
    
    notified_asins.clear()
    alerts_data.clear()
    
    def alert_callback(item, old_price, new_price, discount_percent, drop_detected=False):
        add_alert_data(item, old_price, new_price, discount_percent, drop_detected=drop_detected)
    
    try:
        if all_pages:
            pages = 500
        
        if section == "All Sections":
            for sec in list(CATEGORIES.keys()):
                log(f"🚀 Optimized scraping section: {sec}", "🟢")
                section_url = CATEGORIES[sec]
                await scraper_instance.scrape_section_optimized(
                    sec, section_url, 1, pages, db,
                    log_fn=lambda m: log(m, "🟢"),
                    progress_fn=lambda pn: update_progress(pn / pages),
                    stop_flag=stop_flag,
                    discount_alert_cb=alert_callback,
                    discount_threshold=ALERT_DISCOUNT
                )
        else:
            section_url = CATEGORIES[section]
            await scraper_instance.scrape_section_optimized(
                section, section_url, 1, pages, db,
                log_fn=lambda m: log(m, "🟢"),
                progress_fn=lambda pn: update_progress(pn / pages),
                stop_flag=stop_flag,
                discount_alert_cb=alert_callback,
                discount_threshold=ALERT_DISCOUNT
            )
        
        # حفظ قاعدة البيانات النهائية
        await scraper_instance.save_db_async()
        db.update(scraper_instance.db)  # تحديث قاعدة البيانات المحلية
        
    finally:
        await scraper_instance.cleanup()
    
    log("✅ Optimized scraping completed!")
    running[0] = False

def start_optimized_scraping():
    if running[0]:
        log("Already running.", "⚠️")
        return
    section = section_combo.get()
    all_pages = all_pages_chk.get()
    pages = int(pages_entry.get()) if not all_pages else 9999
    progress_bar.set(0.0)
    stop_flag["stop"] = False
    running[0] = True
    global scrape_thread
    scrape_thread = threading.Thread(
        target=lambda: asyncio.run(optimized_scraper_func(section, pages, all_pages)), 
        daemon=True
    )
    scrape_thread.start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Stopped.")

def show_stats():
    log(f"🔢 Total Products: {len(db)}")
    log(f"📊 Scraper Stats: {scraper_instance.stats if scraper_instance else 'N/A'}")

def resume_scraping():
    load_db()
    log("📦 Database loaded.")
    show_stats()

def exit_app():
    stop_flag["stop"] = True
    save_db()
    root.destroy()

def clear_log():
    log_textbox.configure(state="normal")
    log_textbox.delete("1.0", "end")
    log_textbox.configure(state="disabled")

# ==== MAIN ROOT ====
root = ctk.CTk()
root.title("LAQTA - Optimized Amazon Product Hunter")
root.geometry("1400x980")
root.minsize(1100, 700)
root.rowconfigure(3, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA OPTIMIZED", font=("SST Arabic Medium", 75), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(18, 5), sticky="ew")

controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=1, column=0, padx=10, pady=7, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)

section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
    width=260, font=("Arial", 18), button_color="#54fac8")
section_combo.set("Electronics")
section_combo.grid(row=0, column=0, padx=8, pady=8, sticky="ew")

pages_entry = ctk.CTkEntry(controls_frame, width=120, font=("Arial", 18), fg_color="#232d3a", text_color="#12dafb")
pages_entry.insert(0, "5")
pages_entry.grid(row=0, column=1, padx=8, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages per section", font=("Arial", 18), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=8, pady=8, sticky="ew")

all_pages_chk = ctk.CTkCheckBox(controls_frame, text="All Pages", font=("Arial", 17), text_color="#59ff9d")
all_pages_chk.grid(row=0, column=3, padx=10, pady=8, sticky="ew")

# ===== Checkbox للتحكم في إشعارات التليجرام =====
def toggle_telegram_alert():
    telegram_alerts_enabled[0] = not telegram_alerts_enabled[0]
telegram_checkbox = ctk.CTkCheckBox(controls_frame, text="Send to Telegram", font=("Arial", 17), text_color="#13e6a7",
    command=toggle_telegram_alert)
telegram_checkbox.grid(row=0, column=5, padx=10, pady=8, sticky="ew")
telegram_checkbox.select()  # افتراضياً مفعلة

# ------------ سلايدر التحكم في نسبة الخصم ------------------
min_discount_slider = ctk.CTkSlider(
    controls_frame, from_=1, to=99, number_of_steps=98, width=170,
    command=set_min_discount, progress_color="#12dafb"
)
min_discount_slider.set(ALERT_DISCOUNT)
min_discount_slider.grid(row=0, column=4, padx=10, pady=8, sticky="ew")
min_discount_label = ctk.CTkLabel(
    controls_frame, text=f"Min Discount: {ALERT_DISCOUNT}%", font=("Arial", 16), text_color="#59ff9d"
)
min_discount_label.grid(row=0, column=7, padx=6, pady=8, sticky="ew")
# ------------------------------------------------------------

open_alerts_btn = ctk.CTkButton(controls_frame, text="Show Alerts / Products 📢", font=("Arial", 17, "bold"),
    command=open_alerts_window, fg_color="#59ff9d", hover_color="#13e6a7", text_color="#232d3a", width=190, height=50)
open_alerts_btn.grid(row=0, column=6, padx=8, pady=8, sticky="ew")

progress_bar = ctk.CTkProgressBar(root, height=22, progress_color="#59ff9d", fg_color="#232d3a")
progress_bar.grid(row=2, column=0, padx=10, pady=7, sticky="ew")
progress_bar.set(0.0)

log_textbox = ctk.CTkTextbox(root, font=("Consolas", 16), fg_color="#20242f", text_color="#c2ffe3", border_width=0, height=190)
log_textbox.grid(row=3, column=0, padx=15, pady=(0, 12), sticky="nsew")
log_textbox.configure(state="disabled")

buttons_frame = ctk.CTkFrame(root, fg_color="transparent")
buttons_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
buttons_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)

btn_w, btn_h = 185, 48
btn_font = ("Arial", 20, "bold")

start_btn = ctk.CTkButton(buttons_frame, text="Start Optimized 🚀", command=start_optimized_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
start_btn.grid(row=0, column=0, padx=8, pady=8, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="Stop ✋", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#12dafb", hover_color="#54fac8", text_color="#111927")
stop_btn.grid(row=0, column=1, padx=8, pady=8, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="Resume 🔁", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#59ff9d", hover_color="#12dafb", text_color="#111927")
resume_btn.grid(row=0, column=2, padx=8, pady=8, sticky="ew")

export_btn = ctk.CTkButton(buttons_frame, text="Export CSV 📁", command=export_csv, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#12dafb", hover_color="#59ff9d", text_color="#111927")
export_btn.grid(row=0, column=3, padx=8, pady=8, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="Stats 📊", command=show_stats, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#59ff9d", hover_color="#54fac8", text_color="#111927")
stats_btn.grid(row=0, column=4, padx=8, pady=8, sticky="ew")

clear_btn = ctk.CTkButton(buttons_frame, text="Clear Log 🧹", command=clear_log, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
clear_btn.grid(row=0, column=5, padx=8, pady=8, sticky="ew")

exit_btn = ctk.CTkButton(root, text="Exit ❌", command=exit_app, width=400, height=60,
    font=("Arial Black", 26), fg_color="#232d3a", hover_color="#fa1a50", text_color="#59ff9d")
exit_btn.grid(row=5, column=0, pady=(10, 14))

load_db()
root.mainloop()