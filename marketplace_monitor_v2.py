#!/usr/bin/env python3
"""
Marketplace Monitor v2 - Cloud-Ready Edition
Monitors Craigslist and Facebook Marketplace for underpriced items.
Designed to run 24/7 on cloud servers (Heroku, Railway, AWS, etc.)
"""

import json
import time
import smtplib
import os
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import requests
from bs4 import BeautifulSoup
import feedparser

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION - Load from Environment Variables
# ============================================================================

# Email configuration
EMAIL_CONFIG = {
    "sender": os.getenv("MONITOR_EMAIL", "your_email@gmail.com"),
    "password": os.getenv("MONITOR_EMAIL_PASSWORD", "your_app_password"),
    "recipient": os.getenv("MONITOR_RECIPIENT", "your_email@gmail.com"),
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
}

# Pricing thresholds
PRICING_TARGETS = {
    "dexcom_g6": {"max_buy": 35, "resale_avg": 90, "margin": 0.60},
    "dexcom_g7": {"max_buy": 45, "resale_avg": 120, "margin": 0.60},
    "omnipod_5": {"max_buy": 100, "resale_avg": 200, "margin": 0.50},
    "omnipod_dash": {"max_buy": 90, "resale_avg": 180, "margin": 0.50},
    "freestyle_libre": {"max_buy": 30, "resale_avg": 80, "margin": 0.60},
    "test_strips": {"max_buy": 20, "resale_avg": 50, "margin": 0.60},
    "iphone_15": {"max_buy": 300, "resale_avg": 400, "margin": 0.25},
    "iphone_14_pro": {"max_buy": 350, "resale_avg": 500, "margin": 0.30},
    "iphone_13": {"max_buy": 250, "resale_avg": 350, "margin": 0.30},
}

# Keywords to monitor
SEARCH_KEYWORDS = {
    "diabetic_supplies": [
        "Dexcom G6", "Dexcom G7", "Omnipod 5", "Omnipod DASH",
        "Freestyle Libre", "Test Strips", "Glucose Monitor", "Insulin Pump",
        "CGM", "Continuous Glucose Monitor"
    ],
    "phones": [
        "iPhone 15", "iPhone 14 Pro", "iPhone 13 Pro",
        "Samsung S23", "Pixel 8", "OnePlus 12"
    ]
}

# Craigslist cities to monitor - NYC Area & 70 Mile Radius of Union, NJ
CRAIGSLIST_CITIES = [
    "newyork",      # Manhattan, Brooklyn, Queens, Bronx, Staten Island
    "newjersey",    # Union, Newark, Jersey City, and surrounding areas
    "longisland",   # Long Island (Queens, Nassau, Suffolk)
    "connecticut",  # Stamford, Bridgeport, and surrounding areas
]

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Listing:
    """Represents a marketplace listing."""
    id: str
    title: str
    price: float
    url: str
    platform: str  # "craigslist" or "facebook"
    posted_time: str
    location: str
    condition: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)

@dataclass
class Deal:
    """Represents a deal opportunity."""
    listing: Listing
    target_item: str
    max_buy_price: float
    profit_potential: float
    margin_percentage: float
    found_at: str = None
    
    def __post_init__(self):
        if not self.found_at:
            self.found_at = datetime.now().isoformat()

# ============================================================================
# MARKETPLACE SCRAPERS
# ============================================================================

class CraigslistScraper:
    """Scrapes Craigslist for listings."""
    
    @staticmethod
    def search(city: str, keywords: List[str], max_price: int = 500) -> List[Listing]:
        """
        Search Craigslist for listings.
        Uses RSS feeds (no scraping needed, avoids blocking).
        """
        listings = []
        
        for keyword in keywords:
            try:
                # Craigslist RSS feed URL
                # For NYC: newyork covers all 5 boroughs
                # For NJ: newjersey covers Union and surrounding areas
                # For Long Island: longisland covers Queens, Nassau, Suffolk
                # For CT: connecticut covers Stamford, Bridgeport, etc.
                url = f"https://{city}.craigslist.org/search/sss?query={keyword}&sort=date&format=rss"
                
                # Fetch and parse RSS feed
                feed = feedparser.parse(url)
                
                for entry in feed.entries[:10]:  # Get top 10 results
                    try:
                        # Extract price from title (Craigslist format: "Title - $price")
                        title = entry.title
                        price_str = title.split("$")[-1].split()[0] if "$" in title else "0"
                        price = float(price_str)
                        
                        if price <= max_price:
                            listing = Listing(
                                id=f"cl_{city}_{entry.id}",
                                title=title.split(" - ")[0],  # Remove price from title
                                price=price,
                                url=entry.link,
                                platform="craigslist",
                                posted_time=entry.published,
                                location=city.title(),
                            )
                            listings.append(listing)
                    except (ValueError, IndexError, AttributeError):
                        continue
                
                logger.info(f"✅ Craigslist {city.title()}: Found {len(listings)} listings for '{keyword}'")
            
            except Exception as e:
                logger.error(f"❌ Craigslist scrape error for {city}/{keyword}: {e}")
        
        return listings

