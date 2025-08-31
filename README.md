# Contest Results Fetcher

A simple Flask web app that fetches Codeforces contest standings and generates Excel reports.

## Quick Start

1. **Install Python 3.8+**

2. **Clone and setup**

   ```bash
   git clone https://github.com/Mazen-Ghanayem/contest-results-fetcher.git
   cd contest-results-fetcher
   pip install -r requirements.txt
   ```

3. **Run**

   ```bash
   python app.py
   ```

4. **Use**
   - Open `http://localhost:5000`
   - Enter contest ID (e.g., `631862`)
   - Paste participant handles (one per line)
   - Download Excel file

## Configuration (Optional)

Create `.env` file for Codeforces API access:

```env
CODEFORCES_API_KEY=your_api_key_here
CODEFORCES_API_SECRET=your_api_secret_here
FLASK_SECRET_KEY=random_secret_key
```

Get API credentials from [Codeforces API Settings](https://codeforces.com/settings/api).

## What it does

- Takes a contest ID and list of handles
- Fetches scores from Codeforces
- Generates Excel file with Handle and Points columns
- Preserves empty lines (shows as empty handle with 0 points)
