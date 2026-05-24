#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║       WhatsApp Bulk Messenger — FINAL VERSION        ║
║       by Karthick Kumar M                            ║
║       Cross-platform | Python 3.12 | Playwright      ║
╚══════════════════════════════════════════════════════╝
"""

import asyncio
import argparse
import json
import sys
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo          # Python 3.9+ built-in

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.text import Text
from rich.rule import Rule
from rich import box

# ── IST timezone (built-in, no pytz needed) ─────────────────────────────────
IST = ZoneInfo("Asia/Kolkata")

# ── Paths (cross-platform) ───────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent
CONTACTS_FILE  = BASE_DIR / "contacts.json"
TEMPLATES_FILE = BASE_DIR / "templates.json"
LOG_FILE       = BASE_DIR / "message_log.json"
SESSION_DIR    = BASE_DIR / "wa_session"

# ── Default promo message ────────────────────────────────────────────────────
DEFAULT_MESSAGE = (
    "Hey! 👋 My name is *Karthick Kumar M*.\n"
    "I am a *Web Designer* 🎨 and I can build you a stunning, "
    "professional website tailored just for your needs! 🚀\n"
    "Interested? Let's connect! 💼"
)

console = Console()

# ── Sentinel to signal "go back to previous menu" ───────────────────────────
class GoBack(Exception): pass
class ExitApp(Exception): pass

# ═══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def load_json(path: Path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_contacts():  return load_json(CONTACTS_FILE, {})
def save_contacts(c): save_json(CONTACTS_FILE, c)
def load_templates(): return load_json(TEMPLATES_FILE, {
    "promo":    DEFAULT_MESSAGE,
    "followup": "Hey! 👋 Just following up — have you had a chance to think about that website? Let me know! 😊",
    "greeting": "Hi there! Hope you're having a great day! 🌟",
    "offer":    "🔥 Special Offer! Get a professional website by *Karthick Kumar M* at an unbeatable price this month! DM me 💻✨",
})
def save_templates(t): save_json(TEMPLATES_FILE, t)

def load_log(): return load_json(LOG_FILE, [])
def log_message(to_name, phone, message, status, scheduled_for=None):
    log = load_log()
    entry = {
        "timestamp":     datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
        "to":            to_name,
        "phone":         phone,
        "message":       message[:80] + ("..." if len(message) > 80 else ""),
        "status":        status,
    }
    if scheduled_for:
        entry["scheduled_for"] = scheduled_for
    log.append(entry)
    save_json(LOG_FILE, log)

def format_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    return phone

def now_ist() -> datetime:
    return datetime.now(IST)

def ask(prompt: str, **kwargs) -> str:
    """Prompt wrapper — typing 'back' raises GoBack, 'exit' raises ExitApp."""
    val = Prompt.ask(f"  {prompt}", **kwargs)
    if val.strip().lower() == "back": raise GoBack()
    if val.strip().lower() == "exit": raise ExitApp()
    return val

def nav_hint():
    console.print("  [dim]  (type 'back' = previous menu  |  'exit' = quit app)[/dim]")

# ═══════════════════════════════════════════════════════════════════════════
#  BANNER
# ═══════════════════════════════════════════════════════════════════════════

def print_banner():
    console.print()
    banner = Text()
    banner.append("  ██╗    ██╗ █████╗      ", style="bold green")
    banner.append("SENDER\n", style="bold white")
    banner.append("  ██║    ██║██╔══██╗     ", style="bold green")
    banner.append("WhatsApp Bulk Messenger\n", style="dim white")
    banner.append("  ██║ █╗ ██║███████║     ", style="bold green")
    banner.append("by Karthick Kumar M\n", style="dim cyan")
    banner.append("  ██║███╗██║██╔══██║     ", style="bold green")
    banner.append("Python 3.12 | Playwright\n", style="dim white")
    banner.append("  ╚███╔███╔╝██║  ██║     ", style="bold green")
    banner.append("Cross-Platform ✓\n", style="dim white")
    banner.append("   ╚══╝╚══╝ ╚═╝  ╚═╝\n", style="bold green")
    console.print(Panel(banner, border_style="green", padding=(0, 2)))
    console.print()

# ═══════════════════════════════════════════════════════════════════════════
#  PLAYWRIGHT SENDER
# ═══════════════════════════════════════════════════════════════════════════

MAIN_SELECTORS = [
    '[data-testid="chat-list"]',
    '[data-testid="default-user"]',
    'div[aria-label="Chat list"]',
    '#pane-side',
    '#main',
]
INPUT_SELECTORS = [
    'div[contenteditable="true"][data-tab="10"]',
    'div[contenteditable="true"][data-tab="1"]',
    'div[contenteditable="true"][title="Type a message"]',
    'div[contenteditable="true"][aria-label="Type a message"]',
    'footer div[contenteditable="true"]',
]

async def send_whatsapp_message(phone: str, message: str, headless: bool = True) -> bool:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    encoded_msg = urllib.parse.quote(message)
    chat_url    = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_msg}"

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.set_extra_http_headers({"User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )})

        try:
            console.print("  [dim]↳ Loading WhatsApp Web...[/dim]")
            await page.goto("https://web.whatsapp.com", timeout=90_000,
                            wait_until="domcontentloaded")
            await page.wait_for_timeout(6_000)

            logged_in = False
            for sel in MAIN_SELECTORS:
                try:
                    await page.wait_for_selector(sel, timeout=15_000)
                    logged_in = True
                    console.print("  [dim]↳ Session found ✅[/dim]")
                    break
                except PWTimeout:
                    continue

            if not logged_in:
                console.print(Panel(
                    "[bold yellow]📱 NOT LOGGED IN — Session Expired[/bold yellow]\n\n"
                    "Run: [bold cyan]python wa_send.py --setup[/bold cyan]",
                    border_style="yellow", title="Re-login Required"
                ))
                await browser.close()
                return False

            console.print(f"  [dim]↳ Opening chat with {phone}...[/dim]")
            await page.goto(chat_url, timeout=90_000, wait_until="domcontentloaded")
            await page.wait_for_timeout(8_000)

            input_box = None
            for sel in INPUT_SELECTORS:
                try:
                    input_box = await page.wait_for_selector(sel, timeout=15_000)
                    if input_box:
                        console.print("  [dim]↳ Input box found ✅[/dim]")
                        break
                except PWTimeout:
                    continue

            if not input_box:
                console.print("  [red]❌ Could not find message input. Run --no-headless to debug.[/red]")
                await browser.close()
                return False

            await input_box.click()
            await page.wait_for_timeout(500)
            await page.evaluate(
                "(text) => { document.execCommand('selectAll'); "
                "document.execCommand('insertText', false, text); }",
                message
            )
            await page.wait_for_timeout(1_000)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(3_000)
            console.print("  [dim]↳ Message sent ✅[/dim]")
            await browser.close()
            return True

        except PWTimeout as e:
            console.print(f"  [red]❌ Timeout: {e}[/red]")
            await browser.close()
            return False
        except Exception as e:
            console.print(f"  [red]❌ Error: {e}[/red]")
            await browser.close()
            return False


async def setup_session():
    from playwright.async_api import async_playwright
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    console.print(Panel(
        "[bold green]🔐 SETUP MODE — Scan QR Code[/bold green]\n\n"
        "1. Chrome browser will open\n"
        "2. Scan the WhatsApp QR code with your phone\n"
        "3. Wait until your chats fully load\n"
        "4. Press [bold]ENTER[/bold] here to save & close\n\n"
        "[dim]After this, all future sends work silently in background![/dim]",
        border_style="green", title="One-Time Setup"
    ))
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR), headless=False)
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto("https://web.whatsapp.com", timeout=60_000)
        console.print("\n[bold yellow]⏳ Scan the QR code in the browser window...[/bold yellow]")
        input("\n  ✅ Press ENTER after your chats are fully loaded: ")
        await browser.close()
    console.print("[bold green]✅ Session saved! Future sends are fully silent.[/bold green]\n")

# ═══════════════════════════════════════════════════════════════════════════
#  NUMBER VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def verify_number(phone: str, name: str) -> bool:
    """
    Shows a confirmation panel with the number and asks user to verify.
    Returns True if confirmed, False if user wants to re-enter.
    """
    console.print()
    console.print(Panel(
        f"[bold yellow]🔍 Please verify the recipient details:[/bold yellow]\n\n"
        f"  Name  : [bold cyan]{name}[/bold cyan]\n"
        f"  Phone : [bold white]{phone}[/bold white]\n\n"
        f"[dim]Make sure the country code and digits are correct.\n"
        f"Wrong number = message goes to a stranger! 😬[/dim]",
        border_style="yellow",
        title="⚠️  Number Verification"
    ))
    return Confirm.ask("  ✅ Yes, this number is correct — send!", default=True)

# ═══════════════════════════════════════════════════════════════════════════
#  SCHEDULE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

async def pick_schedule_time() -> datetime | None:
    """
    Inline schedule picker — shown during send flow.
    Returns a datetime (IST) to send at, or None = send immediately.
    Raises GoBack / ExitApp.
    """
    console.print()
    console.print(Rule("[bold yellow]⏰ When to send?[/bold yellow]", style="yellow"))
    nav_hint()
    console.print()
    console.print("  [cyan]1.[/cyan] Send immediately")
    console.print("  [cyan]2.[/cyan] Send after N minutes  (e.g. after 5 mins)")
    console.print("  [cyan]3.[/cyan] Send at specific IST time  (e.g. 14:30)")
    console.print("  [cyan]b.[/cyan] ← Previous menu")
    console.print("  [cyan]x.[/cyan] Exit app")
    console.print()

    while True:
        choice = ask("[bold yellow]Choice[/bold yellow]", default="1")

        if choice == "1":
            return None   # immediate

        elif choice == "2":
            mins_str = ask("  After how many minutes?", default="5")
            try:
                mins = int(mins_str)
                if mins <= 0: raise ValueError()
                target = now_ist() + timedelta(minutes=mins)
                console.print(
                    f"  [green]✅ Will send at [bold]{target.strftime('%H:%M:%S IST')}[/bold] "
                    f"({mins} min from now)[/green]"
                )
                return target
            except ValueError:
                console.print("  [red]Enter a valid positive number.[/red]")

        elif choice == "3":
            time_str = ask("  IST time (HH:MM, 24h)", default="")
            try:
                h, m = map(int, time_str.split(":"))
                now  = now_ist()
                target = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if target <= now:
                    console.print("  [red]That time has already passed today.[/red]")
                    continue
                wait_secs = (target - now).total_seconds()
                console.print(
                    f"  [green]✅ Will send at [bold]{target.strftime('%H:%M IST')}[/bold] "
                    f"({int(wait_secs//60)}m {int(wait_secs%60)}s from now)[/green]"
                )
                return target
            except (ValueError, AttributeError):
                console.print("  [red]Invalid format. Use HH:MM (e.g. 14:30)[/red]")

        elif choice in ("b", "back"):
            raise GoBack()
        elif choice in ("x", "exit"):
            raise ExitApp()
        else:
            console.print("  [red]Choose 1, 2, 3, b, or x[/red]")


async def wait_until(target: datetime):
    """Countdown to target IST datetime with live display. Ctrl+C cancels."""
    while True:
        remaining = (target - now_ist()).total_seconds()
        if remaining <= 0:
            break
        mins = int(remaining // 60)
        secs = int(remaining % 60)
        console.print(
            f"  [yellow]⏳ Sending in {mins:02d}:{secs:02d} — "
            f"[dim]Press Ctrl+C to cancel[/dim][/yellow]",
            end="\r"
        )
        await asyncio.sleep(1)
    console.print(" " * 70, end="\r")   # clear line

# ═══════════════════════════════════════════════════════════════════════════
#  DO SEND  (actual send + log)
# ═══════════════════════════════════════════════════════════════════════════

async def do_send(phone: str, name: str, message: str,
                  headless: bool = True, scheduled_for: str = None):
    with Progress(
        SpinnerColumn(style="green"),
        TextColumn("[bold green]{task.description}"),
        transient=True, console=console
    ) as prog:
        prog.add_task(f"Sending to {name} ({phone})...", total=None)
        success = await send_whatsapp_message(phone, message, headless=headless)

    if success:
        console.print(f"  [bold green]✅ Sent to {name} ({phone})[/bold green]")
        log_message(name, phone, message, "✅ Sent", scheduled_for)
    else:
        console.print(f"  [bold red]❌ Failed → {name} ({phone})[/bold red]")
        log_message(name, phone, message, "❌ Failed", scheduled_for)
    return success

# ═══════════════════════════════════════════════════════════════════════════
#  CONTACT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def cmd_add_contact():
    console.print(Panel("[bold cyan]➕ Add New Contact[/bold cyan]", border_style="cyan"))
    nav_hint()
    contacts = load_contacts()
    name  = ask("Contact Name")
    phone = ask("Phone (with country code, e.g. +919876543210)")
    phone = format_phone(phone)

    # Verify before saving
    if not verify_number(phone, name):
        new_phone = ask("Enter correct phone number")
        phone = format_phone(new_phone)

    contacts[name] = phone
    save_contacts(contacts)
    console.print(f"  [bold green]✅ '{name}' ({phone}) saved![/bold green]\n")

def cmd_list_contacts():
    contacts = load_contacts()
    if not contacts:
        console.print("  [yellow]No contacts saved yet. Use 'add' to add contacts.[/yellow]\n")
        return contacts
    table = Table(title="📖 Contact Book", box=box.ROUNDED, border_style="green", show_lines=True)
    table.add_column("#",     style="dim",         no_wrap=True, width=4)
    table.add_column("Name",  style="bold cyan",   no_wrap=True)
    table.add_column("Phone", style="bold white")
    for i, (name, phone) in enumerate(contacts.items(), 1):
        table.add_row(str(i), name, phone)
    console.print(table)
    console.print()
    return contacts

def cmd_delete_contact():
    contacts = load_contacts()
    if not contacts:
        console.print("  [yellow]No contacts to delete.[/yellow]\n"); return
    console.print(Panel("[bold red]🗑  Delete Contact[/bold red]", border_style="red"))
    nav_hint()
    for i, name in enumerate(contacts, 1):
        console.print(f"  [cyan]{i}.[/cyan] {name} — {contacts[name]}")
    try:
        name = ask("Contact name to delete")
        if name in contacts:
            if Confirm.ask(f"  Delete [bold red]{name}[/bold red]?"):
                del contacts[name]
                save_contacts(contacts)
                console.print(f"  [green]✅ Deleted {name}[/green]\n")
        else:
            console.print("  [red]Contact not found.[/red]\n")
    except GoBack:
        return

# ═══════════════════════════════════════════════════════════════════════════
#  TEMPLATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def cmd_list_templates():
    templates = load_templates()
    table = Table(title="📝 Message Templates", box=box.ROUNDED,
                  border_style="magenta", show_lines=True)
    table.add_column("Name",    style="bold magenta", no_wrap=True)
    table.add_column("Preview", style="dim white", max_width=60)
    for name, msg in templates.items():
        preview = msg.replace("\n", " ")
        preview = preview[:75] + ("..." if len(preview) > 75 else "")
        table.add_row(name, preview)
    console.print(table)
    console.print()
    return templates

def cmd_add_template():
    console.print(Panel("[bold magenta]➕ Add Message Template[/bold magenta]",
                        border_style="magenta"))
    nav_hint()
    templates = load_templates()
    try:
        name = ask("Template name (e.g. promo2)")
        console.print("  Enter message (press ENTER twice to finish):")
        lines = []
        while True:
            line = input("  ")
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        message = "\n".join(lines[:-1] if lines and lines[-1] == "" else lines)
        templates[name] = message
        save_templates(templates)
        console.print(f"  [green]✅ Template '{name}' saved![/green]\n")
    except GoBack:
        return

# ═══════════════════════════════════════════════════════════════════════════
#  LOG VIEWER
# ═══════════════════════════════════════════════════════════════════════════

def cmd_view_log():
    log = load_log()
    if not log:
        console.print("  [yellow]No messages sent yet.[/yellow]\n"); return
    table = Table(title="📜 Message History (last 25)", box=box.ROUNDED,
                  border_style="blue", show_lines=True)
    table.add_column("Time",          style="dim",       no_wrap=True)
    table.add_column("To",            style="bold cyan", no_wrap=True)
    table.add_column("Phone",         style="white",     no_wrap=True)
    table.add_column("Message",       style="dim white", max_width=38)
    table.add_column("Status",        style="bold",      no_wrap=True)
    table.add_column("Scheduled For", style="dim",       no_wrap=True)
    for entry in reversed(log[-25:]):
        table.add_row(
            entry.get("timestamp", ""),
            entry.get("to", ""),
            entry.get("phone", ""),
            entry.get("message", ""),
            entry.get("status", ""),
            entry.get("scheduled_for", "—"),
        )
    console.print(table)
    console.print(f"  [dim]Showing last {min(25, len(log))} of {len(log)} total[/dim]\n")

# ═══════════════════════════════════════════════════════════════════════════
#  SEND FLOW  (interactive, with schedule + verify + back/exit at every step)
# ═══════════════════════════════════════════════════════════════════════════

async def cmd_send_interactive(headless: bool = True):
    contacts  = load_contacts()
    templates = load_templates()

    console.print(Panel("[bold green]📤 Send WhatsApp Message[/bold green]",
                        border_style="green"))
    nav_hint()

    # ────────────────────────────────────────────────────────────────────
    # STEP 1 — Who to send to?
    # ────────────────────────────────────────────────────────────────────
    console.print(Rule("[bold]Step 1 — Recipient[/bold]", style="green"))
    console.print()

    if contacts:
        console.print("  [cyan]1.[/cyan] Choose from saved contacts")
        console.print("  [cyan]2.[/cyan] Enter phone number manually")
        console.print("  [cyan]3.[/cyan] Broadcast to ALL contacts")
        console.print("  [cyan]b.[/cyan] ← Back   [cyan]x.[/cyan] Exit")
        console.print()
        choice = ask("[bold]Who to send to?[/bold]", default="1")
    else:
        console.print("  [yellow]No saved contacts. Enter number manually.[/yellow]")
        choice = "2"

    recipients = []   # list of (name, phone)

    if choice == "1":
        cmd_list_contacts()
        while True:
            cname = ask("Contact name")
            if cname in contacts:
                phone = contacts[cname]
                # ── Number verification ──────────────────────────────────
                if not verify_number(phone, cname):
                    console.print("  [yellow]Let's correct it. Update in contact book? (y) or just re-enter for this send? (n)[/yellow]")
                    fix_in_book = Confirm.ask("  Update in contact book?", default=False)
                    new_phone = format_phone(ask("Correct phone number"))
                    if fix_in_book:
                        contacts[cname] = new_phone
                        save_contacts(contacts)
                        console.print(f"  [green]✅ Contact book updated.[/green]")
                    phone = new_phone
                recipients = [(cname, phone)]
                break
            else:
                console.print("  [red]Contact not found. Try again or type 'back'.[/red]")

    elif choice == "2":
        while True:
            phone = format_phone(ask("Phone number (with country code, e.g. +919876543210)"))
            name  = ask("Label / Name for this send", default=phone)
            # ── Number verification ──────────────────────────────────────
            if verify_number(phone, name):
                recipients = [(name, phone)]
                break
            else:
                console.print("  [yellow]Let's re-enter the details.[/yellow]")

    elif choice == "3":
        if not contacts:
            console.print("  [red]No contacts saved.[/red]"); return
        recipients = list(contacts.items())
        console.print(f"\n  [bold yellow]📢 Broadcasting to {len(recipients)} contacts[/bold yellow]")

    elif choice in ("b", "back"):
        raise GoBack()
    elif choice in ("x", "exit"):
        raise ExitApp()
    else:
        console.print("  [red]Invalid choice.[/red]"); return

    # ────────────────────────────────────────────────────────────────────
    # STEP 2 — What message?
    # ────────────────────────────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold]Step 2 — Message[/bold]", style="green"))
    console.print()
    console.print("  [cyan]1.[/cyan] Type a custom message")
    console.print("  [cyan]2.[/cyan] Choose from saved templates")
    console.print("  [cyan]3.[/cyan] Use default promo message (Karthick's auto-message)")
    console.print("  [cyan]b.[/cyan] ← Back   [cyan]x.[/cyan] Exit")
    console.print()

    msg_choice = ask("[bold]Message choice[/bold]", default="3")

    if msg_choice == "1":
        console.print("  Type your message below. Press ENTER twice when done:")
        lines = []
        while True:
            line = input("  ")
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        message = "\n".join(lines[:-1] if lines and lines[-1] == "" else lines)
        if not message.strip():
            console.print("  [yellow]Empty message — using promo.[/yellow]")
            message = DEFAULT_MESSAGE

    elif msg_choice == "2":
        cmd_list_templates()
        while True:
            tname = ask("Template name (or 'back')")
            if tname in templates:
                message = templates[tname]
                break
            console.print("  [red]Template not found. Try again.[/red]")

    elif msg_choice == "3":
        message = DEFAULT_MESSAGE
        console.print(f"\n  [dim]Auto-message preview:[/dim]\n"
                      f"  [italic cyan]{message[:100]}...[/italic cyan]")

    elif msg_choice in ("b", "back"):
        raise GoBack()
    elif msg_choice in ("x", "exit"):
        raise ExitApp()
    else:
        message = DEFAULT_MESSAGE

    # ────────────────────────────────────────────────────────────────────
    # STEP 3 — Schedule?
    # ────────────────────────────────────────────────────────────────────
    send_target = await pick_schedule_time()   # None = immediate
    scheduled_label = send_target.strftime("%Y-%m-%d %H:%M IST") if send_target else None

    # ────────────────────────────────────────────────────────────────────
    # STEP 4 — Delay between messages (broadcast only)
    # ────────────────────────────────────────────────────────────────────
    delay = 8
    if len(recipients) > 1:
        console.print()
        delay_str = ask("  Delay between messages (seconds)", default="8")
        try:
            delay = max(3, int(delay_str))
        except ValueError:
            delay = 8

    # ────────────────────────────────────────────────────────────────────
    # STEP 5 — Final confirmation
    # ────────────────────────────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold]Step 5 — Confirm & Send[/bold]", style="yellow"))

    summary = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    summary.add_column("", style="dim", width=16)
    summary.add_column("", style="bold white")
    summary.add_row("Recipients",  f"{len(recipients)} contact(s)")
    for name, phone in recipients[:5]:
        summary.add_row("", f"  • {name} ({phone})")
    if len(recipients) > 5:
        summary.add_row("", f"  ... and {len(recipients)-5} more")
    summary.add_row("Message",     message[:60] + ("..." if len(message) > 60 else ""))
    summary.add_row("Schedule",    scheduled_label or "Send immediately")
    if len(recipients) > 1:
        summary.add_row("Delay", f"{delay}s between messages")

    console.print(Panel(summary, border_style="yellow", title="[bold]📋 Summary[/bold]"))
    console.print()
    console.print("  [cyan]y[/cyan] → Confirm & send")
    console.print("  [cyan]b[/cyan] → Back to menu")
    console.print("  [cyan]x[/cyan] → Exit app")
    console.print()

    confirm = ask("Proceed?", default="y")
    if confirm.lower() in ("n", "no", "b", "back"):
        raise GoBack()
    if confirm.lower() in ("x", "exit"):
        raise ExitApp()

    # ────────────────────────────────────────────────────────────────────
    # STEP 6 — Wait if scheduled, then send
    # ────────────────────────────────────────────────────────────────────
    if send_target:
        console.print()
        console.print(Panel(
            f"[bold yellow]⏰ Scheduled at {scheduled_label}[/bold yellow]\n"
            f"[dim]Keep this terminal open. Press Ctrl+C anytime to cancel.[/dim]",
            border_style="yellow"
        ))
        try:
            await wait_until(send_target)
        except asyncio.CancelledError:
            console.print("\n  [red]❌ Schedule cancelled by user.[/red]\n")
            return
        except KeyboardInterrupt:
            console.print("\n  [red]❌ Schedule cancelled (Ctrl+C).[/red]\n")
            return

    console.print()
    success_count = 0
    for i, (name, phone) in enumerate(recipients):
        ok = await do_send(phone, name, message,
                           headless=headless, scheduled_for=scheduled_label)
        if ok:
            success_count += 1
        if i < len(recipients) - 1:
            console.print(f"  [dim]⏳ Waiting {delay}s...[/dim]")
            await asyncio.sleep(delay)

    console.print()
    color = "green" if success_count == len(recipients) else "yellow"
    console.print(Panel(
        f"[bold {color}]{'✅' if success_count == len(recipients) else '⚠️'} "
        f"Sent {success_count} / {len(recipients)}[/bold {color}]",
        border_style=color, title="Done"
    ))

# ═══════════════════════════════════════════════════════════════════════════
#  MAIN MENU
# ═══════════════════════════════════════════════════════════════════════════

def print_menu():
    now = now_ist().strftime("%H:%M IST")
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 3))
    table.add_column("Key",    style="bold green", no_wrap=True, width=8)
    table.add_column("Action", style="white")
    rows = [
        ("send",  "📤 Send / Broadcast / Schedule message"),
        ("add",   "➕ Add contact"),
        ("list",  "📖 List contacts"),
        ("del",   "🗑  Delete contact"),
        ("tmpl",  "📝 Manage templates"),
        ("log",   "📜 View sent log"),
        ("setup", "🔐 QR scan / re-login"),
        ("quit",  "🚪 Exit"),
    ]
    for key, action in rows:
        table.add_row(key, action)
    console.print(Panel(
        table,
        title=f"[bold green]MAIN MENU[/bold green]  [dim]{now}[/dim]",
        border_style="green"
    ))

async def main_menu(headless: bool = True):
    print_banner()
    while True:
        print_menu()
        console.print("  [dim](type 'exit' anywhere to quit)[/dim]")
        choice = Prompt.ask("\n  [bold green]Command[/bold green]").strip().lower()
        console.print()

        try:
            if choice == "send":
                try:
                    await cmd_send_interactive(headless=headless)
                except GoBack:
                    console.print("  [yellow]↩ Back to main menu.[/yellow]\n")

            elif choice == "add":
                try:
                    cmd_add_contact()
                except GoBack:
                    console.print("  [yellow]↩ Back to main menu.[/yellow]\n")

            elif choice == "list":
                cmd_list_contacts()

            elif choice == "del":
                try:
                    cmd_delete_contact()
                except GoBack:
                    console.print("  [yellow]↩ Back to main menu.[/yellow]\n")

            elif choice == "tmpl":
                console.print("  [cyan]1.[/cyan] List templates")
                console.print("  [cyan]2.[/cyan] Add new template")
                console.print("  [cyan]b.[/cyan] Back")
                sub = Prompt.ask("  Choice", default="1")
                if sub == "1":
                    cmd_list_templates()
                elif sub == "2":
                    try:
                        cmd_add_template()
                    except GoBack:
                        pass

            elif choice == "log":
                cmd_view_log()

            elif choice == "setup":
                await setup_session()

            elif choice in ("quit", "exit", "q", "x"):
                raise ExitApp()

            else:
                console.print("  [red]Unknown command.[/red]\n")

        except ExitApp:
            console.print("\n  [bold green]👋 Goodbye! Made by Karthick Kumar M[/bold green]\n")
            sys.exit(0)

        except KeyboardInterrupt:
            console.print("\n  [yellow]Interrupted. Back to menu.[/yellow]\n")

# ═══════════════════════════════════════════════════════════════════════════
#  CLI ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="WhatsApp Bulk Messenger — by Karthick Kumar M",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python wa_send.py                                   Interactive menu
  python wa_send.py --setup                           First-time QR scan
  python wa_send.py --to "Karthi"                     Send promo to contact
  python wa_send.py --to "+919876543210" --message "Hi!"
  python wa_send.py --broadcast                       Promo to ALL contacts
  python wa_send.py --broadcast --message "Custom"
  python wa_send.py --log                             View sent history
  python wa_send.py --contacts                        List saved contacts
  python wa_send.py --no-headless                     Show browser (debug)
        """
    )
    parser.add_argument("--setup",       action="store_true")
    parser.add_argument("--to",          type=str)
    parser.add_argument("--message",     type=str)
    parser.add_argument("--broadcast",   action="store_true")
    parser.add_argument("--no-headless", action="store_true")
    parser.add_argument("--log",         action="store_true")
    parser.add_argument("--contacts",    action="store_true")
    return parser.parse_args()


async def run():
    args = parse_args()
    hl   = not args.no_headless

    print_banner()

    if args.log:      cmd_view_log();     return
    if args.contacts: cmd_list_contacts(); return
    if args.setup:    await setup_session(); return

    if args.broadcast:
        contacts = load_contacts()
        if not contacts:
            console.print("  [red]No contacts saved.[/red]\n"); return
        message = args.message or DEFAULT_MESSAGE
        console.print(f"  [bold yellow]📢 Broadcasting to {len(contacts)} contacts...[/bold yellow]\n")
        for i, (name, phone) in enumerate(contacts.items()):
            await do_send(phone, name, message, headless=hl)
            if i < len(contacts) - 1:
                await asyncio.sleep(8)
        return

    if args.to:
        contacts = load_contacts()
        if args.to in contacts:
            phone, name = contacts[args.to], args.to
        else:
            phone, name = format_phone(args.to), args.to
        message = args.message or DEFAULT_MESSAGE
        await do_send(phone, name, message, headless=hl)
        return

    await main_menu(headless=hl)


if __name__ == "__main__":
    asyncio.run(run())