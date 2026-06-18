import os
import hashlib
import zipfile
import shutil
import xml.etree.ElementTree as ET

class Generator:
    def __init__(self):
        self.addons_paths = []
        self.xml_path = "addons.xml"
        self.md5_path = "addons.xml.md5"

    def scan_and_zip_addons(self):
        # Scan root directory for plugin/repo folders
        for folder in os.listdir("."):
            if os.path.isdir(folder) and folder not in [".git", "__pycache__"]:
                addon_xml_path = os.path.join(folder, "addon.xml")
                if os.path.exists(addon_xml_path):
                    self.addons_paths.append(addon_xml_path)
                    self.create_zip(folder, addon_xml_path)

    def create_zip(self, folder, xml_path):
        # Create Kodi-standard zip files (e.g., plugin.video.iatheater-0.2.0.zip)
        try:
            tree = ET.parse(xml_path)
            version = tree.getroot().get("version")
            zip_name = f"{folder}-{version}.zip"
            zip_path = os.path.join(folder, zip_name)
            
            # --- Cleanup Sweep: Remove any existing .zip files in the folder ---
            for file in os.listdir(folder):
                if file.endswith('.zip'):
                    old_zip_path = os.path.join(folder, file)
                    try:
                        os.remove(old_zip_path)
                        print(f"Removed outdated archive: {old_zip_path}")
                    except Exception as e:
                        print(f"Error removing old zip {old_zip_path}: {e}")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(folder):
                    for file in files:
                        if not file.endswith('.zip') and not file.endswith('.pyc'):
                            file_path = os.path.join(root, file)
                            arcname = os.path.join(folder, os.path.relpath(file_path, folder))
                            zipf.write(file_path, arcname)
            print(f"Generated distribution zip: {zip_path}")
        except Exception as e:
            print(f"Error zipping {folder}: {e}")

    def generate_xml(self):
        # Compile all addon.xml files into the master index
        addons_xml = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n<addons>\n"
        
        for path in self.addons_paths:
            try:
                tree = ET.parse(path)
                xml_str = ET.tostring(tree.getroot(), encoding="unicode")
                if "<?xml" in xml_str:
                    xml_str = xml_str.split("?>\n", 1)[-1]
                addons_xml += xml_str + "\n"
            except Exception as e:
                print(f"Error parsing {path}: {e}")

        addons_xml += "</addons>\n"
        
        with open(self.xml_path, "w", encoding="utf-8") as f:
            f.write(addons_xml)
        print(f"Successfully built master index: {self.xml_path}")

    def generate_md5(self):
        # Hash the master index for Kodi version checking
        try:
            with open(self.xml_path, "rb") as f:
                md5_hash = hashlib.md5(f.read()).hexdigest()
            
            with open(self.md5_path, "w", encoding="utf-8") as f:
                f.write(md5_hash)
            print(f"Successfully generated checksum: {self.md5_path}")
        except Exception as e:
            print(f"Error generating MD5: {e}")

    def sync_root_zip(self):
        # Locate the generated repository zip and copy it to the root directory
        repo_folder = "repository.pythontrousers"
        addon_xml_path = os.path.join(repo_folder, "addon.xml")
        
        if os.path.exists(addon_xml_path):
            try:
                tree = ET.parse(addon_xml_path)
                version = tree.getroot().get("version")
                zip_name = f"{repo_folder}-{version}.zip"
                source_zip = os.path.join(repo_folder, zip_name)
                dest_zip = os.path.join(".", zip_name)
                
                if os.path.exists(source_zip):
                    # --- Cleanup Sweep: Remove outdated repository zips in root ---
                    for file in os.listdir("."):
                        if file.startswith(repo_folder) and file.endswith('.zip') and file != zip_name:
                            try:
                                os.remove(file)
                                print(f"Removed outdated root archive: {file}")
                            except Exception as e:
                                pass
                                
                    shutil.copy2(source_zip, dest_zip)
                    print(f"Successfully synced root installation zip: {dest_zip}")
            except Exception as e:
                print(f"Error syncing root zip: {e}")

if __name__ == "__main__":
    print("Starting Kodi Repository Generator...")
    gen = Generator()
    gen.scan_and_zip_addons()
    gen.generate_xml()
    gen.generate_md5()
    gen.sync_root_zip()
    print("Generation complete.")