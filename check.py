# 和逸飯店‧桃園館 11/7 房價監控（GitHub Actions 版）
# 判斷方式：11/7 當天出現低於 THRESHOLD 的房價，就視為可能釋出雙人房
import os, re, sys, urllib.request
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from playwright.sync_api import sync_playwright

BASE_URL = os.environ["BOOKING_URL"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

ARRIVE = "2026-11-07"
DEPART = "2026-11-08"
ADULTS = "2"
THRESHOLD = 10000   # 低於這個價格就緊急通知


def build_url(base):
    """把訂房網址的日期、人數換成 11/7 入住、11/8 退房、2 大人"""
    parts = urlsplit(base)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q.update({"arrive": ARRIVE, "depart": DEPART,
              "adult": ADULTS, "child": "0", "rooms": "1"})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


URL = build_url(BASE_URL)


def notify(msg, title, priority="default"):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=msg.encode("utf-8"),
        headers={"Title": title, "Priority": priority, "Click": URL},
    )
    urllib.request.urlopen(req, timeout=30)


def find_prices(text):
    """從頁面文字找出房價（含 TWD / NT / $ / 元 的行）"""
    prices = []
    for line in text.splitlines():
        if not re.search(r"TWD|NT|\$|元", line):
            continue
        for m in re.findall(r"\d{1,3}(?:,\d{3})+|\d{4,6}", line):
            v = int(m.replace(",", ""))
            if 1000 <= v <= 200000 and not (2017 <= v <= 2030):  # 排除年份
                prices.append(v)
    return sorted(set(prices))


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            locale="zh-TW",
            timezone_id="Asia/Taipei",
            viewport={"width": 1366, "height": 900},
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"),
        )
        text, title = "", ""
        for attempt in range(3):  # 空白頁面就等一下再重試，最多 3 次
            if attempt == 0:
                page.goto(URL, timeout=90000, wait_until="domcontentloaded")
            else:
                print(f"頁面空白，第 {attempt} 次重試")
                page.wait_for_timeout(20000)
                page.reload(timeout=90000, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                pass
            page.wait_for_timeout(10000)  # 等房價載入
            title = page.title()
            text = page.inner_text("body")
            if len(text.strip()) >= 100:
                break
        page.screenshot(path="page.png", full_page=True)
        browser.close()

    print("頁面標題：", title)
    print("文字長度：", len(text))
    if len(text.strip()) < 100:
        raise RuntimeError(f"頁面沒有內容（可能被擋或還沒載入）標題：{title}")

    # 確認頁面真的是 11/7
    if "11月7日" not in text and "11/7" not in text and "2026-11-07" not in text:
        print(text[:1500])
        raise RuntimeError("頁面日期不是 11/7，網址參數可能沒生效")

    prices = find_prices(text)
    print("找到的房價：", prices)
    print(text[:3000])

    if not prices:
        if "不可用" in text or "沒有可用" in text:
            notify("11/7 目前完全沒有空房", "11/7 sold out", "low")
        else:
            notify("11/7 頁面有載入，但沒找到房價", "No price found")
        return

    low = prices[0]
    if low < THRESHOLD:
        notify(f"11/7 出現 TWD {low:,} 的房價，可能有雙人房！快去訂！\n全部價格：{', '.join(f'{x:,}' for x in prices[:8])}",
               "Price under 10,000!", "urgent")
    else:
        notify(f"11/7 最低價 TWD {low:,}，還沒有一萬以下", "No cheap room yet", "low")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("查詢失敗：", e)
        try:
            notify(f"這次沒抓到（下次會再試）：{e}", "Check failed", "low")
        except Exception:
            pass
        sys.exit(1)
