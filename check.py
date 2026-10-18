# 和逸飯店‧桃園館 雙人房空房監控（GitHub Actions 版）
import os, sys, urllib.request
from playwright.sync_api import sync_playwright

URL = os.environ["BOOKING_URL"]          # 11/7入住、2大人的搜尋結果頁網址（設在 GitHub Secrets）
NTFY_TOPIC = os.environ["NTFY_TOPIC"]    # 你自己取的 ntfy 頻道名稱（設在 GitHub Secrets）

KEYWORDS = ["雙人", "Double", "Twin"]     # 依網站實際房型名稱調整
EXCLUDE = ["四人", "Quad", "售完", "已售完", "額滿", "Sold out"]

def notify(msg):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=msg.encode("utf-8"),
        headers={"Title": "Double room available!", "Priority": "high", "Click": URL},
    )
    urllib.request.urlopen(req, timeout=30)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="zh-TW")
        page.goto(URL, timeout=60000)
        page.wait_for_timeout(10000)  # 等房價載入
        text = page.inner_text("body")
        browser.close()

    found = [l.strip() for l in text.splitlines()
             if any(k in l for k in KEYWORDS) and not any(e in l for e in EXCLUDE)]
    if found:
        print("有雙人房：", found[:5])
        notify("和逸桃園館 11/7 有雙人房了！\n" + "\n".join(found[:5]))
    else:
        print("還沒有雙人房")
        print(text[:1500])  # 方便在 Actions 紀錄裡檢查有沒有抓到頁面

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("查詢失敗：", e)
        sys.exit(1)
