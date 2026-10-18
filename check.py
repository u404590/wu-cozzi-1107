# 和逸飯店‧桃園館 雙人房空房監控（GitHub Actions 版）
import os, sys, urllib.request
from playwright.sync_api import sync_playwright

URL = os.environ["BOOKING_URL"]          # 11/7入住、2大人的搜尋結果頁網址（設在 GitHub Secrets）
NTFY_TOPIC = os.environ["NTFY_TOPIC"]    # 你自己取的 ntfy 頻道名稱（設在 GitHub Secrets）

KEYWORDS = ["雙人", "Double", "Twin"]     # 依網站實際房型名稱調整
EXCLUDE = ["四人", "Quad", "售完", "已售完", "額滿", "Sold out"]

def notify(msg, title, priority="default"):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=msg.encode("utf-8"),
        headers={"Title": title, "Priority": priority, "Click": URL},
    )
    urllib.request.urlopen(req, timeout=30)

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
        page.goto(URL, timeout=90000, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass
        page.wait_for_timeout(8000)  # 等房價載入
        title = page.title()
        final_url = page.url
        text = page.inner_text("body")
        page.screenshot(path="page.png", full_page=True)
        browser.close()

    print("頁面標題：", title)
    print("實際網址：", final_url)
    print("文字長度：", len(text))
    if len(text.strip()) < 100:
        raise RuntimeError(f"頁面沒有內容（可能被擋或還沒載入）標題：{title}")

    found = [l.strip() for l in text.splitlines()
             if any(k in l for k in KEYWORDS) and not any(e in l for e in EXCLUDE)]
    if found:
        print("有雙人房：", found[:5])
        notify("和逸桃園館 11/7 有雙人房了！快去訂！\n" + "\n".join(found[:5]),
               "Double room AVAILABLE!", "urgent")
    else:
        print("還沒有雙人房")
        notify("和逸桃園館 11/7 還沒有雙人房", "No double room yet", "low")
        print(text[:1500])  # 方便在 Actions 紀錄裡檢查有沒有抓到頁面

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("查詢失敗：", e)
        try:
            notify(f"查詢失敗：{e}", "Check failed")
        except Exception:
            pass
        sys.exit(1)
