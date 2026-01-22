#!/usr/bin/env python3
"""
Marketplace Monitor v2 - Cloud Edition
Automated deal hunting for diabetic supplies and phones
NYC/NJ Area Focus
"""

import feedparser
import smtplib
import time
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
MONITOR_EMAIL = os.getenv('MONITOR_EMAIL', 'your_email@gmail.com')
MONITOR_EMAIL_PASSWORD = os.getenv('MONITOR_EMAIL_PASSWORD', 'your_app_password')
MONITOR_RECIPIENT = os.getenv('MONITOR_RECIPIENT', 'your_email@gmail.com')

# Craigslist cities to monitor (NYC/NJ area)
CRAIGSLIST_CITIES = [
    "newyork",      # NYC
    "newjersey",    # New Jersey
    "longisland",   # Long Island
    "connecticut",  # Connecticut
]

# Search keywords for diabetic supplies and phones
SEARCH_KEYWORDS = {
    # Diabetic supplies
    "dexcom_g6": "Dexcom G6",
    "dexcom_g7": "Dexcom G7",
    "omnipod_5": "Omnipod 5",
    "omnipod_dash": "Omnipod DASH",
    "freestyle_libre": "Freestyle Libre",
    "test_strips": "Test Strips",
    "glucose_monitor": "Glucose Monitor",
    # Phones
    "iphone_15": "iPhone 15",
    "iphone_14_pro": "iPhone 14 Pro",
    "iphone_13_pro": "iPhone 13 Pro",
    "samsung_s23": "Samsung S23",
    "pixel_8": "Pixel 8",
    "oneplus_12": "OnePlus 12",
}

# Pricing targets (max buy price to achieve target margin)
PRICING_TARGETS = {
    "dexcom_g6": {"max_buy": 35, "resale_avg": 90, "margin": 0.60},
    "dexcom_g7": {"max_buy": 40, "resale_avg": 100, "margin": 0.60},
    "omnipod_5": {"max_buy": 50, "resale_avg": 120, "margin": 0.58},
    "omnipod_dash": {"max_buy": 45, "resale_avg": 110, "margin": 0.59},
    "freestyle_libre": {"max_buy": 25, "resale_avg": 65, "margin": 0.62},
    "test_strips": {"max_buy": 15, "resale_avg": 45, "margin": 0.67},
    "glucose_monitor": {"max_buy": 30, "resale_avg": 80, "margin": 0.63},
    "iphone_15": {"max_buy": 450, "resale_avg": 650, "margin": 0.31},
    "iphone_14_pro": {"max_buy": 350, "resale_avg": 550, "margin": 0.36},
    "iphone_13_pro": {"max_buy": 280, "resale_avg": 450, "margin": 0.38},
    "samsung_s23": {"max_buy": 300, "resale_avg": 500, "margin": 0.40},
    "pixel_8": {"max_buy": 320, "resale_avg": 550, "margin": 0.42},
    "oneplus_12": {"max_buy": 280, "resale_avg": 480, "margin": 0.42},
}

# Track found deals to avoid duplicates
FOUND_DEALS = set()

def send_email(subject, body):
    """Send email notification"""
    try:
        msg = MIMEMultipart()
        msg['From'] = MONITOR_EMAIL
        msg['To'] = MONITOR_RECIPIENT
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        # Gmail SMTP
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(MONITOR_EMAIL, MONITOR_EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"📧 Email sent: {subject}")
        return True
    except Exception as e:
        logger.error(f"❌ Email error: {e}")
        return False

