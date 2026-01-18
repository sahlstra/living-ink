#!/usr/bin/env python3
"""Process one notebook: preprocess PNGs, run Google Vision OCR, aggregate text, build PDF, create Apple Note."""
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

# --- LOGGING SUPPRESSION ---
# Suppress specific benign warnings from rmscene/rmc that scare users
class WarningFilter(logging.Filter):
    def filter(self, record):
        try:
            msg = record.getMessage()
            if "Unknown formatting code" in msg:
                return False
            if "Some data has not been read" in msg:
                return False
        except Exception:
            pass
        return True

# Apply filter to rmscene logger and rmc logger
for logger_name in ["rmscene", "rmc", "rmscene.text"]:
    logging.getLogger(logger_name).addFilter(WarningFilter())

ROOT = Path('.').resolve()
WHITE_DIR = ROOT / 'remarkable_pngs_white'
VISION_DIR = ROOT / 'remarkable_pngs_for_vision'
OCR_DIR = ROOT / 'output'  # Changed from remarkable_ocr to output
PDF_DIR = ROOT / 'remarkable_pdfs'
PROCESSED_LOG = ROOT / 'processed_notebooks.json'
LOGS_DIR = ROOT / 'logs'
LOGS_DIR.mkdir(exist_ok=True)
LOG_PATH = LOGS_DIR / 'pipeline.log'

VISION_DIR.mkdir(exist_ok=True)
OCR_DIR.mkdir(exist_ok=True)
PDF_DIR.mkdir(exist_ok=True)


import datetime
import importlib.util

# --- NEW CONFIGURATION LOADING (YAML) ---
import yaml

# Try loading from config/config.yml (standard location) or root config.yml
YAML_CONFIG_PATH = ROOT / 'config' / 'config.yml'
if not YAML_CONFIG_PATH.exists():
     YAML_CONFIG_PATH = ROOT / 'config.yml'

if YAML_CONFIG_PATH.exists():
    try:
        with open(YAML_CONFIG_PATH, 'r') as f:
            try:
                yaml_config = yaml.safe_load(f) or {}
            except yaml.YAMLError as ye:
                print(f"\n❌ CONFIGURATION ERROR: Could not parse config.yml")
                print(f"Please check your indentation. YAML is very sensitive to spaces.")
                if hasattr(ye, 'problem_mark'):
                    mark = ye.problem_mark
                    print(f"Error position: line {mark.line + 1}, column {mark.column + 1}")
                print(f"Details: {ye}\n")
                yaml_config = {}

            # 1. OpenAI
            if 'openai' in yaml_config and 'api_key' in yaml_config['openai']:
                os.environ['OPENAI_API_KEY'] = str(yaml_config['openai']['api_key']).strip()
            
            # 2. reMarkable
            if 'remarkable' in yaml_config and 'device_token' in yaml_config['remarkable']:
                os.environ['REMARKABLE_TOKEN'] = str(yaml_config['remarkable']['device_token']).strip()

            # 3. Google Vision (Handle JSON content directly or file path)
            if 'google_vision' in yaml_config:
                gv = yaml_config['google_vision']
                
                # Option A: Path to JSON file (Preferred for humans)
                if 'credentials_path' in gv and gv['credentials_path']:
                    path_str = str(gv['credentials_path']).strip()
                    # Handle typical user paths like ~/Documents
                    expanded_path = os.path.expanduser(path_str)
                    
                    if os.path.exists(expanded_path):
                         os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = expanded_path
                    else:
                         print(f"❌ Config Error: credentials_path file not found at: {path_str}")
                
                # Option B: Embedded JSON content
                elif 'credentials_json' in gv:
                    creds_content = gv['credentials_json']
                    
                    # Validate if it looks like JSON
                    if isinstance(creds_content, str):
                        creds_content = creds_content.strip()
                        if not creds_content.startswith('{'):
                             print("⚠️ Warning: 'credentials_json' in config.yml does not start with '{'. Did you forget the indentation?")
                    
                    if isinstance(creds_content, dict):
                         creds_content = json.dumps(creds_content)
                    
                    # Write to config/google_creds.json
                    creds_path = YAML_CONFIG_PATH.parent / 'google_creds.json'
                    try:
                        if not creds_path.exists() or creds_path.read_text() != creds_content:
                            creds_path.write_text(creds_content)
                        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)
                    except Exception as weave_err:
                        print(f"❌ Error writing google_creds.json: {weave_err}")
            
            # 4. Sync Settings (Global vars that will be picked up later)
            if 'sync' in yaml_config:
                 if 'max_notebooks_per_run' in yaml_config['sync']:
                      os.environ['SYNC_MAX_NOTEBOOKS'] = str(yaml_config['sync']['max_notebooks_per_run'])

            # 5. Apple Notes Settings
            if 'apple_notes' in yaml_config:
                 if 'folder_name' in yaml_config['apple_notes']:
                      os.environ['APPLE_NOTES_FOLDER'] = str(yaml_config['apple_notes']['folder_name'])

    except Exception as e:
        print(f"Critical error loading config.yml: {e}")

