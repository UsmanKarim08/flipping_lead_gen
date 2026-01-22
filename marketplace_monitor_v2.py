#!/usr/bin/env python3
"""
Marketplace Monitor v4 - Final Edition
Automated deal hunting for diabetic supplies only
NYC/NJ Area Focus
Uses exact pricing from HMH Med Supply Buyback & Sunny Med Wholesale
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

# Diabetic supplies pricing (Buy price, Sell price, Profit margin %)
PRICING_TARGETS = {
    # Dexcom G6
    "dexcom_g6_3pk_gs": {"keyword": "Dexcom G6 3 pack", "max_buy": 110, "resale": 150, "margin": 0.27},
    "dexcom_g6_3pk_oe": {"keyword": "Dexcom G6 3 pack OE", "max_buy": 150, "resale": 200, "margin": 0.25},
    "dexcom_g6_3pk_or": {"keyword": "Dexcom G6 3 pack OR", "max_buy": 150, "resale": 200, "margin": 0.25},
    "dexcom_g6_3pk_om": {"keyword": "Dexcom G6 3 pack OM", "max_buy": 135, "resale": 180, "margin": 0.25},
    "dexcom_g6_receiver": {"keyword": "Dexcom G6 receiver", "max_buy": 95, "resale": 127, "margin": 0.25},
    "dexcom_g6_single": {"keyword": "Dexcom G6 single", "max_buy": 22, "resale": 30, "margin": 0.27},
    "dexcom_g6_transmitter": {"keyword": "Dexcom G6 transmitter", "max_buy": 105, "resale": 140, "margin": 0.25},
    
    # Dexcom G7
    "dexcom_g7_15day_010": {"keyword": "Dexcom G7 010", "max_buy": 90, "resale": 120, "margin": 0.25},
    "dexcom_g7_15day_011": {"keyword": "Dexcom G7 011", "max_buy": 75, "resale": 100, "margin": 0.25},
    "dexcom_g7_15day_012": {"keyword": "Dexcom G7 012", "max_buy": 75, "resale": 100, "margin": 0.25},
    "dexcom_g7_15day_013": {"keyword": "Dexcom G7 013", "max_buy": 75, "resale": 100, "margin": 0.25},
    "dexcom_g7_15day_016": {"keyword": "Dexcom G7 016", "max_buy": 65, "resale": 85, "margin": 0.24},
    "dexcom_g7_1pk_018": {"keyword": "Dexcom G7 018", "max_buy": 65, "resale": 89, "margin": 0.27},
    "dexcom_g7_1pk_012": {"keyword": "Dexcom G7 1pk 012", "max_buy": 65, "resale": 89, "margin": 0.27},
    "dexcom_g7_1pk_011": {"keyword": "Dexcom G7 1pk 011", "max_buy": 65, "resale": 84, "margin": 0.23},
    "dexcom_g7_1pk_013": {"keyword": "Dexcom G7 1pk 013", "max_buy": 55, "resale": 75, "margin": 0.27},
    "dexcom_g7_1pk_030": {"keyword": "Dexcom G7 1pk 030", "max_buy": 40, "resale": 50, "margin": 0.20},
    "dexcom_g7_receiver": {"keyword": "Dexcom G7 receiver", "max_buy": 110, "resale": 145, "margin": 0.24},
    "dexcom_transmitter": {"keyword": "Dexcom transmitter", "max_buy": 80, "resale": 110, "margin": 0.27},
    "stelo_2pack": {"keyword": "Stelo 2 pack", "max_buy": 30, "resale": 40, "margin": 0.25},
    "stelo_1pack": {"keyword": "Stelo 1 pack", "max_buy": 11, "resale": 15, "margin": 0.27},
    
    # Omnipod
    "omnipod_dash_pdm": {"keyword": "Omnipod Dash PDM", "max_buy": 75, "resale": 102, "margin": 0.27},
    "omnipod_dash_10pack": {"keyword": "Omnipod Dash 10 pack", "max_buy": 145, "resale": 195, "margin": 0.26},
    "omnipod_dash_5pack": {"keyword": "Omnipod Dash 5 pack", "max_buy": 105, "resale": 140, "margin": 0.25},
    "omnipod_5_pdm": {"keyword": "Omnipod 5 PDM", "max_buy": 85, "resale": 114, "margin": 0.26},
    "omnipod_5_5pack_g6g7": {"keyword": "Omnipod 5 5 pack G6", "max_buy": 160, "resale": 215, "margin": 0.26},
    "omnipod_5_5pack_libre": {"keyword": "Omnipod 5 5 pack Libre", "max_buy": 155, "resale": 204, "margin": 0.24},
    "omnipod_5_10pack": {"keyword": "Omnipod 5 10 pack", "max_buy": 290, "resale": 390, "margin": 0.26},
    "omnipod_10pack": {"keyword": "Omnipod 10 pack", "max_buy": 110, "resale": 144, "margin": 0.24},
    "omnipod_5pack": {"keyword": "Omnipod 5 pack", "max_buy": 65, "resale": 85, "margin": 0.24},
    "omnipod_loose": {"keyword": "Omnipod loose sensor", "max_buy": 16, "resale": 22, "margin": 0.27},
    
    # Freestyle Libre
    "freestyle_libre_14day": {"keyword": "Freestyle Libre 14 day", "max_buy": 40, "resale": 51, "margin": 0.22},
    "freestyle_libre_2": {"keyword": "Freestyle Libre 2", "max_buy": 40, "resale": 51, "margin": 0.22},
    "freestyle_libre_2_plus": {"keyword": "Freestyle Libre 2 PLUS", "max_buy": 40, "resale": 51, "margin": 0.22},
    "freestyle_libre_3": {"keyword": "Freestyle Libre 3", "max_buy": 40, "resale": 50, "margin": 0.20},
    "freestyle_libre_3_plus": {"keyword": "Freestyle Libre 3 PLUS", "max_buy": 40, "resale": 50, "margin": 0.20},
    "freestyle_libre_reader": {"keyword": "Freestyle Libre reader", "max_buy": 40, "resale": 51, "margin": 0.22},
    
    # Medtronic
    "medtronic_770": {"keyword": "Medtronic 770 pump", "max_buy": 260, "resale": 350, "margin": 0.26},
    "medtronic_780g": {"keyword": "Medtronic 780g pump", "max_buy": 450, "resale": 600, "margin": 0.25},
    "medtronic_guardian": {"keyword": "Medtronic Guardian", "max_buy": 60, "resale": 80, "margin": 0.25},
    "medtronic_mio": {"keyword": "Medtronic Mio", "max_buy": 30, "resale": 40, "margin": 0.25},
    
    # Test Strips
    "test_strips_accu_chek": {"keyword": "Accu Chek Active", "max_buy": 8, "resale": 11, "margin": 0.27},
    "test_strips_accuchek_100": {"keyword": "Accuchek Guide 100", "max_buy": 19, "resale": 25, "margin": 0.24},
    "test_strips_accuchek_50": {"keyword": "Accuchek Guide 50", "max_buy": 9, "resale": 12, "margin": 0.25},
    "test_strips_aviva_100": {"keyword": "Aviva 100", "max_buy": 45, "resale": 59, "margin": 0.24},
    "test_strips_aviva_50": {"keyword": "Aviva 50", "max_buy": 25, "resale": 36, "margin": 0.30},
    "test_strips_contour": {"keyword": "Contour", "max_buy": 35, "resale": 44, "margin": 0.21},
    "test_strips_freestyle": {"keyword": "Freestyle test strips", "max_buy": 25, "resale": 34, "margin": 0.27},
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

def scrape_craigslist(city, keyword, keyword_id, max_buy, resale, margin):
    """Scrape Craigslist RSS feed for listings"""
    try:
        # Craigslist RSS feed URL
        url = f"https://{city}.craigslist.org/search/sss?format=rss&query={quote(keyword)}"
        
        feed = feedparser.parse(url)
        deals_found = []
        
        for entry in feed.entries[:10]:  # Check latest 10 listings
            title = entry.title.lower()
            price_str = entry.title.split('$')[-1].split()[0] if '$' in entry.title else None
            
            if price_str:
                try:
                    price = float(price_str)
                    deal_id = f"{city}_{keyword_id}_{entry.link}"
                    
                    # Check if this is a good deal
                    if price <= max_buy and deal_id not in FOUND_DEALS:
                        profit = resale - price
                        actual_margin = (profit / resale) * 100
                        
                        deals_found.append({
                            'title': entry.title,
                            'price': price,
                            'max_buy': max_buy,
                            'resale': resale,
                            'profit': profit,
                            'margin': actual_margin,
                            'link': entry.link,
                            'city': city,
                            'keyword': keyword
                        })
                        
                        FOUND_DEALS.add(deal_id)
                except ValueError:
                    pass
        
        return deals_found
    except Exception as e:
        logger.error(f"❌ Error scraping {city} for {keyword}: {e}")
        return []

def main():
    """Main monitoring loop"""
    logger.info("🚀 Marketplace Monitor v4 - Diabetic Supplies Edition")
    logger.info("📍 Monitoring Craigslist (NYC/NJ area)")
    logger.info(f"⏰ Check interval: 5 minutes")
    
    while True:
        try:
            all_deals = []
            
            # Check each city and keyword combination
            for city in CRAIGSLIST_CITIES:
                logger.info(f"🔍 Checking {city}...")
                
                for keyword_id, pricing in PRICING_TARGETS.items():
                    keyword = pricing['keyword']
                    max_buy = pricing['max_buy']
                    resale = pricing['resale']
                    margin = pricing['margin']
                    
                    deals = scrape_craigslist(city, keyword, keyword_id, max_buy, resale, margin)
                    all_deals.extend(deals)
            
            # Send email if deals found
            if all_deals:
                logger.info(f"✅ Found {len(all_deals)} deal(s)!")
                
                # Group deals by keyword for email
                deals_by_keyword = {}
                for deal in all_deals:
                    keyword = deal['keyword']
                    if keyword not in deals_by_keyword:
                        deals_by_keyword[keyword] = []
                    deals_by_keyword[keyword].append(deal)
                
                # Create email body
                email_body = "<h2>🎉 New Deals Found!</h2>"
                email_body += f"<p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
                
                for keyword, deals in deals_by_keyword.items():
                    email_body += f"<h3>{keyword}</h3>"
                    for deal in deals:
                        email_body += f"""
                        <div style="border: 1px solid #ddd; padding: 10px; margin: 5px 0;">
                            <p><strong>{deal['title']}</strong></p>
                            <p>💰 <strong>Price:</strong> ${deal['price']:.2f}</p>
                            <p>📊 <strong>Max Buy:</strong> ${deal['max_buy']:.2f} | <strong>Resale:</strong> ${deal['resale']:.2f}</p>
                            <p>💵 <strong>Profit:</strong> ${deal['profit']:.2f} ({deal['margin']:.1f}%)</p>
                            <p>📍 <strong>City:</strong> {deal['city'].upper()}</p>
                            <p><a href="{deal['link']}" target="_blank">View on Craigslist</a></p>
                        </div>
                        """
                
                send_email(f"🎉 {len(all_deals)} New Diabetic Supply Deal(s) Found!", email_body)
            else:
                logger.info("✅ No deals found this cycle")
            
            # Wait 5 minutes before next check
            logger.info("⏳ Waiting 5 minutes for next check...")
            time.sleep(300)
            
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
            time.sleep(300)

if __name__ == "__main__":
    main()
