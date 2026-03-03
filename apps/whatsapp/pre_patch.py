import os
import subprocess
import sys
import shutil

def pre_patch(apk_path: str) -> bool:
    """
    Applies the Schwartzblat WhatsAppPatcher logic.
    """
    print(f"[*] Starting WhatsApp Schwartzblat Patcher logic on {apk_path}...")

    repo_url = "https://github.com/Schwartzblat/WhatsAppPatcher.git"
    repo_dir = "WhatsAppPatcher"

    try:
        # 1. Clone the repository with submodules if it doesn't exist
        if os.path.exists(repo_dir):
            print(f"[*] Cleaning up existing {repo_dir}...")
            shutil.rmtree(repo_dir)
        
        print(f"[*] Cloning {repo_url}...")
        subprocess.check_call(["git", "clone", "--recurse-submodules", repo_url, repo_dir])

        # 2. Install dependencies
        print("[*] Installing Patcher Dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", os.path.join(repo_dir, "requirements.txt")])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "stitch-test", 
                               "--index-url", "https://test.pypi.org/simple/", 
                               "--extra-index-url", "https://pypi.org/simple"])

        # 3. Apply Firebase bypass
        print("[*] Bypassing Firebase patch in WhatsAppPatcher...")
        main_py_path = os.path.join(repo_dir, "main.py")
        if os.path.exists(main_py_path):
            with open(main_py_path, 'r', encoding='utf-8') as f:
                content = f.read()
            content = content.replace('FirebaseParamsFinder(args),', '')
            with open(main_py_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        java_path = os.path.join(repo_dir, "smali_generator/app/src/main/java/com/smali_generator/TheAmazingPatch.java")
        if os.path.exists(java_path):
            with open(java_path, 'r', encoding='utf-8') as f:
                java_content = f.read()
            java_content = java_content.replace('new FirebaseParams(),', '')
            with open(java_path, 'w', encoding='utf-8') as f:
                f.write(java_content)

        # 4. Run the patcher
        patched_apk = "latest_patched.apk"
        print(f"[*] Running Patcher on {apk_path}...")
        # Schwartzblat patcher expects absolute or relative path to APK. 
        # We need to make sure we handle the paths correctly since we'll be calling it from inside repo_dir or passing absolute paths.
        abs_apk_path = os.path.abspath(apk_path)
        abs_patched_apk = os.path.abspath(patched_apk)
        
        # We run it from the repo_dir to ensure it finds its own modules
        subprocess.check_call([sys.executable, "main.py", "-p", abs_apk_path, "-o", abs_patched_apk, "--no-sign"], cwd=repo_dir)

        # 5. Replace original APK
        if os.path.exists(patched_apk):
            print(f"[+] WhatsApp Patch successful. Replacing {apk_path}.")
            shutil.move(patched_apk, apk_path)
            return True
        else:
            print("[-] WhatsApp Patch failed. Output file not found.")
            return False

    except Exception as e:
        print(f"[-] Error in WhatsApp pre-patch: {e}")
        return False
    finally:
        # Optional: cleanup repo_dir if needed, but keeping it might speed up subsequent runs if cached
        pass

if __name__ == "__main__":
    # Test call
    import sys
    if len(sys.argv) > 1:
        pre_patch(sys.argv[1])
