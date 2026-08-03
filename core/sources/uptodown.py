import re
import json
import cloudscraper
import urllib.parse
from bs4 import BeautifulSoup

class UptodownSource:
    def __init__(self, uptodown_subdomain=None, timeout=30, debug=True):
        self.uptodown_subdomain = uptodown_subdomain
        self.timeout = timeout
        self.debug = debug

        self.scraper = cloudscraper.create_scraper(
            browser={'browser': 'firefox', 'platform': 'windows', 'desktop': True}
        )
        self.scraper.headers.update({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        })

    def _log(self, *args, **kwargs):
        if self.debug:
            print("[DEBUG]", *args, **kwargs)

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
                # 1. סינון סיומות נפוצות מה-Package Name כדי לנסות לנחש את הכתובת הישירה (הכי מהיר אם עובד)
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
                
                # 2. גיבוי דרך מנוע החיפוש הפנימי של Uptodown
                if not app_url:
                    search_query_escaped = urllib.parse.quote_plus(package_name)
                    search_url = f"https://en.uptodown.com/android/search?q={search_query_escaped}"
                    
                    self._log(f"Search URL: {search_url}")
                    r_search = self.scraper.get(search_url, timeout=self.timeout)
                    self._log(f"Search URL status: {r_search.status_code}")
                    
                    if r_search.status_code == 200:
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

                # 3. גיבוי אוניברסלי מנצח: חיפוש בגוגל ממוקד אתר ושם חבילה
                if not app_url:
                    self._log("Trying external generic search engine (Google)...")
                    try:
                        query = f'site:en.uptodown.com/android "{package_name}"'
                        google_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
                        
                        # כותרות כדי שגוגל יחשוב שאנחנו דפדפן רגיל ולא רובוט
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Accept-Language": "en-US,en;q=0.9"
                        }
                        
                        r_google = self.scraper.get(google_url, headers=headers, timeout=self.timeout)
                        self._log(f"Google Search status: {r_google.status_code}")
                        
                        if r_google.status_code == 200:
                            # חיפוש כל כתובות ה-URL של אפליקציות באפטודאון מתוך תוצאות החיפוש
                            matches = re.findall(r'(https://[a-z0-9-]+\.en\.uptodown\.com/android)', r_google.text)
                            
                            for match in matches:
                                if 'uptodown-android' not in match: # מתעלם מהאפליקציה הרשמית של החנות
                                    app_url = match
                                    self._log(f"Found app via Google search: {app_url}")
                                    break
                        elif r_google.status_code == 429:
                            self._log("Google blocked the request (429 Too Many Requests).")
                            
                    except Exception as e:
                        self._log(f"Google search error: {e}")

            if not app_url:
                self._log("Could not determine app URL after all fallback attempts.")
                return None, None

            # כניסה לעמוד ההורדה הראשי
            download_page = f"{app_url.rstrip('/')}/download"
            self._log(f"Download page: {download_page}")
            r_dl = self.scraper.get(download_page, timeout=self.timeout)
            
            if r_dl.status_code != 200:
                self._log(f"CRITICAL: Failed to load download page! Status {r_dl.status_code}")
                return None, None

            soup_dl = BeautifulSoup(r_dl.text, 'html.parser')
            name_el = soup_dl.select_one('#detail-app-name')
            if not name_el:
                return None, None
            
            default_file_id = name_el.get('data-file-id')
            target_file_id = default_file_id

            # סינון XAPK והעדפת APK טהור
            format_el = soup_dl.select_one('span.format')
            file_format = format_el.get_text(strip=True).upper() if format_el else "APK"

            if "XAPK" in file_format or "APK" not in file_format:
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
                            r_var = self.scraper.get(variants_url, timeout=self.timeout)
                            if r_var.status_code == 200:
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

            if not target_file_id:
                return None, None
                
            self._log(f"Final selected file ID: {target_file_id}")

            current_download_page = download_page
            if target_file_id != default_file_id:
                current_download_page = f"{app_url}/download/{target_file_id}"
                self._log(f"Fetching specific variant download page: {current_download_page}")
                r_dl = self.scraper.get(current_download_page, timeout=self.timeout)
                soup_dl = BeautifulSoup(r_dl.text, 'html.parser')

            # חילוץ הטוקן מהכפתור ישירות מעמוד ההורדה הרשמי
            download_button = soup_dl.select_one('#detail-download-button')
            final_token = download_button.get('data-url') if download_button else None
            
            if not final_token:
                if download_button and download_button.has_attr('href'):
                     final_token = download_button.get('href')
                else:
                    self._log("CRITICAL: Failed to find download token or link in button!")
                    return None, None
            
            # -------------------------------------------------------------
            # השלמת הכתובת
            # -------------------------------------------------------------
            final_token = final_token.strip('/')
            
            if final_token.startswith('dwn/'):
                final_token = final_token[4:]
            elif final_token.startswith('http'):
                if not final_token.endswith('.apk'):
                    final_token = f"{final_token.rstrip('/')}/app.apk"
                download_url = final_token
            
            if not final_token.startswith('http'):
                download_url = f"https://dw.uptodown.com/dwn/{final_token}/app.apk"
            
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
        url, version = self._get_uptodown_app(package_name)
        if url:
            return version, f"uptodown_direct:{url}", package_name
        return "latest", f"fallback:{package_name}", package_name

    def get_download_url(self, initial_url):
        self._log(f"get_download_url({initial_url})")
        
        if initial_url.startswith("uptodown_direct:"):
            return initial_url.split("uptodown_direct:", 1)[1]
            
        package_name = initial_url.split("fallback:", 1)[1] if "fallback:" in initial_url else initial_url
        url, _ = self._get_uptodown_app(package_name)
        return url
