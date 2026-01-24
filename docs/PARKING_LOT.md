# Project Parking Lot

## Open Questions

### Versioning & State Tracking
  - Update state schema to: `{ "id": { "version": "hash", "destinations": ["Obsidian", "AppleNotes"] } }`
  - Implement a "Artifact-Aware Hybrid" cache strategy: Keep expensive cleaned text (`.txt`) but delete heavy images (`.png`).
  - Logic: If version matches but destination is missing -> Reuse cached text -> Publish.

## Bugs

- [ ] **Obsidian note content append broken**
  - Functionality that adds additional content to a note for the Obsidian process is currently broken. Needs investigation and fix.
