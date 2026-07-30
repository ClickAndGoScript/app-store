import re
import json
import cloudscraper
from bs4 import BeautifulSoup

class UptodownSource:
    def __init__(self, uptodown_subdomain=None, timeout=30, debug=True):
        self.uptodown_subdomain = uptodown_subdomain
        self.timeout = timeout
        self.debug = debug

        self.scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )
        self.scraper.headers.update({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
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
                parts = package_name.split('.')
                query_parts = [p for p in parts if p.lower() not in ('com', 'org', 'net', 'co', 'io', 'gov', 'android', 'app', 'mobile')]
                
                # 1. ניחוש חכם של כתובת ה-URL
                if query_parts:
                    guess_subdomain = query_parts[0].lower()
                    direct_url = f"https://{guess_subdomain}.en.uptodown.com/android"
                    self._log(f"Trying direct URL guess: {direct_url}")
                    try:
                        r_dir = self.scraper.get(direct_url, timeout=self.timeout)
                        self._log(f"Direct URL status: {r_dir.status_code}")
                        
                        if r_dir.status_code == 200:
                            if 'detail-app-name' in r_dir.text or re.search(r'\b' + re.escape(package_name) + r'\b', r_dir.text):
                                app_url = direct_url
                                self._log("Direct URL guess successful.")
                            else:
                                self._log("URL works but package name not found. Falling back to search.")
                        elif r_dir.status_code in (403, 429):
                            self._log("Cloudflare blocked the direct URL request.")
                    except Exception as e:
                        self._log(f"Direct URL error: {e}")
                
                # 2. גיבוי דרך מנוע החיפוש
                if not app_url:
                    search_query = " ".join(query_parts) if query_parts else package_name.replace('.', ' ')
                    search_query_escaped = search_query.replace(' ', '+')
                    
                    search_url = f"https://en.uptodown.com/android/search/{search_query_escaped}"
                    self._log(f"Search URL: {search_url}")
                    r_search = self.scraper.get(search_url, timeout=self.timeout)
                    
                    m_redirect = re.search(r'^(https://[a-z0-9-]+\.en\.uptodown\.com/android)', r_search.url)
                    if r_search.url != search_url and m_redirect:
                        self._log("Search auto-redirected directly to the app page.")
                        app_url = m_redirect.group(1)
                    else:
                        soup_search = BeautifulSoup(r_search.text, 'html.parser')
                        candidates = []
                        
                        for link in soup_search.find_all('a', href=True):
                            href = link.get('href', '')
                            m = re.search(r'(https://[a-z0-9-]+\.en\.uptodown\.com/android)', href)
                            if m:
                                base_url = m.group(1)
                                if 'uptodown-android' not in base_url and base_url not in candidates:
                                    candidates.append(base_url)

                        if not candidates:
                            text_clean = r_search.text.replace('\\/', '/')
                            for match in re.findall(r'(https://[a-z0-9-]+\.en\.uptodown\.com/android)', text_clean):
                                if 'uptodown-android' not in match and match not in candidates:
                                    candidates.append(match)

                        self._log(f"Found {len(candidates)} app candidate(s)")
                        if candidates:
                            pkg_keyword = parts[-1]
                            if pkg_keyword.lower() in ('android', 'app', 'music', 'mobile', 'lite', 'pro') and len(parts) > 1:
                                pkg_keyword = parts[-2]
                                
                            candidates = sorted(candidates, key=lambda c: 0 if pkg_keyword.lower() in c.lower() else 1)
                            
                            for cand_url in candidates:
                                try:
                                    cand_r = self.scraper.get(cand_url, timeout=self.timeout)
                                    if re.search(r'\b' + re.escape(package_name) + r'\b', cand_r.text):
                                        app_url = cand_url
                                        break
                                except Exception:
                                    pass
                                    
                            if not app_url:
                                for c in candidates:
                                    if pkg_keyword.lower() in c.lower():
                                        app_url = c
                                        break

                            if not app_url:
                                return None, None
                        else:
                            return None, None

            if not app_url:
                return None, None

            download_page = f"{app_url}/download"
            self._log(f"Download page: {download_page}")
            r_dl = self.scraper.get(download_page, timeout=self.timeout)
            soup_dl = BeautifulSoup(r_dl.text, 'html.parser')

            name_el = soup_dl.select_one('#detail-app-name')
            if not name_el:
                return None, None
            
            target_file_id = name_el.get('data-file-id')

            variants_btn = soup_dl.select_one('button.variants')
            if variants_btn:
                data_version = variants_btn.get('data-version')
                data_code = None
                
                data_code_match = re.search(r'data-code="(\d+)"', r_dl.text)
                if data_code_match:
                    data_code = data_code_match.group(1)
                else:
                    code_el = soup_dl.find(attrs={"data-code": True})
                    if code_el:
                        data_code = code_el.get("data-code")

                if data_code and data_version:
                    domain = app_url.split('//')[1].split('/')[0]
                    variants_url = f"https://{domain}/app/{data_code}/version/{data_version}/files"
                    
                    try:
                        r_var = self.scraper.get(variants_url, timeout=self.timeout)
                        if r_var.status_code == 200:
                            var_json = r_var.json()
                            var_soup = BeautifulSoup(var_json.get('content', ''), 'html.parser')
                            
                            for el in var_soup.find_all(attrs={"data-file-id": True}):
                                curr = el
                                found_format = None
                                while curr and curr.name not in ['body', 'html']:
                                    text = curr.get_text(separator=" ", strip=True).upper()
                                    if bool(re.search(r'\bAPK\b', text)) and bool(re.search(r'\bXAPK\b', text)):
                                        break
                                    elif bool(re.search(r'\bXAPK\b', text)):
                                        found_format = "XAPK"
                                        break
                                    elif bool(re.search(r'\bAPK\b', text)):
                                        found_format = "APK"
                                        break
                                    curr = curr.parent
                                    
                                if found_format == "APK":
                                    target_file_id = el.get('data-file-id')
                                    break
                    except Exception:
                        pass

            if not target_file_id:
                return None, None
                
            self._log(f"Final selected file ID: {target_file_id}")

            # ה-Referer לעמוד יצירת הטוקן חייב להיות עמוד ההורדה הראשי
            pre_download_url = f"{download_page}/{target_file_id}-x"
            self.scraper.headers.update({'Referer': download_page})
            
            r_pre = self.scraper.get(pre_download_url, timeout=self.timeout)
            soup_pre = BeautifulSoup(r_pre.text, 'html.parser')

            download_button = soup_pre.select_one('#detail-download-button')
            final_token = download_button.get('data-url') if download_button else None
            
            if not final_token:
                if download_button and download_button.has_attr('href'):
                     final_token = download_button.get('href')
                else:
                    return None, None
                    
            if final_token.startswith('http'):
                download_url = final_token
            else:
                final_token = final_token.strip('/')
                download_url = f"https://dw.uptodown.com/dwn/{final_token}"
                
            version_name = self._get_real_version(soup_dl, download_url)
            self._log(f"Extracted token URL: {download_url}")

            # --- קסם: פיענוח לינק ה-CDN הישיר ---
            self._log("Resolving final CDN URL using scraper to bypass anti-bot...")
            try:
                # קריטי: השרת דורש שה-Referer יהיה בדיוק העמוד שממנו נלקח הטוקן (זה עם ה-x בסוף)
                self.scraper.headers.update({"Referer": pre_download_url})
                
                # עוקבים אחרי ה-Redirect מבלי להוריד את הקובץ לזיכרון
                r_final = self.scraper.get(download_url, stream=True, allow_redirects=True, timeout=30)
                final_cdn_url = r_final.url
                status_code = r_final.status_code
                r_final.close()
                
                if status_code < 400:
                    self._log(f"Successfully resolved CDN URL: {final_cdn_url}")
                    # אנחנו שותלים את לינק ה-CDN הציבורי והפתוח כדי ש-run.py יקבל אותו
                    download_url = final_cdn_url 
                else:
                    self._log(f"Warning: CDN resolution returned HTTP {status_code}")
                    
            except Exception as e:
                self._log(f"Failed to resolve CDN URL: {e}")
            # ---------------------------------

            self._log(f"Final version: {version_name}")
            self._log(f"Final URL: {download_url}")
            return download_url, version_name

        except Exception as e:
            self._log(f"Error: {e}")
            import traceback
            traceback.print_exc()
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
        
        # מכיוון שפיענחנו את הלינק קודם, initial_url הוא עכשיו לינק ציבורי ישיר לשרת ה-CDN!
        if initial_url.startswith("uptodown_direct:"):
            return initial_url.split("uptodown_direct:", 1)[1]
            
        package_name = initial_url.split("fallback:", 1)[1] if "fallback:" in initial_url else initial_url
        url, _ = self._get_uptodown_app(package_name)
        return url
