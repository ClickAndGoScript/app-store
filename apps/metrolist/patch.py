import os
import re
import shutil

# --- הגדרות ---
# קוד ה-Smali לחומת האש (URL Filter) + הודעת ה-Toast
URL_FILTER_SMALI = """
.method public shouldOverrideUrlLoading(Landroid/webkit/WebView;Landroid/webkit/WebResourceRequest;)Z
    .registers 4

    invoke-interface {p2}, Landroid/webkit/WebResourceRequest;->getUrl()Landroid/net/Uri;
    move-result-object v0
    
    if-eqz v0, :allow_null
    
    invoke-virtual {v0}, Landroid/net/Uri;->toString()Ljava/lang/String;
    move-result-object v0
    
    invoke-virtual {p0, p1, v0}, {class_name}->shouldOverrideUrlLoading(Landroid/webkit/WebView;Ljava/lang/String;)Z
    move-result v0
    return v0
    
    :allow_null
    const/4 v0, 0x0
    return v0
.end method

.method public shouldOverrideUrlLoading(Landroid/webkit/WebView;Ljava/lang/String;)Z
    .registers 7

    const-string v0, "METROLIST_FILTER"

    # 1. Allow accounts.google.*
    const-string v1, "accounts.google."
    invoke-virtual {p2, v1}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v1
    if-eqz v1, :check_2
    goto :allow_url

    :check_2
    # 2. Allow accounts.youtube.com
    const-string v1, "accounts.youtube.com"
    invoke-virtual {p2, v1}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v1
    if-eqz v1, :check_3
    goto :allow_url

    :check_3
    # 3. Allow music.youtube.com
    const-string v1, "music.youtube.com"
    invoke-virtual {p2, v1}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v1
    if-eqz v1, :block_url
    goto :allow_url

    :block_url
    # --- BLOCK AND LOG ---
    new-instance v1, Ljava/lang/StringBuilder;
    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V
    const-string v2, "BLOCKED: "
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v1
    invoke-static {v0, v1}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    # --- SHOW TOAST ---
    iget-object v1, p0, {class_name}->$context:Landroid/content/Context;
    const-string v2, "הגישה לקישור זה נחסמה"
    const/4 v3, 0x0
    invoke-static {v1, v2, v3}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;
    move-result-object v1
    invoke-virtual {v1}, Landroid/widget/Toast;->show()V
    
    # Return 1 (true) to block the URL
    const/4 v0, 0x1
    return v0

    :allow_url
    # --- ALLOW AND LOG ---
    new-instance v1, Ljava/lang/StringBuilder;
    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V
    const-string v2, "ALLOWED: "
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v1
    invoke-static {v0, v1}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    # Return 0 (false) to allow the URL
    const/4 v0, 0x0
    return v0
.end method
"""

# שם המפתח להחלפה
STRING_NAME_TO_REPLACE = "stands_with_palestine"

# הטקסטים להחלפה
HEBREW_TEXT = "🇮🇱 !!!עם ישראל חי 🇮🇱"
ENGLISH_TEXT = "🇮🇱 Am Yisrael Chai!!! 🇮🇱"


def _free_up_main_dex(decompiled_dir: str):
    heavy_libraries = [os.path.join("kotlin"), os.path.join("okhttp3")]
    main_smali = os.path.join(decompiled_dir, "smali")
    dest_dex = os.path.join(decompiled_dir, "smali_classes2")
    
    if not os.path.exists(main_smali): return

    os.makedirs(dest_dex, exist_ok=True)
    for lib in heavy_libraries:
        src_path = os.path.join(main_smali, lib)
        dst_path = os.path.join(dest_dex, lib)
        if os.path.exists(src_path) and not os.path.exists(dst_path):
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.move(src_path, dst_path)
            print(f"[+] Optimization: Moved '{lib}' to smali_classes2 to free up 64K limit.")

