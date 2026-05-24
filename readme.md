# 📱 WhatsApp Bulk Messenger
### by Karthick Kumar M — Python 3.12 | Cross-Platform

A powerful CLI tool to send WhatsApp messages silently in the background using Playwright browser automation. No WhatsApp API key needed — uses your own WhatsApp account.

---

## ✅ Requirements

- Python 3.12+
- Google Chrome or Chromium (installed on your system)
- Internet connection
- WhatsApp account on your phone

---

## 🚀 Installation

### Ubuntu / Linux

```bash
# 1. Clone or copy the folder
cd whatsapp-sender

# 2. Install Python dependencies
pip3 install -r requirements.txt

# 3. Install Playwright browsers (downloads Chromium)
playwright install chromium

# 4. Make shell script executable
chmod +x run_linux.sh

# 5. First-time setup: scan QR code
python3 wa_send.py --setup
```

### Windows

```bat
:: 1. Open Command Prompt in the folder

:: 2. Install Python dependencies
pip install -r requirements.txt

:: 3. Install Playwright browsers
playwright install chromium

:: 4. First-time setup: scan QR code
python wa_send.py --setup
```

---

## 🔐 First-Time Setup (QR Code — One Time Only!)

```bash
python3 wa_send.py --setup        # Ubuntu
python wa_send.py --setup         # Windows
```

This opens a **visible browser window**:
1. Go to your phone → WhatsApp → Linked Devices → Link a Device
2. Scan the QR code shown in the browser
3. Wait for your chats to fully load
4. Press **ENTER** in the terminal

✅ **Session is saved! You never need to scan again.**

---

## 💻 Usage

### Interactive Menu (easiest)
```bash
python3 wa_send.py
```

### Send to a saved contact
```bash
python3 wa_send.py --to "John"
```

### Send to a phone number directly
```bash
python3 wa_send.py --to "+919876543210"
```

### Send with a custom message
```bash
python3 wa_send.py --to "John" --message "Hey! Check this out 🔥"
```

### Send promo message (default) to one contact
```bash
python3 wa_send.py --to "John"
# No message = automatically uses Karthick's promo message
```

### Broadcast to ALL saved contacts
```bash
python3 wa_send.py --broadcast
python3 wa_send.py --broadcast --message "Custom message to everyone"
```

### View sent message log
```bash
python3 wa_send.py --log
```

### List all saved contacts
```bash
python3 wa_send.py --contacts
```

### Show browser window (debug / re-login)
```bash
python3 wa_send.py --no-headless
```

---

## 📋 Menu Commands (Interactive Mode)

| Command | Action |
|---------|--------|
| `send`  | Send message interactively |
| `add`   | Add a new contact |
| `list`  | List all saved contacts |
| `del`   | Delete a contact |
| `tmpl`  | Manage message templates |
| `log`   | View sent message history |
| `sched` | Schedule a message for later |
| `setup` | Re-scan QR code |
| `quit`  | Exit |

---

## ✨ Features

- 🔇 **Silent background sending** — browser is hidden (headless)
- 📖 **Contact book** — save names + numbers locally
- 📝 **Message templates** — reuse common messages
- 📢 **Broadcast** — send to all contacts at once
- ⏰ **Scheduler** — send at a specific time (HH:MM)
- 📜 **Message log** — history of all sent messages
- 🤖 **Auto promo message** — Karthick's default promo if no message given
- 🛡 **Smart delay** — configurable delay between broadcasts to avoid bans
- 🌍 **Cross-platform** — works on Ubuntu & Windows

---

## 📁 File Structure

```
whatsapp-sender/
├── wa_send.py          ← Main app
├── contacts.json       ← Your saved contacts
├── templates.json      ← Message templates
├── message_log.json    ← Auto-created, sent history
├── wa_session/         ← Auto-created, WhatsApp login session
├── requirements.txt    ← Python packages
├── run_linux.sh        ← Ubuntu launcher
├── run_windows.bat     ← Windows launcher
└── README.md           ← This file
```

---

## ⚠️ Notes & Tips

- **Keep delays reasonable** — Use 8-10s+ between messages in broadcasts to avoid WhatsApp flagging your account
- **Session expires rarely** — But if it does, just run `--setup` again
- **Phone must be connected** — WhatsApp Web requires your phone to have internet
- **Country code required** — Always include `+91`, `+1`, etc. in phone numbers
- **WhatsApp ToS** — This uses browser automation, not the official API. Use responsibly and avoid spam

---

## 🆘 Troubleshooting

| Problem | Fix |
|---------|-----|
| `playwright not found` | Run `pip install playwright` then `playwright install chromium` |
| QR code keeps appearing | Run `python wa_send.py --setup` again |
| Message not sending | Run with `--no-headless` to see what's happening |
| Session expired | Run `python wa_send.py --setup` to re-login |
| Phone number invalid | Make sure to include country code: `+919876543210` |

---

Made with ❤️ by Karthick Kumar M