# Legacy Fallback
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from remarkable_mcp.clean import repair_text_with_openai
except ImportError:
    # Construct path hack if running as script from root without package install
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from remarkable_mcp.clean import repair_text_with_openai

# Load config
CONFIG_PATH = ROOT / 'config.py'
max_notebooks_per_run = int(os.environ.get('SYNC_MAX_NOTEBOOKS', 1))

if CONFIG_PATH.exists():
    spec = importlib.util.spec_from_file_location('config', str(CONFIG_PATH))
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    # Prefer legacy config.py if it exists, otherwise fall back to env/default
    if hasattr(config, 'max_notebooks_per_run'):
         max_notebooks_per_run = getattr(config, 'max_notebooks_per_run')

def load_processed_log():
    if PROCESSED_LOG.exists():
        try:
            with open(PROCESSED_LOG, 'r') as f:
                data = json.load(f)
                # Handle legacy format (list of IDs)
                if isinstance(data, list):
                    return {doc_id: 0 for doc_id in data}
                # Handle new format (dict of ID -> Version)
                return data
        except Exception:
            return {}
    return {}

def add_to_processed_log(doc_id, version):
    processed = load_processed_log()
    processed[doc_id] = version
    with open(PROCESSED_LOG, 'w') as f:
        json.dump(processed, f, indent=2, sort_keys=True)


def find_notebook_images(notebook_name: str):
    imgs = sorted([p for p in WHITE_DIR.iterdir() if p.name.startswith(notebook_name)])
    return imgs


def preprocess_image(in_path: Path, out_path: Path):

    im = Image.open(in_path)
    # Always composite onto a white background, regardless of mode
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
        bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
        bg.paste(im, (0, 0), im if im.mode == 'RGBA' else None)
        im = bg.convert('RGB')
    else:
        im = im.convert('RGB')

    # Autocontrast
    im = ImageOps.autocontrast(im, cutoff=2)

    # Upscale 1.5x (rounded)
    w, h = im.size
    im = im.resize((int(w * 1.5), int(h * 1.5)), resample=Image.Resampling.LANCZOS)

    # Sharpen
    im = im.filter(ImageFilter.SHARPEN)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, quality=95)



# --- Google Vision OCR using API key (legacy) ---
def vision_ocr_image(png_path: Path, api_key: str, retries: int = 3):
    import base64

    import requests

    with open(png_path, 'rb') as f:
        content_b64 = base64.b64encode(f.read()).decode('utf-8')

    url = f'https://vision.googleapis.com/v1/images:annotate?key={api_key}'
    payload = {
        'requests': [
            {
                'image': {'content': content_b64},
                'features': [{'type': 'DOCUMENT_TEXT_DETECTION'}],
            }
        ]
    }

    backoff = 1
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                r = data.get('responses', [None])[0]
                if r and 'fullTextAnnotation' in r:
                    return r['fullTextAnnotation'].get('text', '').strip()
                return ''
            elif resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(backoff)
                backoff *= 2
                continue
            else:
                # authentication or client error — stop retrying
                print('Vision API error', resp.status_code, resp.text)
                return None
        except Exception:
            time.sleep(backoff)
            backoff *= 2
    return None

# --- Google Vision OCR using service account (preferred) ---
def vision_ocr_image_service_account(png_path: Path):
    try:
        from google.cloud import vision
        from google.cloud.vision_v1 import types
    except ImportError:
        print('google-cloud-vision not installed. Please run: uv add google-cloud-vision')
        return None

    client = vision.ImageAnnotatorClient()
    with open(png_path, 'rb') as f:
        content = f.read()
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)
    if response.error.message:
        print(f'Vision API error: {response.error.message}')
        return None
    if response.full_text_annotation and response.full_text_annotation.text:
        return response.full_text_annotation.text.strip()
    return ''


