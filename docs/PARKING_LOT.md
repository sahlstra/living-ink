# Project Parking Lot

## Open Questions

### Versioning & State Tracking
- **Current State:** The system tracks `ID -> VersionHash` in `processed_notebooks.json`. It does not track *which* destinations have received a specific version.
- **Problem:** If a user adds a new destination (e.g., Apple Notes) for an already processed notebook, the system skips it because it thinks the version is "up to date".
- **Proposed Solution:** 
  - Update state schema to: `{ "id": { "version": "hash", "destinations": ["Obsidian", "AppleNotes"] } }`
  - Implement a "Artifact-Aware Hybrid" cache strategy: Keep expensive cleaned text (`.txt`) but delete heavy images (`.png`).
  - Logic: If version matches but destination is missing -> Reuse cached text -> Publish.
- **Status:** On hold pending further thought on cache management vs. reprocessing costs.
