import requests, re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

def inspect(u):
    r = requests.get(f'https://www.tiktok.com/@{u}', headers=headers)
    print(f"=== User: {u} ===")
    print("Status:", r.status_code)
    title = re.search(r'<title[^>]*>(.*?)</title>', r.text, re.IGNORECASE)
    print("Title:", title.group(1) if title else "NONE")
    scripts = re.findall(r'<script[^>]*id="([^"]+)"', r.text)
    print("Script IDs:", scripts)
    print(f"Contains @{u.lower()}:", f"@{u.lower()}" in r.text.lower())
    print("Contains user-not-found / couldn't find:", "couldn't find" in r.text.lower() or "user-not-found" in r.text.lower() or "không tìm thấy" in r.text.lower())

inspect("tiktok")
inspect("non_existent_account_99999999999999")
