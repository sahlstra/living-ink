# Living Ink

**Automate the flow of your "Living Signal" from reMarkable to Apple Notes or Obsidian.**

Living Ink is an automated pipeline that bridges the gap between your reMarkable tablet and your digital "Second Brain" (Apple Notes or Obsidian). It goes beyond simple PDF export by converting your handwritten notebooks into fully searchable, typed text while preserving the original context.

## 🚀 Features

*   **Smart Sync**: Automatically detects new or updated notebooks on your reMarkable.
*   **High-Fidelity OCR**: Uses **Google Cloud Vision** to recognize handwriting with superior accuracy compared to on-device conversion.
*   **AI Cleanup**: leveraging **GPT-4o** to fix spelling, format lists, structure paragraphs, and make your notes actually readable.
*   **Apple Notes Integration**: Creates beautiful notes containing the cleaned-up typed text and original handwritten page images.
*   **Obsidian Integration**: Exports notes as Markdown files with YAML frontmatter (tags, date, source) and local image attachments.
*   **Folder Mirroring**: Replicates your reMarkable folder structure into your destination (e.g., `Finance/2026` → `Living Ink > Finance > 2026`).

## 📚 Documentation

*   **[Setup Guide](docs/SETUP_GUIDE.md)**: How to get your API keys (OpenAI, Google Vision, reMarkable) and configure the app.
*   **[User Manual](docs/USER_MANUAL.md)**: How to use the application in Automatic or Manual modes.

## 🛠️ Installation & Config

1.  **Install the Application**: Download the latest release from the Releases page.
2.  **Configure Keys**: Edit `config/config.yml` with your credentials:
    ```yaml
    openai:
      api_key: "sk-..."
    remarkable:
      device_token: "..."
    google_vision:
      credentials_path: "/path/to/credentials.json"
    
    # Choose your destination(s)
    apple_notes:
      enabled: true
      folder_name: "Living Ink"
    
    obsidian:
      enabled: true
      vault_path: "/Users/yourname/Documents/Obsidian Vault"
    ```
    *(See `config.yml.example` for a template)*

## 🏗️ How It Works

1.  **Download**: Fetches notebooks from reMarkable Cloud.
2.  **Render**: Converts pages to high-res images.
3.  **Read**: Google Vision extracts raw text from handwriting.
4.  **Refine**: OpenAI reformats the text into structured notes.
5.  **Publish**: Dispatches the result to your enabled destinations (Apple Notes and/or Obsidian).

## Acknowledgements

Built on top of the excellent work of the generic [remarkable-mcp](https://github.com/SamMorrowDrums/remarkable-mcp) project.
