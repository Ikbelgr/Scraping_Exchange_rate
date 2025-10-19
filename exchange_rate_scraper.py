#!/usr/bin/env python3
import time
import logging
from datetime import datetime
import os
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import re

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('exchange_rates_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ExchangeRatesScraper:
    def __init__(self, reuse_driver=True):
        self.reuse_driver = reuse_driver
        self.setup_chrome_options()

        # Scraper settings - AUGMENTÉ pour sites problématiques
        self.max_retries = 5  # Augmenté de 3 à 5
        self.delay_between_requests = 3
        self.page_load_timeout = 45  # Augmenté de 30 à 45

        self._chromedriver_path = None

        self.country_mapping = {
            'France': 'France',
            'Germany': 'Germany', 
            'Italy': 'Italy',
            'Belgium': 'Belgium',
            'Spain': 'Spain'
        }

        self.currency_pairs = [
            # WesternUnion - France
            {'pair': 'EUR-TND', 'url': 'https://www.westernunion.com/fr/fr/currency-converter/eur-to-tnd-rate.html', 'provider': 'WesternUnion (France)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://www.westernunion.com/fr/fr/currency-converter/eur-to-mad-rate.html', 'provider': 'WesternUnion (France)', 'currency': 'MAD'},

            # WesternUnion - Germany
            {'pair': 'EUR-TND', 'url': 'https://www.westernunion.com/de/de/currency-converter/eur-to-tnd-rate.html', 'provider': 'WesternUnion (Germany)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://www.westernunion.com/de/de/currency-converter/eur-to-mad-rate.html', 'provider': 'WesternUnion (Germany)', 'currency': 'MAD'},

            # WesternUnion - Spain
            {'pair': 'EUR-TND', 'url': 'https://www.westernunion.com/es/es/currency-converter/eur-to-tnd-rate.html', 'provider': 'WesternUnion (Spain)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://www.westernunion.com/es/es/currency-converter/eur-to-mad-rate.html', 'provider': 'WesternUnion (Spain)', 'currency': 'MAD'},

            # WesternUnion - Belgium
            {'pair': 'EUR-TND', 'url': 'https://www.westernunion.com/be/en/currency-converter/eur-to-tnd-rate.html', 'provider': 'WesternUnion (Belgium)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://www.westernunion.com/be/en/send-money-to-morocco.html', 'provider': 'WesternUnion (Belgium)', 'currency': 'MAD'},

            # WesternUnion - Italy
            {'pair': 'EUR-TND', 'url': 'https://www.westernunion.com/it/it/currency-converter/eur-to-tnd-rate.html', 'provider': 'WesternUnion (Italy)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://www.westernunion.com/it/it/currency-converter/eur-to-mad-rate.html', 'provider': 'WesternUnion (Italy)', 'currency': 'MAD'},

            # MoneyGram
            {'pair': 'EUR-TND', 'url': 'https://www.moneygram.com/fr/en/corridor/tunisia', 'provider': 'MoneyGram (France)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://www.moneygram.com/fr/en/corridor/morocco', 'provider': 'MoneyGram (France)', 'currency': 'MAD'},
            {'pair': 'EUR-TND', 'url': 'https://www.moneygram.com/be/en/corridor/tunisia', 'provider': 'MoneyGram (Belgium)', 'currency': 'TND'},
            {'pair': 'EUR-TND', 'url': 'https://www.moneygram.com/it/en/corridor/tunisia', 'provider': 'MoneyGram (Italy)', 'currency': 'TND'},
            {'pair': 'EUR-TND', 'url': 'https://www.moneygram.com/es/en/corridor/tunisia', 'provider': 'MoneyGram (Spain)', 'currency': 'TND'},
            {'pair': 'EUR-TND', 'url': 'https://www.moneygram.com/de/en/corridor/tunisia', 'provider': 'MoneyGram (Germany)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://www.moneygram.com/be/en/corridor/morocco', 'provider': 'MoneyGram (Belgium)', 'currency': 'MAD'},
            {'pair': 'EUR-MAD', 'url': 'https://www.moneygram.com/it/en/corridor/morocco', 'provider': 'MoneyGram (Italy)', 'currency': 'MAD'},
            {'pair': 'EUR-MAD', 'url': 'https://www.moneygram.com/es/en/corridor/morocco', 'provider': 'MoneyGram (Spain)', 'currency': 'MAD'},
            {'pair': 'EUR-MAD', 'url': 'https://www.moneygram.com/de/en/corridor/morocco', 'provider': 'MoneyGram (Germany)', 'currency': 'MAD'},

            # LemFi
            {'pair': 'EUR-TND', 'url': 'https://lemfi.com/fr-fr/international-money-transfer/tunisia', 'provider': 'LemFi (France)', 'currency': 'TND'},
            {'pair': 'EUR-TND', 'url': 'https://lemfi.com/fr-de/international-money-transfer/tunisia', 'provider': 'LemFi (Germany)', 'currency': 'TND'},
            {'pair': 'EUR-TND', 'url': 'https://lemfi.com/fr-it/international-money-transfer/tunisia', 'provider': 'LemFi (Italy)', 'currency': 'TND'},
            {'pair': 'EUR-TND', 'url': 'https://lemfi.com/fr-es/international-money-transfer/tunisia', 'provider': 'LemFi (Spain)', 'currency': 'TND'},
            {'pair': 'EUR-TND', 'url': 'https://lemfi.com/fr-be/international-money-transfer/tunisia', 'provider': 'LemFi (Belgium)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://lemfi.com/fr-fr/international-money-transfer/morocco', 'provider': 'LemFi (France)', 'currency': 'MAD'},
            {'pair': 'EUR-MAD', 'url': 'https://lemfi.com/fr-de/international-money-transfer/morocco', 'provider': 'LemFi (Germany)', 'currency': 'MAD'},
            {'pair': 'EUR-MAD', 'url': 'https://lemfi.com/fr-it/international-money-transfer/morocco', 'provider': 'LemFi (Italy)', 'currency': 'MAD'},
            {'pair': 'EUR-MAD', 'url': 'https://lemfi.com/fr-es/international-money-transfer/morocco', 'provider': 'LemFi (Spain)', 'currency': 'MAD'},
            {'pair': 'EUR-MAD', 'url': 'https://lemfi.com/fr-be/international-money-transfer/morocco', 'provider': 'LemFi (Belgium)', 'currency': 'MAD'},

            # Remitly
            {'pair': 'EUR-TND', 'url': 'https://www.remitly.com/fr/fr/tunisia/pricing', 'provider': 'Remitly (France)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://www.remitly.com/fr/fr/morocco/pricing', 'provider': 'Remitly (France)', 'currency': 'MAD'},
            {'pair': 'EUR-TND', 'url': 'https://www.remitly.com/de/fr/currency-converter/eur-to-tnd-rate', 'provider': 'Remitly (Germany)', 'currency': 'TND'},
            {'pair': 'EUR-TND', 'url': 'https://www.remitly.com/es/fr/currency-converter/eur-to-tnd-rate', 'provider': 'Remitly (Spain)', 'currency': 'TND'},
            {'pair': 'EUR-TND', 'url': 'https://www.remitly.com/be/fr/currency-converter/eur-to-tnd-rate', 'provider': 'Remitly (Belgium)', 'currency': 'TND'},
            {'pair': 'EUR-TND', 'url': 'https://www.remitly.com/it/fr/currency-converter/eur-to-tnd-rate', 'provider': 'Remitly (Italy)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://www.remitly.com/de/fr/currency-converter/eur-to-mad-rate', 'provider': 'Remitly (Germany)', 'currency': 'MAD'},
            {'pair': 'EUR-MAD', 'url': 'https://www.remitly.com/es/fr/currency-converter/eur-to-mad-rate', 'provider': 'Remitly (Spain)', 'currency': 'MAD'},
            {'pair': 'EUR-MAD', 'url': 'https://www.remitly.com/be/fr/currency-converter/eur-to-mad-rate', 'provider': 'Remitly (Belgium)', 'currency': 'MAD'},
            {'pair': 'EUR-MAD', 'url': 'https://www.remitly.com/it/fr/currency-converter/eur-to-mad-rate', 'provider': 'Remitly (Italy)', 'currency': 'MAD'},

            # Sendwave
            {'pair': 'EUR-TND', 'url': 'https://www.sendwave.com/en/countries/tunisia/fr', 'provider': 'Sendwave (France)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://www.sendwave.com/en/countries/morocco/fr', 'provider': 'Sendwave (France)', 'currency': 'MAD'},
            {'pair': 'EUR-TND', 'url': 'https://www.sendwave.com/en/countries/tunisia/de', 'provider': 'Sendwave (Germany)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://www.sendwave.com/en/countries/morocco/de', 'provider': 'Sendwave (Germany)', 'currency': 'MAD'},
            {'pair': 'EUR-TND', 'url': 'https://www.sendwave.com/en/countries/tunisia/it', 'provider': 'Sendwave (Italy)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://www.sendwave.com/en/countries/morocco/it', 'provider': 'Sendwave (Italy)', 'currency': 'MAD'},
            {'pair': 'EUR-TND', 'url': 'https://www.sendwave.com/en/countries/tunisia/be', 'provider': 'Sendwave (Belgium)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://www.sendwave.com/en/countries/morocco/be', 'provider': 'Sendwave (Belgium)', 'currency': 'MAD'},
            {'pair': 'EUR-TND', 'url': 'https://www.sendwave.com/en/countries/tunisia/es', 'provider': 'Sendwave (Spain)', 'currency': 'TND'},
            {'pair': 'EUR-MAD', 'url': 'https://www.sendwave.com/en/countries/morocco/es', 'provider': 'Sendwave (Spain)', 'currency': 'MAD'},
        ]

        self.driver = None
        if self.reuse_driver:
            self.create_driver()

    def setup_chrome_options(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless=new')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        self.chrome_options.add_argument('--disable-extensions')
        self.chrome_options.add_argument('--disable-plugins')
        prefs = {"profile.managed_default_content_settings.images": 2}
        self.chrome_options.add_experimental_option("prefs", prefs)

    def get_chromedriver_path(self):
        """Get or cache the chromedriver path"""
        if self._chromedriver_path:
            return self._chromedriver_path
        
        driver_path = ChromeDriverManager().install()
        
        if os.path.isfile(driver_path):
            self._chromedriver_path = driver_path
            return driver_path
        
        exe_path = os.path.join(os.path.dirname(driver_path), 'chromedriver.exe')
        if os.path.isfile(exe_path):
            self._chromedriver_path = exe_path
            return exe_path
        
        unix_path = os.path.join(os.path.dirname(driver_path), 'chromedriver')
        if os.path.isfile(unix_path):
            self._chromedriver_path = unix_path
            return unix_path
        
        raise Exception('Could not find a valid chromedriver executable')

    def create_driver(self):
        """Create a new Chrome driver instance"""
        try:
            driver_path = self.get_chromedriver_path()
            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=self.chrome_options)
            driver.set_page_load_timeout(self.page_load_timeout)
            driver.implicitly_wait(2)
            self.driver = driver
            logger.info("Chrome driver created successfully.")
            return driver
        except Exception as e:
            logger.error(f"Failed to create Chrome driver: {e}")
            raise

    def close_driver(self):
        """Close the Chrome driver"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                logger.info("Chrome driver closed.")
        except Exception as e:
            logger.warning(f"Exception while closing driver: {e}")
            self.driver = None

    def safe_get(self, url):
        """Safely navigate to URL with retry logic"""
        last_exc = None
        for attempt in range(2):
            try:
                if not self.driver:
                    self.create_driver()
                self.driver.get(url)
                return self.driver
            except Exception as e:
                last_exc = e
                logger.warning(f"Navigation error, restarting driver (attempt {attempt+1}): {e}")
                try:
                    self.close_driver()
                except Exception:
                    pass
                time.sleep(2)
        raise last_exc

    def exponential_backoff_wait(self, attempt):
        """Attente exponentielle entre les tentatives"""
        wait_time = min(2 ** attempt, 30)  # Max 30 secondes
        logger.info(f"Waiting {wait_time}s before retry...")
        time.sleep(wait_time)

    def get_wu_rate(self, entry):
        """Scrape Western Union exchange rate"""
        url = entry['url']
        currency = entry.get('currency', '')
        logger.info(f"Scraping WU: {entry['provider']} -> {url}")
        
        for attempt in range(self.max_retries):
            try:
                driver = self.safe_get(url)
                
                try:
                    driver.delete_all_cookies()
                except Exception:
                    pass
                
                time.sleep(3)
                
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span.fx-to, div.fx-to, [class*='fx-to']"))
                )
                
                selectors = ["span.fx-to", "div.fx-to", "[class*='fx-to']", "[class*='exchange-rate']"]
                
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            rate_text = elem.text.strip()
                            if rate_text and currency in rate_text:
                                logger.info(f"WU raw rate text: {rate_text}")
                                numbers = re.findall(r'[\d,\.]+', rate_text)
                                for num in numbers:
                                    try:
                                        rate = float(num.replace(',', '.'))
                                        if rate > 0 and rate < 1000:
                                            return rate
                                    except ValueError:
                                        continue
                    except NoSuchElementException:
                        continue
                
                screenshot_path = f"wu_debug_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                logger.warning(f"Could not find rate. Screenshot saved: {screenshot_path}")
                raise Exception("Could not extract WU rate")
                
            except Exception as e:
                logger.error(f"WU attempt {attempt+1}/{self.max_retries} error for {url}: {e}")
                if attempt < self.max_retries - 1:
                    self.exponential_backoff_wait(attempt)
                else:
                    self.close_driver()
                    
        raise Exception(f"Failed to get WesternUnion rate from {url}")

    def get_moneygram_rate(self, entry):
        """Scrape MoneyGram exchange rate - Enhanced for GitHub Actions"""
        url = entry['url']
        currency = entry.get('currency', '')
        logger.info(f"Scraping MoneyGram: {entry['provider']} -> {url}")
        
        for attempt in range(self.max_retries):
            try:
                driver = self.safe_get(url)
                
                try:
                    driver.delete_all_cookies()
                except Exception:
                    pass
                
                time.sleep(8)  # Longer wait for dynamic content
                
                try:
                    consent_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]"))
                    )
                    consent_btn.click()
                    logger.info("Clicked cookie consent button (MoneyGram).")
                    time.sleep(3)
                except Exception:
                    logger.debug("No cookie consent button found on MoneyGram.")
                
                # Wait for page to load completely
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                )
                
                time.sleep(8)  # Additional wait for dynamic content
                
                # Scroll to trigger any lazy loading
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(3)
                
                # Scroll back up to look for rate elements
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)
                
                # Wait a bit more for any dynamic content to load
                time.sleep(5)
                
                # Look for the specific exchange rate element
                try:
                    # First try XPath for the exact element structure
                    xpath_patterns = [
                        "//span[contains(text(), '1 EUR =') and contains(text(), 'TND')]",
                        "//span[contains(text(), '1 EUR =') and contains(text(), 'MAD')]",
                        "//span[contains(@class, 'text-mgSuccess-500') and contains(text(), '1 EUR =')]"
                    ]
                    
                    for xpath in xpath_patterns:
                        try:
                            elements = driver.find_elements(By.XPATH, xpath)
                            for elem in elements:
                                text = elem.text.strip()
                                if text and "1 EUR" in text and "=" in text and currency in text:
                                    logger.info(f"MoneyGram XPath found: {text}")
                                    match = re.search(r'1\s*EUR\s*=\s*([\d,\.]+)', text)
                                    if match:
                                        try:
                                            rate = float(match.group(1).replace(',', '.'))
                                            if rate > 0 and rate < 1000:
                                                logger.info(f"✓ MoneyGram rate found: {rate}")
                                                return rate
                                        except ValueError:
                                            continue
                        except Exception:
                            continue
                except Exception:
                    pass
                
                # Fallback: search all text elements
                all_elements = driver.find_elements(By.CSS_SELECTOR, "span, div, p")
                for elem in all_elements:
                    text = elem.text.strip()
                    if text and "1 EUR" in text and "=" in text and currency in text and "Send up to" not in text:
                        logger.info(f"MoneyGram found: {text}")
                        match = re.search(r'1\s*EUR\s*=\s*([\d,\.]+)', text)
                        if match:
                            try:
                                rate = float(match.group(1).replace(',', '.'))
                                if rate > 0 and rate < 1000:
                                    logger.info(f"✓ MoneyGram rate found: {rate}")
                                    return rate
                            except ValueError:
                                continue
                
                screenshot_path = f"moneygram_debug_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                logger.warning(f"Could not find MoneyGram rate. Screenshot: {screenshot_path}")
                raise Exception("Could not locate MoneyGram rate.")
                
            except Exception as e:
                logger.error(f"MoneyGram attempt {attempt+1}/{self.max_retries} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    self.exponential_backoff_wait(attempt)
                else:
                    self.close_driver()
                    
        raise Exception(f"Failed to get MoneyGram rate from {url}")

    def get_lemfi_rate(self, entry):
        """Scrape LemFi exchange rate"""
        url = entry['url']
        currency = entry.get('currency', '')
        logger.info(f"Scraping LemFi: {entry['provider']} -> {url}")
        
        for attempt in range(self.max_retries):
            try:
                driver = self.safe_get(url)
                
                try:
                    driver.delete_all_cookies()
                except Exception:
                    pass
                
                time.sleep(3)
                
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span, div, p"))
                )
                
                elems = driver.find_elements(By.CSS_SELECTOR, "span, div, p")
                
                for elem in elems:
                    text = elem.text.strip().replace('\xa0', ' ').replace('\u202f', ' ')
                    if text and ("1 EUR" in text or "1EUR" in text) and currency in text:
                        logger.info(f"LemFi candidate text: {text}")
                        match = re.search(r'1\s*EUR\s*=\s*([\d,.]+)\s*' + currency, text, re.IGNORECASE)
                        if match:
                            return float(match.group(1).replace(',', '.'))
                
                screenshot_path = f"lemfi_debug_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                logger.warning(f"Could not find LemFi rate. Screenshot: {screenshot_path}")
                raise Exception("Rate not found in LemFi DOM.")
                
            except Exception as e:
                logger.error(f"LemFi attempt {attempt+1}/{self.max_retries} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    self.exponential_backoff_wait(attempt)
                else:
                    self.close_driver()
                    
        raise Exception(f"Failed to get LemFi rate from {url}")

    def get_remitly_rate(self, entry):
        """Scrape Remitly exchange rate"""
        url = entry['url']
        currency = entry.get('currency', '')
        logger.info(f"Scraping Remitly: {entry['provider']} -> {url}")
        
        for attempt in range(self.max_retries):
            try:
                driver = self.safe_get(url)
                
                try:
                    driver.delete_all_cookies()
                except Exception:
                    pass
                
                time.sleep(3)
                
                WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div, span, p")))
                
                elems = driver.find_elements(By.CSS_SELECTOR, "div, span, p")
                
                for elem in elems:
                    text = elem.text.strip().replace('\xa0', ' ').replace('\u202f', ' ')
                    if "1 EUR" in text and currency in text:
                        logger.info(f"Remitly candidate text: {text}")
                        match = re.search(r'1\s*EUR\s*=\s*([\d,.]+)\s*' + currency, text, re.IGNORECASE)
                        if match:
                            return float(match.group(1).replace(',', '.'))
                
                screenshot_path = f"remitly_debug_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                logger.warning(f"Could not find Remitly rate. Screenshot: {screenshot_path}")
                raise Exception("Rate not found on Remitly page.")
                
            except Exception as e:
                logger.error(f"Remitly attempt {attempt+1}/{self.max_retries} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    self.exponential_backoff_wait(attempt)
                else:
                    self.close_driver()
                    
        raise Exception(f"Failed to get Remitly rate from {url}")

    def get_ria_rate(self, entry):
        """Scrape Ria exchange rate - AMÉLIORATION"""
        url = entry['url']
        currency = entry.get('currency', '')
        logger.info(f"Scraping Ria: {entry['provider']} -> {url}")
        
        for attempt in range(self.max_retries):
            try:
                driver = self.safe_get(url)
                
                try:
                    driver.delete_all_cookies()
                except Exception:
                    pass
                
                # Attente plus longue pour Ria
                time.sleep(5)
                
                # Attendre que la page soit complètement chargée
                WebDriverWait(driver, 40).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                )
                
                # Attendre spécifiquement les éléments de taux
                time.sleep(3)
                
                # Scrolling pour déclencher le chargement
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(2)
                
                # Chercher dans tous les éléments possibles
                all_elems = driver.find_elements(By.CSS_SELECTOR, "h3, p, div, span, strong, b")
                
                for elem in all_elems:
                    text = elem.text.strip().replace('\xa0', ' ').replace('\u202f', ' ')
                    if text and ("EUR" in text or "€" in text) and currency in text:
                        logger.info(f"Ria candidate text: {text}")
                        
                        # Pattern: 1 EUR = X.XX TND
                        match = re.search(r'1[.,]0*\s*EUR\s*=\s*([\d,.]+)\s*' + currency, text, re.IGNORECASE)
                        if match:
                            rate = float(match.group(1).replace(',', '.'))
                            logger.info(f"✓ Ria rate found: {rate}")
                            return rate
                        
                        # Pattern: 1€ = X.XX TND
                        match = re.search(r'1€\s*=\s*([\d,.]+)\s*' + currency, text, re.IGNORECASE)
                        if match:
                            rate = float(match.group(1).replace(',', '.'))
                            logger.info(f"✓ Ria rate found: {rate}")
                            return rate
                
                screenshot_path = f"ria_debug_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                logger.warning(f"Could not find Ria rate. Screenshot: {screenshot_path}")
                raise Exception("Rate not found on Ria page.")
                
            except Exception as e:
                logger.error(f"Ria attempt {attempt+1}/{self.max_retries} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    self.exponential_backoff_wait(attempt)
                else:
                    self.close_driver()
                    
        raise Exception(f"Failed to get Ria rate from {url}")

    def get_myeasytransfer_rate(self, entry):
        """Scrape MyEasyTransfer exchange rate"""
        url = entry['url']
        currency = entry.get('currency', '')
        logger.info(f"Scraping MyEasyTransfer: {entry['provider']} -> {url}")
        
        for attempt in range(self.max_retries):
            try:
                driver = self.safe_get(url)
                
                try:
                    driver.delete_all_cookies()
                except Exception:
                    pass
                
                time.sleep(3)
                
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div, span, p"))
                )
                
                elems = driver.find_elements(By.CSS_SELECTOR, "div.font-semibold, .font-semibold, div, span, p")
                
                for elem in elems:
                    text = elem.text.strip().replace('\xa0', ' ').replace('\u202f', ' ')
                    if currency in text:
                        logger.info(f"MyEasyTransfer candidate text: {text}")
                        numbers = re.findall(r'([\d,\.]+)', text)
                        for num in numbers:
                            try:
                                rate = float(num.replace(',', '.'))
                                if rate > 0 and rate < 1000:
                                    return rate
                            except ValueError:
                                continue
                
                screenshot_path = f"myeasytransfer_debug_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                logger.warning(f"Could not find MyEasyTransfer rate. Screenshot: {screenshot_path}")
                raise Exception("Rate not found on MyEasyTransfer page.")
                
            except Exception as e:
                logger.error(f"MyEasyTransfer attempt {attempt+1}/{self.max_retries} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    self.exponential_backoff_wait(attempt)
                else:
                    self.close_driver()
                    
        raise Exception(f"Failed to get MyEasyTransfer rate from {url}")

    def get_taptapsend_rate_multi_countries(self, url: str, currency: str) -> list:
        """Scrape TaptapSend rates for multiple countries - AMÉLIORATION"""
        # Mapping correct des codes pays TaptapSend (format: XX-EUR-ORIGIN)
        countries = [
            ('FR-EUR-ORIGIN', 'France'),
            ('DE-EUR-ORIGIN', 'Germany'),
            ('IT-EUR-ORIGIN', 'Italy'),
            ('BE-EUR-ORIGIN', 'Belgium'),
            ('ES-EUR-ORIGIN', 'Spain')
        ]
        
        results = []
        for country_code, country_name in countries:
            for attempt in range(self.max_retries):
                try:
                    rate = self.get_taptapsend_rate_for_country(url, currency, country_code, country_name)
                    results.append({
                        'currency_pair': f'EUR-{currency}',
                        'provider': 'TaptapSend',
                        'country': country_name,
                        'rate': rate
                    })
                    logger.info(f"✓ TaptapSend {country_name}: {rate}")
                    time.sleep(3)
                    break
                except Exception as e:
                    logger.error(f"TaptapSend {country_name} attempt {attempt+1}/{self.max_retries}: {e}")
                    if attempt < self.max_retries - 1:
                        self.exponential_backoff_wait(attempt)
                    else:
                        logger.error(f"✗ Failed to get TaptapSend rate for {country_name} after all retries")
        
        return results

    def get_taptapsend_rate_for_country(self, url: str, currency: str, country_code: str, country_name: str = "") -> float:
        """Scrape TaptapSend rate for a specific country - AMÉLIORATION"""
        driver = None
        try:
            driver_path = self.get_chromedriver_path()
            driver = webdriver.Chrome(service=Service(driver_path), options=self.chrome_options)
            driver.set_page_load_timeout(self.page_load_timeout)
            driver.get(url)
            
            wait = WebDriverWait(driver, 40)
            
            # Attente pour le chargement de la page
            time.sleep(4)
            
            # Attendre et sélectionner la devise d'origine
            origin_select = wait.until(EC.presence_of_element_located((By.ID, "origin-currency")))
            select_origin = Select(origin_select)
            
            # Sélectionner par valeur (format: FR-EUR-ORIGIN)
            logger.info(f"Selecting origin country: {country_code}")
            select_origin.select_by_value(country_code)
            time.sleep(3)
            
            # Attendre et sélectionner la devise de destination
            dest_select = wait.until(EC.presence_of_element_located((By.ID, "destination-currency")))
            select_dest = Select(dest_select)
            
            # Log les options de destination disponibles
            dest_options = [opt.get_attribute('value') for opt in select_dest.options]
            logger.info(f"Available destination options: {dest_options}")
            
            # Sélectionner la destination selon la devise
            if currency == "TND":
                # Chercher l'option Tunisia
                found = False
                for option in select_dest.options:
                    opt_value = option.get_attribute('value')
                    opt_text = option.text
                    if opt_value and ('TN-TND' in opt_value or 'tunisia' in opt_text.lower()):
                        logger.info(f"Selecting Tunisia option: {opt_value}")
                        select_dest.select_by_value(opt_value)
                        found = True
                        break
                if not found:
                    raise Exception(f"Cannot find Tunisia option in destination select")
                    
            elif currency == "MAD":
                # Chercher l'option Morocco
                found = False
                for option in select_dest.options:
                    opt_value = option.get_attribute('value')
                    opt_text = option.text
                    if opt_value and ('MA-MAD' in opt_value or 'morocco' in opt_text.lower()):
                        logger.info(f"Selecting Morocco option: {opt_value}")
                        select_dest.select_by_value(opt_value)
                        found = True
                        break
                if not found:
                    raise Exception(f"Cannot find Morocco option in destination select")
            else:
                raise Exception(f"Unsupported currency for TaptapSend: {currency}")
            
            # Attendre que le taux se charge après sélection
            time.sleep(5)
            
            # Chercher le taux dans l'élément #fxRateText
            try:
                rate_elem = wait.until(EC.presence_of_element_located((By.ID, "fxRateText")))
                text = rate_elem.text.strip()
                logger.info(f"TaptapSend {country_name} found fxRateText: {text}")
                
                if text and "=" in text and currency in text:
                    # Pattern: EUR 1 = X.XX TND ou 1 EUR = X.XX TND
                    # On cherche le nombre APRÈS le signe =
                    match = re.search(r'=\s*([\d,\.]+)', text)
                    if match:
                        rate = float(match.group(1).replace(',', '.'))
                        if rate > 0 and rate < 1000:
                            logger.info(f"✓ TaptapSend rate extracted: {rate}")
                            return rate
            except Exception as e:
                logger.warning(f"Could not find/parse fxRateText element: {e}")
            
            # Si pas trouvé, chercher dans tous les éléments visibles
            all_elems = driver.find_elements(By.CSS_SELECTOR, "div, span, p, h1, h2, h3, strong")
            for elem in all_elems:
                try:
                    text = elem.text.strip()
                    if text and len(text) < 100:  # Éviter les gros blocs de texte
                        # Chercher pattern avec EUR et la devise cible
                        if ("EUR" in text or "€" in text) and currency in text and ("=" in text or ":" in text):
                            logger.info(f"Found potential rate text: {text}")
                            # Extraire le nombre
                            match = re.search(r'([\d,\.]+)\s*' + currency, text)
                            if match:
                                rate = float(match.group(1).replace(',', '.'))
                                if rate > 0 and rate < 1000:
                                    logger.info(f"Extracted rate: {rate}")
                                    return rate
                except Exception:
                    continue
            
            # Screenshot pour debugging
            screenshot_path = f"taptapsend_{country_name}_{currency}_{int(time.time())}.png"
            driver.save_screenshot(screenshot_path)
            logger.warning(f"Could not find rate. Screenshot saved: {screenshot_path}")
            
            raise Exception(f"Could not extract rate for {country_name}")
            
        except Exception as e:
            logger.error(f"Error extracting rate from TaptapSend {country_name} {url}: {e}")
            if driver:
                # Save page source for debugging
                try:
                    with open(f"taptapsend_{country_name or country_code}_page.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    logger.info(f"Page source saved for debugging")
                except Exception:
                    pass
            raise
        finally:
            if driver:
                driver.quit()

    def get_sendwave_rate(self, entry):
        """Scrape Sendwave exchange rate"""
        url = entry['url']
        currency = entry.get('currency', '')
        logger.info(f"Scraping Sendwave: {entry['provider']} -> {url}")
        
        for attempt in range(self.max_retries):
            try:
                driver = self.safe_get(url)
                time.sleep(3)
                
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h6, div, span, p"))
                )
                
                elems = driver.find_elements(By.CSS_SELECTOR, "h6[data-testid='title-exchange-rate'], h6, div, span, p")
                
                for elem in elems:
                    text = elem.text.strip()
                    if currency in text and "=" in text:
                        logger.info(f"Sendwave candidate text: {text}")
                        match = re.search(r'=\s*([\d,\.]+)', text)
                        if match:
                            rate = float(match.group(1).replace(',', '.'))
                            return rate
                
                screenshot_path = f"sendwave_debug_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                logger.warning(f"Could not find Sendwave rate. Screenshot: {screenshot_path}")
                raise Exception("Rate not found on Sendwave page.")
                
            except Exception as e:
                logger.error(f"Sendwave attempt {attempt+1}/{self.max_retries} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    self.exponential_backoff_wait(attempt)
                else:
                    self.close_driver()
                    
        raise Exception(f"Failed to get Sendwave rate from {url}")

    def extract_country_from_provider(self, provider_name):
        """Extract country name from provider string"""
        if '(' in provider_name and ')' in provider_name:
            country = provider_name.split('(')[1].split(')')[0]
            return self.country_mapping.get(country, country)
        return "France"

    def scrape_and_save(self):
        """Main scraping function"""
        tz = pytz.timezone('Africa/Tunis')
        current_time = datetime.now(tz)
        results = []
        failed_scrapers = []
        
        # Scrape all currency pairs
        for entry in self.currency_pairs:
            provider = entry.get('provider', '')
            url = entry.get('url')
            currency = entry.get('currency', '')
            
            try:
                if provider.startswith('WesternUnion'):
                    rate = self.get_wu_rate(entry)
                elif provider.startswith('MoneyGram'):
                    rate = self.get_moneygram_rate(entry)
                elif provider.startswith('LemFi'):
                    rate = self.get_lemfi_rate(entry)
                elif provider.startswith('Remitly'):
                    rate = self.get_remitly_rate(entry)
                elif provider.startswith('Sendwave'):
                    rate = self.get_sendwave_rate(entry)
                else:
                    rate = self.get_wu_rate(entry)
                
                logger.info(f"✓ Scraped {entry['provider']} ({entry['pair']}) => {rate}")
                
                results.append({
                    'datetime': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'indice': current_time.strftime('%H:%M (Tunisia)'),
                    'currency_pair': entry['pair'],
                    'origin_provider': entry['provider'],
                    'url': url,
                    'rate': rate
                })
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"✗ Error scraping {entry.get('pair')} from {entry.get('provider')}: {e}")
                failed_scrapers.append(f"{entry.get('provider')} ({entry.get('pair')})")

        # Scrape additional providers
        european_countries = ['France', 'Germany', 'Italy', 'Belgium', 'Spain']
        
        # MyEasyTransfer
        try:
            logger.info("Scraping MyEasyTransfer TND...")
            myeasy_entry = {
                'pair': 'EUR-TND',
                'url': 'https://www.myeasytransfer.com/convertisseur-euro-dinar-tunisie',
                'provider': 'MyEasyTransfer (France)',
                'currency': 'TND'
            }
            myeasy_tnd_rate = self.get_myeasytransfer_rate(myeasy_entry)
            
            logger.info("Scraping MyEasyTransfer MAD...")
            myeasy_entry_mad = {
                'pair': 'EUR-MAD',
                'url': 'https://www.myeasytransfer.com/convertisseur-euro-mad-maroc',
                'provider': 'MyEasyTransfer (France)',
                'currency': 'MAD'
            }
            myeasy_mad_rate = self.get_myeasytransfer_rate(myeasy_entry_mad)
            
            for country in european_countries:
                results.append({
                    'datetime': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'indice': current_time.strftime('%H:%M (Tunisia)'),
                    'currency_pair': 'EUR-TND',
                    'origin_provider': f'MyEasyTransfer ({country})',
                    'url': myeasy_entry['url'],
                    'rate': myeasy_tnd_rate
                })
                results.append({
                    'datetime': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'indice': current_time.strftime('%H:%M (Tunisia)'),
                    'currency_pair': 'EUR-MAD',
                    'origin_provider': f'MyEasyTransfer ({country})',
                    'url': myeasy_entry_mad['url'],
                    'rate': myeasy_mad_rate
                })
        except Exception as e:
            logger.error(f"✗ Error adding MyEasyTransfer rates: {e}")
            failed_scrapers.append("MyEasyTransfer")
        
        # Ria TND
        try:
            logger.info("Scraping Ria TND...")
            ria_entry_tnd = {
                'pair': 'EUR-TND',
                'url': 'https://www.riamoneytransfer.com/fr-fr/rates-conversion/?From=EUR&To=TND&Amount=1',
                'provider': 'Ria (France)',
                'currency': 'TND'
            }
            ria_tnd_rate = self.get_ria_rate(ria_entry_tnd)
            
            for country in european_countries:
                results.append({
                    'datetime': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'indice': current_time.strftime('%H:%M (Tunisia)'),
                    'currency_pair': 'EUR-TND',
                    'origin_provider': f'Ria ({country})',
                    'url': ria_entry_tnd['url'],
                    'rate': ria_tnd_rate
                })
        except Exception as e:
            logger.error(f"✗ Error adding Ria TND rates: {e}")
            failed_scrapers.append("Ria (TND)")
        
        # Ria MAD
        try:
            logger.info("Scraping Ria MAD...")
            ria_entry_mad = {
                'pair': 'EUR-MAD',
                'url': 'https://www.riamoneytransfer.com/fr-fr/rates-conversion/?From=EUR&To=MAD&Amount=1',
                'provider': 'Ria (France)',
                'currency': 'MAD'
            }
            ria_mad_rate = self.get_ria_rate(ria_entry_mad)
            
            for country in european_countries:
                results.append({
                    'datetime': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'indice': current_time.strftime('%H:%M (Tunisia)'),
                    'currency_pair': 'EUR-MAD',
                    'origin_provider': f'Ria ({country})',
                    'url': ria_entry_mad['url'],
                    'rate': ria_mad_rate
                })
        except Exception as e:
            logger.error(f"✗ Error adding Ria MAD rates: {e}")
            failed_scrapers.append("Ria (MAD)")
        
        # TaptapSend
        try:
            logger.info("Scraping TaptapSend...")
            taptap_url = 'https://www.taptapsend.com/'
            taptap_tnd_results = self.get_taptapsend_rate_multi_countries(taptap_url, 'TND')
            taptap_mad_results = self.get_taptapsend_rate_multi_countries(taptap_url, 'MAD')
            
            for taptap_result in taptap_tnd_results:
                results.append({
                    'datetime': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'indice': current_time.strftime('%H:%M (Tunisia)'),
                    'currency_pair': 'EUR-TND',
                    'origin_provider': f"TaptapSend ({taptap_result['country']})",
                    'url': taptap_url,
                    'rate': taptap_result['rate']
                })
            
            for taptap_result in taptap_mad_results:
                results.append({
                    'datetime': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'indice': current_time.strftime('%H:%M (Tunisia)'),
                    'currency_pair': 'EUR-MAD',
                    'origin_provider': f"TaptapSend ({taptap_result['country']})",
                    'url': taptap_url,
                    'rate': taptap_result['rate']
                })
            
            if not taptap_tnd_results and not taptap_mad_results:
                failed_scrapers.append("TaptapSend (all countries)")
                
        except Exception as e:
            logger.error(f"✗ Error adding TaptapSend rates: {e}")
            failed_scrapers.append("TaptapSend")

        # Organize results and send email
        if results:
            organized_results = {}
            
            for r in results:
                pair = r['currency_pair']
                country = self.extract_country_from_provider(r['origin_provider'])
                
                if pair not in organized_results:
                    organized_results[pair] = {}
                if country not in organized_results[pair]:
                    organized_results[pair][country] = {}
                
                provider_name = r['origin_provider'].split(' (')[0] if ' (' in r['origin_provider'] else r['origin_provider']
                organized_results[pair][country][provider_name] = r['rate']
            
            # Build email body
            mail_body = f"Hello,\n\nAttached below is the table containing the exchange rates scraped for today ({current_time.strftime('%Y-%m-%d %H:%M:%S')}):\n\n"
            

            
            provider_order = ['WesternUnion', 'MoneyGram', 'LemFi', 'Remitly', 'Ria', 'Sendwave', 'TaptapSend', 'MyEasyTransfer']
            country_order = ['France', 'Germany', 'Italy', 'Belgium', 'Spain']
            currency_order = ['EUR-TND', 'EUR-MAD']
            
            for pair in currency_order:
                if pair in organized_results:
                    mail_body += f"=== {pair} ===\n\n"
                    
                    for country in country_order:
                        mail_body += f"--- {country} ---\n"
                        
                        for provider_name in provider_order:
                            if country in organized_results[pair] and provider_name in organized_results[pair][country]:
                                rate = organized_results[pair][country][provider_name]
                                mail_body += f"  {provider_name}: {rate}\n"
                            else:
                                mail_body += f"  {provider_name}: N/A\n"
                        
                        mail_body += "\n"
                    
                    mail_body += "\n"
            
            mail_body += "Regards,\nExchange Rate Bot\n\nThis is an automated message."
            
            # Send email
            self.send_email_without_attachment(
                to_email=[
                    "ikbelghrab13@gmail.com",
                    # "nouha@myeasytransfer.com",
                    # "selim.maaoui@myeasytransfer.com",
                    # "ismail.khenissi@myeasytransfer.com",
                    # "jabrane.khenissi@myeasytransfer.com"
                ],
                subject=f"Exchange Rates -- {current_time.strftime('%Y-%m-%d %H:%M:%S')}",
                body=mail_body
            )
        else:
            logger.warning("No results were collected. No email sent.")
        
        self.close_driver()

    def send_email_without_attachment(self, to_email, subject, body):
        """Send email via Gmail SMTP"""
        sender_email = os.environ.get("SENDER_EMAIL")
        app_password = os.environ.get("EMAIL_APP_PASSWORD")
        
        if not sender_email or not app_password:
            logger.error("SENDER_EMAIL and EMAIL_APP_PASSWORD must be set in environment variables to send email.")
            return
        
        msg = EmailMessage()
        msg["From"] = sender_email
        
        if isinstance(to_email, list):
            msg["To"] = ", ".join(to_email)
        else:
            msg["To"] = to_email
        
        msg["Subject"] = subject
        msg.set_content(body)
        
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(sender_email, app_password)
                smtp.send_message(msg)
            logger.info(f"✓ Email sent successfully to {msg['To']}")
        except Exception as e:
            logger.error(f"✗ Failed to send email: {e}")

    def run_once(self):
        """Run the scraper once"""
        logger.info("="*60)
        logger.info("Starting scrape run...")
        logger.info("="*60)
        
        try:
            self.scrape_and_save()
            logger.info("="*60)
            logger.info("Scrape run completed successfully!")
            logger.info("="*60)
        except Exception as e:
            logger.error(f"Unexpected error during scraping run: {e}")
        finally:
            self.close_driver()


def main():
    try:
        scraper = ExchangeRatesScraper(reuse_driver=True)
        scraper.run_once()
    except KeyboardInterrupt:
        logger.info("Scraper interrupted by user.")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")


if __name__ == "__main__":
    main()
