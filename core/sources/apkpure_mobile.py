import re
import requests

class APKPureMobileSource:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.base_api = "https://api.pureapk.com/m/v3/cms/app_version"
        
        # כותרות שמחקות מכשיר אנדרואיד
        self.headers = {
            'x-sv': '29',
            'x-abis': 'arm64-v8a,armeabi-v7a,armeabi',
            'x-gp': '1',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36'
        }
        # שימוש ב-Session כדי לשמור על חיבור יעיל ותמיכה בהפניות (Redirects)
        self.scraper = requests.Session()

    def _extract_version(self, text: str) -> str | None:
        if not text:
            return None
        # מחפש תבנית של גרסה, למשל 1.2.3 או 4.100.0
        match = re.search(r"(\d+(?:\.\d+){1,})", text)
        return match.group(1) if match else None

    def get_latest_version(self, package_name: str):
        print(f"[*] [APKPure Mobile] Fetching metadata for: {package_name}")
        params = {
            'hl': 'en-US',
            'package_name': package_name
        }
        
        try:
            response = self.scraper.get(
                self.base_api,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            # מחקה את פקודת ה-strings של ה-Bash: מושך את כל הרצפים של תווים קריאים באורך 8 ומעלה
            strings = re.findall(rb'[ -~]{8,}', response.content)
            
            # מחפש מחרוזת שמתחילה ב-http ומכילה /APK או /XAPK (בדיוק כמו ה-grep)
            valid_urls =[]
            for s in strings:
                if s.startswith(b'http'):
                    s_upper = s.upper()
                    if b'/APK' in s_upper or b'/XAPK' in s_upper:
                        valid_urls.append(s.decode('utf-8'))
            
            if not valid_urls:
                print("[-] [APKPure Mobile] No APK/XAPK URL found in API response.")
                return None, None, None
                
            # לוקחים את הכתובת הראשונה (שהיא העדכנית ביותר)
            release_url = valid_urls[0]
            title = package_name
            version = None
            
            # ניסיון 1: חילוץ הגרסה מתוך ה-URL עצמו
            version = self._extract_version(release_url)
            
            # ניסיון 2: אם אין גרסה ב-URL, נבצע בקשת "הצצה" (HEAD) כדי לקרוא את שם הקובץ האמיתי מהשרת
            if not version:
                try:
                    head_resp = self.scraper.head(release_url, headers=self.headers, allow_redirects=True, timeout=10)
                    cd = head_resp.headers.get("Content-Disposition", "")
                    match = re.search(r"filename\*?=['\"]?(?:UTF-8'')?([^'\";\n]+)", cd)
                    if match:
                        filename = match.group(1)
                        version = self._extract_version(filename)
                except Exception as e:
                    print(f"[-] [APKPure Mobile] Warning - Could not fetch headers for version: {e}")

            # כגיבוי אחרון אם שום דבר לא עבד
            if not version:
                version = "latest"
            
            return version, release_url, title
            
        except Exception as e:
            print(f"[-] [APKPure Mobile] Error resolving via API: {e}")
            return None, None, None

    def get_download_url(self, initial_url: str):
        # ה-URL שהתקבל הוא כבר קישור ישיר להורדה
        return initial_url
