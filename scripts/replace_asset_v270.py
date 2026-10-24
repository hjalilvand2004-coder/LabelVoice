#!/usr/bin/env python3
"""جایگزینی دارایی Mobile-App-PWA در Release v2.7.0 با نسخهٔ تمیز (بدون نام تکراری).

توکن فقط گذرا از متغیر محیطی GH_TOKEN یا ورودی استاندارد خوانده می‌شود؛ هرگز ذخیره نمی‌شود.
"""
import json
import os
import sys
import urllib.request

TOKEN = os.environ.get("GH_TOKEN") or sys.stdin.readline().strip()
API = "https://api.github.com/repos/hjalilvand2004-coder/LabelVoice"
REL_ID = 422948603
NAME = "LabelVoice-v2.7.0-Mobile-App-PWA.zip"


def req(method, url, data=None, headers=None):
    h = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(r, timeout=300) as resp:
        body = resp.read()
        return json.loads(body) if body else {}


rel = req("GET", f"{API}/releases/{REL_ID}")
for a in rel.get("assets", []):
    if a["name"] == NAME:
        req("DELETE", f"{API}/releases/assets/{a['id']}")
        print("حذف دارایی قدیمی:", a["id"])

data = open(f"/home/z/my-project/download/{NAME}", "rb").read()
up = rel["upload_url"].split("{")[0]
out = req("POST", up + f"?name={NAME}", data=data,
          headers={"Content-Type": "application/octet-stream",
                   "Content-Length": str(len(data))})
print("آپلود شد:", out["name"], out["size"] // 1024 // 1024, "MB")
