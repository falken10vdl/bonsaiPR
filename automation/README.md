# Weekly BonsaiPR Automation

This project automates the process of managing BonsaiPR development by running a series of scripts on a weekly basis. The automation includes cloning repositories, merging pull requests, building addons, creating GitHub releases, uploading source code, and maintaining the automation system itself.

## Project Structure

```
weekly-bonsaipr-automation
├── src
│   ├── main.py                # Entry point that runs scripts sequentially
│   └── config
│       ├── __init__.py        # Empty initializer for the config module
│       └── settings.py        # Configuration settings for the project
├── scripts
│   ├── 00_clone_merge_and_replace.py     # Clones repo and merges PRs
│   ├── 01_build_bonsaiPR_addons.py       # Builds the bonsaiPR addons
│   ├── 02_upload_to_falken10vdl.py       # Creates GitHub releases
│   ├── 03_upload_mergedPR.py             # Uploads source code
│   └── 04_upload_automation_scripts.py   # Uploads automation system
├── logs
│   └── .gitkeep                # Keeps the logs directory tracked by Git
├── requirements.txt            # Python dependencies for the project
├── .env.example                 # Example of environment variables needed
├── cron
│   └── weekly-automation.cron   # Cron job configuration for weekly execution
└── README.md                   # Documentation for the project
```

## Setup Instructions

1. **Clone the Repository**: Clone this repository to your local machine.
   
   ```bash
   git clone <repository-url>
   cd weekly-bonsaipr-automation
   ```

2. **Install Dependencies**: Install the required Python packages listed in `requirements.txt`.

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**: Copy the `.env.example` file to `.env` and update the necessary environment variables.

4. **Set Up Cron Job**: Configure the cron job by adding the contents of `cron/weekly-automation.cron` to your crontab. Note that you can also run this manually with `crontab -e` and add the line directly.

   ```bash
   crontab -e
   # Then add the line from cron/weekly-automation.cron
   ```

   Or to use the file directly:
   ```bash
   crontab cron/weekly-automation.cron
   ```

5. **Run the Automation**: You can manually run the automation by executing the `src/main.py` script.

   ```bash
   python src/main.py
   ```

## Usage

The automation will run the following scripts sequentially:

1. `00_clone_merge_and_replace.py`: Clones the IfcOpenShell repository, merges open pull requests, and applies bonsai→bonsaiPR replacements
2. `01_build_bonsaiPR_addons.py`: Builds BonsaiPR addons for multiple platforms (Linux, macOS, Windows)
3. `02_upload_to_falken10vdl.py`: Creates GitHub releases and uploads addon files with rich descriptions
4. `03_upload_mergedPR.py`: Uploads complete source code to GitHub repository for developer access
5. `04_upload_automation_scripts.py`: Uploads sanitized automation scripts to maintain system transparency

### Manual Execution

To run the automation manually:

```bash
cd /home/falken10vdl/bonsaiPRDevel/weekly-bonsaipr-automation
python src/main.py
```

### Scheduled Execution

The cron job runs every Sunday at 2:00 AM UTC:

```bash
# View current cron jobs
crontab -l

# Edit cron jobs
crontab -e
```

## Logging

**Automated Logging**: When run via cron, logs are automatically written to the `logs/` directory with timestamped filenames:
- Format: `automation-YYYYMMDD-HHMMSS.log`
- Location: `/home/falken10vdl/bonsaiPRDevel/weekly-bonsaipr-automation/logs/`
- Example: `logs/automation-20251013-020000.log`

**Manual Logging**: When run manually, output goes to console. To log manually:

```bash
python src/main.py > logs/manual-$(date +%Y%m%d-%H%M%S).log 2>&1
```

**Log Monitoring**: Monitor logs for execution status:

```bash
# View latest log
ls -la logs/ | tail -1

# Follow latest log in real-time
tail -f logs/automation-*.log

# Check for errors in recent logs
grep -i error logs/automation-*.log
```

## Architecture

### Core Components

- **`src/main.py`**: Main orchestrator that runs scripts sequentially with proper logging
- **`src/config/settings.py`**: Configuration management using environment variables
- **`scripts/`**: Individual automation scripts for each workflow step
- **`logs/`**: Timestamped execution logs for monitoring and debugging
- **`cron/`**: Cron job configuration file

### Configuration Management

The system uses a centralized configuration approach:

- **Environment Variables**: Stored in `.env` file (not tracked in git)
- **Settings Class**: `src/config/settings.py` loads and validates configuration
- **Script Discovery**: Automatically detects numbered scripts in `scripts/` directory
- **Dynamic Execution**: Scripts run in numerical order (00_, 01_, 02_, etc.)

### Key Features

- **Self-Maintaining**: Automation system uploads itself for transparency
- **Error Handling**: Comprehensive logging and error reporting
- **Multi-Platform Support**: Builds for Linux, macOS, and Windows
- **GitHub Integration**: Automated releases with rich descriptions
- **Source Code Transparency**: Complete source uploaded for developer access

## License

This project is licensed under the MIT License. See the LICENSE file for more details.