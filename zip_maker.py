import os
import zipfile

dist_dir = r"dist\orologic"
zip_path = "Orologic.zip"

print(f"Creating zip file '{zip_path}' from directory '{dist_dir}'...")

if not os.path.exists(dist_dir):
    print(f"Error: directory '{dist_dir}' does not exist. Make sure PyInstaller finished compiling.")
    exit(1)

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    file_count = 0
    for root, dirs, files in os.walk(dist_dir):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, dist_dir)
            zipf.write(file_path, arcname)
            file_count += 1

print(f"Successfully created '{zip_path}' with {file_count} files.")