class FacebookMarketplaceScraper:
    """
    Scrapes Facebook Marketplace for listings.
    Note: Facebook actively blocks scrapers. For production, consider:
    - Using Facebook Graph API (requires approval)
    - Using a third-party service (ScraperAPI, Bright Data)
    - Manual monitoring with alerts
    """
    
    @staticmethod
    def search(keywords: List[str], location: str = "US", max_price: int = 500) -> List[Listing]:
        """
        Placeholder for Facebook Marketplace scraping.
        In production, use Selenium or a scraping service.
        """
        logger.warning("⚠️ Facebook Marketplace scraping requires Selenium or API access")
        return []

# ============================================================================
# MONITORING LOGIC
# ============================================================================

class MarketplaceMonitor:
    """Main monitoring class."""
    
    def __init__(self):
        self.listings_seen = set()
        self.deals_found = []
        self.last_check = {}
        
    def check_price_match(self, price: float, item_key: str) -> Optional[Dict]:
        """Check if a price matches our buying criteria."""
        if item_key not in PRICING_TARGETS:
            return None
        
        target = PRICING_TARGETS[item_key]
        if price <= target["max_buy"]:
            return {
                "item": item_key,
                "max_buy": target["max_buy"],
                "resale_avg": target["resale_avg"],
                "profit": target["resale_avg"] - price,
                "margin": (target["resale_avg"] - price) / target["resale_avg"],
            }
        return None
    
    def match_keywords(self, title: str, keywords: List[str]) -> Optional[str]:
        """Match listing title against keywords."""
        title_lower = title.lower()
        for keyword in keywords:
            if keyword.lower() in title_lower:
                return keyword
        return None
    
    def evaluate_listing(self, listing: Listing) -> Optional[Deal]:
        """Evaluate if a listing is a good deal."""
        # Check diabetic supplies
        matched_keyword = self.match_keywords(listing.title, SEARCH_KEYWORDS["diabetic_supplies"])
        if matched_keyword:
            item_key = matched_keyword.lower().replace(" ", "_")
            price_match = self.check_price_match(listing.price, item_key)
            if price_match:
                return Deal(
                    listing=listing,
                    target_item=matched_keyword,
                    max_buy_price=price_match["max_buy"],
                    profit_potential=price_match["profit"],
                    margin_percentage=price_match["margin"],
                )
        
        # Check phones
        matched_keyword = self.match_keywords(listing.title, SEARCH_KEYWORDS["phones"])
        if matched_keyword:
            item_key = matched_keyword.lower().replace(" ", "_")
            price_match = self.check_price_match(listing.price, item_key)
            if price_match:
                return Deal(
                    listing=listing,
                    target_item=matched_keyword,
                    max_buy_price=price_match["max_buy"],
                    profit_potential=price_match["profit"],
                    margin_percentage=price_match["margin"],
                )
        
        return None
    
    def send_alert(self, deals: List[Deal]):
        """Send email alert with found deals."""
        if not deals:
            return
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"🎯 {len(deals)} New Deal(s) Found!"
            msg["From"] = EMAIL_CONFIG["sender"]
            msg["To"] = EMAIL_CONFIG["recipient"]
            
            # Build email body
            text_body = f"Found {len(deals)} potential deal(s):\n\n"
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px;">
                        <h2 style="color: #16a34a;">🎯 {len(deals)} New Deal(s) Found!</h2>
                        <p style="color: #666;">Check these listings immediately:</p>
            """
            
            for deal in deals:
                listing = deal.listing
                text_body += f"""
