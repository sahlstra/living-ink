# User Manual: Living Ink
**Created by Aaron Sahlstrom**

## Overview

**Living Ink** is an automated pipeline that bridges the gap between your reMarkable tablet and Apple Notes. It converts your handwritten notebooks into fully searchable, typed text in Apple Notes, While preserving the original handwriting references your "Living Signal".

## How It Works

1.  **Detect**: The app periodically checks your reMarkable Cloud account.
    *   **New Notebooks**: Automatically detected and processed.
    *   **Updated Notebooks**: If you write more pages or edit an existing notebook, the app detects the version change and re-syncs the note.
    *   **Trash**: Notebooks in the Trash folder (or named starting with `[TRASH]`) are ignored.
2.  **Download & Render**: It downloads the notebook pages and converts them into high-quality images.
3.  **OCR (Optical Character Recognition)**: It sends these images to Google Cloud Vision to read your handwriting.
4.  **AI Cleanup**: It uses OpenAI (GPT-4o) to fix spelling, formatting, and structure (converting bullet points, fixing broken sentences).
5.  **Publish**: It creates (or overwrites) a note in Apple Notes containing:
    *   The cleaned up, typed text.
    *   The original handwritten page image (embedded).

## Folder Syncing

The application now supports **Automatic Folder Nesting**. It mirrors your **top-level** folder structure from reMarkable into Apple Notes.

*   **reMarkable:** `/Finance/Budget 2026`
*   **Apple Notes:** `Living Ink > Finance > Budget 2026`

If a notebook is at the root level (not in any folder), it will appear directly in the main `Living Ink` folder.

**Note on Renaming:**
If you rename a top-level folder on your reMarkable (e.g., from "Finance" to "Money"), the application will create a **new** folder called "Money" in Apple Notes and sync your notes there. The old "Finance" folder will remain (containing the old versions) and you can safely delete it manually.

## Usage

### Automatic Mode
Once installed, the application runs in the background (typically every hour). You simply write on your reMarkable, force a sync (by swiping down on the tablet list view), and wait. The note will appear in your "Living Ink" folder in Apple Notes (this folder name can be configured).

### Manual Mode (Advanced)
If you want to force a run immediately (instead of waiting for the hourly schedule):

1.  Open the folder `/Applications/Living Ink`.
2.  Double-click the **Run Manual Sync.command** file.
3.  A terminal window will open, show the progress, and you can close it when finished.

Alternatively, you can run the command in the terminal:

**Process all new notes:**
```bash
uv run python scripts/process_notebook.py
```

**Process a specific notebook:**
```bash
uv run python scripts/process_notebook.py --notebook "My Notebook Name"
```

## Configuration

You can customize the behavior by editing `config/config.yml`:

*   **Sync Limit**: Control how many notebooks are processed in one run (to avoid hitting API limits).
    ```yaml
    sync:
      max_notebooks_per_run: 5
    ```

*   **Apple Notes Folder**: Change the destination folder name.
    ```yaml
    apple_notes:
      folder_name: "My Journal"
    ```

## Troubleshooting

### "Configuration Error"
If you see an error about missing keys or credentials, please refer to `SETUP_GUIDE.md`. The app cannot function without the OpenAI API key and Google Cloud Vision credentials.

### Note Not Appearing?
1.  **Sync**: Ensure your reMarkable tablet has actually synced to the cloud. Check the reMarkable desktop or mobile app to confirm.
2.  **Naming**: If you renamed a notebook recently, wait for the sync to propagate.
3.  **Logs**: Check the log files (location varies by install, usually `logs/pipeline.log`) for specific error messages.

### "Limit Exceeded"
The Google Cloud Vision API has a free tier, but if you process thousands of pages effectively instantly, you might hit a rate limit or billing limit. The app will retry automatically.

## Data Privacy
*   **Google**: Your handwriting images are sent to Google Cloud Vision for processing.
*   **OpenAI**: The raw text is sent to OpenAI for cleanup.
*   **Local**: All final notes are stored locally in your Apple Notes database.
