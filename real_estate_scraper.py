import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import os
from typing import Dict, List, Set
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define Miami ZIP codes of interest
MIAMI_ZIP_CODES = {
    '33125': 'Little Havana',
    '33127': 'Design District/Midtown',
    '33128': 'Downtown Miami',
    '33130': 'Brickell',
    '33131': 'Brickell/Downtown',
    '33132': 'Downtown Miami/Port of Miami',
    '33133': 'Coconut Grove',
    '33134': 'Coral Gables',
    '33135': 'Little Havana/West Miami',
    '33136': 'Overtown/Health District',
    '33137': 'Design District/Upper Eastside',
    '33138': 'Upper Eastside/Miami Shores'
}

class RealEstateScraper:
    def __init__(self):
        # Add your default headers to mimic a real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Initialize filters
        self.filters = {
            'min_price': None,
            'max_price': None,
            'min_bedrooms': None,
            'max_bedrooms': None,
            'property_type': None,
            'zip_codes': set(),  # Set of allowed ZIP codes
            'wheelchair_accessible': False,
            'section_8_accepted': False,
            'min_sqft': None,
            'max_sqft': None
        }
        
        # Create directory for saving results
        self.results_dir = 'scraping_results'
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)

    def set_filters(self, **kwargs):
        """Set search filters"""
        for key, value in kwargs.items():
            if key in self.filters:
                if key == 'zip_codes' and isinstance(value, (list, set)):
                    self.filters[key] = set(str(zip_code) for zip_code in value)
                else:
                    self.filters[key] = value
            else:
                logger.warning(f"Unknown filter: {key}")

    def build_search_url(self) -> str:
        """Build the search URL based on filters"""
        # This is a placeholder - you'll need to modify this based on the website you're scraping
        base_url = "https://example-real-estate-site.com/search?"
        params = []
        
        # Add ZIP codes as location parameter
        if self.filters['zip_codes']:
            zip_codes_str = ",".join(self.filters['zip_codes'])
            params.append(f"zip_codes={zip_codes_str}")
        
        if self.filters['min_price']:
            params.append(f"price_from={self.filters['min_price']}")
        if self.filters['max_price']:
            params.append(f"price_to={self.filters['max_price']}")
        if self.filters['wheelchair_accessible']:
            params.append("wheelchair=true")
        if self.filters['section_8_accepted']:
            params.append("section8=true")
        
        return base_url + "&".join(params)

    def is_wheelchair_accessible(self, soup: BeautifulSoup) -> bool:
        """Check if the listing is wheelchair accessible"""
        # Modify these selectors based on the website's structure
        accessibility_indicators = [
            'wheelchair accessible',
            'ada compliant',
            'handicap accessible',
            'accessible unit',
            'accessibility features'
        ]
        
        description = soup.find('div', class_='description')
        if description:
            text = description.text.lower()
            return any(indicator in text for indicator in accessibility_indicators)
        return False

    def accepts_section_8(self, soup: BeautifulSoup) -> bool:
        """Check if the listing accepts Section 8"""
        # Modify these selectors based on the website's structure
        section8_indicators = [
            'section 8',
            'section 8 accepted',
            'section 8 welcome',
            'housing choice voucher',
            'hcv welcome'
        ]
        
        description = soup.find('div', class_='description')
        if description:
            text = description.text.lower()
            return any(indicator in text for indicator in section8_indicators)
        return False

    def scrape_listing(self, url: str) -> Dict:
        """Scrape a single listing"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check if listing matches our accessibility and Section 8 requirements
            if (self.filters['wheelchair_accessible'] and not self.is_wheelchair_accessible(soup)) or \
               (self.filters['section_8_accepted'] and not self.accepts_section_8(soup)):
                return None
            
            # This is a placeholder - modify according to the website's HTML structure
            listing_data = {
                'title': soup.find('h1', class_='listing-title').text.strip(),
                'price': soup.find('div', class_='price').text.strip(),
                'bedrooms': soup.find('span', class_='bedrooms').text.strip(),
                'bathrooms': soup.find('span', class_='bathrooms').text.strip(),
                'sqft': soup.find('span', class_='sqft').text.strip(),
                'address': soup.find('div', class_='address').text.strip(),
                'zip_code': self.extract_zip_code(soup),
                'wheelchair_accessible': self.is_wheelchair_accessible(soup),
                'section_8_accepted': self.accepts_section_8(soup),
                'description': soup.find('div', class_='description').text.strip(),
                'url': url
            }
            
            # Check if the listing is in our desired ZIP codes
            if self.filters['zip_codes'] and listing_data['zip_code'] not in self.filters['zip_codes']:
                return None
                
            return listing_data
        except Exception as e:
            logger.error(f"Error scraping listing {url}: {str(e)}")
            return None

    def extract_zip_code(self, soup: BeautifulSoup) -> str:
        """Extract ZIP code from the listing"""
        # Modify this according to the website's HTML structure
        address = soup.find('div', class_='address')
        if address:
            # This is a simple example - modify based on actual address format
            text = address.text.strip()
            # Look for 5-digit ZIP code
            import re
            zip_match = re.search(r'\b(\d{5})\b', text)
            if zip_match:
                return zip_match.group(1)
        return ""

    def scrape_listings(self, max_pages: int = 5) -> List[Dict]:
        """Scrape multiple listings based on filters"""
        all_listings = []
        
        for page in range(1, max_pages + 1):
            try:
                url = self.build_search_url() + f"&page={page}"
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all listing URLs on the page
                # Modify this according to the website's HTML structure
                listing_urls = [a['href'] for a in soup.find_all('a', class_='listing-link')]
                
                for url in listing_urls:
                    listing_data = self.scrape_listing(url)
                    if listing_data:
                        all_listings.append(listing_data)
                        
                # Respect the website's rate limiting
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error scraping page {page}: {str(e)}")
                break
                
        return all_listings

    def save_results(self, listings: List[Dict]):
        """Save scraped listings to CSV"""
        if not listings:
            logger.warning("No listings to save")
            return
            
        df = pd.DataFrame(listings)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.results_dir}/miami_listings_{timestamp}.csv"
        df.to_csv(filename, index=False)
        logger.info(f"Results saved to {filename}")

def main():
    # Initialize scraper
    scraper = RealEstateScraper()
    
    # Set your filters
    scraper.set_filters(
        min_price=1000,  # Minimum monthly rent
        max_price=3000,  # Maximum monthly rent
        min_bedrooms=1,
        max_bedrooms=3,
        property_type="apartment",
        zip_codes=MIAMI_ZIP_CODES.keys(),  # Use predefined Miami ZIP codes
        wheelchair_accessible=True,
        section_8_accepted=True,
        min_sqft=600,
        max_sqft=1500
    )
    
    # Scrape listings
    logger.info("Starting scraping process...")
    logger.info(f"Searching in ZIP codes: {', '.join(MIAMI_ZIP_CODES.keys())}")
    listings = scraper.scrape_listings(max_pages=10)  # Increased pages to find more matches
    
    # Save results
    scraper.save_results(listings)
    logger.info(f"Scraping completed! Found {len(listings)} matching listings")

if __name__ == "__main__":
    main() 