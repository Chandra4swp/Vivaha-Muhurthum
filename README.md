# 💍 Vivaha Muhurthum – Offline Local App

A complete offline matrimonial web application built with Python (Flask) + SQLite.
All data and photos are stored **locally on your machine**.

---

## 📁 Project Structure

```
matrimonial/
├── app.py                  ← Main Flask application
├── requirements.txt        ← Python dependencies
├── matrimonial.db          ← SQLite database (auto-created on first run)
├── static/
│   └── uploads/            ← Profile photos stored here
└── templates/
    ├── base.html
    ├── index.html          ← Home page
    ├── register.html       ← Profile registration
    ├── search.html         ← Search by name/email/ID
    ├── browse.html         ← Browse all profiles with filters
    ├── profile.html        ← Individual profile view
    └── 404.html
```

---

## 🚀 Setup & Run

### Step 1 – Install Python
Make sure Python 3.8+ is installed:
```bash
python --version
```

### Step 2 – Install dependencies
```bash
cd matrimonial
pip install -r requirements.txt
```

### Step 3 – Run the app
```bash
python app.py
```

### Step 4 – Open in browser
```
http://127.0.0.1:5000
```

---

## 📱 Mobile Access (Same WiFi Network)

To access from your phone on the same WiFi network:

1. Find your computer's local IP:
   - Windows: `ipconfig` → look for IPv4 Address
   - Mac/Linux: `ifconfig` or `ip addr`

2. The app already runs on `0.0.0.0`, so open on phone:
   ```
   http://YOUR_COMPUTER_IP:5000
   ```
   Example: `http://192.168.1.100:5000`

---

## 📲 Installable Mobile App Support

This portal now includes Progressive Web App configuration so mobile users can install it like an app:

- `static/manifest.json` defines app name, icons, theme, and standalone display mode
- `static/service-worker.js` caches key assets for faster load and offline compatibility
- `static/icons/` includes install icons used by mobile browsers
- `templates/base.html` registers the service worker and links the manifest

### How to install on mobile

- On Android: open the site in Chrome and choose "Add to Home screen"
- On iOS: open in Safari, tap the Share button, and select "Add to Home Screen"

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Register Profile** | Full matrimonial form with photo upload |
| **Search** | Search by name, email, or profile ID |
| **Browse** | Browse all profiles with gender/religion/education filters |
| **Profile View** | Detailed profile page |
| **Login / Sign Up** | Local user authentication stored in the SQLite database |
| **Photo Storage** | Photos saved in `static/uploads/` folder |
| **Offline** | Works 100% without internet |
| **Mobile-friendly** | Responsive design |

---

## 🗄️ Database

- SQLite database file: `matrimonial.db`
- Auto-created on first run
- Each profile gets a unique ID like `MAT1A2B3C4D`

---

## 🔒 Privacy

- All data stays on your local machine
- No internet connection required
- No data sent to any server
