#!/usr/bin/env python3
"""
Marketplace Monitor v6 - Complete Edition
Automated deal hunting for diabetic supplies
Monitors: Craigslist + Facebook Marketplace
Buys from marketplaces, sells to Sunny Med Wholesale
NYC/NJ Area Focus
Target: 30-40% profit margin
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
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

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
FACEBOOK_EMAIL = os.getenv('FACEBOOK_EMAIL', '')
FACEBOOK_PASSWORD = os.getenv('FACEBOOK_PASSWORD', '')

# Craigslist cities to monitor (NYC/NJ area)
CRAIGSLIST_CITIES = [
    "newyork",      # NYC
    "newjersey",    # New Jersey
    "longisland",   # Long Island
    "connecticut",  # Connecticut
]

# Facebook Marketplace search terms
FACEBOOK_SEARCH_TERMS = [
    "Dexcom G6", "Dexcom G7", "Omnipod", "Freestyle Libre",
    "Medtronic pump", "test strips", "glucose monitor"
]

# Profit targets: 30-40% margin
MIN_PROFIT_MARGIN = 0.30
MAX_PROFIT_MARGIN = 0.40

# Sunny Med Wholesale buying prices (what they pay you)
SUNNY_MED_PRICES = {
    # Test Strips
    "accu_chek_active": {"keyword": "Accu Chek Active", "sunny_price": 11.00},
    "accuchek_guide_100": {"keyword": "Accuchek Guide 100", "sunny_price": 25.00},
    "accuchek_guide_50": {"keyword": "Accuchek Guide 50", "sunny_price": 12.00},
    "arkay_glucocard": {"keyword": "Arkay Glucocard", "sunny_price": 6.00},
    "aviva_100": {"keyword": "Aviva 100", "sunny_price": 59.00},
    "aviva_50": {"keyword": "Aviva 50", "sunny_price": 36.00},
    "contour_7080g": {"keyword": "Contour 7080G", "sunny_price": 21.00},
    "contour_7090g": {"keyword": "Contour 7090G", "sunny_price": 44.00},
    "contour_next_100": {"keyword": "Contour Next 100", "sunny_price": 29.00},
    "contour_next_50": {"keyword": "Contour Next 50", "sunny_price": 15.00},
    "freestyle_100": {"keyword": "Freestyle 100", "sunny_price": 34.00},
    "freestyle_50": {"keyword": "Freestyle 50", "sunny_price": 17.00},
    "freestyle_lite": {"keyword": "Freestyle Lite", "sunny_price": 20.00},
    "smartview_100": {"keyword": "SmartView 100", "sunny_price": 53.00},
    "smartview_50": {"keyword": "SmartView 50", "sunny_price": 25.00},
    "true_metrix_100": {"keyword": "True Metrix 100", "sunny_price": 27.00},
    
    # Dexcom G6
    "dexcom_g6_3pk_gs": {"keyword": "Dexcom G6 3 pack GS", "sunny_price": 150.00},
    "dexcom_g6_3pk_oe": {"keyword": "Dexcom G6 3 pack OE", "sunny_price": 200.00},
    "dexcom_g6_3pk_or": {"keyword": "Dexcom G6 3 pack OR", "sunny_price": 200.00},
    "dexcom_g6_3pk_om": {"keyword": "Dexcom G6 3 pack OM", "sunny_price": 180.00},
    "dexcom_g6_receiver": {"keyword": "Dexcom G6 receiver", "sunny_price": 127.00},
    "dexcom_g6_single": {"keyword": "Dexcom G6 single", "sunny_price": 30.00},
    "dexcom_g6_transmitter": {"keyword": "Dexcom G6 transmitter", "sunny_price": 140.00},
    
    # Dexcom G7
    "dexcom_g7_15day_010": {"keyword": "Dexcom G7 010", "sunny_price": 120.00},
    "dexcom_g7_15day_011": {"keyword": "Dexcom G7 011", "sunny_price": 100.00},
    "dexcom_g7_15day_012": {"keyword": "Dexcom G7 012", "sunny_price": 100.00},
    "dexcom_g7_15day_013": {"keyword": "Dexcom G7 013", "sunny_price": 100.00},
    "dexcom_g7_15day_016": {"keyword": "Dexcom G7 016", "sunny_price": 85.00},
    "dexcom_g7_1pk_018": {"keyword": "Dexcom G7 1pk 018", "sunny_price": 89.00},
    "dexcom_g7_1pk_012": {"keyword": "Dexcom G7 1pk 012", "sunny_price": 89.00},
    "dexcom_g7_1pk_011": {"keyword": "Dexcom G7 1pk 011", "sunny_price": 84.00},
    "dexcom_g7_1pk_013": {"keyword": "Dexcom G7 1pk 013", "sunny_price": 75.00},
    "dexcom_g7_1pk_030": {"keyword": "Dexcom G7 1pk 030", "sunny_price": 50.00},
    "dexcom_g7_receiver": {"keyword": "Dexcom G7 receiver", "sunny_price": 145.00},
    "dexcom_transmitter": {"keyword": "Dexcom transmitter", "sunny_price": 110.00},
    "stelo_2pack": {"keyword": "Stelo 2 pack", "sunny_price": 40.00},
    "stelo_1pack": {"keyword": "Stelo 1 pack", "sunny_price": 15.00},
    
    # Omnipod
    "omnipod_dash_pdm": {"keyword": "Omnipod Dash PDM", "sunny_price": 102.00},
    "omnipod_dash_10pack": {"keyword": "Omnipod Dash 10 pack", "sunny_price": 195.00},
    "omnipod_dash_5pack": {"keyword": "Omnipod Dash 5 pack", "sunny_price": 140.00},
    "omnipod_5_pdm": {"keyword": "Omnipod 5 PDM", "sunny_price": 114.00},
    "omnipod_5_5pack_g6g7": {"keyword": "Omnipod 5 5 pack G6", "sunny_price": 215.00},
    "omnipod_5_5pack_libre": {"keyword": "Omnipod 5 5 pack Libre", "sunny_price": 204.00},
    "omnipod_5_10pack": {"keyword": "Omnipod 5 10 pack", "sunny_price": 390.00},
    "omnipod_10pack": {"keyword": "Omnipod 10 pack", "sunny_price": 144.00},
    "omnipod_5pack": {"keyword": "Omnipod 5 pack", "sunny_price": 85.00},
    "omnipod_loose": {"keyword": "Omnipod loose sensor", "sunny_price": 22.00},
    
    # Freestyle Libre
    "freestyle_libre_14day": {"keyword": "Freestyle Libre 14 day", "sunny_price": 51.00},
    "freestyle_libre_2": {"keyword": "Freestyle Libre 2", "sunny_price": 51.00},
    "freestyle_libre_2_plus": {"keyword": "Freestyle Libre 2 PLUS", "sunny_price": 51.00},
    "freestyle_libre_3": {"keyword": "Freestyle Libre 3", "sunny_price": 50.00},
    "freestyle_libre_3_plus": {"keyword": "Freestyle Libre 3 PLUS", "sunny_price": 50.00},
    "freestyle_libre_reader": {"keyword": "Freestyle Libre reader", "sunny_price": 51.00},
    
    # Medtronic
    "medtronic_770": {"keyword": "Medtronic 770 pump", "sunny_price": 350.00},
    "medtronic_780g": {"keyword": "Medtronic 780g pump", "sunny_price": 600.00},
    "medtronic_guardian": {"keyword": "Medtronic Guardian", "sunny_price": 80.00},
    "medtronic_mio": {"keyword": "Medtronic Mio", "sunny_price": 40.00},
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

def calculate_max_buy_price(sunny_price, target_margin=0.35):
    """Calculate max buy price to achieve target profit margin"""
    return sunny_price * (1 - target_margin)

def scrape_craigslist(city, keyword, keyword_id, sunny_price):
    """Scrape Craigslist RSS feed for listings"""
    try:
        max_buy = calculate_max_buy_price(sunny_price, 0.35)
        url = f"https://{city}.craigslist.org/search/sss?format=rss&query={quote(keyword)}"
        
        feed = feedparser.parse(url)
        deals_found = []
        
        for entry in feed.entries[:10]:
            title = entry.title.lower()
            price_str = entry.title.split('$')[-1].split()[0] if '$' in entry.title else None
            
            if price_str:
                try:
                    price = float(price_str)
                    deal_id = f"craigslist_{city}_{keyword_id}_{entry.link}"
                    
                    if price <= max_buy and deal_id not in FOUND_DEALS:
                        profit = sunny_price - price
                        profit_margin = (profit / sunny_price)
                        
                        if MIN_PROFIT_MARGIN <= profit_margin <= MAX_PROFIT_MARGIN:
                            deals_found.append({
                                'title': entry.title,
                                'price': price,
                                'sunny_price': sunny_price,
                                'profit': profit,
                                'margin': profit_margin * 100,
                                'link': entry.link,
                                'city': city,
                                'keyword': keyword,
                                'platform': 'Craigslist'
                            })
                            FOUND_DEALS.add(deal_id)
                except ValueError:
                    pass
        
        return deals_found
    except Exception as e:
        logger.error(f"❌ Error scraping Craigslist {city} for {keyword}: {e}")
        return []

def scrape_facebook_marketplace(search_term, sunny_price):
    """Scrape Facebook Marketplace for listings (headless browser)"""
    if not FACEBOOK_EMAIL or not FACEBOOK_PASSWORD:
        logger.warning("⚠️  Facebook credentials not set, skipping Facebook Marketplace")
        return []
    
    try:
        # Setup headless Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # Facebook Marketplace search URL
        search_url = f"https://www.facebook.com/marketplace/search?query={quote(search_term)}&radius=50&latitude=40.7128&longitude=-74.0060"
        
        driver.get(search_url)
        time.sleep(3)
        
        deals_found = []
        max_buy = calculate_max_buy_price(sunny_price, 0.35)
        
        # Try to find listings (simplified - Facebook is heavily protected)
        try:
            listings = driver.find_elements(By.CSS_SELECTOR, "[data-testid='marketplace_listing_card']")
            
            for listing in listings[:5]:
                try:
                    title = listing.find_element(By.CSS_SELECTOR, "[role='heading']").text
                    price_elem = listing.find_element(By.CSS_SELECTOR, "[data-testid='marketplace_price']")
                    price_text = price_elem.text.replace('$', '').replace(',', '')
                    price = float(price_text.split()[0])
                    
                    deal_id = f"facebook_{search_term}_{title}_{price}"
                    
                    if price <= max_buy and deal_id not in FOUND_DEALS:
                        profit = sunny_price - price
                        profit_margin = (profit / sunny_price)
                        
                        if MIN_PROFIT_MARGIN <= profit_margin <= MAX_PROFIT_MARGIN:
                            deals_found.append({
                                'title': title,
                                'price': price,
                                'sunny_price': sunny_price,
                                'profit': profit,
                                'margin': profit_margin * 100,
                                'link': listing.find_element(By.TAG_NAME, 'a').get_attribute('href'),
                                'city': 'NYC/NJ',
                                'keyword': search_term,
                                'platform': 'Facebook Marketplace'
                            })
                            FOUND_DEALS.add(deal_id)
                except:
                    pass
        except:
            pass
        
        driver.quit()
        return deals_found
        
    except Exception as e:
        logger.error(f"❌ Error scraping Facebook Marketplace for {search_term}: {e}")
        return []

def main():
    """Main monitoring loop"""
    logger.info("🚀 Marketplace Monitor v6 - Complete Edition")
    logger.info("📍 Monitoring: Craigslist + Facebook Marketplace (NYC/NJ area)")
    logger.info(f"💰 Target profit margin: 30-40%")
    logger.info(f"📊 Selling to: Sunny Med Wholesale")
    logger.info(f"⏰ Check interval: 5 minutes")
    
    while True:
        try:
            all_deals = []
            
            # Check Craigslist
            logger.info("🔍 Checking Craigslist...")
            for city in CRAIGSLIST_CITIES:
                for keyword_id, pricing in SUNNY_MED_PRICES.items():
                    keyword = pricing['keyword']
                    sunny_price = pricing['sunny_price']
                    deals = scrape_craigslist(city, keyword, keyword_id, sunny_price)
                    all_deals.extend(deals)
            
            # Check Facebook Marketplace (every 3rd cycle to avoid rate limiting)
            if int(time.time()) % 3 == 0:
                logger.info("🔍 Checking Facebook Marketplace...")
                for search_term in FACEBOOK_SEARCH_TERMS:
                    # Use average Sunny Med price for Facebook search
                    avg_price = sum(p['sunny_price'] for p in SUNNY_MED_PRICES.values()) / len(SUNNY_MED_PRICES)
                    deals = scrape_facebook_marketplace(search_term, avg_price)
                    all_deals.extend(deals)
            
            # Send email if deals found
            if all_deals:
                logger.info(f"✅ Found {len(all_deals)} deal(s) with 30-40% profit!")
                
                # Group deals by platform and keyword
                deals_by_platform = {}
                for deal in all_deals:
                    platform = deal['platform']
                    if platform not in deals_by_platform:
                        deals_by_platform[platform] = {}
                    keyword = deal['keyword']
                    if keyword not in deals_by_platform[platform]:
                        deals_by_platform[platform][keyword] = []
                    deals_by_platform[platform][keyword].append(deal)
                
                # Create email body
                email_body = "<h2>🎉 New Deals Found! (30-40% Profit)</h2>"
                email_body += f"<p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
                email_body += f"<p><strong>Total Deals:</strong> {len(all_deals)}</p>"
                
                for platform, keywords in deals_by_platform.items():
                    email_body += f"<h3>{platform}</h3>"
                    for keyword, deals in keywords.items():
                        email_body += f"<h4>{keyword}</h4>"
                        for deal in deals:
                            email_body += f"""
                            <div style="border: 1px solid #ddd; padding: 10px; margin: 5px 0; background-color: #f9f9f9;">
                                <p><strong>{deal['title']}</strong></p>
                                <p>💰 <strong>Price:</strong> ${deal['price']:.2f}</p>
                                <p>💵 <strong>Sunny Med Buys For:</strong> ${deal['sunny_price']:.2f}</p>
                                <p>📈 <strong>Your Profit:</strong> ${deal['profit']:.2f} ({deal['margin']:.1f}%)</p>
                                <p>📍 <strong>Location:</strong> {deal['city'].upper()}</p>
                                <p><a href="{deal['link']}" target="_blank" style="color: #0066cc; font-weight: bold;">👉 View Listing</a></p>
                            </div>
                            """
                
                send_email(f"💰 {len(all_deals)} New Deal(s) - 30-40% Profit!", email_body)
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
