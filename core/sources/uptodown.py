import re
import json
import time
import cloudscraper
import urllib.parse
import socket
from bs4 import BeautifulSoup

class UptodownSource:
    def __init__(self, uptodown_subdomain=None, timeout=30, debug=True):
        self.uptodown_subdomain = uptodown_subdomain
        self.timeout = timeout
        self.debug = debug

        # שינינו ל-Chrome מודרני כדי לחמוק מחסימות 410
        self.scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )
        self.scraper.headers.update({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        })
        # === התיקון שלנו (שורה אחת!) ===
        # מונע מ-downloader.py לדרוס את ה-Headers של ה-scraper עם DEFAULT_HEADERS בעייתיים
        self.headers = {}
    
    def _log(self, *args, **kwargs):
        if self.debug:
            print("[DEBUG]", *args, **kwargs)

    # פונקציית עזר להעלאת ה-HTML לשרת Termbin
    def _dump_html(self, step_name, html_content):
        if not self.debug:
            return
            
        self._log(f"Uploading HTML dump for '{step_name}' to Termbin...")
        try:
            text_to_send = f"=== HTML DUMP FOR STEP: {step_name} ===\n\n{html_content}"
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(15) 
            s.connect(("termbin.com", 9999))
            s.sendall(text_to_send.encode("utf-8"))
            url = s.recv(1024).decode("utf-8").strip()
            s.close()
            
            self._log(f"========================================================")
            self._log(f"[!] HTML DUMP READY TO VIEW! {step_name} -> {url}")
            self._log(f"========================================================")
        except Exception as e:
            self._log(f"[-] Failed to upload HTML dump to Termbin: {e}")

    # ---------- Version extraction ----------
    def _extract_version_from_title(self, soup):
        title = soup.find('title')
        if title:
            match = re.search(r'(\d+(?:\.\d+)+)', title.get_text())
            if match:
                return match.group(1)
        return None

    def _extract_version_from_ld_json(self, soup):
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            if script.string:
                try:
                    data = json.loads(script.string)
                    ver = None
                    if 'mainEntity' in data and isinstance(data['mainEntity'], dict):
                        ver = data['mainEntity'].get('softwareVersion')
                    else:
                        ver = data.get('softwareVersion')
                    if ver and ver.strip():
                        return ver.strip()
                except:
                    continue
        return None

    def _extract_version_from_div(self, soup):
        version_el = soup.select_one('.version, .detail-version')
        if version_el:
            match = re.search(r'(\d+(?:\.\d+)+)', version_el.get_text())
            if match:
                return match.group(1)
        return None

    def _extract_version_from_url(self, url):
        match = re.search(r'(\d+(?:\.\d+)+)', url)
        return match.group(1) if match else None

    def _extract_version_from_headers(self, url):
        try:
            head = self.scraper.head(url, allow_redirects=True, timeout=10)
            cd = head.headers.get('Content-Disposition', '')
            match = re.search(r'filename="?([^"]+)"?', cd)
            if match:
                filename = match.group(1)
                return self._extract_version_from_url(filename)
        except:
            pass
        return None

    def _get_real_version(self, soup, download_url):
        ver = self._extract_version_from_ld_json(soup)
        if ver:
            self._log(f"Version from LD+JSON: {ver}")
            return ver

        ver = self._extract_version_from_div(soup)
        if ver:
            self._log(f"Version from HTML element: {ver}")
            return ver

        ver = self._extract_version_from_title(soup)
        if ver:
            self._log(f"Version from title: {ver}")
            return ver

        if download_url:
            ver = self._extract_version_from_headers(download_url)
            if ver:
                self._log(f"Version from Content-Disposition: {ver}")
                return ver

        self._log("Searching raw text for version (fallback)...")
        text = soup.get_text()
        all_versions = re.findall(r'\b(\d+(?:\.\d+){1,5})\b', text)
        if all_versions:
            valid_versions = [v for v in all_versions if v.count('.') >= 2]
            if not valid_versions:
                valid_versions = all_versions
            best = max(valid_versions, key=lambda v: tuple(map(int, v.split('.'))))
            self._log(f"Version from text fallback: {best}")
            return best

        self._log("No version found, using 'latest'")
        return "latest"

    # ---------- Download logic ----------
    def _get_uptodown_app(self, package_name):
        self._log(f"Querying Uptodown for {package_name}...")
        try:
            app_url = None

            if self.uptodown_subdomain:
                app_url = f"https://{self.uptodown_subdomain}.en.uptodown.com/android"
            else:
                # 1. ניסיון ניחוש אוניברסלי לפי Package Name
                parts = package_name.split('.')
                query_parts = [p for p in parts if p.lower() not in ('com', 'org', 'net', 'co', 'io', 'gov', 'android', 'app', 'mobile')]
                
                if query_parts:
                    guesses = []
                    guesses.append(f"https://{query_parts[0].lower()}.en.uptodown.com/android")
                    if query_parts[-1].lower() != query_parts[0].lower():
                        guesses.append(f"https://{query_parts[-1].lower()}.en.uptodown.com/android")
                    if len(query_parts) > 1:
                        joined_guess = "-".join(query_parts).lower()
                        guesses.append(f"https://{joined_guess}.en.uptodown.com/android")
                    
                    for direct_url in guesses:
                        self._log(f"Trying direct URL guess: {direct_url}")
                        try:
                            r_dir = self.scraper.get(direct_url, timeout=self.timeout)
                            self._log(f"Direct URL status: {r_dir.status_code}")
                            
                            if r_dir.status_code == 200:
                                if 'detail-app-name' in r_dir.text or re.search(r'\b' + re.escape(package_name) + r'\b', r_dir.text):
                                    app_url = direct_url
                                    self._log(f"Direct URL guess successful: {app_url}")
                                    break
                        except Exception as e:
                            self._log(f"Direct URL error: {e}")
                        
                        if app_url: break
                
                # 2. חיפוש דרך מנוע החיפוש הפנימי
                if not app_url:
                    search_query_escaped = urllib.parse.quote_plus(package_name)
                    search_url = f"https://en.uptodown.com/android/search?q={search_query_escaped}"
                    
                    self._log(f"Search URL: {search_url}")
                    r_search = self.scraper.get(search_url, timeout=self.timeout)
                    self._log(f"Search URL status: {r_search.status_code}")
                    
                    if r_search.status_code == 200:
                        self._dump_html(f"uptodown_search_{package_name}", r_search.text)
                        
                        m_redirect = re.search(r'^(https://[a-z0-9-]+\.en\.uptodown\.com/android)', r_search.url)
                        if r_search.url != search_url and m_redirect:
                            app_url = m_redirect.group(1)
                            self._log(f"Search auto-redirected directly to: {app_url}")
                        else:
                            soup_search = BeautifulSoup(r_search.text, 'html.parser')
                            for item in soup_search.select('.item .name a, a.app-link'):
                                href = item.get('href', '')
                                if href and 'uptodown-android' not in href:
                                    app_url = href.split('/download')[0]
                                    self._log(f"Found app via search selector: {app_url}")
                                    break
                    else:
                        self._log("Internal search page blocked. Moving to external search fallback.")

                # 3. גיבוי אוניברסלי 1: Bing
                if not app_url:
                    self._log("Trying external generic search engine (Bing)...")
                    try:
                        query = f'site:en.uptodown.com/android "{package_name}"'
                        bing_url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(query)}"
                        
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Accept-Language": "en-US,en;q=0.9"
                        }
                        r_bing = self.scraper.get(bing_url, headers=headers, timeout=self.timeout)
                        self._log(f"Bing status: {r_bing.status_code}")
                        
                        if r_bing.status_code == 200:
                            self._dump_html(f"bing_{package_name}", r_bing.text)
                            
                            decoded_text = urllib.parse.unquote(r_bing.text)
                            matches = re.findall(r'(https://[a-z0-9-]+\.en\.uptodown\.com/android)', decoded_text)
                            
                            for match in matches:
                                if 'uptodown-android' not in match:
                                    app_url = match
                                    self._log(f"Found app via Bing search: {app_url}")
                                    break
                    except Exception as e:
                        self._log(f"Bing search error: {e}")

                # 4. גיבוי אוניברסלי 2: Yahoo
                if not app_url:
                    self._log("Trying external generic search engine (Yahoo)...")
                    try:
                        query = f'site:en.uptodown.com/android "{package_name}"'
                        yahoo_url = f"https://search.yahoo.com/search?p={urllib.parse.quote_plus(query)}"
                        
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Accept-Language": "en-US,en;q=0.9"
                        }
                        
                        r_yahoo = self.scraper.get(yahoo_url, headers=headers, timeout=self.timeout)
                        self._log(f"Yahoo status: {r_yahoo.status_code}")
                        
                        if r_yahoo.status_code == 200:
                            self._dump_html(f"yahoo_{package_name}", r_yahoo.text)
                            
                            decoded_text = urllib.parse.unquote(r_yahoo.text)
                            matches = re.findall(r'(https://[a-z0-9-]+\.en\.uptodown\.com/android)', decoded_text)
                            
                            for match in matches:
                                if 'uptodown-android' not in match:
                                    app_url = match
                                    self._log(f"Found app via Yahoo search: {app_url}")
                                    break
                    except Exception as e:
                        self._log(f"Yahoo search error: {e}")

            if not app_url:
                self._log("Could not determine app URL after all fallback attempts.")
                return None, None

            # --- שלב 1: כניסה לעמוד הראשי של האפליקציה ---
            self._log(f"Fetching main app page: {app_url}")
            r_main = self.scraper.get(app_url, timeout=self.timeout)
            
            if r_main.status_code != 200:
                self._log(f"CRITICAL: Failed to load main app page! Status {r_main.status_code}")
                return None, None
                
            self._dump_html(f"main_page_{package_name}", r_main.text)
            soup_main = BeautifulSoup(r_main.text, 'html.parser')
            
            latest_btn = soup_main.select_one('a.button-download, div.button-download a, button#detail-download-button, a.latest, a[href$="/download"]')
            
            if not latest_btn:
                self._log("CRITICAL: Could not find the 'Get the latest version' button on the main page.")
                return None, None
                
            raw_download_link = latest_btn.get('href') or latest_btn.get('data-url')
            if not raw_download_link:
                self._log("CRITICAL: Found the button but it has no link attached.")
                return None, None
            
            # בניית כתובת מלאה ובטוחה לעמוד ההורדה
            base_url = r_main.url if r_main.url.endswith('/') else r_main.url + '/'
            download_page_url = urllib.parse.urljoin(base_url, raw_download_link)
            self._log(f"Successfully extracted exact download page URL: {download_page_url}")
            
            # --- המתנה קריטית לעקיפת 410 ---
            # חומת האש חוסמת בוטים שעוברים עמודים ללא המתנה (0 מילישניות). נדמה בן אדם!
            time.sleep(2)
            
            # --- שלב 2: כניסה לעמוד ההורדה ---
            self.scraper.headers.update({"Referer": r_main.url})
            r_dl = self.scraper.get(download_page_url, timeout=self.timeout)
            
            # נשק יום הדין למקרה של 410/403 על עמוד ההורדה
            if r_dl.status_code in [410, 403]:
                self._log(f"Got {r_dl.status_code} on download page. Trying standard requests fallback...")
                import requests
                fallback_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Referer": r_main.url
                }
                r_dl = requests.get(download_page_url, headers=fallback_headers, timeout=self.timeout)
            
            if r_dl.status_code != 200:
                self._log(f"CRITICAL: Failed to load specific download page! Status {r_dl.status_code}")
                return None, None
                
            self._dump_html(f"download_page_{package_name}", r_dl.text)
            soup_dl = BeautifulSoup(r_dl.text, 'html.parser')
            
            name_el = soup_dl.select_one('#detail-app-name')
            default_file_id = name_el.get('data-file-id') if name_el else None
            target_file_id = default_file_id

            format_el = soup_dl.select_one('span.format')
            file_format = format_el.get_text(strip=True).upper() if format_el else "APK"

            if ("XAPK" in file_format or "APK" not in file_format) and default_file_id:
                self._log("Default file is XAPK. Searching for pure APK variants...")
                variants_btn = soup_dl.select_one('button.variants')
                if variants_btn:
                    data_version = variants_btn.get('data-version')
                    data_code_match = re.search(r'data-code="(\d+)"', r_dl.text)
                    if data_code_match and data_version:
                        data_code = data_code_match.group(1)
                        domain = app_url.split('//')[1].split('/')[0]
                        variants_url = f"https://{domain}/app/{data_code}/version/{data_version}/files"
                        
                        try:
                            time.sleep(1)
                            self.scraper.headers.update({"Referer": r_dl.url})
                            r_var = self.scraper.get(variants_url, timeout=self.timeout)
                            if r_var.status_code == 200:
                                self._dump_html(f"variants_{package_name}", r_var.text)
                                var_json = r_var.json()
                                var_soup = BeautifulSoup(var_json.get('content', ''), 'html.parser')
                                for variant in var_soup.select('div.variant'):
                                    v_format_el = variant.select_one('div.v-file span')
                                    v_format = v_format_el.get_text(strip=True).upper() if v_format_el else ""
                                    if "APK" in v_format and "XAPK" not in v_format:
                                        report_el = variant.select_one('.v-report')
                                        if report_el:
                                            target_file_id = report_el.get('data-file-id')
                                            self._log(f"Found pure APK variant (ID: {target_file_id})")
                                            break
                        except Exception:
                            pass

            if target_file_id and target_file_id != default_file_id:
                current_download_page = f"{app_url}/download/{target_file_id}"
                self._log(f"Fetching specific variant download page: {current_download_page}")
                
                time.sleep(1)
                self.scraper.headers.update({"Referer": r_dl.url})
                r_dl_var = self.scraper.get(current_download_page, timeout=self.timeout)
                
                if r_dl_var.status_code in [410, 403]:
                    import requests
                    r_dl_var = requests.get(current_download_page, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": r_dl.url}, timeout=self.timeout)

                if r_dl_var.status_code == 200:
                    self._dump_html(f"specific_variant_{package_name}", r_dl_var.text)
                    soup_dl = BeautifulSoup(r_dl_var.text, 'html.parser')
                else:
                    self._log(f"Failed to load variant page (Status {r_dl_var.status_code}). Proceeding with default.")

            # --- שלב 3: חילוץ טוקן ההורדה והרכבת הכתובת הסופית ---
            download_button = soup_dl.select_one('#detail-download-button')
            final_token = download_button.get('data-url') if download_button else None
            
            if not final_token:
                if download_button and download_button.has_attr('href'):
                     final_token = download_button.get('href')
                else:
                    self._log("CRITICAL: Failed to find download token or link in button!")
                    return None, None
            
            final_token = final_token.strip('/')
            
            if final_token.startswith('dwn/'):
                final_token = final_token[4:]
                
            if final_token.startswith('http'):
                download_url = final_token
            else:
                # הרכבת הקישור לשרתי uptodown.net (על בסיס התמונה מה-IDM שלך)
                download_url = f"https://dw.uptodown.net/dwn/{final_token}"
            
            if not download_url.endswith('.apk'):
                download_url = f"{download_url.rstrip('/')}/app.apk"
            
            version_name = self._get_real_version(soup_dl, download_url)

            self._log(f"Final version: {version_name}")
            self._log(f"Final URL: {download_url}")
            
            return download_url, version_name

        except Exception as e:
            self._log(f"Exception caught in _get_uptodown_app: {e}")
            return None, None

    # ---------- Public interface ----------
    def get_latest_version(self, package_name):
        self._log(f"get_latest_version({package_name})")
        
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            self._log(f"--- Attempt {attempt} of {max_retries} for {package_name} ---")
            
            url, version = self._get_uptodown_app(package_name)
            
            if url:
                self._log(f"Success on attempt {attempt}!")
                return version, f"uptodown_direct:{url}", package_name
            
            if attempt < max_retries:
                self._log(f"Attempt {attempt} failed. Waiting 5 seconds before retrying...")
                time.sleep(5) # המתנה כדי לתת למנוע החיפוש/חומת האש "להירגע" לפני הניסיון הבא
        
        # אם הגענו לפה, סימן שכל הניסיונות נכשלו. 
        # כאן אנחנו חייבים לרסק את התהליך במקום להחזיר "latest", כדי לא להשחית את הנתונים בגיטהאב
        raise Exception(f"Failed to find URL for {package_name} after {max_retries} attempts. Aborting to prevent version corruption.")

    def get_download_url(self, initial_url):
        self._log(f"get_download_url({initial_url})")
        
        if initial_url.startswith("uptodown_direct:"):
            return initial_url.split("uptodown_direct:", 1)[1]
            
        package_name = initial_url.split("fallback:", 1)[1] if "fallback:" in initial_url else initial_url
        url, _ = self._get_uptodown_app(package_name)
        return url
