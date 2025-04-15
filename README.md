# GitHub Devlog CSV Scraper

The GitHub Devlog CSV Scraper is an asynchronous Python script designed to retrieve various GitHub activities—such as commits, issues, pull requests, forks, and releases—from your GitHub account and write the data into a CSV file. This tool is useful for developers who wish to analyze or record their GitHub activity over time.

## Table of Contents

- [GitHub Devlog CSV Scraper](#github-devlog-csv-scraper)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Features](#features)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
    - [GITHUB\_TOKEN](#github_token)
    - [TIMEZONE](#timezone)
    - [EXCLUDED\_REPO](#excluded_repo)
    - [OUTPUT\_FILE](#output_file)
  - [Usage](#usage)
    - [Examples](#examples)
  - [Troubleshooting](#troubleshooting)

## Overview

This script uses the GitHub API to fetch data from your GitHub account in an asynchronous manner, ensuring efficient data retrieval. All activities fetched since a specified start date are recorded in a CSV file, making it easy to analyze your activity or archive a development log.

## Features

- **Asynchronous Data Fetching:** Uses `aiohttp` and `asyncio` for concurrent API calls.
- **Flexible Date Filtering:** Fetches data from a user-supplied "since" date.
- **Configurable Output:** Outputs data to a CSV file, with customizable file name.
- **Timezone Conversion:** Converts activity timestamps to your preferred timezone.
- **Repository Exclusion:** Optionally exclude a repository from the log (e.g. internal devlogs).

## Prerequisites

- **Python 3.7+** (the script has been tested on Python 3.10)
- Required Python packages:
  - `aiohttp`
  - `pytz`
  - `tqdm`

Install them via pip:

```bash
pip install aiohttp pytz tqdm
```

## Installation

1. Clone or download the repository containing the script.
2. Navigate to the project directory.

## Configuration

Before running the script, you need to adjust some settings and set an environment variable for GitHub authentication.

### GITHUB_TOKEN

The script requires a personal access token to authenticate with the GitHub API. To get your token:

1. **Generate a GitHub Personal Access Token:**
   - Log in to [GitHub](https://github.com).
   - Navigate to **Settings** → **Developer settings** → **Personal access tokens**.
   - Click **Generate new token**.
   - Provide a descriptive name.
   - Select required scopes (e.g., `repo` for private repositories or `public_repo` for public repositories).
   - Click **Generate token** and **copy** the generated token.

2. **Set the Environment Variable:**

   - **On Unix/Linux/MacOS:**
     ```bash
     export GITHUB_TOKEN="your_token_here"
     ```
   - **On Windows (Command Prompt):**
     ```cmd
     set GITHUB_TOKEN=your_token_here
     ```
   - **On Windows (PowerShell):**
     ```powershell
     $env:GITHUB_TOKEN = "your_token_here"
     ```

> **Note:** The script sanitizes the token (removing extra spaces and newlines) to ensure proper functioning.

### TIMEZONE

The `TIMEZONE` setting in the script defines the timezone used for converting and displaying activity timestamps. You can set it as any valid timezone string supported by [pytz](https://pythonhosted.org/pytz/).

**Examples:**
- `America/New_York`
- `America/Detroit`
- `Europe/London`
- `UTC`
- `Asia/Tokyo`

In the script, you'll see:

```python
TIMEZONE = 'America/New_York'
```

This value is converted to a pytz timezone object so that the timestamps in the CSV reflect the chosen timezone.

### EXCLUDED_REPO

Sometimes you may want to exclude a specific repository (for example, an internal development log repository) from being processed. The `EXCLUDED_REPO` constant allows you to do exactly that.

- To exclude a repository, set its exact name:
  
  ```python
  EXCLUDED_REPO = 'daily-devlog'
  ```

- If you want to include all repositories, leave it as an empty string:

  ```python
  EXCLUDED_REPO = ''
  ```

### OUTPUT_FILE

This constant defines the name of the CSV file that the script will create. You can change this to any valid filename.

```python
OUTPUT_FILE = 'devlog-csv.csv'
```

## Usage

The script accepts an optional `-since` parameter that allows you to specify the start date (in `YYYY-MM-DD` format) from which to collect GitHub activity.

### Examples

- **With a Since Date:**
  ```bash
  python devlog-csv.py --since 2025-04-01
  ```
  This command retrieves all activities from April 1, 2025, onward.

- **Without a Since Date:**
  ```bash
  python devlog-csv.py
  ```
  If no since date is provided, the script defaults to January 1, 2000.

Remember to set your `GITHUB_TOKEN` environment variable and update the settings (USERNAME, TIMEZONE, EXCLUDED_REPO, OUTPUT_FILE) in the script as desired.

## Troubleshooting

- **401 Unauthorized Errors:**  
  These errors typically indicate that the `GITHUB_TOKEN` environment variable is missing, incorrect, or lacks the required permissions. Make sure your token is generated with the appropriate scopes and that you've set it correctly.

- **No Activity in CSV:**  
  Verify that:
  - You have GitHub activity after your specified "since" date.
  - The `USERNAME` constant is correctly set.
  - The `EXCLUDED_REPO` is not accidentally filtering out repositories containing your activity.

- **TimeZone Issues:**  
  Ensure that the timezone string you provide is valid. Refer to the [list of pytz timezones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) if needed.