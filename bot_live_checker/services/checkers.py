import re
import json
import time
import requests
import instaloader
from config import MAX_RETRIES, RETRY_DELAY

HEADERS_DEFAULT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
}

def clean_target(target: str) -> str:
    """Extract clean UID or username from text or link."""
    target = target.strip()
    if not target:
        return ""
    if target.startswith("@"):
        target = target[1:]
    # TikTok URL
    tt_match = re.search(r'tiktok\.com/@([a-zA-Z0-9_\.]+)', target)
    if tt_match:
        return tt_match.group(1)
    # IG URL
    ig_match = re.search(r'instagram\.com/([a-zA-Z0-9_\.]+)', target)
    if ig_match:
        return ig_match.group(1)
    # FB profile.php?id=1000xxx
    fb_id_match = re.search(r'facebook\.com/profile\.php\?id=(\d+)', target)
    if fb_id_match:
        return fb_id_match.group(1)
    # FB facebook.com/username
    fb_user_match = re.search(r'facebook\.com/([a-zA-Z0-9\.]+)', target)
    if fb_user_match and fb_user_match.group(1) not in ['groups', 'pages', 'watch', 'marketplace']:
        return fb_user_match.group(1)
    return target.rstrip('/')

def check_facebook_uid_status(target: str, access_token: str = "") -> dict:
    """Check Facebook UID / profile live/die status."""
    uid = clean_target(target)
    if not uid:
        return {"live": False, "target": target, "name": "", "error": "Target không hợp lệ"}

    # 1. Graph API check if access_token provided
    if access_token:
        try:
            url = f"https://graph.facebook.com/v19.0/{uid}?fields=id,name&access_token={access_token}"
            resp = requests.get(url, headers=HEADERS_DEFAULT, timeout=8)
            data = resp.json()
            if "error" not in data and "id" in data:
                return {"live": True, "target": uid, "name": data.get("name", uid), "error": ""}
            elif "error" in data:
                err_msg = data["error"].get("message", "Tài khoản không tồn tại hoặc bị khoá")
                return {"live": False, "target": uid, "name": "", "error": err_msg}
        except Exception:
            pass

    # 2. Graph Picture API Check with redirect=false
    try:
        url = f"https://graph.facebook.com/{uid}/picture?type=large&redirect=false"
        resp = requests.get(url, headers=HEADERS_DEFAULT, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and "url" in data["data"]:
                img_url = data["data"].get("url", "")
                # Generic static silhouette avatar or broken resource url
                if "Ul-w-hFGGye.png" in img_url or "static.xx.fbcdn.net/rsrc.php" in img_url:
                    return {"live": False, "target": uid, "name": "", "error": "Tài khoản bị khoá / DIE"}
                return {"live": True, "target": uid, "name": uid, "error": ""}
            elif "error" in data:
                return {"live": False, "target": uid, "name": "", "error": data["error"].get("message", "Tài khoản không tồn tại")}
        elif resp.status_code in [400, 404]:
            return {"live": False, "target": uid, "name": "", "error": "Tài khoản không tồn tại hoặc đã bị xóa"}
    except Exception as e:
        return {"live": False, "target": uid, "name": "", "error": str(e)}

    return {"live": False, "target": uid, "name": "", "error": "Không thể kiểm tra trạng thái"}

def check_instagram_user(username: str) -> dict:
    """Check Instagram profile live/die status."""
    user = clean_target(username)
    if not user:
        return {"live": False, "target": username, "error": "Username không hợp lệ"}

    # 1. Web API profile check with IG App ID header
    ig_headers = {
        **HEADERS_DEFAULT,
        "X-IG-App-ID": "936619743392459",
        "Accept": "*/*",
    }
    try:
        url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={user}"
        resp = requests.get(url, headers=ig_headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            user_data = data.get("data", {}).get("user")
            if user_data:
                full_name = user_data.get("full_name", user)
                return {"live": True, "target": user, "name": full_name, "error": ""}
            else:
                return {"live": False, "target": user, "name": "", "error": "Tài khoản không tồn tại"}
        elif resp.status_code == 404:
            return {"live": False, "target": user, "name": "", "error": "Tài khoản không tồn tại hoặc đã đổi tên"}
    except Exception:
        pass

    # 2. Instaloader library fallback
    try:
        L = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(L.context, user)
        return {"live": True, "target": user, "name": profile.full_name or user, "error": ""}
    except instaloader.exceptions.ProfileNotExistsException:
        return {"live": False, "target": user, "name": "", "error": "Tài khoản không tồn tại"}
    except Exception as e:
        return {"live": False, "target": user, "name": "", "error": f"Không thể kiểm tra: {str(e)}"}

def check_tiktok_user(username: str) -> dict:
    """Check TikTok user live/die status."""
    user = clean_target(username)
    if not user:
        return {"live": False, "target": username, "error": "Username không hợp lệ"}

    # 1. oEmbed API check (Reliable & Fast for TikTok)
    try:
        oembed_url = f"https://www.tiktok.com/oembed?url=https://www.tiktok.com/@{user}"
        resp = requests.get(oembed_url, headers=HEADERS_DEFAULT, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            author_name = data.get("author_name", user)
            return {"live": True, "target": user, "name": author_name, "error": ""}
        elif resp.status_code in [404, 400]:
            return {"live": False, "target": user, "name": "", "error": "Tài khoản DIE / Không tồn tại"}
    except Exception:
        pass

    # 2. Web fallback check
    url = f"https://www.tiktok.com/@{user}"
    headers = {
        **HEADERS_DEFAULT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 404:
            return {"live": False, "target": user, "name": "", "error": "Tài khoản không tồn tại"}
        
        text = resp.text
        text_lower = text.lower()
        dead_signals = [
            "couldn't find this account",
            "không tìm thấy tài khoản này",
            "page not available",
            "user-not-found"
        ]
        if any(signal in text_lower for signal in dead_signals):
            return {"live": False, "target": user, "name": "", "error": "Tài khoản DIE / Không tồn tại"}
        
        if f'@{user.lower()}' in text_lower or 'webapp.user-detail' in text_lower:
            return {"live": True, "target": user, "name": user, "error": ""}
            
        return {"live": False, "target": user, "name": "", "error": "Tài khoản không tồn tại"}
    except Exception as e:
        return {"live": False, "target": user, "name": "", "error": f"Lỗi kiểm tra TikTok: {str(e)}"}
