# 和逸飯店‧桃園館 11/7 雙人房監控

GitHub Actions 每 30 分鐘打開訂房頁，出現雙人房就用 ntfy 推播到手機。

## 要設定的 Secrets（Settings → Secrets and variables → Actions）
- `BOOKING_URL`：訂房網站上 11/7 入住、11/8 退房、2 大人的搜尋結果頁網址
- `NTFY_TOPIC`：手機 ntfy App 訂閱的頻道名稱

## 測試
Actions → check-double-room → Run workflow，看紀錄有沒有印出房型文字。

訂到房後到 Actions 把這個 workflow 停用（Disable workflow）。