Title: {listing.title}
Price: ${listing.price:.2f}
Max Buy: ${deal.max_buy_price:.2f}
Profit Potential: ${deal.profit_potential:.2f} ({deal.margin_percentage*100:.1f}%)
Location: {listing.location}
Platform: {listing.platform}
Posted: {listing.posted_time}
URL: {listing.url}
---
"""
                
                html_body += f"""
                <div style="border: 2px solid #16a34a; padding: 15px; margin: 15px 0; border-radius: 5px; background-color: #f9fafb;">
                    <h3 style="margin-top: 0; color: #1f2937;">{listing.title}</h3>
                    <p><strong>Price:</strong> <span style="font-size: 18px; color: #dc2626;">${listing.price:.2f}</span></p>
                    <p><strong>Max Buy:</strong> ${deal.max_buy_price:.2f}</p>
                    <p><strong>Profit Potential:</strong> <span style="color: #16a34a; font-weight: bold;">${deal.profit_potential:.2f} ({deal.margin_percentage*100:.1f}%)</span></p>
                    <p><strong>Location:</strong> {listing.location}</p>
                    <p><strong>Platform:</strong> {listing.platform.title()}</p>
                    <p><strong>Posted:</strong> {listing.posted_time}</p>
                    <p><a href="{listing.url}" style="display: inline-block; background-color: #16a34a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold;">View Listing →</a></p>
                </div>
"""
            
            html_body += """
                    </div>
                </body>
            </html>
            """
            
            # Attach both versions
            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            
            # Send email
            with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
                server.starttls()
                server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
                server.send_message(msg)
            
            logger.info(f"✅ Alert sent for {len(deals)} deal(s)")
        
        except Exception as e:
            logger.error(f"❌ Failed to send email alert: {e}")
    
    def monitor_cycle(self):
        """Run one monitoring cycle."""
        logger.info("=" * 70)
        logger.info(f"🔍 Starting monitoring cycle at {datetime.now().isoformat()}")
        logger.info("=" * 70)
        
        deals_this_cycle = []
        
        # Monitor Craigslist - NYC & NJ Area
        logger.info("📍 Monitoring Craigslist (NYC + 70 mile radius of Union, NJ)...")
        for city in CRAIGSLIST_CITIES:
            listings = CraigslistScraper.search(
                city,
                SEARCH_KEYWORDS["diabetic_supplies"] + SEARCH_KEYWORDS["phones"],
                max_price=600  # Slightly higher for NYC area (higher prices)
            )
            
            for listing in listings:
                if listing.id not in self.listings_seen:
                    self.listings_seen.add(listing.id)
                    deal = self.evaluate_listing(listing)
                    if deal:
                        deals_this_cycle.append(deal)
                        logger.info(f"✅ Deal found: {deal.listing.title} @ ${deal.listing.price}")
        
        # Monitor Facebook Marketplace (placeholder)
        logger.info("📍 Facebook Marketplace monitoring (requires API setup)...")
        
        # Send alerts if deals found
        if deals_this_cycle:
            logger.info(f"📧 Sending alerts for {len(deals_this_cycle)} deal(s)...")
            self.send_alert(deals_this_cycle)
            self.deals_found.extend(deals_this_cycle)
        else:
            logger.info("ℹ️ No deals found this cycle")
        
        logger.info(f"✅ Cycle complete. Total deals found: {len(self.deals_found)}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    logger.info("=" * 70)
    logger.info("🚀 Marketplace Monitor v2 - Cloud Edition")
    logger.info("=" * 70)
    logger.info(f"Monitoring {len(SEARCH_KEYWORDS['diabetic_supplies'])} diabetic supply keywords")
    logger.info(f"Monitoring {len(SEARCH_KEYWORDS['phones'])} phone keywords")
    logger.info(f"Monitoring {len(CRAIGSLIST_CITIES)} Craigslist regions: NYC (all boroughs) + 70 mile radius of Union, NJ")
    logger.info("=" * 70)
    
    monitor = MarketplaceMonitor()
    
    # Run monitoring cycles
    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            monitor.monitor_cycle()
            
            # Wait 5 minutes before next check (adjust as needed)
            logger.info(f"⏳ Next check in 5 minutes...")
            time.sleep(300)  # 5 minutes
    
    except KeyboardInterrupt:
        logger.info(f"\n\n📊 Monitoring stopped after {cycle_count} cycles")
        logger.info(f"Total deals found: {len(monitor.deals_found)}")
        
        # Save deals to file
        if monitor.deals_found:
            with open("deals_found.json", "w") as f:
                deals_data = [
                    {
                        "listing": deal.listing.to_dict(),
                        "target_item": deal.target_item,
                        "max_buy_price": deal.max_buy_price,
                        "profit_potential": deal.profit_potential,
                        "margin_percentage": deal.margin_percentage,
                        "found_at": deal.found_at,
                    }
                    for deal in monitor.deals_found
                ]
                json.dump(deals_data, f, indent=2)
            logger.info(f"✅ Deals saved to deals_found.json")

if __name__ == "__main__":
    main()
