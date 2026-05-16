# Telegram Sales Funnels & Lead Management: Open-Source Research

> **Date:** 2025-07-30
> **Focus:** Free / open-source tools for Telegram-based sales funnels, CRM integration, payment processing, document automation, and broadcast
> **Language of research:** English

---

## Table of Contents

1. [Telegram Bot API — Best Practices](#1-telegram-bot-api--best-practices)
2. [Lead Qualification Bot Frameworks](#2-lead-qualification-bot-frameworks)
3. [Open-Source CRM — Integration with Telegram](#3-open-source-crm--integration-with-telegram)
4. [Notion as CRM — Free Tier, API, Python](#4-notion-as-crm--free-tier-api-python)
5. [Airtable Free Tier — CRM, API, Automation](#5-airtable-free-tier--crm-api-automation)
6. [Payment Integration in Telegram](#6-payment-integration-in-telegram)
7. [PDF Invoice Generation in Python](#7-pdf-invoice-generation-in-python)
8. [Contract/Agreement Automation](#8-contractagreement-automation)
9. [Telegram Mini Apps — Storefront](#9-telegram-mini-apps--storefront)
10. [Broadcast / Mailing in Telegram](#10-broadcast--mailing-in-telegram)
11. [Recommended Sales Pipeline for Telegram Agent](#11-recommended-sales-pipeline-for-telegram-agent)
12. [Summary & Quick Decision Matrix](#12-summary--quick-decision-matrix)

---

## 1. Telegram Bot API — Best Practices

### Inline Keyboards & Callback Buttons

Inline keyboards are the primary UI element for interactive Telegram bots. They attach directly to messages and provide a native app-like experience without requiring text input from users. [^260^]

**Core principles:**

- Use `InlineKeyboardMarkup` with structured `callback_data` payloads. Each button sends a `CallbackQuery` to your bot when clicked
- Always call `await query.answer()` in callback handlers — otherwise Telegram shows a loading spinner indefinitely [^262^]
- For multi-level navigation, use prefix-based `callback_data` like `menu:main`, `menu:settings`, `menu:profile` to route user actions
- Use `query.edit_message_text()` to update the same message instead of sending new ones — keeps chat history clean [^219^]
- Keep `callback_data` under 64 bytes (Telegram limit). Use compact encoding: `c:product_12` instead of full JSON

**Example pattern (aiogram 3.x):**

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Dynamic menu builder
def build_menu(items: list, back_callback: str = "main"):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for item in items:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=item['name'], callback_data=f"item:{item['id']}")
        ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="Back", callback_data=back_callback)
    ])
    return kb
```

### Finite State Machine (FSM) for Conversation Flow

For lead qualification and multi-step funnels, FSM is essential. Telegram bots are stateless by nature — FSM provides persistent conversation state across messages. [^178^] [^181^] [^182^]

**Recommended: aiogram FSM with aiogram-dialog**

```python
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage

class LeadQualify(StatesGroup):
    budget = State()
    timeline = State()
    requirements = State()
    contact = State()

# Redis-backed storage for production
storage = RedisStorage.from_url("redis://localhost:6379/0")
dp = Dispatcher(storage=storage)
```

**Key best practices:**
- Use `MemoryStorage` only for development; switch to `RedisStorage` in production for persistence across restarts [^212^] [^214^]
- Set TTL on state data to prevent storage bloat: `state_ttl=3600` (1 hour)
- Implement cancel/reset handlers accessible from any state: `@dp.message(Command("cancel"), State("*"))`
- Use `aiogram_dialog` library for complex multi-window dialogs with inline keyboards [^218^]
- Validate user input at each state step before transitioning to the next state [^181^]

### Webhook vs Polling

| Mode | Best For | Pros | Cons |
|------|----------|------|------|
| **Polling** | Development, low traffic | Easy setup, no HTTPS required | Higher latency, more bandwidth |
| **Webhook** | Production, high traffic | Instant delivery, serverless-friendly | Requires HTTPS, SSL certificate |

For production deployments, webhooks with FastAPI/uvicorn behind nginx or cloudflare tunnel are recommended. [^234^]

---

## 2. Lead Qualification Bot Frameworks

### Framework Comparison

| Framework | Stars | License | Async | Best For |
|-----------|-------|---------|-------|----------|
| **python-telegram-bot** | 28,536 | GPL-3.0 | Yes (v20+) | Mature projects, extensive docs |
| **aiogram** | 5,470 | MIT | Yes (native) | Modern async, FSM, rapid development |
| **pyTelegramBotAPI** | N/A | GPL-2.1 | Partial | Simple bots, quick prototypes |

[Source: LibHunt comparison] [^141^]

**Recommendation: aiogram 3.x** for lead qualification bots. It's fully asynchronous, has built-in FSM, and a cleaner API for conversation flows. The MIT license is more permissive than GPL-3.0.

### Lead Qualification Pattern

A proven lead qualification flow using FSM: [^174^] [^177^] [^183^]

```
/start → Welcome + Qualification Question 1 (Budget?)
  → State: budget → Qualification Question 2 (Timeline?)
    → State: timeline → Qualification Question 3 (Requirements?)
      → State: requirements → Contact info collection
        → State: contact → Scoring + CRM write
          → Offer generation or human handoff
```

**Scoring logic example:**
- Budget > $1000 + Timeline < 30 days = **Hot lead** → Immediate human handoff
- Budget $200-1000 + Timeline 30-90 days = **Warm lead** → Nurture sequence
- Budget < $200 or Timeline > 90 days = **Cold lead** → Drip campaign

**Key integration points:**
- Write qualified leads to SQLite/PostgreSQL directly from the bot
- Use webhooks to push leads to external CRM (EspoCRM, Notion, Airtable)
- Implement auto-reply with estimated response time for human handoff

---

## 3. Open-Source CRM — Integration with Telegram

### Top Open-Source CRMs for Self-Hosting

| CRM | License | Self-Host | Min Cost | Best For |
|-----|---------|-----------|----------|----------|
| **EspoCRM** | AGPL | Yes | Free | Lightweight, fast, REST API |
| **SuiteCRM** | AGPL | Yes | Free | Enterprise-grade, Salesforce alternative |
| **Odoo Community** | LGPL | Yes | Free | ERP-first, modular |
| **Frappe CRM** | MIT | Yes | Free | Modern UI, easy customization |
| **Twenty** | AGPL | Yes | Free ($9/user cloud) | Developer-friendly, clean API |
| **Vtiger** | VPL | Yes | Free / $12/user | SMB-focused, built-in workflows |

[Sources: Forbes, marmelab, Nutshell, Coalition Technologies] [^138^] [^139^] [^140^] [^144^] [^145^] [^146^] [^147^]

### EspoCRM — Top Pick for Telegram Integration

**Why EspoCRM:**
- Lightweight (~50MB), runs on shared hosting
- Clean REST API for CRUD operations
- Built-in workflow engine and BPM
- Active community with Telegram bot integrations [^206^]

**Integration via webhook:**
```python
# Python webhook handler for EspoCRM
import requests

ESPO_URL = "https://your-espocrm.com/api/v1"
API_KEY = "your-api-key"

def create_lead(telegram_data: dict):
    payload = {
        "name": telegram_data.get("name"),
        "emailAddress": telegram_data.get("email"),
        "phoneNumber": telegram_data.get("phone"),
        "source": "Telegram",
        "description": telegram_data.get("requirements"),
        "budget": telegram_data.get("budget"),
        "assignedUserId": None  # Round-robin assignment
    }
    headers = {
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json"
    }
    r = requests.post(f"{ESPO_URL}/Lead", json=payload, headers=headers)
    return r.json()
```

Integration platforms like Make.com and n8n offer pre-built EspoCRM + Telegram Bot connectors. [^202^]

### Frappe CRM

- Fully open-source (MIT license)
- Self-hosted via Docker in ~5 minutes
- Built on Frappe Framework (Python + MariaDB)
- Has WhatsApp integration; Telegram integration possible via custom app
- Modern, responsive UI with deal pipeline views [^191^] [^201^] [^204^]

---

## 4. Notion as CRM — Free Tier, API, Python

### Free Tier Limitations

| Feature | Free Personal | Free Team |
|---------|--------------|-----------|
| Pages & Blocks | Unlimited | 1,000 blocks limit |
| File Upload | 5 MB per file | 5 MB per file |
| Version History | 7 days | 7 days |
| Guest Invites | 10 | 10 |
| API Access | Yes (3 req/sec) | Yes (3 req/sec) |
| Automations | 15 per database | 15 per database |

[Sources: Vendr, TaskRhino, notionmastery.com] [^211^] [^213^] [^216^] [^217^]

**Verdict:** Notion's free plan is excellent for a **solo operator**. Unlimited pages/blocks for individuals, with full API access. The 3 req/sec rate limit and 7-day history are the main constraints. Teams hit the 1,000-block limit quickly.

### Python Integration

```python
# notion-py or official notion-client
import asyncio
from notion_client import Client

notion = Client(auth="secret_xxx")

# Query CRM database
def get_leads(status="New"):
    db_id = "your-database-id"
    results = notion.databases.query(
        database_id=db_id,
        filter={"property": "Status", "select": {"equals": status}}
    )
    return results["results"]

# Create lead from Telegram
def create_lead(lead_data: dict):
    notion.pages.create(
        parent={"database_id": "your-db-id"},
        properties={
            "Name": {"title": [{"text": {"content": lead_data["name"]}}]},
            "Source": {"select": {"name": "Telegram"}},
            "Budget": {"number": lead_data.get("budget", 0)},
            "Status": {"select": {"name": "New"}},
            "Telegram ID": {"rich_text": [{"text": {"content": str(lead_data["tg_id"])}}]}
        }
    )
```

**Automation:** Use Notion's built-in automations (free: 15 per database) to trigger status changes, or connect via Pipedream/Zapier/Make for cross-platform workflows. [^143^] [^180^]

---

## 5. Airtable Free Tier — CRM, API, Automation

### Free Tier Limits

| Feature | Free Tier |
|---------|-----------|
| Records per base | 1,000 |
| API calls/month | 1,000 |
| Attachment storage | 1 GB per base |
| Revision history | 2 weeks |
| Editors | 5 collaborators |
| Automations | Limited (no "Run a script") |
| Extensions | Not available |

[Source: Medium Airtable for Developers] [^137^]

**Verdict:** Airtable free is suitable for **prototyping and very small operations**. The 1,000 records and 1,000 API calls/month limit make it unsuitable for production at scale. Rate limit: 5 requests/second per base.

**Python integration pattern:**
```python
import requests

BASE_ID = "appXXX"
TABLE_NAME = "Leads"
API_KEY = "patXXX"

def create_lead(data: dict):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"fields": data}
    r = requests.post(url, json=payload, headers=headers)
    return r.json()
```

**Alternatives with better free tiers:** Baserow (3K free, unlimited self-hosted), NocoDB (unlimited with SQL backend), Grist (unlimited with Python formulas). [^142^]

---

## 6. Payment Integration in Telegram

### Payment Methods Overview

Telegram supports payments via two main approaches: native Bot Payments API and external crypto processors. [^153^] [^160^] [^161^] [^196^]

#### Native Telegram Payments API 2.0

Built into Telegram since 2017, supports 100+ currencies. Flow: [^196^]

1. Bot sends invoice via `sendInvoice` with product details
2. User clicks Pay button → checkout UI opens inside Telegram
3. User enters card details → payment provider processes transaction
4. Bot receives `pre_checkout_query` → confirms availability
5. Bot receives `successful_payment` → delivers product

**Supported payment providers by region:**

| Provider | Region | Card/Crypto | Fees |
|----------|--------|-------------|------|
| **Stripe** | Global | Cards, Wallets | 2.9% + $0.30 |
| **PayPal** | Global | Cards, PayPal balance | 2.9% + $0.30 |
| **YooKassa** | Russia/CIS | Cards, SBP, wallets | ~3.5% |
| **SmartGlocal** | Emerging markets | Cards, local methods | Varies |
| **CryptoCloud** | Global | BTC, ETH, USDT, 30+ coins | 1-2% |
| **Revolut** | EU/UK | Cards, Revolut Pay | 1-2.5% |
| **Binance Pay** | Global | Crypto | 1% |

[Source: BotSubscription docs] [^209^]

#### Crypto Payments (TON)

The TON ecosystem is deeply integrated with Telegram: [^173^] [^176^] [^235^] [^236^] [^238^]

- **TON Connect 2.0**: Wallet authentication standard (Tonkeeper, Telegram Wallet, MyTonWallet)
- **Telegram Stars**: Native digital currency for in-app purchases
- **Smart contracts on TON**: Automated escrow, subscription payments, instant settlement
- **Transaction speed**: ~2-5 seconds, fees ~$0.005-0.01 per transaction

**Example: aiogram bot with TON payment:**
```python
from aiogram import types

@dp.message_handler(commands=['buy'])
async def cmd_buy(message: types.Message):
    prices = [types.LabeledPrice(label="Service Package", amount=5000)]  # $50.00
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Premium Package",
        description="Full service access",
        payload=f"user_{message.from_user.id}_pkg1",
        provider_token=STRIPE_TOKEN,  # Or YooKassa token
        currency="USD",
        prices=prices,
        start_parameter="premium"
    )
```

**Key consideration:** For a fully free/open-source stack, **crypto payments via TON** or **self-hosted payment verification** (manual bank transfer + bot confirmation) avoid third-party fees entirely. For card payments, **Stripe** has the most mature Telegram integration.

---

## 7. PDF Invoice Generation in Python

### Library Comparison

| Library | Type | Ease | CSS Support | Dependencies | License | Best For |
|---------|------|------|-------------|--------------|---------|----------|
| **FPDF2** | Canvas | Easy | None | pip only | MIT | Simple invoices, no deps |
| **ReportLab** | Canvas | Moderate | None | pip only | BSD | Complex layouts, charts |
| **WeasyPrint** | HTML→PDF | Moderate | Full CSS3 | Pango libs | BSD | HTML templates, styled invoices |
| **xhtml2pdf** | HTML→PDF | Easy | CSS 2.1+ | pip only | Apache | Simple HTML→PDF |
| **PDFKit** | HTML→PDF | Moderate | Full | wkhtmltopdf binary | MIT | Browser rendering |
| **Playwright** | HTML→PDF | Moderate | Full CSS3 | Browser binary (~150MB) | Apache | Pixel-perfect output |
| **borb** | Canvas | Moderate | None | pip only | AGPL | Rich docs, barcodes |

[Sources: Nutrient, DailyHunt, Quora, Rost Glukhov] [^149^] [^152^] [^157^] [^158^]

### Recommended: WeasyPrint + Jinja2 for Invoice Generation

The optimal stack for invoice generation: **Jinja2 HTML template → WeasyPrint → PDF**. [^255^] [^257^] [^258^] [^259^] [^261^]

**Why this combination:**
- Jinja2 handles dynamic data injection (customer info, line items, totals)
- HTML/CSS gives full design flexibility without coding coordinates
- WeasyPrint renders modern CSS (flexbox, grid, page breaks, headers/footers)
- Output is professional, print-ready PDF

**Minimal example:**

```python
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import tempfile

def generate_invoice(invoice_data: dict) -> bytes:
    env = Environment(loader=FileSystemLoader("templates/"))
    template = env.get_template("invoice.html")
    html_content = template.render(**invoice_data)
    return HTML(string=html_content).write_pdf()

# invoice.html template uses standard CSS for styling
# @page { size: A4; margin: 15mm; }
# thead { display: table-header-group; }  # repeat headers
# tr { break-inside: avoid; }  # prevent row splitting
```

**Invoice template key elements:** [^257^]
- Company logo (base64-encoded inline)
- Invoice number, date, due date
- Customer billing details
- Line items table with thead repetition
- Subtotal, tax, total calculations
- Payment terms and bank details
- Footer with page numbers

---

## 8. Contract / Agreement Automation

### Recommended Stack: docxtpl + Jinja2

**docxtpl** extends `python-docx` with Jinja2 templating, allowing non-developers to maintain Word templates while developers handle data rendering. [^150^] [^192^] [^195^] [^198^] [^205^]

**Template example (contract_template.docx):**

```
SERVICE AGREEMENT

Client: {{ customer_name }}
Date: {{ contract_date }}
Project: {{ project_title }}

{% if contract_type == 'premium' %}
Premium terms apply including extended support hours.
{% endif %}

Services:
{% tr for item in line_items %}
  - {{ item.description }}: ${{ item.price }}
{% tr endfor %}

Total Value: ${{ total_amount }}

{% if signature %}
Signed: {{ signature }}
{% else %}
[Signature pending]
{% endif %}
```

**Python rendering:**

```python
from docxtpl import DocxTemplate

def generate_contract(data: dict, template_path: str, output_path: str):
    doc = DocxTemplate(template_path)
    doc.render(data)
    doc.save(output_path)
    return output_path

# Usage
context = {
    "customer_name": "Acme Corp",
    "contract_date": "2025-07-30",
    "project_title": "Telegram Bot Development",
    "contract_type": "premium",
    "line_items": [
        {"description": "Bot Development", "price": 2000},
        {"description": "Monthly Maintenance", "price": 500}
    ],
    "total_amount": 2500,
    "signature": "John Doe, CEO"
}
generate_contract(context, "contract_tpl.docx", "contract_acme.docx")
```

**Advanced features:**
- `{%p if condition %}` for conditional paragraphs
- `{%tr for item in items %}` for dynamic table rows
- `InlineImage` for embedded logos and signatures
- Combine with WeasyPrint to convert final DOCX → PDF

**Alternative: python-docx for programmatic generation** (no templates):
```python
from docx import Document
doc = Document()
doc.add_heading('Service Agreement', 0)
doc.add_paragraph(f'Client: {customer_name}')
doc.add_paragraph(f'Total: ${total}')
doc.save('contract.docx')
```

---

## 9. Telegram Mini Apps — Storefront

### What Are Mini Apps?

Telegram Mini Apps are web applications that run inside Telegram's native interface via WebView. They combine the reach of Telegram (900M+ users) with the flexibility of web apps. [^156^] [^184^] [^235^] [^239^]

### Tech Stack for Mini App Storefront

| Layer | Technology |
|-------|------------|
| Frontend | React / Vue.js + @twa-dev/sdk |
| Backend | Node.js/Express or Python/FastAPI |
| Payment | TON Connect 2.0 + Telegram Stars |
| Auth | Telegram initData HMAC-SHA256 validation |
| Wallet | Tonkeeper, Telegram Wallet, MyTonWallet |
| Smart Contracts | FunC / Tact (TON) |

### Key Resources

- **Awesome Telegram Mini Apps**: GitHub collection of templates, boilerplates, and example projects [^184^]
- **TON Documentation**: Official guides for payment integration and wallet connection [^176^] [^236^]
- **TonCircle**: Open-source Mini App for group payments on TON (React + Tact smart contracts) [^173^]
- **TONPAY**: Python-based Telegram crypto wallet on TON [^175^]

### Mini App vs. Bot-Only Storefront

| Approach | Complexity | UX | Best For |
|----------|-----------|-----|----------|
| **Bot only** (inline keyboards) | Low | Good | Simple catalogs, < 20 products |
| **Mini App** | High | Excellent | Rich storefronts, complex UX |
| **Hybrid** (bot + Mini App) | Medium | Best of both | Most real-world cases |

**Recommended pattern for a free setup:** Start with bot-only inline catalog. Graduate to Mini App when product count exceeds 20 or when you need visual product galleries.

---

## 10. Broadcast / Mailing in Telegram

### Using python-telegram-bot JobQueue

The built-in `JobQueue` (powered by APScheduler) handles scheduled broadcasts: [^193^] [^197^] [^199^] [^200^]

```python
from telegram.ext import Application, ContextTypes
import datetime

application = Application.builder().token("TOKEN").build()
job_queue = application.job_queue

# Broadcast to all subscribers
async def broadcast_job(context: ContextTypes.DEFAULT_TYPE):
    subscribers = get_all_subscribers()  # From DB
    message = "Weekly update: New features available!"
    for user_id in subscribers:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Failed to send to {user_id}: {e}")

# Schedule daily at 10:00 UTC
job_queue.run_daily(
    broadcast_job,
    time=datetime.time(hour=10, minute=0),
    days=(0, 1, 2, 3, 4, 5, 6)  # All days
)

# Or run once after delay
job_queue.run_once(broadcast_job, when=3600)  # 1 hour from now

# Or repeating
job_queue.run_repeating(broadcast_job, interval=3600, first=10)
```

**Best practices for broadcasts:**
- Add rate limiting: max 30 messages/second to avoid Telegram flood limits
- Track failed deliveries and unsubscribe invalid chat_ids
- Segment audiences by tags/interests rather than blasting everyone
- Respect user preferences with `/unsubscribe` command
- Use Markdown or HTML formatting sparingly — keep messages readable

### Rate Limiting for Broadcasts

Telegram's flood limits: [^212^]
- ~30 messages/second to different users
- ~20 messages/minute to the same group
- Exceeding limits triggers temporary bans (increasing from 1 min to 24 hours)

**Mitigation:** Use `asyncio.sleep()` between sends, or implement a queue system (Redis + worker) for large lists.

---

## 11. Recommended Sales Pipeline for Telegram Agent

### Pipeline Stages

```
[Traffic] → [Capture] → [Qualify] → [Offer] → [Payment] → [Delivery] → [Retention]
     ↓           ↓           ↓          ↓          ↓           ↓            ↓
  Ads/SEO   Bot /start   FSM Bot    Proposal   Invoice    Service     Follow-up
  Content   Mini App    Scoring    Contract   Stripe     Delivery    Referral
  Referral  Landing     Tags       PDF gen    Crypto     Files       Review
```

### Stage-by-Stage Implementation

| Stage | Tool | Free Option |
|-------|------|-------------|
| **Traffic** | Telegram channel, SEO, word-of-mouth | Free |
| **Capture** | Bot with `/start` + inline menu | aiogram (free) |
| **Qualify** | FSM conversation + scoring logic | aiogram FSM (free) |
| **CRM Storage** | SQLite / PostgreSQL + EspoCRM | SQLite is free |
| **Offer** | PDF proposal (WeasyPrint + Jinja2) | Open source |
| **Contract** | DOCX template (docxtpl) | Open source |
| **Payment** | Stripe / TON / YooKassa | TON is near-free |
| **Delivery** | Telegram file send + Mini App access | Free |
| **Retention** | JobQueue broadcast + follow-up bot | Free |

### Complete Free Stack Recommendation

```
Bot Framework:     aiogram 3.x (MIT)
Database:          PostgreSQL or SQLite (free)
CRM:               EspoCRM self-hosted (AGPL) or Notion free (solo)
Invoices:          WeasyPrint + Jinja2 (BSD)
Contracts:         docxtpl (MIT)
Payments:          TON crypto (near-zero fees) or Stripe (2.9%)
Broadcast:         python-telegram-bot JobQueue (free)
Mini App:          React + @twa-dev/sdk (free)
Hosting:           Railway free tier / Render / self-hosted VPS
```

### Estimated Costs (Free Tier)

| Component | Monthly Cost |
|-----------|-------------|
| Bot hosting (Render/Railway free) | $0 |
| Database (PostgreSQL on Render) | $0 |
| CRM (EspoCRM self-hosted) | $0 |
| Invoice/Contract generation | $0 |
| Telegram Bot API | $0 |
| Payment processing (TON) | ~$0.01/tx |
| **Total** | **$0 + transaction fees only** |

---

## 12. Summary & Quick Decision Matrix

### If you need...

| Need | Use This | Why |
|------|----------|-----|
| Modern async bot framework | **aiogram 3.x** | Native async, FSM, MIT license |
| Lead qualification flow | **aiogram FSM + scoring logic** | Stateful conversations, data validation |
| Self-hosted CRM | **EspoCRM** | Lightweight, REST API, free |
| Zero-config CRM (solo) | **Notion free** | Unlimited blocks, API access |
| PDF invoices | **WeasyPrint + Jinja2** | HTML templates, professional output |
| Contract generation | **docxtpl (python-docx-template)** | Word templates, Jinja2 logic |
| Card payments in Telegram | **Stripe via Bot Payments API** | Mature, global, 2.9% fee |
| Crypto payments | **TON Connect 2.0** | Near-zero fees, native Telegram |
| Scheduled broadcasts | **JobQueue (APScheduler)** | Built into bot frameworks |
| Rich storefront | **Telegram Mini App + React** | Native UX, 900M+ users |

### Key Open-Source Repositories

| Repo | Description | Tech |
|------|-------------|------|
| [aiogram/aiogram](https://github.com/aiogram/aiogram) | Async Telegram Bot framework | Python |
| [frappe/crm](https://github.com/frappe/crm) | Modern open-source CRM | Python/Frappe |
| [telegram-leads](https://github.com/makarenos/telegram-leads) | CRM for Telegram bot leads | FastAPI + React |
| [TonCircle](https://github.com/winsznx/TonCircle) | Mini App with TON payments | React + Tact |
| [awesome-telegram-mini-apps](https://github.com/telegram-mini-apps-dev/awesome-telegram-mini-apps) | Curated resources | Various |
| [notion-py](https://github.com/jamalex/notion-py) | Unofficial Notion API client | Python |
| [docxtpl](https://github.com/elapouya/python-docx-template) | Word doc generation with Jinja2 | Python |

---

## Citations

[^138^] https://www.larksuite.com/en_us/blog/open-source-crm — Top Open Source CRM Software for Teams and Startups

[^139^] https://coalitiontechnologies.com/blog/comparing-the-best-open-source-crm-software — Comparing The Best Open Source CRM Software

[^140^] https://www.forbes.com/advisor/business/software/best-open-source-crm/ — 9 Best Open Source CRMs Of 2026

[^141^] https://www.libhunt.com/compare-python-telegram-bot-vs-aiogram — python-telegram-bot vs aiogram comparison

[^143^] https://thomasjfrank.com/notion-automations/ — The Ultimate Guide to Notion Automations and the Notion API

[^144^] https://devdiligent.com/blog/best-open-source-crm-stack-for-small-businesses-in-2026/ — Best Open-Source CRM Stack for Small Businesses

[^145^] https://www.nutshell.com/blog/best-open-source-crms — 9 Best Open Source CRMS in 2026

[^146^] https://marmelab.com/blog/2025/02/03/open-source-crm-benchmark-for-2025.html — Best Open Source CRM for 2025

[^147^] https://prospeo.io/s/open-source-sales-crm — Best Open Source Sales CRMs in 2026

[^149^] https://www.nutrient.io/blog/top-10-ways-to-generate-pdfs-in-python/ — Top 10 Python PDF generator libraries

[^150^] https://www.softkraft.co/python-word-automation/ — 8 Ways to Supercharge Microsoft Word Automation with Python

[^153^] https://cryptocloud.plus/en/blog/accepting-payments-in-telegram-bot — How to Accept Payments in Telegram Bots

[^156^] https://habr.com/en/articles/990338/ — An Overview of Telegram Mini Apps

[^157^] https://www.quora.com/What-is-the-best-Python-library-to-create-PDF-documents — Best Python PDF library guide

[^173^] https://github.com/winsznx/TonCircle — TonCircle: TON group payments Mini App

[^174^] https://www.ucartz.com/blog/build-lead-qualification-bot-nanobot-telegram/ — Build a Lead Qualification Bot

[^176^] https://docs.ton.org/v3/guidelines/dapps/tutorials/telegram-bot-examples/accept-payments-in-a-telegram-bot-2 — Bot with TON balance

[^178^] https://aiogram-birdi7.readthedocs.io/en/latest/examples/finite_state_machine_example.html — aiogram FSM example

[^180^] https://medium.com/@jamiealexandre/introducing-notion-py — notion-py: Unofficial Python API wrapper for Notion

[^181^] https://docs.aiogram.dev/en/v2.25.1/examples/finite_state_machine_example.html — aiogram FSM example v2.x

[^182^] https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/index.html — Finite State Machine aiogram 3.x docs

[^184^] https://github.com/telegram-mini-apps-dev/awesome-telegram-mini-apps — Awesome Telegram Mini Apps

[^191^] https://minixium.com/posts/open-source-crm-frappe-crm/ — Frappe CRM: Comprehensive Review

[^192^] https://medium.com/@engineering_holistic_ai/how-to-automate-creating-reports-using-docx-templates — Automate reports using docx templates

[^193^] https://stackoverflow.com/questions/77002882/schedule-task-telegram-application — Schedule task with JobQueue

[^195^] https://docxtpl.readthedocs.io/ — python-docx-template documentation

[^196^] https://www.peacetech.net/2026/04/21/how-to-receive-payment-on-telegram-a-complete-guide-to-bot-payments-api/ — Complete guide to Bot Payments API

[^197^] https://medium.com/@steve.dua/scheduled-job-queue-for-telegram-bots-84deb19c9a8 — Scheduled Job Queue for Telegram Bots

[^199^] https://docs.python-telegram-bot.org/en/v21.5/telegram.ext.jobqueue.html — JobQueue documentation

[^200^] https://medium.com/analytics-vidhya/python-telegram-bot-with-scheduled-tasks-932edd61c534 — Python Telegram Bot with Scheduled Tasks

[^201^] https://github.com/frappe/crm — Frappe CRM GitHub

[^202^] https://www.make.com/en/integrations/espo-crm/telegram — EspoCRM + Telegram Bot integration

[^204^] https://frappe.io/crm — Frappe CRM official

[^205^] https://dev.to/huseinkntrc/automating-word-document-creation-with-python-and-fastapi — FastAPI + docxtpl automation

[^209^] https://docs.botsubscription.com/payments/ — Payment Providers for Telegram & Discord Bots

[^210^] https://github.com/makarenos/telegram-leads — CRM system for Telegram bot leads

[^211^] https://www.vendr.com/blog/is-notion-free — Is Notion Really Free?

[^212^] https://aiogram-birdi7.readthedocs.io/en/latest/examples/middleware_and_antiflood.html — aiogram antiflood middleware

[^213^] https://www.taskrhino.ca/blog/notion-review/ — Notion Review 2025

[^214^] https://docs.aiogram.dev/en/v3.25.0/_modules/aiogram/fsm/storage/redis.html — aiogram Redis FSM storage

[^216^] https://www.cloudeagle.ai/blogs/notion-pricing-guide — Notion Pricing Guide

[^217^] https://notionmastery.com/pushing-notion-to-the-limits/ — Pushing Notion to the Limits

[^218^] https://github.com/Tishka17/aiogram_dialog — aiogram_dialog example

[^219^] https://n8n.io/workflows/7664-telegram-bot-inline-keyboard-with-dynamic-menus-and-rating-system/ — Telegram bot inline keyboard with dynamic menus

[^233^] https://dev.to/amverum/telegram-bot-store-on-python-step-by-step-guide-with-payment-catalog-and-admin-panel-aiogram-3-294p — Telegram Bot Store on Python (Aiogram 3)

[^235^] https://blocsys.com/telegram-mini-app-web3-gaming-and-defi-platform/ — Telegram Mini App Web3 Platform

[^236^] https://docs.ton.org/v3/guidelines/dapps/tutorials/telegram-bot-examples/accept-payments-in-a-telegram-bot — Storefront bot with TON payments

[^237^] https://github.com/python-telegram-bot/python-telegram-bot/issues/1737 — JobQueue with webhooks

[^238^] https://jwarnerinfo.medium.com/build-a-telegram-mini-app-with-ton-connect-a-step-by-step-guide-eb1847dff376 — Build a Telegram Mini App with TON Connect

[^239^] https://cryptolinks.com/news/telegram-mini-apps-on-ton-fastest-web3-onramp — Telegram mini apps on TON

[^255^] https://www.nutrient.io/blog/how-to-generate-pdf-reports-from-html-in-python/ — WeasyPrint HTML to PDF tutorial

[^256^] https://apitemplate.io/blog/how-to-convert-html-to-pdf-using-python/ — Convert HTML to PDF in Python

[^257^] https://davidmuraya.com/blog/fastapi-create-secure-pdf/ — Create and Secure PDFs with FastAPI

[^258^] https://blog.franciscoarocas.com/generate-pdfs-in-python-django-with-weasyprint-step-by-step-guide-e26fbb0d3a72 — Generate PDFs with WeasyPrint

[^259^] https://practicalpython.yasoob.me/chapter3 — Automatic Invoice Generation

[^260^] https://www.geeksforgeeks.org/python/keyboard-buttons-in-telegram-bot-using-python/ — Keyboard buttons in Telegram bot

[^261^] https://joshkaramuth.com/blog/generate-good-looking-pdfs-weasyprint-jinja2 — Generate PDFs with WeasyPrint and Jinja2

[^262^] https://medium.com/@travilabs/building-a-simple-telegram-bot-with-buttons-using-python-0a16c52485c0 — Building a Telegram Bot with Buttons

---

*Report compiled from 12+ web searches, covering 11 research areas with 50+ cited sources.*