def make_pdf_from_images(image_paths, out_pdf: Path):
    imgs = []
    for p in image_paths:
        # Open and ensure consistent RGB mode (avoiding potentially problematic RGBA/transparency issues in PDF)
        im = Image.open(p).convert('RGBA')
        bg = Image.new('RGB', im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[3])
        imgs.append(bg)
    if not imgs:
        return None

    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    # Use ReportLab for more robust PDF generation instead of PIL's direct save
    try:
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(str(out_pdf))
        for img in imgs:
            # Set page size to image size
            width, height = img.size
            c.setPageSize((width, height))

            # Convert PIL image to ReportLab ImageReader
            # Flattening to simpler format often helps compatibility

            c.drawInlineImage(img, 0, 0, width, height)
            c.showPage()
        c.save()
        return out_pdf
    except ImportError:
        print("ReportLab not found, falling back to PIL PDF generation. Run 'uv add reportlab' for better compatibility.")
        # Fallback to PIL
        first, rest = imgs[0], imgs[1:]
        first.save(out_pdf, save_all=True, append_images=rest)
        return out_pdf


def create_apple_note_with_images(notebook_name: str, text_path: Path, image_paths: list[Path], folder_name: str = "reMarkable", sub_folder: str = None, retries: int = 3):
    import subprocess
    import time
    
    # ... (existing text processing code) ...
    full_text = text_path.read_text(errors='ignore') if text_path.exists() else ''

    # Skip the first JSON line and blank lines at the top
    lines = full_text.split('\n')
    text_start = 0
    for i, line in enumerate(lines):
        if line.startswith('---'):  # First "--- Page X ---" marker
            text_start = i
            break
    text = '\n'.join(lines[text_start:])

    # Add blank lines before each page header for better formatting in Apple Notes
    text = text.replace('--- Page', '\n\n--- Page')
    text = text.lstrip()

    # Convert text to HTML for Apple Notes body
    # Apple Notes uses <div>line content</div> for each line
    import html
    html_lines = []
    for line in text.splitlines():
        if not line:
            html_lines.append('<div><br></div>')
        else:
            html_lines.append(f'<div>{html.escape(line)}</div>')
    text_html = "".join(html_lines)

    # Body is just the OCR text
    final_body = "<div><br></div>" + text_html
    
    # Prepare attachment commands
    attachment_cmds = ""
    for img_p in image_paths:
        if img_p.exists():
            # Create a detached opaque version of the PNG to ensure Apple Notes renders it correctly (no alpha channel)
            from PIL import Image
            opaque_path = img_p.parent / f"opaque_{img_p.name}"

            try:
                # Open original
                pil_img = Image.open(img_p)
                # Create white background
                bg = Image.new("RGB", pil_img.size, (255, 255, 255))
                # Paste with alpha mask if present
                if pil_img.mode in ('RGBA', 'LA') or (pil_img.mode == 'P' and 'transparency' in pil_img.info):
                    pil_img = pil_img.convert('RGBA')
                    bg.paste(pil_img, mask=pil_img.split()[3])
                else:
                    bg.paste(pil_img)
                # Save as standard flattened PNG
                bg.save(opaque_path, "PNG")

                # Use the opaque version for attachment
                final_path = opaque_path
            except Exception as e:
                log(f"Warning: Failed to create opaque PNG for {img_p.name}: {e}. Using original.")
                final_path = img_p

            # Use safe quoting for the file path too
            # ensure_ascii=False ensures no \uXXXX escapes which AppleScript dislikes
            safe_path = json.dumps(str(final_path.resolve()), ensure_ascii=False)
            attachment_cmds += f'make new attachment at end of attachments of newNote with data (POSIX file {safe_path})\n    '

    try:
        for attempt in range(1, retries + 1):
            try:
                # Security Fix: Use Python's JSON encoder to create safe AppleScript string literals
                # This handles quotes, backslashes, and control characters automatically.
                # ensure_ascii=False prevents \uXXXX escapes which AppleScript does not support in string literals.
                safe_folder = json.dumps(folder_name, ensure_ascii=False)
                safe_name = json.dumps(notebook_name, ensure_ascii=False)
                safe_body = json.dumps(final_body, ensure_ascii=False)
                
                # Logic for Sub-Folder
                if sub_folder:
                    safe_sub_folder = json.dumps(sub_folder, ensure_ascii=False)
                    has_sub = "true"
                else:
                    safe_sub_folder = '""'
                    has_sub = "false"

                # Create a note directly with HTML body property in "reMarkable" folder
                applescript = f'''
tell application "Notes"
    set rootFolderName to {safe_folder}
    
    -- Check if root folder exists, if not create it
    if not (exists folder rootFolderName) then
        make new folder with properties {{name:rootFolderName}}
    end if
    set rootFolder to folder rootFolderName
    
    -- Determine target folder (Root or Sub)
    set targetFolder to rootFolder
    
    if {has_sub} then
        set subFolderName to {safe_sub_folder}
        -- Check if subFolder exists INSIDE rootFolder
        if not (exists folder subFolderName of rootFolder) then
            make new folder at rootFolder with properties {{name:subFolderName}}
        end if
        set targetFolder to folder subFolderName of rootFolder
    end if

    -- Check if note exists in that folder and delete it to avoid duplication
    set noteName to {safe_name}
    try
        delete (every note in targetFolder whose name is noteName)
    end try
    
    -- Create the new note with HTML body in the specific folder
    set newNote to make new note at targetFolder with properties {{name:noteName, body:{safe_body}}}
    
    -- Attach images
    {attachment_cmds}
end tell
'''
                log(f'--- Attachment commands for {notebook_name}:')
                log(attachment_cmds.strip())

                result = subprocess.run(['osascript', '-e', applescript], check=False, capture_output=True, text=True, timeout=10)

                if result.returncode != 0:
                    log(f'AppleScript error (attempt {attempt}/{retries}, code {result.returncode}): {result.stderr}')
                    if attempt < retries:
                        log(f'Retrying Apple Note creation for {notebook_name}...')
                        time.sleep(2)
                        continue
                    else:
                        return False

                log(f'Apple Note created for {notebook_name}')
                return True

            except subprocess.TimeoutExpired:
                log(f'AppleScript timeout (attempt {attempt}/{retries}) for {notebook_name}')
                if attempt < retries:
                    log(f'Retrying Apple Note creation for {notebook_name}...')
                    time.sleep(2)
                    continue
                else:
                    return False
            except Exception as e:
                log(f'Failed creating Apple Note (attempt {attempt}/{retries}): {e}')
                if attempt < retries:
                    log(f'Retrying Apple Note creation for {notebook_name}...')
                    time.sleep(2)
                    continue
                else:
                    return False
    finally:
        pass


