"""
Destinations for publishing reMarkable notes.
Abstracts the target (Apple Notes, Obsidian, etc.) from the processing logic.
"""

import abc
import html
import json
import logging
import shutil
import subprocess
import time
import datetime
from pathlib import Path
from typing import List, Optional

from PIL import Image

# Configure module logger
logger = logging.getLogger(__name__)


class Destination(abc.ABC):
    """Abstract base class for publication destinations."""

    @abc.abstractmethod
    def publish(
        self,
        notebook_name: str,
        text_content: str,
        image_paths: List[Path],
        sub_folder: Optional[str] = None,
    ) -> bool:
        """
        Publish a notebook to the destination.

        Args:
            notebook_name: Title of the note.
            text_content: The cleaned-up text content.
            image_paths: List of paths to the page images.
            sub_folder: Optional sub-folder name (e.g., "Work/Projects").

        Returns:
            True if successful, False otherwise.
        """
        pass


class AppleNotesDestination(Destination):
    """Publishes notes to Apple Notes application via AppleScript."""

    def __init__(self, folder_name: str = "reMarkable"):
        self.folder_name = folder_name

    def _convert_to_html(self, text: str) -> str:
        """Convert plain text to the HTML format expected by Apple Notes."""
        text = text.lstrip()
        html_lines = []
        for line in text.splitlines():
            if not line:
                html_lines.append("<div><br></div>")
            else:
                html_lines.append(f"<div>{html.escape(line)}</div>")
        return "".join(html_lines)

    def _create_opaque_image(self, img_path: Path) -> Path:
        """Create a version of the image with a white background (Apple Notes handles alpha poorly)."""
        opaque_path = img_path.parent / f"opaque_{img_path.name}"
        if opaque_path.exists():
            return opaque_path

        try:
            pil_img = Image.open(img_path)
            bg = Image.new("RGB", pil_img.size, (255, 255, 255))
            if pil_img.mode in ("RGBA", "LA") or (
                pil_img.mode == "P" and "transparency" in pil_img.info
            ):
                pil_img = pil_img.convert("RGBA")
                bg.paste(pil_img, mask=pil_img.split()[3])
            else:
                bg.paste(pil_img)
            bg.save(opaque_path, "PNG")
            return opaque_path
        except Exception as e:
            logger.warning(f"Failed to create opaque PNG for {img_path.name}: {e}. Using original.")
            return img_path

    def publish(
        self,
        notebook_name: str,
        text_content: str,
        image_paths: List[Path],
        sub_folder: Optional[str] = None,
    ) -> bool:
        retries = 3

        # 1. Prepare Content
        text_html = self._convert_to_html(text_content)
        final_body = "<div><br></div>" + text_html

        # 2. Prepare Attachments
        attachment_cmds = ""
        for img_p in image_paths:
            if img_p.exists():
                final_path = self._create_opaque_image(img_p)
                # Safe quoting for AppleScript
                safe_path = json.dumps(str(final_path.resolve()), ensure_ascii=False)
                attachment_cmds += f"make new attachment at end of attachments of newNote with data (POSIX file {safe_path})\n    "

        # 3. Execute AppleScript
        try:
            for attempt in range(1, retries + 1):
                safe_folder = json.dumps(self.folder_name, ensure_ascii=False)
                safe_name = json.dumps(notebook_name, ensure_ascii=False)
                safe_body = json.dumps(final_body, ensure_ascii=False)

                if sub_folder:
                    safe_sub_folder = json.dumps(sub_folder, ensure_ascii=False)
                    has_sub = "true"
                else:
                    safe_sub_folder = '""'
                    has_sub = "false"

                applescript = f"""
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
"""
                # logger.debug(f'--- Attachment commands for {notebook_name}:')
                # logger.debug(attachment_cmds.strip())

                result = subprocess.run(
                    ["osascript", "-e", applescript],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    logger.warning(
                        f"AppleScript error (attempt {attempt}/{retries}, code {result.returncode}): {result.stderr}"
                    )
                    if attempt < retries:
                        time.sleep(2)
                        continue
                    else:
                        return False

                logger.info(f"Apple Note created for {notebook_name}")
                return True

        except Exception as e:
            logger.error(f"Failed creating Apple Note: {e}")
            return False


class ObsidianDestination(Destination):
    """Publishes notes to a local Obsidian Vault as Markdown files."""

    def __init__(self, vault_path: str, attachments_folder: str = "attachments"):
        self.vault_path = Path(vault_path).expanduser().resolve()
        if not self.vault_path.exists():
            raise ValueError(f"Obsidian Vault path does not exist: {self.vault_path}")
        self.attachments_folder = attachments_folder

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for filesystem."""
        # Simple sanitization - replace / and : with -
        return name.replace("/", "-").replace(":", "-").replace("\\", "-")

    def publish(
        self,
        notebook_name: str,
        text_content: str,
        image_paths: List[Path],
        sub_folder: Optional[str] = None,
    ) -> bool:
        try:
            # 1. Determine Target Folder
            target_dir = self.vault_path

            # If we are syncing the full folder structure (sub_folder provided)
            # We mirror it in the vault
            if sub_folder:
                # Example: sub_folder might be "Projects/Work" or just "Projects"
                # We treat it as relative path from Vault Root
                target_dir = self.vault_path / sub_folder

            target_dir.mkdir(parents=True, exist_ok=True)

            # 2. Handle Attachments
            # We store attachments in a dedicated folder (e.g. vault/attachments or vault/Folder/attachments)
            # A common Obsidian pattern is a central attachments folder or subfolder-relative
            # Let's use a central attachments folder implementation for simplicity and robustness first,
            # or `attachments` relative to the note's folder.
            # Local choice: `target_dir / self.attachments_folder`

            attach_dir = target_dir / self.attachments_folder
            attach_dir.mkdir(parents=True, exist_ok=True)

            image_refs = []

            for img_p in image_paths:
                if img_p.exists():
                    # Create a unique filename for the attachment to avoid collisions
                    # Format: {NotebookName}_{PageNum}.png or similar.
                    # Assuming img_p.name is unique enough or we prepend notebook name
                    clean_nb_name = self._sanitize_filename(notebook_name)
                    new_filename = f"{clean_nb_name}_{img_p.name}"
                    dest_path = attach_dir / new_filename

                    shutil.copy2(img_p, dest_path)

                    # Markdown link logic
                    # If attachments are in a subfolder, we need the relative path
                    # Obsidian handles [[filename]] automatically if it's unique, but standard markdown needs path
                    # Let's use standard markdown for max compatibility: ![Alt](path)
                    # Path should be relative to the note file

                    # Obsidian WikiLink style (often preferred by Obsidian users)
                    image_refs.append(f"![[{new_filename}]]")

            # 3. Create Markdown Content
            md_lines = []
            
            # --- YAML Frontmatter ---
            source_path = notebook_name.replace(" / ", "/")
            today_str = datetime.date.today().isoformat()
            
            md_lines.append("---")
            md_lines.append(f"created: {today_str}")
            md_lines.append(f"source: Remarkable/{source_path}")
            md_lines.append("tags:")
            md_lines.append("  - remarkable")
            md_lines.append("  - handwritten")
            md_lines.append("---")
            md_lines.append("")

            # --- Content ---
            md_lines.append(text_content)
            md_lines.append("")
            
            if image_refs:
                md_lines.append("## Original Pages")
                for ref in image_refs:
                    md_lines.append(ref)
                    md_lines.append("")

            final_md = "\n".join(md_lines)

            # 4. Write File
            safe_name = self._sanitize_filename(notebook_name)
            note_path = target_dir / f"{safe_name}.md"

            with open(note_path, "w", encoding="utf-8") as f:
                f.write(final_md)

            logger.info(f"Obsidian note created at: {note_path}")
            return True

        except Exception as e:
            logger.error(f"Failed creating Obsidian note for {notebook_name}: {e}")
            return False
