# core/hotfix.py
import os
import re

def apply_hotfix_if_needed(decompiled_dir: str, config: dict):
    """
    Checks if the current version has a hotfix suffix, or a full version/code override defined in app.json.
    If so, it applies the modifications to both apktool.yml and AndroidManifest.xml.
    """
    hotfixes = config.get("hotfixes", {})
    version_overrides = config.get("version_overrides", {})
    version_code_overrides = config.get("version_code_overrides", {})
    
    if not hotfixes and not version_overrides and not version_code_overrides:
        return

    # 1. Edit apktool.yml
    apktool_yml_path = os.path.join(decompiled_dir, "apktool.yml")
    if os.path.exists(apktool_yml_path):
        with open(apktool_yml_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern_yml_name = re.compile(r"(versionName:\s*)(['\"]?)([^'\">\r\n]+)\2")
        match_yml = pattern_yml_name.search(content)
        
        if match_yml:
            original_version_name = match_yml.group(3).strip()
            new_version_name = None
            
            # Check versionName override
            if original_version_name in version_overrides:
                new_version_name = str(version_overrides[original_version_name])
            elif original_version_name in hotfixes:
                suffix = hotfixes[original_version_name]
                if not original_version_name.endswith(suffix):
                    new_version_name = f"{original_version_name}{suffix}"
                    
            if new_version_name:
                content = pattern_yml_name.sub(rf"\g<1>\g<2>{new_version_name}\g<2>", content, count=1)
                print(f"[+] [Version Patch] apktool.yml versionName patched: {original_version_name} -> {new_version_name}")

            # Check versionCode override (depends on original_version_name)
            if original_version_name in version_code_overrides:
                new_version_code = str(version_code_overrides[original_version_name])
                pattern_yml_code = re.compile(r"(versionCode:\s*)(['\"]?)([^'\">\r\n]+)\2")
                match_code = pattern_yml_code.search(content)
                if match_code:
                    original_code = match_code.group(3).strip()
                    content = pattern_yml_code.sub(rf"\g<1>\g<2>{new_version_code}\g<2>", content, count=1)
                    print(f"[+] [Version Patch] apktool.yml versionCode patched: {original_code} -> {new_version_code}")

        with open(apktool_yml_path, "w", encoding="utf-8") as f:
            f.write(content)

    # 2. Edit AndroidManifest.xml
    manifest_path = os.path.join(decompiled_dir, "AndroidManifest.xml")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern_manifest_name = re.compile(r'(android:versionName=")([^"]+)(")')
        match_manifest = pattern_manifest_name.search(content)
        
        if match_manifest:
            original_version_name = match_manifest.group(2)
            new_version_name = None
            
            if original_version_name in version_overrides:
                new_version_name = str(version_overrides[original_version_name])
            elif original_version_name in hotfixes:
                suffix = hotfixes[original_version_name]
                if not original_version_name.endswith(suffix):
                    new_version_name = f"{original_version_name}{suffix}"
                    
            if new_version_name:
                content = pattern_manifest_name.sub(rf"\g<1>{new_version_name}\g<3>", content, count=1)
                print(f"    [+] [Version Patch] AndroidManifest.xml versionName patched: {original_version_name} -> {new_version_name}")

            # Check versionCode
            if original_version_name in version_code_overrides:
                new_version_code = str(version_code_overrides[original_version_name])
                pattern_manifest_code = re.compile(r'(android:versionCode=")([^"]+)(")')
                match_code = pattern_manifest_code.search(content)
                if match_code:
                    original_code = match_code.group(2)
                    content = pattern_manifest_code.sub(rf"\g<1>{new_version_code}\g<3>", content, count=1)
                    print(f"    [+] [Version Patch] AndroidManifest.xml versionCode patched: {original_code} -> {new_version_code}")

        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(content)