def _patch_strings(decompiled_dir: str) -> bool:
    print(f"[*] Searching for strings.xml to replace '{STRING_NAME_TO_REPLACE}'...")
    res_dir = os.path.join(decompiled_dir, "res")
    
    if not os.path.exists(res_dir):
        print("[-] Error: 'res' directory not found.")
        return False

    pattern = re.compile(rf'(<string[^>]*name="{STRING_NAME_TO_REPLACE}"[^>]*>)(.*?)(</string>)')
    modified_count = 0

    for root, dirs, files in os.walk(res_dir):
        folder_name = os.path.basename(root)
        
        if folder_name.startswith("values") and "strings.xml" in files:
            filepath = os.path.join(root, "strings.xml")
            
            # בדיקה האם זו תיקיית עברית (iw באנדרואיד ישן או he בחדש)
            if folder_name in ["values-iw", "values-he", "values-b+iw", "values-b+he"]:
                replacement_text = HEBREW_TEXT
            else:
                # לכל שאר השפות ולברירת המחדל
                replacement_text = ENGLISH_TEXT
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                if pattern.search(content):
                    new_content = pattern.sub(rf'\g<1>{replacement_text}\g<3>', content)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    modified_count += 1
                    print(f"  [+] Patched {folder_name}: {replacement_text}")
                    
            except Exception as e:
                print(f"[-] Error processing string file {filepath}: {e}")

    if modified_count > 0:
        print(f"[+] Successfully replaced '{STRING_NAME_TO_REPLACE}' across {modified_count} language files!")
        return True
    else:
        print(f"[-] Target string '{STRING_NAME_TO_REPLACE}' was not found in any strings.xml files.")
        return False

def patch(decompiled_dir: str) -> bool:
    print("[*] Starting MetroList 'Kosher' patch...")
    
    _free_up_main_dex(decompiled_dir)
    
    if not _patch_thumbnail(decompiled_dir):
        print("[-] Warning: Failed to patch Thumbnail.smali. Continuing...")
        
    # הפעלת פאצ' המחרוזות
    _patch_strings(decompiled_dir)
    
    webview_client_file = _find_webview_client_target(decompiled_dir)
    if webview_client_file:
        if not _inject_url_filter(webview_client_file):
            print("[-] CRITICAL: URL filter patch failed. Aborting build to maintain security!")
            return False
    else:
        print("[-] CRITICAL: Could not find the WebViewClient file. Patch failed.")
        return False
        
    print("[+] MetroList patch applied successfully.")
    return True

def _patch_thumbnail(root_dir):
    print("[*] Searching for Thumbnail.smali to block image URLs...")
    for root, dirs, files in os.walk(root_dir):
        if "Thumbnail.smali" in files and "metrolist" in root and "models" in root:
            target_path = os.path.join(root, "Thumbnail.smali")
            try:
                with open(target_path, 'r', encoding='utf-8') as f: content = f.read()
                pattern = r'(iput-object p2, p0, Lcom/metrolist/innertube/models/Thumbnail;->(?:a|url):Ljava/lang/String;)'
                if re.search(pattern, content):
                    new_content = re.sub(pattern, r'const-string p2, ""\n    \1', content)
                    with open(target_path, 'w', encoding='utf-8') as f: f.write(new_content)
                    print("[+] Thumbnail.smali: URL loading blocked.")
                    return True
            except Exception as e:
                print(f"[-] Error patching Thumbnail.smali: {e}")
    return False

def _find_webview_client_target(root_dir):
    anchor_string = 'javascript:Android.onRetrieveVisitorData'
    known_relative_path = os.path.join("com", "metrolist", "music", "ui", "screens", "LoginScreenKt$LoginScreen$1$1$1.smali")
    
    print("[*] Trying fast-path: Checking known class for WebViewClient...")
    
    for smali_dir in os.listdir(root_dir):
        if smali_dir.startswith("smali"):
            exact_path = os.path.join(root_dir, smali_dir, known_relative_path)
            if os.path.exists(exact_path):
                try:
                    with open(exact_path, 'r', encoding='utf-8') as f:
                        if anchor_string in f.read():
                            print(f"[+] Found known WebViewClient file quickly: {os.path.basename(exact_path)}")
                            return exact_path
                except Exception:
                    pass

    print("[i] Known class not found or anchor missing. Falling back to full scan...")
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".smali"):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        if anchor_string in f.read():
                            print(f"[+] Found WebViewClient file via fallback scan: {file}")
                            return path
                except (IOError, UnicodeDecodeError):
                    pass
                    
    return None

def _inject_url_filter(file_path):
    print(f"[*] Injecting URL Filter & Toast into: {os.path.basename(file_path)}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
        
        class_match = re.search(r'\.class .*? (L[^;]+;)', content)
        if not class_match:
            print("[-] Could not dynamically identify Class Name.")
            return False
        
        class_desc = class_match.group(1)
        
        if "METROLIST_FILTER" in content:
            print("[i] URL filter already injected. Skipping.")
            return True
            
        smali_to_inject = "\n" + URL_FILTER_SMALI.replace("{class_name}", class_desc) + "\n"
        content += smali_to_inject
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"[+] Successfully injected URL Filter to {class_desc}")
        return True
    except Exception as e:
        print(f"[-] An error occurred during URL filter injection: {e}")
        return False