def scrape_craigslist(city, keyword, keyword_id):
    """Scrape Craigslist RSS feed for listings"""
    try:
        # Properly encode the search query
        encoded_keyword = quote(keyword)
        url = f"https://{city}.craigslist.org/search/sss?query={encoded_keyword}&sort=date&format=rss"
        
        feed = feedparser.parse(url)
        deals = []
        
        if feed.entries:
            for entry in feed.entries:
                try:
                    title = entry.get('title', '')
                    price_text = entry.get('summary', '')
                    link = entry.get('link', '')
                    
                    # Extract price from title (format: "$XXX")
                    price = None
                    if '$' in title:
                        price_str = title.split('$')[1].split()[0]
                        try:
                            price = float(price_str)
                        except:
                            pass
                    
                    if price and keyword_id in PRICING_TARGETS:
                        target = PRICING_TARGETS[keyword_id]
                        max_buy = target['max_buy']
                        resale_avg = target['resale_avg']
                        margin = target['margin']
                        
                        # Check if price is below our target
                        if price <= max_buy:
                            profit = resale_avg - price
                            profit_margin = (profit / resale_avg) * 100
                            
                            deal_id = f"{city}_{keyword_id}_{price}_{title[:20]}"
                            if deal_id not in FOUND_DEALS:
                                FOUND_DEALS.add(deal_id)
                                deals.append({
                                    'title': title,
                                    'price': price,
                                    'max_buy': max_buy,
                                    'resale_avg': resale_avg,
                                    'profit': profit,
                                    'margin': profit_margin,
                                    'location': city,
                                    'link': link,
                                    'keyword': keyword
                                })
                except Exception as e:
                    logger.debug(f"Error parsing entry: {e}")
        
        return deals
    except Exception as e:
        logger.error(f"❌ Craigslist scrape error for {city}/{keyword}: {e}")
        return []

def send_deal_alert(deal):
    """Send email alert for a found deal"""
    subject = f"🎯 New Deal Found! {deal['keyword']} - ${deal['price']:.2f}"
    
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #2ecc71;">🎯 New Deal Found!</h2>
            
            <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
                <tr style="background-color: #f0f0f0;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Title</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{deal['title']}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Price</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b style="color: #e74c3c;">${deal['price']:.2f}</b></td>
                </tr>
                <tr style="background-color: #f0f0f0;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Max Buy</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">${deal['max_buy']:.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Resale Avg</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">${deal['resale_avg']:.2f}</td>
                </tr>
                <tr style="background-color: #f0f0f0;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Profit Potential</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b style="color: #27ae60;">${deal['profit']:.2f} ({deal['margin']:.1f}%)</b></td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Location</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{deal['location'].upper()}</td>
                </tr>
                <tr style="background-color: #f0f0f0;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><b>Posted</b></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
            
            <p style="margin-top: 20px;">
                <a href="{deal['link']}" style="background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    View Listing →
                </a>
            </p>
            
            <hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">
            <p style="color: #7f8c8d; font-size: 12px;">
                Automated deal alert from Marketplace Monitor
            </p>
        </body>
    </html>
    """
    
    send_email(subject, body)

def monitor_cycle():
    """Run one monitoring cycle"""
    logger.info("🚀 Marketplace Monitor v2 - Cloud Edition")
    logger.info("📍 Monitoring Craigslist (NYC + 70 mile radius of Union, NJ)...")
    
    total_deals = 0
    
    for city in CRAIGSLIST_CITIES:
        for keyword_id, keyword in SEARCH_KEYWORDS.items():
            deals = scrape_craigslist(city, keyword, keyword_id)
            
            if deals:
                logger.info(f"✅ {city.upper()}: Found {len(deals)} deal(s) for {keyword}")
                for deal in deals:
                    send_deal_alert(deal)
                    total_deals += 1
    
    if total_deals == 0:
        logger.info("ℹ️ No deals found this cycle")
    
    logger.info(f"✅ Cycle complete. Total deals found: {total_deals}")
    logger.info("⏳ Next check in 5 minutes...")

def main():
    """Main monitoring loop"""
    logger.info("🚀 Starting Marketplace Monitor...")
    logger.info(f"📧 Email notifications: {MONITOR_RECIPIENT}")
    
    while True:
        try:
            monitor_cycle()
            time.sleep(300)  # Check every 5 minutes
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"❌ Error in monitoring cycle: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    main()
