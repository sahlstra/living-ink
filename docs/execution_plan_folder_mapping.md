# Execution Plan: Automatic Top-Level Folder Nesting

## Overview

Implement an automatic folder nesting system that mirrors the **top-level** folder structure from reMarkable into Apple Notes. This creates a clean "Project" or "Category" view inside Apple Notes without requiring manual configuration files.

**Behavior:**
*   reMarkable: `/Work/Project A/Note` -> Apple Notes: `Living Ink > Work > Note`
*   reMarkable: `/Personal/Note` -> Apple Notes: `Living Ink > Personal > Note`
*   reMarkable: `/RootNote` -> Apple Notes: `Living Ink > RootNote`

## Implementation Steps

### 1. Python Logic (`scripts/process_notebook.py`)

#### A. Build the Folder Tree Cache
*   **Current State**: We fetch documents as a flat list and ignore hierarchy.
*   **Change**:
    *   Fetch all items (documents + folders) from the reMarkable Cloud API.
    *   Build an in-memory dictionary acting as a tree: `FolderID -> {Name, ParentID}`.
    *   Implement helper `get_top_level_folder_name(doc_id)`:
        *   Traverse up the `ParentID` chain.
        *   Stop when the parent is empty (Root).
        *   Return the name of the folder just below Root.
        *   Return `None` if the document itself is at Root.

#### B. Determine Target Folder
*   **Input**: `base_folder_name` (from Config, e.g., "Living Ink").
*   **Logic**:
    *   `sub_folder` = `get_top_level_folder_name(notebook_id)`
    *   If `sub_folder` exists: We prepare to create/use `base_folder` -> `sub_folder`.
    *   If `sub_folder` is None: We target `base_folder` directly.

### 2. AppleScript Enhancements

The AppleScript block needs to become dynamic to handle the optional second level of depth.

**Pseudocode Logic:**
1.  **Ensure Base Folder**: Check if "Living Ink" exists; create if not. Set as `rootFolder`.
2.  **Handle Sub-Folder**:
    *   If a `sub_folder` name is provided (e.g., "Work"):
        *   Check if folder "Work" exists *inside* `rootFolder`.
        *   If not, `make new folder at rootFolder with properties {name:"Work"}`.
        *   Set `targetFolder` to this sub-folder.
    *   Else:
        *   Set `targetFolder` to `rootFolder`.
3.  **Create Note**: Proceed with creating the note inside `targetFolder`.

## Technical Risks & Limitations

1.  **Renaming Folders (The "Copy" Effect)**:
    *   *Scenario*: User renames generic folder "Project" to "Launched Project" on reMarkable.
    *   *Result*: The system sees "Launched Project" as a brand new top-level folder. It creates `Living Ink > Launched Project` and syncs the note there.
    *   *Cleanup*: The old `Living Ink > Project` folder remains in Apple Notes (with the old version of the note) and must be deleted manually. This is safer than auto-deleting but requires user awareness.

2.  **Folder Name Sanitization**:
    *   reMarkable allows characters in folder names that might confuse AppleScript (quotes, slashes).
    *   *Mitigation*: We will apply the existing `sanitize_filename` function to folder names before passing them to AppleScript.

## Testing Plan

1.  **Unit Test Tree Traversal**: Verify `get_top_level_folder_name` correctly handles:
    *   Item at Root (returns None).
    *   Item in `/FolderA` (returns "FolderA").
    *   Item in `/FolderA/SubB/SubC` (returns "FolderA").
2.  **AppleScript Validation**:
    *   Test creating a note in `Living Ink` (Root).
    *   Test creating a note in `Living Ink > NewFolder` (Sub-folder).
    *   Test proper string escaping for folder names like `Work & "Stuff"`.
