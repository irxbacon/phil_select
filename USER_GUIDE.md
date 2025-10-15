# 🎯 Philmont Trek Selector - User Guide

**The easiest way to find your perfect Philmont adventure!**

This guide shows you how to download and run the Philmont Trek Selection System without any technical setup. No Python installation, no command line - just download and run!

## 🚀 Quick Start (2 Minutes)

### Step 1: Download the App
1. Go to the **[Latest Release](https://github.com/irxbacon/phil_select/releases/latest)** page
2. Download the file for your computer:
   - **Windows**: `philmont-trek-selector-windows.exe`
   - **Mac**: `philmont-trek-selector-macos` 
   - **Linux**: `philmont-trek-selector-linux`

### Step 2: Run the App

**Windows:**
- Double-click the `.exe` file
- **If Windows blocks it:** Click "More info" → "Run anyway"
- **If antivirus flags it:** This is normal for new apps - choose "Allow" or "Run anyway"
- **If still blocked:** Right-click → "Run as Administrator"

**Mac:**
- **First time:** Right-click → "Open" (don't double-click)
- **If macOS blocks it:** Go to System Preferences → Security & Privacy → General → Click "Open Anyway"
- **Alternative:** Hold Control while clicking → "Open"
- **Note:** macOS may show "unidentified developer" warning - this is normal for open source apps

**Linux:**
- Make executable and run:
  ```bash
  chmod +x philmont-trek-selector-linux
  ./philmont-trek-selector-linux
  ```

### Step 3: Use the App
1. The app will start automatically
2. Open your web browser 
3. Go to: **http://127.0.0.1:5002**
4. Start planning your Philmont trek!

## 📋 What You Get

This standalone application includes everything you need:

- ✅ **Complete Philmont Database** - All 84 trek itineraries (2024 data)
- ✅ **56+ Activity Programs** - Climbing, STEM, historical activities, and more
- ✅ **Smart Scoring System** - Ranks treks based on your crew's preferences
- ✅ **No Installation Required** - Just download and run
- ✅ **Works Offline** - No internet connection needed once downloaded
- ✅ **Cross-Platform** - Available for Windows, Mac, and Linux

## 🎮 How to Use

### 1. Set Your Crew Preferences
- Choose difficulty levels your crew can handle
- Select preferred areas (South, Central, North, Valle Vidal)
- Set altitude and distance preferences
- Pick which peaks you want to climb

### 2. Rate Activity Programs
- Score each program 0-20 based on your crew's interests
- Programs include: rock climbing, historical sites, STEM activities, nature studies, etc.
- You can rate programs for individual crew members or as a group

### 3. Get Your Results
- View treks ranked by how well they match your preferences
- See detailed scoring breakdown for each recommendation
- Click any trek to see day-by-day details and available programs

### 4. Make Your Decision
Use the recommendations to guide your official Philmont reservation through their website.

## 🔧 Troubleshooting

### App Won't Start
**Windows:**
- Right-click → "Run as Administrator"
- Check Windows Defender hasn't blocked it
- Try downloading again if file seems corrupted

**Mac:**
- Go to System Preferences → Security & Privacy → General
- Click "Open Anyway" if macOS blocked the app
- Or try: Right-click → "Open" instead of double-clicking

**Linux:**
- Make sure file is executable: `chmod +x philmont-trek-selector-linux`
- Check you have required libraries: `sudo apt update && sudo apt install libc6`

### Browser Won't Connect
- Make sure the app is still running (don't close the terminal window)
- Try: http://localhost:5002 instead of http://127.0.0.1:5002
- Check no other apps are using port 5002

### App Crashes
- Try running from a terminal/command prompt to see error messages
- Make sure you have enough disk space (app needs ~100MB)
- Restart your computer and try again

## 📁 File Information

### What Gets Downloaded
- **Single executable file** (50-80MB depending on platform)
- **No additional files needed** - database and templates are built-in
- **No installation** - runs directly

### Where to Store It
- **Windows**: Desktop or `C:\Users\[YourName]\Documents`
- **Mac**: Applications folder or Desktop
- **Linux**: `/home/[username]/bin` or Desktop
- **Any platform**: Create a "Philmont Tools" folder

## 🛡️ Security & Privacy

### Is It Safe?
- ✅ **Open Source** - All code is publicly available on GitHub
- ✅ **No Network Access** - App works completely offline
- ✅ **No Data Collection** - Your preferences stay on your computer
- ✅ **Digitally Signed** - Releases are built automatically from verified source code

### Antivirus Warnings
Some antivirus software may flag the executable because it's relatively new:
- This is normal for Python-compiled apps
- You can safely allow/whitelist the file
- Check the GitHub release page shows official build status

## 🏕️ About the Data

### Trek Information Included
- **All 84 Itineraries** from 2024 Philmont guidebook
- **169 Backcountry Camps** with elevation data
- **56+ Activity Programs** with detailed descriptions
- **Daily Schedules** for each trek day
- **Elevation Profiles** and distance information

### Data Accuracy
- Based on official 2024 Philmont Itinerary Guidebook
- Carefully cross-checked with Philmont's published information
- Regularly updated when new guidebooks are released

## 🆘 Getting Help

### Need Support?
1. **Check this guide first** - Most common issues are covered above
2. **Search existing issues** on the [GitHub Issues page](https://github.com/irxbacon/phil_select/issues)
3. **Create a new issue** if you find a bug or need help
4. **Include details**: Your operating system, what you tried, and any error messages

### Want to Contribute?
- Report bugs or suggest features via GitHub Issues
- The app is open source - developers welcome to contribute
- Help improve this documentation

## 📊 Understanding Your Results

### Score Components
Your trek recommendations are based on several factors:

- **Program Score** (200-800+ points): Based on activity ratings × 1.5
- **Camp Score** (100-600 points): Optimized for camp types and quality  
- **Difficulty Score** (0 or 2000+ points): Full points if trek matches your preferences
- **Distance Score** (4000-6000 points): Based on your distance preferences
- **Area Score** (0-1000 points): Bonus for preferred regions
- **Peak Score** (0-500+ points): Bonus for desired mountain climbs

**Higher total scores = Better matches for your crew**

### Interpreting Rankings
- **Top 5 treks**: Excellent matches worth serious consideration
- **Top 10 treks**: Good options that meet most of your criteria  
- **Lower ranked treks**: May miss key preferences but still viable
- **Use judgment**: Scores are guidance - consider crew dynamics too

## 🎯 Tips for Best Results

### Before You Start
- **Involve your whole crew** in setting preferences
- **Be realistic** about difficulty levels your crew can handle
- **Consider all crew members** when rating activity programs
- **Think about timing** - some programs may conflict with your dates

### Getting Better Recommendations  
- **Rate more programs** - More data gives better recommendations
- **Use the full 0-20 scale** - Don't just use 10, 15, 20
- **Consider crew variety** - Balance different interests and abilities
- **Review trek details** - Scores are just the starting point

---

## 🏔️ Ready to Plan Your Adventure?

**[Download the Latest Release →](https://github.com/irxbacon/phil_select/releases/latest)**

*This tool provides recommendations only. Final trek selection and reservations are handled through Philmont Scout Ranch's official systems.*

**Questions?** Open an issue on [GitHub](https://github.com/irxbacon/phil_select/issues) or check the [full documentation](README.md).