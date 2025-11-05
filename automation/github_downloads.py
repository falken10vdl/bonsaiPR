import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
OWNER = "falken10vdl"
REPO = "bonsaiPR"
GITHUB_API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/releases"
TOKEN = os.getenv("GITHUB_TOKEN")

# --- HEADERS ---
headers = {}
if TOKEN:
    headers["Authorization"] = f"token {TOKEN}"

# --- FETCH RELEASES ---
response = requests.get(GITHUB_API_URL, headers=headers)
if response.status_code != 200:
    print(f"Error fetching releases: {response.status_code} {response.text}")
    exit(1)

releases = response.json()

# --- CALCULATE TOTALS ---
grand_total = 0
print(f"\n📦 Download statistics for {OWNER}/{REPO}\n")

for release in releases:
    tag = release.get("tag_name", "(no tag)")
    release_total = sum(asset["download_count"] for asset in release.get("assets", []))
    grand_total += release_total

    print(f"🔖 Release: {tag} — {release_total} downloads")
    for asset in release.get("assets", []):
        name = asset["name"]
        count = asset["download_count"]
        print(f"   • {name}: {count}")
    print()

print(f"🏁 Total downloads across all releases: {grand_total}\n")
