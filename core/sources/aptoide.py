import requests

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

    def get_download_url(self, initial_url: str):
        """
        Aptoide provides the direct link, but before passing it to the downloader,
        we inspect the server headers to see what file we are actually getting.
        """
        print(f"\n================ [ DEBUG: SERVER URL INSPECTION ] ================")
        try:
            # בקשת "הצצה" לשרת שקוראת רק את ההדרים (Headers) בלי להוריד את התוכן
            with requests.get(initial_url, stream=True, timeout=self.timeout) as r:
                content_length = r.headers.get('Content-Length', '0')
                content_disp = r.headers.get('Content-Disposition', 'None')
                
                size_mb = int(content_length) / (1024 * 1024) if content_length.isdigit() else 0
                
                print(f"[*] True Download URL: {r.url}")
                print(f"[*] Expected File Size: {size_mb:.2f} MB")
                print(f"[*] Content-Disposition: {content_disp}")
                
                if ".aab" in r.url or ".aab" in content_disp:
                    print("[!] DIAGNOSIS: The server is sending an App Bundle (.aab)")
                elif ".apks" in r.url or ".apks" in content_disp:
                    print("[!] DIAGNOSIS: The server is sending a Split APK Archive (.apks)")
                else:
                    print("[!] DIAGNOSIS: The server is sending an APK (Could be a base.apk or monolithic)")
        except Exception as e:
            print(f"[-] Could not inspect URL: {e}")
        print("==================================================================\n")
        
        return initial_url