def sanitize_filename(name: str) -> str:
    """Replace / and other problematic characters in notebook names for safe file paths."""
    return name.replace('/', '_').replace('\\', '_').replace(' ', '_')


def log(msg):
    print(msg)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f'{datetime.datetime.now().isoformat()} {msg}\n')


def validate_environment():
    """Check configuration health and fail fast with helpful docs if missing."""
    docs_path = ROOT / 'docs' / 'SETUP_GUIDE.md'
    docs_hint = f"See {docs_path} for instructions."
    
    errors = []

    # 1. Check OpenAI
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        errors.append("❌ Missing OPENAI_API_KEY environment variable. functionality will fail.")
    elif "YOUR-OPENAI-KEY-HERE" in api_key:
        errors.append("❌ OpenAI API Key still has default placeholder value. Please edit config.yml.")

    # 2. Check Google Credentials
    # The config loader above sets GOOGLE_APPLICATION_CREDENTIALS if a key exists in config.yml
    # Or users might have put a file in secrets/ (legacy)
    has_creds = False
    
    # Check env var (set by config.yml loader or system)
    if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        # Check if it points to a file with default placeholder content
        p = Path(os.environ['GOOGLE_APPLICATION_CREDENTIALS'])
        if p.exists():
             content = p.read_text()
             if "your-project-id" in content or "BEGIN PRIVATE KEY" not in content:
                 errors.append("❌ Google Credentials JSON still has default placeholder values. Please edit config.yml.")
             else:
                 has_creds = True
        else:
            errors.append(f"❌ Google Credentials file defined but not found at {p}")

    # Check Legacy Secrets Dir
    if not has_creds:
        secrets_dir = ROOT / 'secrets'
        if secrets_dir.exists() and list(secrets_dir.glob("*.json")):
             has_creds = True
    
    if not has_creds:
         errors.append("❌ No Google Cloud credentials found. Please add 'credentials_json' to config.yml (see SETUP_GUIDE.md).")
    
    if errors:
        msg = "\n".join(errors)
        log("\n" + "="*60)
        log("CONFIGURATION ERROR")
        log("="*60)
        log(msg)
        log("-" * 60)
        log(docs_hint)
        log("="*60 + "\n")
        
        print("\n" + "="*60)
        print("CONFIGURATION ERROR")
        print("="*60)
        print(msg)
        print("-" * 60)
        print(docs_hint)
        print("="*60 + "\n")
        
        # We perform a hard exit here to prevent partial runs
        sys.exit(1)
    
    log("Configuration valid.")


