import os
import requests
import subprocess
import zipfile
import shutil

class AptoideSource:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.base_url = "https://ws2.aptoide.com/api/7/app/getMeta"

    def get_latest_version(self, package_name: str):
        print(f"[*] [Aptoide] Fetching metadata for: {package_name}")
        params = {
            "package_name": package_name,
            "language": "en",
            "aab": True  # <--- הוספנו תמיכה ב-App Bundles
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get("info", {}).get("status") != "OK":
                print(f"[-] [Aptoide] API returned status: {data.get('info', {}).get('status')}")
                return None, None, None
            
            app_data = data.get("data", {})
            file_data = app_data.get("file", {})
            
            version = file_data.get("vername")
            download_url = file_data.get("path") or file_data.get("path_alt")
            title = app_data.get("name", package_name)
            
            return version, download_url, title
            
        except Exception as e:
            print(f"[-] [Aptoide] Error fetching metadata: {e}")
            return None, None, None

def is_newer_version(local_ver: str, remote_ver: str) -> bool:
    """משווה בצורה חכמה בין גרסאות כדי למנוע Downgrade"""
    try:
        # חילוץ מספרים בלבד מתוך מחרוזת הגרסה
        local_parts = [int(x) for x in local_ver.split('.') if x.isdigit()]
        remote_parts = [int(x) for x in remote_ver.split('.') if x.isdigit()]
        return tuple(remote_parts) > tuple(local_parts)
    except Exception:
        # גיבוי למקרה שיש פורמט גרסה מוזר
        return remote_ver != local_ver

def convert_aab_to_apk(aab_path: str, output_apk_path: str):
    """ממיר קובץ AAB לקובץ APK אוניברסלי בעזרת bundletool"""
    bundletool_path = "bundletool.jar"
    
    if not os.path.exists(bundletool_path):
        print("[-] [Error] bundletool.jar not found! Please download it and place it in the same folder.")
        return False

    apks_path = "temp_output.apks"
    print(f"[*] Converting {aab_path} to universal APK using bundletool...")

    # הרצת פקודת bundletool
    cmd = [
        "java", "-jar", bundletool_path,
        "build-apks",
        f"--bundle={aab_path}",
        f"--output={apks_path}",
        "--mode=universal"
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"[-] [Error] bundletool failed: {e.stderr.decode()}")
        return False

    # חילוץ קובץ ה-APK האוניברסלי מתוך ארכיון ה-APKS (שהוא בעצם קובץ ZIP)
    print("[*] Extracting universal.apk...")
    try:
        with zipfile.ZipFile(apks_path, 'r') as zip_ref:
            zip_ref.extract("universal.apk", ".")
            
        # שינוי שם לקובץ הרצוי
        if os.path.exists(output_apk_path):
            os.remove(output_apk_path)
        os.rename("universal.apk", output_apk_path)
        
        # ניקוי קבצים זמניים
        os.remove(apks_path)
        os.remove(aab_path) # מוחק את ה-AAB המקורי אחרי שהמרנו אותו
        
        print(f"[+] Successfully generated: {output_apk_path}")
        return True
    except Exception as e:
        print(f"[-] [Error] Failed to extract APK: {e}")
        return False

def main():
    package_name = "com.spotify.music"
    local_version = "9.1.70.1902.1"
    
    aptoide = AptoideSource()
    version, download_url, title = aptoide.get_latest_version(package_name)
    
    if not version or not download_url:
        print("[-] Could not fetch details.")
        return

    print(f"[*] [Spotify] Local version: {local_version}")
    print(f"[*] [Spotify] Remote version: {version}")
    print(f"[*] [Spotify] Download URL: {download_url}")

    if is_newer_version(local_version, version):
        print(f"[!] [Spotify] Update detected! ({local_version} -> {version})")
        
        # קביעת סוג הקובץ לפי כתובת ההורדה
        ext = ".aab" if download_url.endswith(".aab") else ".apk"
        downloaded_file = f"downloaded_spotify{ext}"
        final_file = "spotify_latest.apk"

        print(f"[*] Downloading {ext} file...")
        # הורדת הקובץ
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(downloaded_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        
        print(f"[+] Download complete: {downloaded_file}")

        # אם ירד קובץ AAB, נבצע לו המרה ל-APK
        if ext == ".aab":
            convert_aab_to_apk(downloaded_file, final_file)
        else:
            # אם ירד APK מלכתחילה, פשוט נשנה לו את השם
            os.rename(downloaded_file, final_file)
            print(f"[+] File is already an APK. Saved as {final_file}")

    else:
        print(f"[*] [Spotify] App is up to date (or remote version is older). No download needed.")

if __name__ == "__main__":
    print("============================================================")
    print("  Testing Spotify Download with App Bundle Support")
    print("============================================================")
    main()
