# X.com Tweet Scraper

A robust, automated tool for scraping tweets from X.com (formerly Twitter) with built-in authentication and intelligent data collection.

## Features

- **Automatic Authentication**: Logs into X.com and saves session cookies for future use
- **Smart Cookie Management**: Handles session persistence across multiple runs
- **Robust Error Handling**: Multiple fallback strategies for navigation and element detection
- **Duplicate Detection**: Prevents collecting the same tweet multiple times
- **Flexible Search**: Search by any keyword or phrase
- **JSON Output**: Clean, structured data export
- **Command Line Interface**: Easy to use with various options
- **Headless Support**: Run in background without browser window

## Prerequisites

- Python 3.7+
- Playwright browser automation library

## Installation

1. **Clone or download the script**
   ```
   git clone https://github.com/Bhanunamikaze/X.com_Scraper.git

   ```

2. **Install dependencies**
   ```
   pip install playwright
   playwright install chromium
   ```

## Usage

### Basic Usage

**First time (with login):**
```
python x_scraper.py -u your_username -p your_password -k "search keyword"
```

**Subsequent runs (using saved cookies):**
```
python x_scraper.py --skip-login -k "search keyword"
```

### Command Line Options

| Option | Short | Description | Required |
|--------|-------|-------------|----------|
| `--username` | `-u` | X.com username or email | Yes (unless `--skip-login`) |
| `--password` | `-p` | X.com password | Yes (unless `--skip-login`) |
| `--keyword` | `-k` | Search keyword or phrase | Yes |
| `--output` | `-o` | Output JSON filename | No |
| `--max-scrolls` | `-s` | Maximum page scrolls (default: 15) | No |
| `--headless` | | Run without browser window | No |
| `--skip-login` | | Use existing cookies, skip login | No |

### Examples

**Search for cryptocurrency tweets:**
```
python x_scraper.py -u myemail@domain.com -p mypassword -k "cryptocurrency"
```

**Search with custom output file:**
```
python x_scraper.py -u myemail@domain.com -p mypassword -k "AI technology" -o ai_tweets.json
```

**Extended search (more scrolls):**
```
python x_scraper.py -u myemail@domain.com -p mypassword -k "climate change" -s 30
```

**Use existing login session:**
```
python x_scraper.py --skip-login -k "breaking news"
```

**Run in background (headless):**
```
python x_scraper.py --skip-login --headless -k "tech news" -s 20
```

## Output Format

The scraper generates JSON files with the following structure:

```json
[
  {
    "username": "john_doe",
    "handle": "/john_doe",
    "text": "This is the tweet content...",
    "timestamp": "2024-01-15T10:30:00.000Z",
    "scraped_at": "2024-01-15 15:30:45"
  }
]
```

### Output Fields

- **username**: Display name of the tweet author
- **handle**: X.com handle/profile URL
- **text**: Full tweet content
- **timestamp**: Original tweet timestamp (ISO format)
- **scraped_at**: When the tweet was collected

## How It Works

1. **Authentication**: 
   - Navigates to X.com login page
   - Handles username/password entry
   - Manages 2FA/verification if required
   - Saves session cookies for future use

2. **Search Navigation**:
   - Tests authentication status
   - Navigates to search results page
   - Applies real-time filter (`f=live`)

3. **Data Collection**:
   - Progressively scrolls through results
   - Extracts tweet data using multiple selector strategies
   - Prevents duplicate collection
   - Handles dynamic content loading

4. **Error Recovery**:
   - Multiple navigation strategies
   - Fallback element selectors
   - Graceful error handling
   - Automatic retry mechanisms

## Configuration Files

### Generated Files

- **`x_cookies.json`**: Saved authentication session
- **`{keyword}_tweets.json`**: Default output filename (if not specified)

### Cookie Management

The scraper automatically:
- Saves cookies after successful login
- Loads cookies for subsequent runs
- Validates authentication before scraping
- Handles cookie expiration gracefully

## Troubleshooting

### Common Issues

**Login fails:**
- Verify username/password are correct
- Check if 2FA is enabled (you'll be prompted)
- Try running without `--headless` to see browser interaction

**No tweets collected:**
- Ensure cookies are valid (try fresh login)
- Check if search keyword returns results on X.com
- Verify internet connection

**Authentication errors:**
- Delete `x_cookies.json` and login again
- Check if account is suspended/limited
- Try different browser user agent

### Debug Mode

Run without `--headless` to see browser interaction:
```
python x_scraper.py -u username -p password -k "keyword"
```

### Re-authentication

Force fresh login by deleting cookie file:
```
rm x_cookies.json
python x_scraper.py -u username -p password -k "keyword"
```

## Rate Limiting & Best Practices

- **Respectful Usage**: Don't overwhelm X.com servers
- **Reasonable Delays**: Built-in delays between actions
- **Limited Scrolls**: Default 15 scrolls (adjust as needed)
- **Account Safety**: Use dedicated scraping accounts

## Legal & Ethical Considerations

- **Terms of Service**: Review X.com's ToS before use
- **Data Privacy**: Handle collected data responsibly
- **Rate Limits**: Respect platform limitations
- **Fair Use**: Use for research/analysis purposes



## License

This tool is provided as-is for educational and research purposes. Users are responsible for compliance with X.com's terms of service and applicable laws.