def main():
    # At the start of main(), clear the log for a new run
    with open(LOG_PATH, 'w', encoding='utf-8') as f:
        f.write('')
    
    validate_environment()
    
    log('Pipeline started.')

    # --- Argument parsing ---
    parser = argparse.ArgumentParser()
    parser.add_argument('--notebook', help='Notebook safe name prefix (e.g., Notebook_8)')
    parser.add_argument('--limit', type=int, default=0, help='Max notebooks to process per run')
    parser.add_argument('--folder', default=os.environ.get('APPLE_NOTES_FOLDER', 'Living Ink'), help='Apple Notes folder name')
    parser.add_argument('--state-file', help='Ignored (legacy compatibility)')
    args = parser.parse_args()

    # --- Cleanup previous outputs for this notebook ---
    import shutil
    pre_dir = VISION_DIR / (args.notebook or 'Notebook_8')
    if pre_dir.exists():
        shutil.rmtree(pre_dir)
    out_txt = OCR_DIR / f"{args.notebook or 'Notebook_8'}.txt"
    if out_txt.exists():
        out_txt.unlink()
    out_pdf = PDF_DIR / f"{args.notebook or 'Notebook_8'}.pdf"
    if out_pdf.exists():
        out_pdf.unlink()


    # Ensure white PNG dir exists
    WHITE_DIR.mkdir(exist_ok=True)



    # Clean all output folders at the start of each run
    for folder in [WHITE_DIR, VISION_DIR, OCR_DIR, PDF_DIR]:
        if folder.exists():
            for item in folder.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

    # Step 0: List all notebooks in reMarkable cloud and find new ones
    from remarkable_mcp.api import get_rmapi
    client = get_rmapi()
    collection = client.get_meta_items()
    # Only consider notebooks (not PDFs/EPUBs)
    def get_val(item, key):
        # Support both dict and object attribute access
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)

    # Build ID map for path resolution
    id_map = {get_val(item, 'ID'): item for item in collection}

    def get_notebook_path(item, id_map):
        path = []
        current = item
        while get_val(current, 'Parent'):
            parent_id = get_val(current, 'Parent')
            if parent_id == 'trash':
                 path.insert(0, "[TRASH]")
                 break
            parent = id_map.get(parent_id)
            if parent:
                parent_name = get_val(parent, 'VissibleName') or get_val(parent, 'VisibleName')
                path.insert(0, parent_name)
                current = parent
            else:
                break
        return " / ".join(path)

    def is_native_notebook(item):
        """Check if document is a native notebook (not PDF/EPUB)."""
        files = get_val(item, 'files') or []
        for f in files:
            fid = f.get('id', '').lower()
            if fid.endswith('.pdf') or fid.endswith('.epub'):
                return False
        return True

    # Filter out notebooks that are in the trash
    candidates = [
        item for item in collection 
        if get_val(item, 'Type') == 'DocumentType' 
        and (get_val(item, 'VissibleName') or get_val(item, 'VisibleName'))
        and not get_notebook_path(item, id_map).startswith("[TRASH]")
    ]

    notebooks = []
    skipped_count = 0
    for item in candidates:
        if is_native_notebook(item):
            notebooks.append(item)
        else:
            skipped_count += 1
            
    if skipped_count > 0:
        log(f"Skipped {skipped_count} non-native documents (PDFs/EPUBs).")

    # Find already processed notebooks (from processed_notebooks.json)
    processed = load_processed_log()
    
    # Find new or updated notebooks (tracking by ID and Hash/Version)
    new_notebooks = []
    for item in notebooks:
        doc_id = get_val(item, 'ID')
        
        # Prefer 'hash', fall back to 'Version' (legacy), default to 1
        curr_val = get_val(item, 'hash')
        if not curr_val:
            try:
                 curr_val = int(get_val(item, 'Version'))
            except (ValueError, TypeError):
                 curr_val = 1
        
        last_val = processed.get(doc_id, -1)
        
        # Check for change:
        # 1. If we have a hash now, but stored a number (legacy), it's an update
        # 2. If strings differ (hash change or version mismatch), it's an update
        if str(last_val) != str(curr_val):
            new_notebooks.append(item)

    if not new_notebooks:
        log('No new or updated notebooks found in reMarkable cloud. Exiting.')
        sys.exit(0)
    # Limit number of notebooks to process per run
    limit = args.limit if args.limit > 0 else max_notebooks_per_run
    if limit > 0:
        new_notebooks = new_notebooks[:limit]
    # If --notebook is specified, process only that one; else process all new (up to limit)
    if args.notebook:
        notebook = args.notebook
        log(f'Processing notebook: {notebook}')
        # Filter logic slightly complex due to VissibleName
        notebooks_to_process = []
        for item in new_notebooks:
             name = get_val(item, 'VissibleName') or get_val(item, 'VisibleName')
             if name == notebook:
                  notebooks_to_process.append(item)
        
        if not notebooks_to_process:
            log(f'Notebook {notebook} not found or already processed. Exiting.')
            sys.exit(1)
    else:
        notebooks_to_process = new_notebooks
        
    for nb_item in notebooks_to_process:
        notebook = get_val(nb_item, 'VissibleName') or get_val(nb_item, 'VisibleName')
        notebook_id = get_val(nb_item, 'ID')
        
        # Get the value to store after processing (Hash or Version)
        item_hash = get_val(nb_item, 'hash')
        if item_hash:
             notebook_version = item_hash
        else:
            try:
                 notebook_version = int(get_val(nb_item, 'Version'))
            except:
                 notebook_version = 1
             
        safe_notebook = sanitize_filename(notebook)

        # Determine Path and Display Title
        folder_path = get_notebook_path(nb_item, id_map)
        if folder_path:
            display_title = f"{folder_path} / {notebook}"
        else:
            display_title = notebook

        log(f'Processing notebook: {display_title} (ID: {notebook_id})')
        # Step 1: Pull and render notebook pages if not present
        # Use + '.' to ensure strict prefix matching (e.g. "Notebook_1." won't match "Notebook_10.")
        prefix_pattern = safe_notebook + '.'
        imgs = sorted([p for p in WHITE_DIR.iterdir() if p.name.startswith(prefix_pattern) and p.suffix.lower() == '.png'])
        if not imgs:
            log(f'No white-background PNGs found for {notebook}. Attempting to pull from reMarkable cloud...')
            # Find the document by name
            doc = None
            for item in collection:
                name1 = get_val(item, 'VissibleName')
                name2 = get_val(item, 'VisibleName')
                if (name1 and name1.strip() == notebook) or (name2 and name2.strip() == notebook):
                    doc = item
                    break
            if not doc:
                log(f'Notebook "{notebook}" not found in your reMarkable cloud library. Exiting.')
                continue
            # Download the document zip (cloud: use client.download)
            from remarkable_mcp.extract import (
                get_document_page_count,
                render_page_from_document_zip,
            )
            tmp_zip = ROOT / f"{safe_notebook}.zip"
            raw_bytes = client.download(doc)
            if not raw_bytes:
                log(f"Failed to download notebook zip for {notebook} from cloud.")
                continue
            with open(tmp_zip, 'wb') as f:
                f.write(raw_bytes)
            # Get page count
            page_count = get_document_page_count(tmp_zip)
            log(f"Rendering {page_count} pages for {notebook}...")
            for page in range(1, page_count + 1):
                png_bytes = render_page_from_document_zip(tmp_zip, page)
                if png_bytes is None:
                    log(f"Failed to render page {page} of {notebook}.")
                    continue
                # Save as PNG with white background
                with open(WHITE_DIR / f"{safe_notebook}.page-{page}.png", 'wb') as out_f:
                    out_f.write(png_bytes)
                log(f"Saved: {WHITE_DIR / f'{safe_notebook}.page-{page}.png'}")
            # Remove temp zip
            tmp_zip.unlink(missing_ok=True)
            # Re-scan for white PNGs
            imgs = sorted([p for p in WHITE_DIR.iterdir() if p.name.startswith(prefix_pattern) and p.suffix.lower() == '.png'])
            if not imgs:
                log(f'Failed to generate white-background PNGs for {notebook} from cloud. Exiting.')
                continue
        log(f'Found {len(imgs)} white-background PNGs for {notebook}: {[p.name for p in imgs]}')

        # Preprocess images
        pre_dir = VISION_DIR / safe_notebook
        pre_dir.mkdir(parents=True, exist_ok=True)
        pre_paths = []
        for p in imgs:
            out_p = pre_dir / p.name
            preprocess_image(p, out_p)
            pre_paths.append(out_p)

        # OCR via Google Vision (always use service account)
        raw_texts = []
        cleaned_texts = []
        for p in pre_paths:
            log(f'Vision OCR (service account): {p.name}')
            txt = vision_ocr_image_service_account(p)
            if txt is None:
                log(f'Vision failed for {p}')
            
            raw_text = txt or ''
            raw_texts.append(raw_text)
            
            log(f'  Cleaning text with OpenAI for {p.name}...')
            cleaned_text = repair_text_with_openai(raw_text)
            cleaned_texts.append(cleaned_text)
        
        # Save RAW text
        raw_out_txt = OCR_DIR / f'{safe_notebook}_raw.txt'
        meta = {'notebook': notebook, 'images': [p.name for p in imgs]}
        with open(raw_out_txt, 'w', encoding='utf-8') as f:
            f.write(json.dumps(meta) + '\n\n')
            for i, t in enumerate(raw_texts, 1):
                f.write(f'--- Page {i} ---\n')
                f.write((t or '').strip() + '\n\n')
        log(f'Raw OCR text saved to {raw_out_txt}')

        # Save CLEANED text (this is what goes to Apple Notes)
        clean_out_txt = OCR_DIR / f'{safe_notebook}_clean.txt'
        with open(clean_out_txt, 'w', encoding='utf-8') as f:
            f.write(json.dumps(meta) + '\n\n')
            for i, t in enumerate(cleaned_texts, 1):
                f.write(f'--- Page {i} ---\n')
                f.write((t or '').strip() + '\n\n')
        log(f'Cleaned OCR text saved to {clean_out_txt}')
                                                           
        # Build PDF from the white PNGs - DISABLED for performance
        # out_pdf = PDF_DIR / f'{safe_notebook}.pdf'
        # make_pdf_from_images(imgs, out_pdf)
        # log(f'PDF created: {out_pdf}')
        
        # Create Apple Note with text and inline images
        # We no longer rely on attaching the PDF, as it causes crashes or sandbox issues.
        # Instead, we embed the images directly into the HTML body.
        success = False
        try:
            # Determine strict top-level folder name for Apple Notes nesting
            # folder_path is like "Work / Project A" -> top_level is "Work"
            top_level_subfolder = None
            if folder_path:
                 parts = folder_path.split(' / ')
                 if parts:
                     top_level_subfolder = sanitize_filename(parts[0])

            # We use the list of PNGs 'imgs' we already have
            success = create_apple_note_with_images(display_title, clean_out_txt, imgs, 
                                                  folder_name=args.folder, 
                                                  sub_folder=top_level_subfolder)
        except Exception as e:
            log(f'Failed creating Apple Note: {e}')

        # After successful processing, add to processed log
        if success:
            add_to_processed_log(notebook_id, notebook_version)
            log(f'Notebook {notebook} processing complete.')
        else:
             log(f'Notebook {notebook} processing FAILED. Not marking as complete.')

    log('Pipeline finished.')


if __name__ == '__main__':
    # Required for PyInstaller to handle multiprocessing correctly (especially to avoid infinite spawn loops)
    import multiprocessing
    multiprocessing.freeze_support()

    log(f"Script started. Working directory: {os.getcwd()}. Log path: {LOG_PATH.resolve()}")
    main()
