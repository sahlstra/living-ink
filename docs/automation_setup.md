# Automation Setup

To work around macOS security restrictions (TCC) that prevent background `launchd` scripts from accessing the `~/Documents` folder, this project uses a "Deploy to Home" strategy for automation.

## Project Structure

1.  **Development Folder**: `~/Documents/remarkable-mcp` (Where you work, edit code, and run tests manually).
2.  **Automation Folder**: `~/remarkable-mcp-automation` (A copy of the code purely for the background hourly job).

## How it Works

The hourly sync script runs from `~/remarkable-mcp-automation`. This folder is located in your Home directory root, which macOS allows background scripts to access more freely than `Documents`.

## Updating the Automation

If you make changes to the code (e.g., in `process_notebook.py`), you must "deploy" them to the automation folder for them to take effect in the background job.

Run this command from your Development folder:

```bash
./deploy_automation.sh
```

This script will:
1.  Copy your latest code to `~/remarkable-mcp-automation`.
2.  Update the `launchd` configuration if needed.
3.  Re-install dependencies in the automation folder.
4.  Restart the background timer.

## Logs

- **Standard Output**: `~/remarkable-mcp-automation/logs/launchd.log`
- **Errors**: `~/remarkable-mcp-automation/logs/launchd.err`

To check logs:
```bash
tail -f ~/remarkable-mcp-automation/logs/launchd.log
```
