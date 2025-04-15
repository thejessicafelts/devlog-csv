import argparse
import os
import sys
from datetime import datetime
import pytz
import aiohttp
import asyncio
import time
from tqdm import tqdm
from pathlib import Path
import csv

# =======================
# Settings (user adjustable)
# =======================
USERNAME = 'YOUR_USERNAME'
TIMEZONE = 'America/New_York'   # Provide your preferred timezone as a string.
EXCLUDED_REPO = ''              # Set to the name of a repo to exclude; leave blank to include all.
OUTPUT_FILE = 'devlog-csv.csv'  # CSV output file name.

# Convert the TIMEZONE setting (a string) to a pytz timezone object.
TIMEZONE = pytz.timezone(TIMEZONE)

# =======================
# Internal constants and setup
# =======================
# On Windows, use the SelectorEventLoopPolicy to avoid the "Event loop is closed" error.
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Retrieve and sanitize the token to remove extra whitespace/newlines.
TOKEN = os.getenv('GITHUB_TOKEN', '').strip()
if not TOKEN:
    print("Error: Please set your GitHub token in the GITHUB_TOKEN environment variable.")
    sys.exit(1)
HEADERS = {'Authorization': f'token {TOKEN}'}

# =======================
# Argument parsing (only for the "since" date)
# =======================
def arguments(argsval):
    parser = argparse.ArgumentParser()
    parser.add_argument('-since', '--since', type=str, required=False,
                        help="Start date in YYYY-MM-DD format for fetching new data")
    return parser.parse_args(argsval)

# =======================
# Helper Functions
# =======================
# Check rate limit
async def check_rate_limit(session):
    async with session.get('https://api.github.com/rate_limit', headers=HEADERS) as response:
        if response.status == 200:
            data = await response.json()
            remaining = data['resources']['core']['remaining']
            reset_time = data['resources']['core']['reset']

            if remaining == 0:
                reset_datetime_utc = datetime.fromtimestamp(reset_time, tz=pytz.utc)
                reset_datetime_local = reset_datetime_utc.astimezone(TIMEZONE)
                print(f"Rate limit exceeded. Reset at {reset_datetime_local.strftime('%Y-%m-%d %H:%M:%S')} {TIMEZONE.zone}")
                time_to_wait = reset_time - time.time()
                print(f"Waiting for {format_time(time_to_wait)} before retrying...")

                with tqdm(total=time_to_wait, desc="Rate limit reset", unit="s", dynamic_ncols=True) as pbar:
                    while time_to_wait > 0:
                        time.sleep(1)
                        time_to_wait -= 1
                        pbar.update(1)
            else:
                print(f"Rate limit remaining: {remaining}")
        else:
            print(f"Error checking rate limit: {response.status}")

# Format time as HH:MM:SS
def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

# Clean descriptions (remove newlines and quote marks)
def clean_description(text):
    return text.replace('\n', ' ').replace('\r', ' ').replace('"', '')

