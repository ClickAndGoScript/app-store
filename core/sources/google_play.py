import os
import sys
import json
import subprocess
import urllib.request
from pathlib import Path

class FakeResponse:
    """מזייף אובייקט Response של requests כדי ש-downloader.py יעבוד כרגיל"""
    def __init__(self, filepath, url):
        self.filepath = filepath
        self.status_code = 200
        self.url = url
        self.headers = {
            "Content-Type": "application/vnd.android.package-archive",
            "Content-Disposition": f'attachment; filename="{os.path.basename(filepath)}"'
        }

    def iter_content(self, chunk_size=8192):
        with open(self.filepath, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def close(self):
        # מוחק את קובץ הטיוטה לאחר שההורדה הסתיימה
        if os.path.exists(self.filepath):
            os.remove(self.filepath)

class GPlayScraper:
    def __init__(self, gplay_script):
        self.gplay_script = gplay_script

    def get(self, url, stream=False, headers=None, allow_redirects=True):
        # מחלצים את שם החבילה מה-URL המזויף שלנו
        package_name = url.split("gplay_dl:")[1]
        out_dir = os.path.join(os.getcwd(), "scratch", "gplay_tmp")
        os.makedirs(out_dir, exist_ok=True)

        print(f"[*] [GooglePlay] Downloading & Merging {package_name} via GPlay Engine...")
        
        # שימוש ב-sys.executable מבטיח שנשתמש בסביבת הפייתון הנוכחית
        cmd = [
            sys.executable, self.gplay_script, "download", package_name,
            "-m",  # מיזוג של ה-Splits ל-APK אחד
            "-o", out_dir
        ]
        
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            raise Exception("GPlay CLI download failed. Check console logs.")

        # מציאת ה-APK המוכן בתיקיית הפלט
        downloaded_file = None
        for f in os.listdir(out_dir):
            if f.startswith(package_name) and f.endswith(".apk"):
                downloaded_file = os.path.join(out_dir, f)
                break

        if not downloaded_file:
            raise Exception("GPlay CLI finished but no APK was found in the output directory.")

        return FakeResponse(downloaded_file, url)

class GooglePlaySource:
    def __init__(self, timeout: int = 300):
        self.timeout = timeout
        self.engine_dir = os.path.join(os.getcwd(), "core", "gplay_engine")
        self.gplay_script = os.path.join(self.engine_dir, "gplay-downloader.py")
        self.headers = {} # השארת Headers ריקים למניעת קריסות ב-downloader
        
        # הורדה של הריפו תוך כדי ריצה (אם לא קיים)
        self._ensure_engine_downloaded()
        
        self.scraper = GPlayScraper(self.gplay_script)
        self._ensure_auth()

    def _ensure_engine_downloaded(self):
        # שיבוט הריפו של GPlay
        if not os.path.exists(self.gplay_script):
            print("[*] [GooglePlay] GPlay Engine not found. Cloning at runtime...")
            repo_url = "https://github.com/alltechdev/gplay-apk-downloader.git"
            try:
                # --depth 1 כדי להוריד מהר בלי היסטוריית גיט
                subprocess.run(["git", "clone", "--depth", "1", repo_url, self.engine_dir], check=True)
            except subprocess.CalledProcessError as e:
                raise Exception(f"Failed to clone GPlay Engine: {e}")

        # הורדת APKEditor.jar למיזוג (במידה וחסר)
        apkeditor_path = os.path.join(self.engine_dir, "APKEditor.jar")
        if not os.path.exists(apkeditor_path):
            print("[*] [GooglePlay] Downloading APKEditor.jar for GPlay Engine...")
            apkeditor_url = "https://github.com/REAndroid/APKEditor/releases/download/V1.4.7/APKEditor-1.4.7.jar"
            try:
                urllib.request.urlretrieve(apkeditor_url, apkeditor_path)
            except Exception as e:
                print(f"[-] [GooglePlay] Failed to download APKEditor: {e}")

    def _ensure_auth(self):
        auth_file = Path.home() / ".gplay-auth.json"
        if not auth_file.exists():
            print("[*] [GooglePlay] Auth file missing. Authenticating with Dispenser...")
            
            # משתמשים בדיספנסר הציבורי של אורורה כברירת מחדל
            dispenser_url = os.environ.get("DISPENSER_URL", "https://dispenser.auroraoss.com/")
            
            cmd = [sys.executable, self.gplay_script, "auth", "-d", dispenser_url]
            subprocess.run(cmd, check=True)

    def get_latest_version(self, package_name: str):
        print(f"[*] [GooglePlay] Checking latest version for: {package_name}")
        try:
            result = subprocess.run(
                [sys.executable, self.gplay_script, "check-version", package_name, "--json"],
                capture_output=True, text=True, check=True
            )
            data = json.loads(result.stdout)
            
            if data.get("success"):
                version = data.get("version")
                title = data.get("title", package_name)
                # מחזירים את ה-package_name כ"URL" כדי שיועבר בהמשך
                return version, package_name, title
            else:
                print(f"[-] [GooglePlay] Error from API: {data.get('error')}")
                return None, None, None
        except Exception as e:
            print(f"[-] [GooglePlay] Failed to run check-version: {e}")
            return None, None, None

    def get_download_url(self, initial_url: str):
        # מעבירים את שם החבילה יחד עם תחילית מזהה אל ה-Fake Scraper שלנו
        return f"gplay_dl:{initial_url}"
