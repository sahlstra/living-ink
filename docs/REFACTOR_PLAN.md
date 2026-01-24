# Refactoring Plan: Apple Notes & Obsidian Sync

## Goal
Refactor the current reMarkable-to-Apple Notes sync tool to support Obsidian as a second destination, while removing unused "MCP" (Model Context Protocol) server components.

## Phase 1: Cleanup (Remove MCP Server)
The "Model Context Protocol" (MCP) server code is unused for the sync workflow and complicates the project.

- [ ] **Delete:** `server.py` (Root entry point for MCP).
- [ ] **Delete:** `remarkable_mcp/server.py` (FastMCP server initialization).
- [ ] **Delete:** `remarkable_mcp/tools.py` (MCP tool definitions).
- [ ] **Delete:** `remarkable_mcp/prompts.py` (MCP prompts).
- [ ] **Delete:** `remarkable_mcp/resources.py` (MCP resources).
- [ ] **Delete:** `remarkable_mcp/cli.py` (CLI wrapper for MCP).
- [ ] **Delete:** `remarkable_mcp/sampling.py` (MCP sampling).
- [ ] **Delete:** `remarkable_mcp/capabilities.py` (MCP capabilities).
- [ ] **Delete:** `remarkable_mcp/responses.py` (MCP response utilities, check usage first).
- [ ] **Update:** `pyproject.toml` to remove `mcp` dependency.

## Phase 2: Architecture Refactoring (Pluggable Destinations)
Abstract the "publish" step so the system can target either Apple Notes or Obsidian without duplicating the processing logic.

- [ ] **Create `remarkable_mcp/destinations.py`**:
    - **Base Class**: `Destination` (abstract base class).
        - Method: `publish(notebook_name, text_content, attachments)`
    - **Class**: `AppleNotesDestination`
        - Move the existing `osascript` (AppleScript) logic from `scripts/process_notebook.py` into this class.
    - **Class**: `ObsidianDestination`
        - Implement logic to write Markdown files (`.md`).
        - Implement logic to move attachments (images/PDFs) to a Vault folder.

## Phase 3: Implement Obsidian Support
- [ ] **Logic**:
    - Convert cleaned HTML content to Markdown.
    - Handle file naming (sanitize).
    - Handle attachments folder structure.
- [ ] **Configuration**:
    - Update `config.yml` structure (backwards compatible if possible, or clear new section).
    - Add `destination: "apple_notes" | "obsidian"`.
    - Add `vault_path` for Obsidian.

## Phase 4: Integration
- [ ] **Update `scripts/process_notebook.py`**:
    - Import `destinations`.
    - Instantiate the correct `Destination` subclass based on config.
    - Replace the hardcoded AppleScript block with `destination.publish(...)`.

## Phase 5: Testing
- [ ] Test Apple Notes sync (ensure no regression).
- [ ] Test Obsidian sync (verify markdown creation and image linking).
