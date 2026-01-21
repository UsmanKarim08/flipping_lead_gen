# Flipping Lead Gen - Automated Marketplace Monitor

Automated deal hunting system for diabetic supplies and phones in the NYC/NJ area.

## What This Does

- **Monitors Craigslist** every 5 minutes across NYC (all 5 boroughs) + New Jersey + Long Island + Connecticut
- **Finds underpriced items** (Dexcom, Omnipod, iPhones, etc.)
- **Sends email alerts** when deals matching your profit targets are found
- **Runs 24/7** on cloud servers (Railway, Heroku, AWS)
- **No laptop needed** - fully automated

## Quick Start

### 1. Deploy to Railway (Recommended)

1. Go to https://railway.app
2. Click "Start Project" → "Deploy from GitHub"
3. Connect your GitHub account
4. Select this repository
5. Railway will auto-detect and build

### 2. Set Environment Variables

In Railway dashboard, go to "Variables" and add:

```
MONITOR_EMAIL=your_email@gmail.com
MONITOR_EMAIL_PASSWORD=your_gmail_app_password
MONITOR_RECIPIENT=your_email@gmail.com
```

### 3. Deploy

Click "Deploy" and wait 2-3 minutes. Check logs to confirm it's running.

## Getting Your Gmail App Password

1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification (if not already enabled)
3. Find "App passwords" in Security settings
4. Select "Mail" and "Windows Computer"
5. Copy the 16-character password
6. Use this in your environment variables

## What You'll Receive

When a deal is found, you get an email like:

```
Subject: 🎯 1 New Deal Found!

Title: Dexcom G6 Sensors - Sealed Box
Price: $28.00
Max Buy: $35.00
Profit Potential: $62.00 (68.9%)
Location: Brooklyn
Platform: Craigslist
Posted: 2 hours ago
[View Listing →]
```

## Customization

### Add More Cities

Edit `marketplace_monitor_v2.py`:

```python
CRAIGSLIST_CITIES = [
    "newyork",
    "newjersey",
    "longisland",
    "connecticut",
    # Add more cities here
]
```

### Adjust Price Targets

Edit `PRICING_TARGETS`:

```python
PRICING_TARGETS = {
    "dexcom_g6": {"max_buy": 35, "resale_avg": 90, "margin": 0.60},
    # Increase max_buy to be more aggressive
}
```

### Change Check Frequency

Edit the sleep time in `main()`:

```python
time.sleep(300)  # 300 seconds = 5 minutes
# Change to 600 for 10 minutes, 180 for 3 minutes, etc.
```

## Monitoring Areas

- **NYC:** Manhattan, Brooklyn, Queens, Bronx, Staten Island
- **New Jersey:** Union, Newark, Jersey City, surrounding areas
- **Long Island:** Queens, Nassau, Suffolk
- **Connecticut:** Stamford, Bridgeport, surrounding areas

**Total Coverage:** ~70-mile radius from Union, NJ

## Keywords Monitored

### Diabetic Supplies
- Dexcom G6, G7
- Omnipod 5, DASH
- Freestyle Libre
- Test Strips
- Glucose Monitors
- Insulin Pumps

### Phones
- iPhone 15, 14 Pro, 13 Pro
- Samsung S23
- Google Pixel 8
- OnePlus 12

## Expected Results

**Conservative (5 deals/week):**
- 5 deals × $60 profit = $300/week = $1,200/month

**Moderate (10 deals/week):**
- 10 deals × $75 profit = $750/week = $3,000/month

**Aggressive (20 deals/week):**
- 20 deals × $80 profit = $1,600/week = $6,400/month

## Cost

**Completely Free!**

- Railway: 500 hours/month free (enough for 24/7 operation)
- Heroku: 550 hours/month free
- Gmail: Free with your account

## Troubleshooting

### Not receiving emails?
1. Check spam/junk folder
2. Verify Gmail app password is exactly correct
3. Confirm 2FA is enabled on your Gmail
4. Check Railway logs for SMTP errors

### No deals found?
1. Check logs for "Found X listings"
2. Verify your price targets aren't too low
3. Try increasing max_buy prices
4. Add more keywords

### Script keeps crashing?
1. Check Railway logs for error messages
2. Verify all environment variables are set
3. Ensure all dependencies in `requirements.txt` are installed

## Files

- `marketplace_monitor_v2.py` - Main monitoring script
- `requirements.txt` - Python dependencies
- `Procfile` - Railway/Heroku configuration

## Support

For issues:
1. Check the logs in your cloud platform
2. Review error messages carefully
3. Verify environment variables are correct
4. Test your Gmail credentials locally first

## License

MIT

---

**Ready to start?** Deploy to Railway and start receiving deal alerts! 🚀
