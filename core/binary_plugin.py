import importlib.util
import os
import sys

def run_binary_patch(app_id: str, apk_path: str) -> bool:
    """
    Checks if apps/{app_id}/binary_patch.py exists.
    If so, executes its `patch(apk_path)` function.
    
    Returns:
        True if patch succeeded or no patch needed.
        False if patch failed.
    """
    patch_module_path = os.path.join("apps", app_id, "binary_patch.py")

    # אם הקובץ לא קיים, מדלגים בשקט (כמו שביקשת)
    if not os.path.isfile(patch_module_path):
        return True

    print(f"[*] [{app_id}] Found binary patch module. Executing...")

    try:
        spec = importlib.util.spec_from_file_location(
            f"apps.{app_id}.binary_patch", patch_module_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"[-] [{app_id}] Failed to load binary patch module: {e}")
        return False

    if not hasattr(module, "patch") or not callable(module.patch):
        print(f"[-] [{app_id}] binary_patch.py missing 'patch(apk_path)' function")
        return False

    try:
        # מריץ את הפונקציה patch מתוך הקובץ של האפליקציה
        result = module.patch(apk_path)
        if result:
            print(f"[+] [{app_id}] Binary patch applied successfully.")
        else:
            print(f"[-] [{app_id}] Binary patch returned failure.")
        return result
    except Exception as e:
        print(f"[-] [{app_id}] Binary patch raised exception: {e}")
        return False
