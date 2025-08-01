#!/usr/bin/env python3
"""
X.com Tweet Scraper with automatic authentication
A robust tool for scraping tweets from X.com (formerly Twitter) with command line interface
"""

import json
import time
import argparse
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ANSI Color codes for better output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(message):
    print(f"{Colors.GREEN}+ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}- {message}{Colors.END}")

def print_warning(message):
    print(f"{Colors.YELLOW}* {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}> {message}{Colors.END}")

def print_progress(message):
    print(f"{Colors.CYAN}+ {message}{Colors.END}")

class XScraper:
    def __init__(self, headless=False, slow_mo=100):
        self.headless = headless
        self.slow_mo = slow_mo
        self.cookies_file = "x_cookies.json"
        
    def normalize_cookies(self, raw_cookies):
        """Normalize cookies format for X.com compatibility"""
        normalized = []
        for cookie in raw_cookies:
            # Handle both twitter.com and x.com domains
            domain = cookie.get("domain", "")
            if domain and not domain.startswith("."):
                domain = "." + domain
            
            # Ensure x.com cookies work
            if "twitter.com" in domain:
                domain = domain.replace("twitter.com", "x.com")
            
            c = {
                "name": cookie["name"],
                "value": cookie["value"],
                "path": cookie.get("path", "/"),
                "secure": cookie.get("secure", True),
                "httpOnly": cookie.get("httpOnly", False),
                "domain": domain or ".x.com",
                "sameSite": "None" if cookie.get("secure") else "Lax",
            }
            
            # Handle sameSite properly
            ss = cookie.get("sameSite", "").lower()
            if ss == "no_restriction":
                c["sameSite"] = "None"
                c["secure"] = True
            elif ss in ["lax", "strict"]:
                c["sameSite"] = ss.capitalize()
                
            if "expirationDate" in cookie:
                c["expires"] = int(cookie["expirationDate"])
            elif "expires" in cookie:
                c["expires"] = int(cookie["expires"])
                
            normalized.append(c)
        return normalized

    def robust_navigation(self, page, url, max_retries=3):
        """Navigate with improved error handling"""
        strategies = [
            {"wait_until": "domcontentloaded", "timeout": 60000},
            {"wait_until": "load", "timeout": 45000},
            {"timeout": 30000},
        ]
        
        for attempt in range(max_retries):
            for i, strategy in enumerate(strategies):
                try:
                    print_info(f"Navigation attempt {attempt + 1}.{i + 1} using strategy {strategy}")
                    page.goto(url, **strategy)
                    print_success("Navigation successful")
                    return True
                except PlaywrightTimeoutError as e:
                    print_warning(f"Strategy {i + 1} failed: {str(e)[:100]}...")
                    continue
                except Exception as e:
                    print_error(f"Unexpected error: {e}")
                    continue
            
            if attempt < max_retries - 1:
                print_warning("Retrying navigation in 5 seconds...")
                time.sleep(5)
        
        return False

    def wait_and_fill_input(self, page, selectors, value, field_name):
        """Wait for input field and fill it"""
        for selector in selectors:
            try:
                input_locator = page.locator(selector)
                input_locator.wait_for(timeout=15000)
                print_success(f"Found {field_name} field with selector: {selector}")
                
                input_locator.clear()
                time.sleep(0.5)
                input_locator.type(value, delay=50)
                time.sleep(1)
                return True
                
            except PlaywrightTimeoutError:
                continue
            except Exception as e:
                print_warning(f"Error with selector {selector}: {e}")
                continue
        
        print_error(f"Could not find {field_name} input field")
        return False

    def click_button(self, page, selectors, button_name):
        """Click button with improved reliability"""
        for selector in selectors:
            try:
                button_locator = page.locator(selector)
                button_locator.wait_for(timeout=15000)
                
                if button_locator.is_enabled():
                    button_locator.click()
                    print_success(f"Clicked {button_name} button with selector: {selector}")
                    return True
                else:
                    print_warning(f"Button {button_name} is disabled")
                    
            except PlaywrightTimeoutError:
                continue
            except Exception as e:
                print_warning(f"Error clicking button with selector {selector}: {e}")
                continue
        
        print_error(f"Could not find or click {button_name} button")
        return False

    def verify_login_success(self, page):
        """Verify that login was actually successful"""
        print_progress("Verifying login success...")
        
        time.sleep(5)
        
        current_url = page.url
        print_info(f"Current URL: {current_url}")
        
        # Check for successful login indicators
        success_indicators = [
            lambda: '/home' in page.url,
            lambda: page.locator('[data-testid="SideNav_AccountSwitcher_Button"]').count() > 0,
            lambda: page.locator('[data-testid="primaryNavigation"]').count() > 0,
            lambda: 'login' not in page.url and 'flow' not in page.url,
        ]
        
        for i, indicator in enumerate(success_indicators):
            try:
                if indicator():
                    print_success(f"Login verified using indicator {i + 1}")
                    return True
            except:
                continue
        
        # Try to navigate to home and see if we stay there
        try:
            print_progress("Testing navigation to home page...")
            page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
            time.sleep(3)
            
            if '/home' in page.url and 'login' not in page.url:
                print_success("Successfully navigated to home - login confirmed")
                return True
            else:
                print_error(f"Redirected to: {page.url} - login failed")
                return False
                
        except Exception as e:
            print_error(f"Error testing home navigation: {e}")
            return False

    def login_and_save_cookies(self, username, password):
        """Enhanced login with better verification"""
        print_info(f"Logging in as {username}...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless, 
                slow_mo=self.slow_mo,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            
            context = browser.new_context(
                viewport={"width": 1200, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York"
            )
            
            try:
                page = context.new_page()
                page.set_default_timeout(60000)
                page.set_default_navigation_timeout(60000)
                
                # Navigate to login page
                login_url = "https://x.com/i/flow/login"
                print_progress("Navigating to X.com login page...")
                
                if not self.robust_navigation(page, login_url):
                    print_error("Failed to navigate to login page")
                    return False
                
                time.sleep(3)
                
                # Enter username
                print_progress("Entering username...")
                username_selectors = [
                    'input[autocomplete="username"]',
                    'input[name="text"]',
                    'input[data-testid="ocfEnterTextTextInput"]'
                ]
                
                if not self.wait_and_fill_input(page, username_selectors, username, "username"):
                    return False
                
                # Click Next
                print_progress("Clicking Next button...")
                next_selectors = [
                    '[role="button"]:has-text("Next")',
                    'button:has-text("Next")',
                    '[data-testid="LoginForm_Login_Button"]'
                ]
                
                if not self.click_button(page, next_selectors, "Next"):
                    return False
                
                time.sleep(4)
                
                # Handle verification if needed
                try:
                    verification_locator = page.locator('input[data-testid="ocfEnterTextTextInput"]')
                    verification_locator.wait_for(timeout=8000)
                    
                    print_warning("Additional verification step detected")
                    verification_text = input("Enter verification (phone/username/email): ")
                    
                    verification_locator.clear()
                    verification_locator.type(verification_text, delay=50)
                    time.sleep(1)
                    
                    verify_button = page.locator('[role="button"]:has-text("Next")')
                    verify_button.click()
                    time.sleep(4)
                    
                except PlaywrightTimeoutError:
                    print_info("No additional verification step")
                
                # Enter password
                print_progress("Entering password...")
                password_selectors = [
                    'input[name="password"]',
                    'input[type="password"]',
                    'input[autocomplete="current-password"]'
                ]
                
                if not self.wait_and_fill_input(page, password_selectors, password, "password"):
                    return False
                
                # Click Login
                print_progress("Clicking Login button...")
                login_selectors = [
                    '[data-testid="LoginForm_Login_Button"]',
                    '[role="button"]:has-text("Log in")',
                    'button[type="submit"]'
                ]
                
                if not self.click_button(page, login_selectors, "Login"):
                    return False
                
                # Wait longer and verify login
                print_progress("Waiting for login completion...")
                time.sleep(8)
                
                if not self.verify_login_success(page):
                    print_error("Login verification failed")
                    return False
                
                # Save cookies after successful verification
                cookies = context.cookies()
                print_info(f"Retrieved {len(cookies)} cookies")
                
                with open(self.cookies_file, "w", encoding="utf-8") as f:
                    json.dump(cookies, f, indent=2)
                print_success(f"Cookies saved to {self.cookies_file}")
                
                return True
                
            except Exception as e:
                print_error(f"Login failed: {e}")
                return False
            finally:
                browser.close()

    def load_cookies(self):
        """Load and validate cookies"""
        if not os.path.exists(self.cookies_file):
            return False
        
        try:
            with open(self.cookies_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            
            print_info(f"Loading {len(cookies)} cookies from file")
            normalized = self.normalize_cookies(cookies)
            print_success(f"Normalized {len(normalized)} cookies")
            return normalized
            
        except Exception as e:
            print_warning(f"Failed to load cookies: {e}")
            return False

    def test_authentication(self, page):
        """Test if authentication is working"""
        try:
            auth_indicators = [
                '[data-testid="SideNav_AccountSwitcher_Button"]',
                '[data-testid="primaryNavigation"]',
                '[aria-label="Home timeline"]'
            ]
            
            for indicator in auth_indicators:
                if page.locator(indicator).count() > 0:
                    print_success("Authentication verified - user is logged in")
                    return True
            
            if 'login' in page.url or page.locator('input[name="password"]').count() > 0:
                print_error("Not authenticated - on login page")
                return False
            
            print_warning("Authentication status unclear")
            return False
            
        except Exception as e:
            print_warning(f"Error checking authentication: {e}")
            return False

    def scrape_tweets(self, keyword, max_scrolls=15, output_file=None):
        """Enhanced scraping with authentication verification"""
        if not output_file:
            output_file = f"{keyword.replace(' ', '_').replace('/', '_')}_tweets.json"
        
        all_data = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless, slow_mo=self.slow_mo)
            context = browser.new_context(
                viewport={"width": 1200, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US"
            )

            try:
                # Load cookies
                cookies = self.load_cookies()
                if cookies:
                    context.add_cookies(cookies)
                    print_success("Cookies applied to context")
                else:
                    print_warning("No cookies to load")
                    return []

                page = context.new_page()
                page.set_default_timeout(30000)

                # First, test authentication by going to home
                print_progress("Testing authentication...")
                if not self.robust_navigation(page, "https://x.com/home"):
                    print_error("Failed to navigate to home page")
                    return []

                time.sleep(4)
                
                if not self.test_authentication(page):
                    print_error("Authentication failed - cookies may be expired")
                    print_warning("Try running without --skip-login to refresh cookies")
                    return []

                # Now navigate to search
                search_url = f"https://x.com/search?q={keyword}&src=typed_query&f=live"
                print_progress(f"Navigating to search: {keyword}")
                
                if not self.robust_navigation(page, search_url):
                    print_error("Failed to navigate to search page")
                    return []

                time.sleep(5)

                print_progress(f"Starting to collect tweets (max {max_scrolls} scrolls)...")
                
                seen_tweets = set()
                consecutive_no_new_tweets = 0
                
                for scroll_count in range(max_scrolls):
                    print_info(f"Scroll {scroll_count + 1}/{max_scrolls}")
                    
                    # Scroll down
                    page.mouse.wheel(0, 3000)
                    time.sleep(4)
                    
                    # Look for tweets with multiple selectors
                    article_selectors = [
                        "article[data-testid='tweet']",
                        "article",
                        "[data-testid='tweet']"
                    ]
                    
                    articles = None
                    for selector in article_selectors:
                        try:
                            articles = page.locator(selector)
                            count = articles.count()
                            if count > 0:
                                print_success(f"Found {count} articles using selector: {selector}")
                                break
                        except:
                            continue
                    
                    if not articles or articles.count() == 0:
                        print_warning("No articles found with any selector")
                        consecutive_no_new_tweets += 1
                        if consecutive_no_new_tweets >= 2:
                            break
                        continue
                    
                    current_count = articles.count()
                    new_tweets_count = 0
                    
                    for i in range(current_count):
                        try:
                            article = articles.nth(i)
                            
                            # Extract tweet text
                            tweet_texts = article.locator("div[lang]").all_text_contents()
                            tweet_text = " ".join(tweet_texts).strip() if tweet_texts else ""
                            
                            if not tweet_text or len(tweet_text) < 10:
                                continue
                            
                            # Check for duplicates
                            tweet_hash = hash(tweet_text)
                            if tweet_hash in seen_tweets:
                                continue
                            
                            seen_tweets.add(tweet_hash)
                            new_tweets_count += 1
                            
                            # Extract metadata
                            try:
                                username = article.locator("div[dir='ltr'] span").first.text_content(timeout=2000) or "N/A"
                            except:
                                username = "N/A"
                            
                            try:
                                handle = article.locator("a[role='link']").nth(1).get_attribute("href", timeout=2000) or "N/A"
                            except:
                                handle = "N/A"
                            
                            try:
                                timestamp = article.locator("time").get_attribute("datetime", timeout=2000) or "N/A"
                            except:
                                timestamp = "N/A"

                            tweet_data = {
                                "username": username,
                                "handle": handle,
                                "text": tweet_text,
                                "timestamp": timestamp,
                                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            all_data.append(tweet_data)
                            
                        except Exception:
                            continue
                    
                    print_info(f"Found {new_tweets_count} new tweets (Total: {len(all_data)})")
                    
                    if new_tweets_count == 0:
                        consecutive_no_new_tweets += 1
                        if consecutive_no_new_tweets >= 3:
                            print_warning("No new tweets found, stopping...")
                            break
                    else:
                        consecutive_no_new_tweets = 0

                print_success(f"Scraping completed! Found {len(all_data)} unique tweets")

            except Exception as e:
                print_error(f"Error during scraping: {e}")
            finally:
                browser.close()

        # Save results
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)
            print_success(f"Tweets saved to {output_file}")
        except Exception as e:
            print_error(f"Failed to save tweets: {e}")

        return all_data

def main():
    print(f"{Colors.BOLD}{Colors.PURPLE}X.com Tweet Scraper v1.0{Colors.END}")
    print(f"{Colors.CYAN}Robust tweet collection with automatic authentication{Colors.END}")
    print("-" * 50)
    
    parser = argparse.ArgumentParser(description="X.com Tweet Scraper")
    parser.add_argument("-u", "--username", type=str, help="X.com username or email")
    parser.add_argument("-p", "--password", type=str, help="X.com password")
    parser.add_argument("-k", "--keyword", type=str, required=True, help="Search keyword")
    parser.add_argument("-o", "--output", type=str, help="Output JSON file")
    parser.add_argument("-s", "--max-scrolls", type=int, default=15, help="Max scrolls")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--skip-login", action="store_true", help="Use existing cookies")
    
    args = parser.parse_args()

    if not args.skip_login and (not args.username or not args.password):
        print_error("Username and password required unless --skip-login is used")
        sys.exit(1)

    scraper = XScraper(headless=args.headless)
    
    if not args.skip_login:
        print_progress("Starting login process...")
        success = scraper.login_and_save_cookies(args.username, args.password)
        if not success:
            print_error("Login failed")
            sys.exit(1)
        time.sleep(3)

    tweets = scraper.scrape_tweets(
        keyword=args.keyword,
        max_scrolls=args.max_scrolls,
        output_file=args.output
    )
    
    if tweets:
        print_success(f"Successfully scraped {len(tweets)} tweets!")
    else:
        print_error("No tweets were scraped")

if __name__ == "__main__":
    main()
