import os
import shutil
import glob

brain_dir = r"C:\Users\lisha\.gemini\antigravity\brain\d1005426-32db-4b7a-8675-86b026661586\.tempmediaStorage"
target_logo = r"c:\Users\lisha\OneDrive\Desktop\Wallet\static\img\logo.png"

# Find the most recently added image in the temp media storage
list_of_files = glob.glob(os.path.join(brain_dir, '*'))
if not list_of_files:
    print("No images found in temp media storage.")
else:
    latest_file = max(list_of_files, key=os.path.getctime)
    
    # Copy it to the static/img/logo.png
    os.makedirs(os.path.dirname(target_logo), exist_ok=True)
    shutil.copy2(latest_file, target_logo)
    print(f"Successfully updated Trackify logo using: {latest_file}")