# =======================
# API Functions
# =======================
# Get all repositories
async def get_repos(session, since):
    repos = []
    page = 1
    while True:
        async with session.get(
            'https://api.github.com/user/repos',
            headers=HEADERS,
            params={'visibility': 'all', 'per_page': 100, 'page': page, 'affiliation': 'owner'}
        ) as response:
            if response.status != 200:
                print(f"Error fetching repos: {response.status}")
                break
            repo_data = await response.json()
            if not repo_data:
                break
            for repo in repo_data:
                if isinstance(repo, dict):
                    repo_creation_date = datetime.strptime(repo['created_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
                    if repo_creation_date.date() >= since.date():
                        if repo['name'] == EXCLUDED_REPO:
                            continue
                        repos.append(repo)
                else:
                    print(f"Unexpected repo format: {repo}")
            page += 1
    return repos

# Get commits for a repository
async def get_commits(repo_name, since, until, session):
    commits = {}
    page = 1
    while True:
        async with session.get(
            f'https://api.github.com/repos/{USERNAME}/{repo_name}/commits',
            headers=HEADERS,
            params={
                'author': USERNAME,
                'since': since.isoformat(),
                'until': until.isoformat(),
                'per_page': 100,
                'page': page
            }
        ) as response:
            if response.status != 200:
                print(f"Error fetching commits for {repo_name}: {response.status}")
                break
            commit_data = await response.json()
            if not commit_data or 'message' in commit_data:
                break
            commits[repo_name] = commit_data
            page += 1
    return commits

# Get issues
async def get_issues(since, until, session):
    issues = []
    page = 1
    while True:
        async with session.get(
            'https://api.github.com/issues',
            headers=HEADERS,
            params={
                'filter': 'created',
                'since': since.isoformat(),
                'per_page': 100,
                'page': page
            }
        ) as response:
            if response.status != 200:
                print(f"Error fetching issues: {response.status}")
                break
            issue_data = await response.json()
            if not issue_data or 'message' in issue_data:
                break
            for issue in issue_data:
                created_at = datetime.strptime(issue['created_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
                if since <= created_at < until and issue['user']['login'] == USERNAME and 'pull_request' not in issue:
                    issues.append(issue)
            page += 1
    return issues

# Get pull requests for a repository
async def get_pull_requests(repo_name, since, until, session):
    pulls = []
    page = 1
    while True:
        async with session.get(
            f'https://api.github.com/repos/{USERNAME}/{repo_name}/pulls',
            headers=HEADERS,
            params={
                'state': 'all',
                'per_page': 100,
                'page': page
            }
        ) as response:
            if response.status != 200:
                print(f"Error fetching pull requests for {repo_name}: {response.status}")
                break
            pr_data = await response.json()
            if not pr_data or 'message' in pr_data:
                break
            for pr in pr_data:
                created_at = datetime.strptime(pr['created_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
                if since <= created_at < until and pr['user']['login'] == USERNAME:
                    pulls.append(pr)
            page += 1
    return pulls

# Get forks for a repository
async def get_forks(repo_name, since, until, session):
    forks = []
    page = 1
    while True:
        async with session.get(
            f'https://api.github.com/repos/{USERNAME}/{repo_name}/forks',
            headers=HEADERS,
            params={
                'per_page': 100,
                'page': page
            }
        ) as response:
            if response.status != 200:
                print(f"Error fetching forks for {repo_name}: {response.status}")
                break
            fork_data = await response.json()
            if not fork_data or 'message' in fork_data:
                break
            forks.extend(fork_data)
            page += 1
    return forks

# Get releases for a repository
async def get_releases(repo_name, since, until, session):
    releases = []
    page = 1
    while True:
        async with session.get(
            f'https://api.github.com/repos/{USERNAME}/{repo_name}/releases',
            headers=HEADERS,
            params={
                'per_page': 100,
                'page': page
            }
        ) as response:
            if response.status != 200:
                print(f"Error fetching releases for {repo_name}: {response.status}")
                break
            release_data = await response.json()
            if not release_data or 'message' in release_data:
                break
            releases.extend(release_data)
            page += 1
    return releases

# =======================
# CSV Functions
# =======================
# Create CSV file using the constant OUTPUT_FILE
def create_csv():
    csv_file = Path(OUTPUT_FILE)
    with open(csv_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['date', 'time', 'repository', 'activity', 'description'])
    return csv_file

# Write log data to CSV
async def write_log_to_csv(csv_file, log_date, commit_data, issues, pull_requests, forks, releases, repo_name):
    with open(csv_file, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        # Write commits
        for repo, commits in commit_data.items():
            for commit in commits:
                commit_time = datetime.strptime(commit['commit']['author']['date'],
                                                '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
                description = clean_description(commit['commit']['message'])
                writer.writerow([commit_time.date(), commit_time.time(), repo, 'commit', description])

        # Write issues
        for issue in issues:
            created_at = datetime.strptime(issue['created_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
            description = clean_description(issue['title'])
            repo_from_issue = issue.get('repository', {}).get('name', repo_name)
            writer.writerow([created_at.date(), created_at.time(), repo_from_issue, 'issue', description])

        # Write pull requests
        for pr in pull_requests:
            created_at = datetime.strptime(pr['created_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
            description = clean_description(pr['title'])
            pr_repo = pr.get('base', {}).get('repo', {}).get('name', repo_name)
            writer.writerow([created_at.date(), created_at.time(), pr_repo, 'pull_request', description])

        # Write forks
        for fork in forks:
            created_at = datetime.strptime(fork['created_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
            if 'parent' in fork:
                parent_name = fork['parent'].get('name', repo_name)
                description = clean_description(f"Forked from {parent_name}")
            else:
                description = clean_description("Fork")
            writer.writerow([created_at.date(), created_at.time(), fork.get('name', repo_name), 'fork', description])

        # Write releases
        for release in releases:
            created_at = datetime.strptime(release['created_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
            description = clean_description(release.get('name', ''))
            writer.writerow([created_at.date(), created_at.time(), repo_name, 'release', description])

# =======================
# Main Routine
# =======================
async def main():
    args = arguments(sys.argv[1:])

    # Parse the "since" argument and make it timezone-aware (assuming UTC for input)
    if args.since:
        since = datetime.strptime(args.since, '%Y-%m-%d').replace(tzinfo=pytz.utc)
    else:
        since = datetime(2000, 1, 1, tzinfo=pytz.utc)
    until = datetime.now(pytz.utc)

    csv_file = create_csv()

    async with aiohttp.ClientSession() as session:
        await check_rate_limit(session)
        repos = await get_repos(session, since)

        # Loop through each repository and fetch its activities.
        for repo in repos:
            repo_name = repo['name']
            commit_data = await get_commits(repo_name, since, until, session)
            # Note: Issues are fetched globally; they may be repeated on each repo iteration.
            issues = await get_issues(since, until, session)
            pull_requests = await get_pull_requests(repo_name, since, until, session)
            forks = await get_forks(repo_name, since, until, session)
            releases = await get_releases(repo_name, since, until, session)

            await write_log_to_csv(csv_file, datetime.now(pytz.utc),
                                   commit_data, issues, pull_requests, forks, releases, repo_name)

    print(f"Data successfully written to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
