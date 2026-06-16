import os
import hashlib
import zipfile
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

if __name__ == "__main__":
    print("Starting Kodi Repository Generator...")
    gen = Generator()
    gen.scan_and_zip_addons()
    gen.generate_xml()
    gen.generate_md5()
    print("Generation complete.")