# Setup Guide for Living Ink

This guide explains how to configure the necessary API keys and credentials for the Living Ink application (syncing reMarkable notes to Apple Notes).

## 1. OpenAI API Key (Required for Cleanup)

The application uses OpenAI's GPT-4o to clean up and format the handwritten text converted by OCR.

1.  **Sign Up/Login**: Go to [platform.openai.com](https://platform.openai.com) and sign in.
2.  **Create Key**:
    *   Navigate to **Dashboard** -> **API keys**.
    *   Click **+ Create new secret key**.
    *   Name it something like "Remarkable Sync".
    *   **Copy the key immediately**. You will not be able to see it again.
3.  **Configuration**:
    *   Open the `config/config.yml` file.
    *   Find the `openai:` section.
    *   Paste your key into the `api_key` field: `api_key: "sk-proj-..."`

## 2. Google Cloud Vision API (Required for OCR)

We use Google's enterprise-grade Vision API for handwriting recognition because it is significantly more accurate than on-device models.

1.  **Create Project**:
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Click the project dropdown (top left) and select **New Project**.
    *   Name it "Remarkable OCR" and create it.
2.  **Enable API**:
    *   In the search bar, type "Cloud Vision API".
    *   Select "Cloud Vision API" from the marketplace results.
    *   Click **Enable**.
    *   *Note: You may need to enable billing. This API has a generous free tier (usually 1,000 units/month).*
3.  **Create Service Account**:
    *   Go to **IAM & Admin** -> **Service Accounts**.
    *   Click **+ Create Service Account**.
    *   Name: `remarkable-ocr-sa`.
    *   Description: "OCR for remarkable sync".
    *   Click **Create and Continue**.
    *   **Role**: Select **Basic** -> **Owner** (or **Cloud Vision API User** for least privilege).
    *   Click **Done**.
4.  **Download Key**:
    *   Click on the newly created email address (e.g., `remarkable-ocr-sa@...`).
    *   Go to the **Keys** tab.
    *   Click **Add Key** -> **Create new key**.
    *   Select **JSON**.
    *   A `.json` file will download to your computer.
5.  **Configuration**:
    *   Open the downloaded JSON file in a text editor (like TextEdit or VS Code).
    *   Copy the **entire content** of the file.
    *   Open `config/config.yml`.
    *   Find the `google_vision:` section and `credentials_json:` key.
    *   Paste the JSON content as a **block string** (using the `|` character), ensuring proper indentation.

    Example:
    ```yaml
    google_vision:
      credentials_json: |
        {
          "type": "service_account",
          ...
        }
    ```

## 4. Advanced Configuration (Optional)

You can check `config/config.yml` for additional settings:

*   **`sync.max_notebooks_per_run`**: Limits the number of notebooks processed in a single hour to avoid hitting API rate limits (Default: 5).
*   **`apple_notes.folder_name`**: The folder name in Apple Notes where your synced notes will appear (Default: "Living Ink").

## 3. reMarkable Connection

The application needs to download your notebooks. It uses the `rmapi` or `remarkable-mcp` connection.

1.  **Get One-Time Code**:
    *   Go to [my.remarkable.com/device/desktop/connect](https://my.remarkable.com/device/desktop/connect).
    *   Log in and click **Connect a new device** -> **Desktop**.
    *   Copy the 8-letter code.
2.  **Register**:
    *   Run the command: `uv run python server.py --register <your-code>`
    *   Or if installed as a standalone app, run the registration utility provided.

## 4. Final Configuration Structure

Your application folder (often in `~/Library/Application Support/RemarkableSync` or your project root) should look like this:

```text
config/
  .env               (Contains OPENAI_API_KEY=...)
  secrets/
     my-google-project-key.json
```
