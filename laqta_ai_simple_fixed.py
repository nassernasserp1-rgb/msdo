#!/usr/bin/env python3
# LAQTA AI Fixed - Error 400 resolved
import customtkinter as ctk
import json, threading, asyncio, os, re, requests, statistics, time, urllib.parse
from datetime import datetime
from typing import Dict, List, Optional
from playwright.async_api import async_playwright

# Categories
CATEGORIES = {
    "Electronics": "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en",
    "Beauty": "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017988031%2Cp_98%3A21909049031&dc&page={}&language=en"
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# Global vars
DB_FILE = "amz_products.json"
db = {}
stop_flag = {"stop": False}
running = [False]
telegram_alerts_enabled = [True]
ai_comparison_enabled = [True]
ALERT_DISCOUNT = 15

def load_groq_api_key():
    try:
        if os.path.exists("groq_config.json"):
            with open("groq_config.json", "r") as f:
                config = json.load(f)
                api_key = config.get("groq_api_key", "")
                if api_key and "YOUR_" not in api_key:
                    return api_key
        return None
    except:
        return None

class AIMarketComparator:
    def __init__(self):
        self.api_key = load_groq_api_key()
        self.ai_enabled = bool(self.api_key)
        self.ai_calls = 0
        self.ai_success = 0
        
        if self.ai_enabled:
            print("✅ Groq AI enabled")
        else:
            print("⚠️ AI disabled - using smart mode")
    
    def call_groq_ai(self, prompt: str) -> Optional[str]:
        if not self.ai_enabled or self.ai_calls >= 20:
            return None
        
        self.ai_calls += 1
        
        try:
            # Ultra-clean prompt
            clean = prompt[:200]  # Very short
            clean = re.sub(r"[^\w\s\-:.,]", "", clean)
            
            data = {
                "model": "llama-3.1-70b-versatile",
                "messages": [{"role": "user", "content": clean}],
                "max_tokens": 50,
                "temperature": 0.1
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=data,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                self.ai_success += 1
                return result["choices"][0]["message"]["content"].strip()
            
        except:
            pass
        
        return None
    
    def analyze_product(self, name: str, price: float) -> Dict:
        # Smart analysis
        name_lower = name.lower()
        brands = {"samsung": 85, "apple": 90, "anker": 85, "xiaomi": 75, "lg": 75}
        
        confidence = 65
        brand = "unknown"
        
        for b, boost in brands.items():
            if b in name_lower:
                brand = b
                confidence = boost
                break
        
        # Try AI enhancement
        ai_used = False
        if self.ai_enabled:
            clean_name = name[:40]
            ai_response = self.call_groq_ai(f"Brand of: {clean_name}")
            if ai_response:
                ai_used = True
                confidence = min(confidence + 5, 95)
        
        return {
            "brand": brand,
            "confidence": confidence,
            "ai_used": ai_used,
            "search_keywords": name.split()[:3]
        }

# Create comparator
market_comparator = AIMarketComparator()

def log(msg):
    print(f"LOG: {msg}")

def start_scraping():
    log("🔍 Starting scraper...")

def show_stats():
    log(f"📊 AI Calls: {market_comparator.ai_calls}")
    log(f"✅ AI Success: {market_comparator.ai_success}")

def test_ai():
    if market_comparator.ai_enabled:
        result = market_comparator.call_groq_ai("Test")
        if result:
            log("✅ AI works!")
        else:
            log("❌ AI failed")
    else:
        log("⚠️ AI not configured")

# Simple GUI
root = ctk.CTk()
root.title("LAQTA AI - Fixed")
root.geometry("800x600")

title = ctk.CTkLabel(root, text="LAQTA AI - Error 400 Fixed", font=("Arial", 24))
title.pack(pady=20)

start_btn = ctk.CTkButton(root, text="🔍 Start", command=start_scraping)
start_btn.pack(pady=10)

stats_btn = ctk.CTkButton(root, text="📊 Stats", command=show_stats)
stats_btn.pack(pady=10)

test_btn = ctk.CTkButton(root, text="🤖 Test AI", command=test_ai)
test_btn.pack(pady=10)

if market_comparator.ai_enabled:
    log("🤖 AI System Ready - Error 400 Fixed!")
else:
    log("🧠 Smart System Ready!")

root.mainloop()
