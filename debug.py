import os
import sys

print("--- RBXStalker V2 Diagnostic Tool ---")
print(f"Current Folder: {os.getcwd()}")

files = os.listdir(".")
required_files = ["main.py", "database.py", ".env"]
errors = False

print("\n[Checking Root Files]")
for file in required_files:
    if file in files:
        print(f"✅ Found: {file}")
    else:
        # Check for common mistakes
        if f"{file}.txt" in files:
            print(f"❌ ERROR: Found '{file}.txt'. Please rename it to '{file}' (remove .txt)")
            errors = True
        elif f"{file}.py" in files and file.endswith(".py"):
             print(f"❌ ERROR: Found '{file}.py'. You likely have double extensions hidden. Rename it to just '{file[:-3]}'")
             errors = True
        else:
            print(f"❌ MISSING: {file}")
            errors = True

print("\n[Checking Folders]")
if "cogs" in files and os.path.isdir("cogs"):
    print("✅ Found 'cogs' folder")
else:
    print("❌ MISSING 'cogs' folder")
    errors = True

if "utils" in files and os.path.isdir("utils"):
    print("✅ Found 'utils' folder")
else:
    print("❌ MISSING 'utils' folder")
    errors = True

print("\n[Checking .env Content]")
if os.path.exists(".env"):
    try:
        with open(".env", "r", encoding="utf-8") as f:
            content = f.read()
            if "```" in content:
                print("❌ ERROR: Your .env file contains markdown backticks (```). Remove them!")
                errors = True
            elif "YOUR_BOT_TOKEN_HERE" in content:
                print("⚠️ WARNING: You haven't replaced 'YOUR_BOT_TOKEN_HERE' in .env yet.")
            else:
                print("✅ .env looks okay (structure-wise)")
    except Exception as e:
        print(f"⚠️ Could not read .env: {e}")

print("\n" + "="*30)
if errors:
    print("❌ DIAGNOSIS: The bot cannot run because of the missing or misnamed files above.")
else:
    print("✅ DIAGNOSIS: Files look correct. If it still fails, try running start.bat again.")
print("="*30)
input("Press Enter to exit...")