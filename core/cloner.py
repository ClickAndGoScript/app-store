import os
import re
import xml.etree.ElementTree as ET


def run_clone(decompiled_dir: str, clone_config: dict) -> bool:
    """
    Apply a perfect MT-Manager style clone logic to AndroidManifest.xml.
    - No Smali modification.
    - Resolves relative classes.
    - Prefixes Authorities and Permissions exactly like MT Manager.
    - Ignores <action> and <category> tags.
    """
    old_pkg = clone_config.get("old_pkg")
    new_pkg = clone_config.get("new_pkg")
    app_name_suffix = clone_config.get("app_name_suffix", " (Cloned)")


    if not all([old_pkg, new_pkg]):
        print("[-] [Cloner] 'old_pkg' and 'new_pkg' are required in clone_config.")
        return False


    print(f"\n[*] [Cloner] Starting Smart Clone: {old_pkg} -> {new_pkg}")


    # Setup XML namespaces for Android
    ET.register_namespace('android', '                                              ;)
    ns_android = '                                              ;
    attr_name = f'{{{ns_android}}}name'
    attr_auth = f'{{{ns_android}}}authorities'
    attr_target = f'{{{ns_android}}}targetActivity'


    # ==========================================
    # 1. Edit AndroidManifest.xml safely via XML
    # ==========================================
    manifest_path = os.path.join(decompiled_dir, "AndroidManifest.xml")
    if os.path.exists(manifest_path):
        try:
            tree = ET.parse(manifest_path)
            root = tree.getroot()


            # Step A: Resolve relative paths (MUST do before changing the package)
            components =['application', 'activity', 'activity-alias', 'service', 'receiver', 'provider']
            for tag in components:
                for elem in root.iter(tag):
                    name = elem.get(attr_name)
                    if name and name.startswith('.'):
                        elem.set(attr_name, old_pkg + name)


                    target = elem.get(attr_target)
                    if target and target.startswith('.'):
                        elem.set(attr_target, old_pkg + target)


            # Step B: Change Root Package
            root.set('package', new_pkg)


            # Step C: Update Authorities (Critical for <provider>)
            # MT Manager Rule: If it contains old_pkg, replace. Otherwise, prepend new_pkg + "_"
            for provider in root.iter('provider'):
                auths = provider.get(attr_auth)
                if auths:
                    new_auth_list =[]
                    for a in auths.split(';'):
                        if old_pkg in a:
                            new_auth_list.append(a.replace(old_pkg, new_pkg))
                        else:
                            # Matches MT Manager output on row 185 (e.g. com.whatsapp.kosher_androidx...)
                            new_auth_list.append(f"{new_pkg}_{a}")
                    provider.set(attr_auth, ";".join(new_auth_list))


            # Step D: Update Permissions only (Do NOT touch <action> or <category>)
            tags_to_check =['permission', 'uses-permission', 'uses-permission-sdk-23']
            for tag in tags_to_check:
                for elem in root.iter(tag):
                    val = elem.get(attr_name)
                    if val:
                        # Skip standard Android permissions (android.permission.* / com.android.*)
                        if val.startswith("android.permission.") or val.startswith("com.android."):
                            continue


                        # Replace if old package name exists, otherwise prepend
                        if old_pkg in val:
                            elem.set(attr_name, val.replace(old_pkg, new_pkg))
                        else:
                            elem.set(attr_name, f"{new_pkg}_{val}")


            # Step E: Write back Manifest
            tree.write(manifest_path, encoding='utf-8', xml_declaration=True)
            print("    [+] AndroidManifest.xml parsed and modified successfully.")


        except ET.ParseError as e:
            print(f"[-] [Cloner] Failed to parse AndroidManifest.xml: {e}")
            return False
    else:
        print("[-] [Cloner] AndroidManifest.xml not found!")
        return False




    # ==========================================
    # 2. Update apktool.yml (Manifest Renaming)
    # ==========================================
    apktool_yml_path = os.path.join(decompiled_dir, "apktool.yml")
    if os.path.exists(apktool_yml_path):
        with open(apktool_yml_path, 'r', encoding='utf-8') as f:
            yml_content = f.read()


        if "renameManifestPackage:" in yml_content:
            yml_content = re.sub(r'renameManifestPackage:.*', f'renameManifestPackage: {new_pkg}', yml_content)
        else:
            yml_content += f'\nrenameManifestPackage: {new_pkg}\n'


        with open(apktool_yml_path, 'w', encoding='utf-8') as f:
            f.write(yml_content)
        print("    [+] apktool.yml configured for new package.")


    # ==========================================
    # 3. Change App Name in strings.xml
    # ==========================================
    strings_path = os.path.join(decompiled_dir, "res", "values", "strings.xml")
    if os.path.exists(strings_path):
        try:
            with open(strings_path, 'r', encoding='utf-8') as f:
                strings_content = f.read()


            new_content = re.sub(
                r'(<string name="app_name">)(.*?)(</string>)', 
                rf'\1\2{app_name_suffix}\3', 
                strings_content
            )


            if new_content != strings_content:
                with open(strings_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"    [+] App name updated (added suffix: '{app_name_suffix}').")
        except Exception as e:
             print(f"    [-] Could not update strings.xml: {e}")


    print("    [+] [Cloner] Clone applied successfully!")
    return True
