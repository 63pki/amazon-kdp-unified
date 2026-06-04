"""KDP publishing automation agent for direct Amazon publishing."""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


@dataclass
class KDPBookMetadata:
    """Metadata for KDP book publishing."""
    
    title: str
    subtitle: Optional[str] = None
    series_name: Optional[str] = None
    series_number: Optional[int] = None
    description: str = ""
    keywords: List[str] = None
    categories: List[str] = None
    language: str = "English"
    
    # Publishing details
    author_name: str = ""
    contributors: List[Dict[str, str]] = None  # [{"name": "...", "role": "..."}]
    
    # Pricing and rights
    price: float = 4.99
    territories: List[str] = None  # ["US", "CA", "GB", etc.]
    drm_protection: bool = False
    
    # Age and content ratings
    age_range: Optional[str] = None  # "6-8", "9-12", etc.
    content_warning: bool = False
    
    # Publication options
    pre_order: bool = False
    publication_date: Optional[str] = None  # "YYYY-MM-DD"
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.categories is None:
            self.categories = []
        if self.contributors is None:
            self.contributors = []
        if self.territories is None:
            self.territories = ["US", "CA", "GB", "AU"]


@dataclass
class KDPUploadFiles:
    """Files required for KDP upload."""
    
    manuscript_file: Path  # PDF or DOCX
    cover_file: Path       # JPEG, PNG, or PDF
    
    # Optional files
    preview_file: Optional[Path] = None
    enhanced_typesetting: bool = True


@dataclass
class PublishingResult:
    """Result of publishing attempt."""
    
    success: bool
    asin: Optional[str] = None
    kdp_url: Optional[str] = None
    status: str = ""  # "Live", "In Review", "Draft", "Blocked"
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class KDPPublishingConfig(BaseModel):
    """Configuration for KDP publishing automation."""
    
    # Amazon credentials (stored securely)
    amazon_email: str = Field(description="Amazon account email")
    amazon_password: str = Field(description="Amazon account password")
    
    # Browser automation settings
    headless: bool = Field(default=False, description="Run browser in headless mode")
    timeout: int = Field(default=30, description="Timeout for web elements")
    implicit_wait: int = Field(default=10, description="Implicit wait time")
    
    # Upload settings
    max_upload_retries: int = Field(default=3, description="Maximum upload retries")
    upload_timeout: int = Field(default=300, description="Upload timeout in seconds")
    
    # Default publishing options
    default_price: float = Field(default=4.99, description="Default book price")
    default_territories: List[str] = Field(
        default=["US", "CA", "GB", "AU"], 
        description="Default territories to publish in"
    )
    auto_pricing: bool = Field(default=True, description="Enable automatic pricing suggestions")
    
    # Quality checks
    validate_before_upload: bool = Field(default=True, description="Validate files before upload")
    require_isbn: bool = Field(default=False, description="Require ISBN for publishing")


class KDPPublishingAgent:
    """Agent for automating Amazon KDP book publishing."""
    
    def __init__(self, config: KDPPublishingConfig):
        """Initialize the KDP publishing agent.
        
        Args:
            config: KDP publishing configuration
        """
        self.config = config
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.logged_in = False
        
    async def setup_browser(self) -> None:
        """Setup Chrome browser with appropriate options."""
        chrome_options = Options()
        
        if self.config.headless:
            chrome_options.add_argument("--headless")
        
        # Additional Chrome options for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        # File upload handling
        prefs = {
            "download.default_directory": str(Path.cwd()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(self.config.implicit_wait)
            self.wait = WebDriverWait(self.driver, self.config.timeout)
            
            logger.info("Browser setup completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup browser: {e}")
            raise
    
    async def login_to_kdp(self) -> bool:
        """Login to Amazon KDP."""
        if self.logged_in:
            return True
        
        try:
            logger.info("Logging into Amazon KDP...")
            
            # Navigate to KDP login
            self.driver.get("https://kdp.amazon.com/en_US/signin")
            
            # Wait for email field and enter email
            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "ap_email"))
            )
            email_field.clear()
            email_field.send_keys(self.config.amazon_email)
            
            # Click continue
            continue_btn = self.driver.find_element(By.ID, "continue")
            continue_btn.click()
            
            # Wait for password field and enter password
            password_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "ap_password"))
            )
            password_field.clear()
            password_field.send_keys(self.config.amazon_password)
            
            # Click sign in
            signin_btn = self.driver.find_element(By.ID, "signInSubmit")
            signin_btn.click()
            
            # Check for 2FA or CAPTCHA
            await self._handle_login_challenges()
            
            # Verify login success
            self.wait.until(
                EC.any_of(
                    EC.url_contains("kdp.amazon.com/en_US/bookshelf"),
                    EC.presence_of_element_located((By.CLASS_NAME, "kdp-bookshelf"))
                )
            )
            
            self.logged_in = True
            logger.info("Successfully logged into KDP")
            return True
            
        except TimeoutException:
            logger.error("Login timeout - please check credentials or handle 2FA manually")
            return False
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    async def publish_book(
        self, 
        metadata: KDPBookMetadata,
        files: KDPUploadFiles
    ) -> PublishingResult:
        """Publish a book to Amazon KDP.
        
        Args:
            metadata: Book metadata
            files: Upload files
            
        Returns:
            Publishing result
        """
        logger.info(f"Starting publication of '{metadata.title}'")
        
        try:
            # Validate files if required
            if self.config.validate_before_upload:
                validation_result = await self._validate_files(files)
                if not validation_result["valid"]:
                    return PublishingResult(
                        success=False,
                        error_message=f"File validation failed: {validation_result['errors']}"
                    )
            
            # Setup browser if not already done
            if not self.driver:
                await self.setup_browser()
            
            # Login if not already logged in
            if not await self.login_to_kdp():
                return PublishingResult(
                    success=False,
                    error_message="Failed to login to KDP"
                )
            
            # Create new book
            book_url = await self._create_new_book()
            if not book_url:
                return PublishingResult(
                    success=False,
                    error_message="Failed to create new book"
                )
            
            # Fill in book details
            details_success = await self._fill_book_details(metadata)
            if not details_success:
                return PublishingResult(
                    success=False,
                    error_message="Failed to fill book details"
                )
            
            # Upload manuscript and cover
            upload_success = await self._upload_files(files)
            if not upload_success:
                return PublishingResult(
                    success=False,
                    error_message="Failed to upload files"
                )
            
            # Set pricing and territories
            pricing_success = await self._set_pricing_and_territories(metadata)
            if not pricing_success:
                return PublishingResult(
                    success=False,
                    error_message="Failed to set pricing"
                )
            
            # Submit for publishing
            submit_result = await self._submit_for_publishing()
            
            return submit_result
            
        except Exception as e:
            logger.error(f"Publishing failed: {e}")
            return PublishingResult(
                success=False,
                error_message=str(e)
            )
    
    async def update_book_metadata(
        self, 
        asin: str, 
        metadata: KDPBookMetadata
    ) -> PublishingResult:
        """Update existing book metadata.
        
        Args:
            asin: Amazon ASIN of the book
            metadata: Updated metadata
            
        Returns:
            Update result
        """
        logger.info(f"Updating metadata for ASIN: {asin}")
        
        try:
            # Navigate to book edit page
            edit_url = f"https://kdp.amazon.com/en_US/title-setup/paperback/{asin}"
            self.driver.get(edit_url)
            
            # Wait for page to load
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "a-form-label"))
            )
            
            # Update metadata fields
            await self._fill_book_details(metadata, is_update=True)
            
            # Save changes
            save_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Save')]")
            save_btn.click()
            
            # Wait for save confirmation
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "a-alert-success"))
            )
            
            return PublishingResult(
                success=True,
                asin=asin,
                status="Updated"
            )
            
        except Exception as e:
            logger.error(f"Update failed: {e}")
            return PublishingResult(
                success=False,
                error_message=str(e)
            )
    
    async def get_book_status(self, asin: str) -> Dict[str, Any]:
        """Get current status of a published book.
        
        Args:
            asin: Amazon ASIN of the book
            
        Returns:
            Book status information
        """
        try:
            # Navigate to bookshelf
            self.driver.get("https://kdp.amazon.com/en_US/bookshelf")
            
            # Search for book by ASIN or title
            search_box = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "search-input"))
            )
            search_box.clear()
            search_box.send_keys(asin)
            search_box.send_keys(Keys.RETURN)
            
            # Wait for search results
            time.sleep(3)
            
            # Extract book status
            book_row = self.driver.find_element(
                By.XPATH, f"//tr[contains(@data-asin, '{asin}')]"
            )
            
            status_element = book_row.find_element(By.CLASS_NAME, "status")
            status = status_element.text.strip()
            
            # Extract additional details
            sales_element = book_row.find_element(By.CLASS_NAME, "sales-data")
            sales_data = sales_element.text.strip() if sales_element else "N/A"
            
            return {
                "asin": asin,
                "status": status,
                "sales_data": sales_data,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get book status: {e}")
            return {
                "asin": asin,
                "status": "Unknown",
                "error": str(e)
            }
    
    async def batch_publish_series(
        self, 
        books: List[tuple[KDPBookMetadata, KDPUploadFiles]]
    ) -> List[PublishingResult]:
        """Publish multiple books in a series.
        
        Args:
            books: List of (metadata, files) tuples
            
        Returns:
            List of publishing results
        """
        logger.info(f"Starting batch publication of {len(books)} books")
        
        results = []
        
        for i, (metadata, files) in enumerate(books, 1):
            logger.info(f"Publishing book {i}/{len(books)}: {metadata.title}")
            
            result = await self.publish_book(metadata, files)
            results.append(result)
            
            if not result.success:
                logger.error(f"Failed to publish book {i}: {result.error_message}")
                
                # Option to continue or stop on first failure
                # For now, continue with remaining books
                continue
            
            # Add delay between publications to avoid rate limiting
            await asyncio.sleep(5)
        
        # Summary
        successful = sum(1 for r in results if r.success)
        logger.info(f"Batch publication completed: {successful}/{len(books)} successful")
        
        return results
    
    async def _handle_login_challenges(self) -> None:
        """Handle 2FA, CAPTCHA, or other login challenges."""
        try:
            # Check for 2FA
            if self.driver.find_elements(By.ID, "auth-mfa-otpcode"):
                logger.warning("2FA detected - manual intervention required")
                # In a real implementation, you might integrate with SMS services
                # or provide a way for users to input the code
                input("Please complete 2FA manually and press Enter to continue...")
            
            # Check for CAPTCHA
            if self.driver.find_elements(By.ID, "captchacharacters"):
                logger.warning("CAPTCHA detected - manual intervention required")
                input("Please complete CAPTCHA manually and press Enter to continue...")
            
            # Wait a bit for any redirects
            time.sleep(2)
            
        except Exception as e:
            logger.warning(f"Error handling login challenges: {e}")
    
    async def _validate_files(self, files: KDPUploadFiles) -> Dict[str, Any]:
        """Validate upload files meet KDP requirements."""
        errors = []
        warnings = []
        
        # Check manuscript file
        if not files.manuscript_file.exists():
            errors.append(f"Manuscript file not found: {files.manuscript_file}")
        else:
            # Check file size (max 50MB for KDP)
            size_mb = files.manuscript_file.stat().st_size / (1024 * 1024)
            if size_mb > 50:
                errors.append(f"Manuscript file too large: {size_mb:.1f}MB (max 50MB)")
            
            # Check file format
            allowed_formats = ['.pdf', '.doc', '.docx']
            if files.manuscript_file.suffix.lower() not in allowed_formats:
                errors.append(f"Invalid manuscript format: {files.manuscript_file.suffix}")
        
        # Check cover file
        if not files.cover_file.exists():
            errors.append(f"Cover file not found: {files.cover_file}")
        else:
            # Check file size (max 10MB for covers)
            size_mb = files.cover_file.stat().st_size / (1024 * 1024)
            if size_mb > 10:
                errors.append(f"Cover file too large: {size_mb:.1f}MB (max 10MB)")
            
            # Check file format
            allowed_formats = ['.jpg', '.jpeg', '.png', '.pdf']
            if files.cover_file.suffix.lower() not in allowed_formats:
                errors.append(f"Invalid cover format: {files.cover_file.suffix}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def _create_new_book(self) -> Optional[str]:
        """Create a new book in KDP and return the edit URL."""
        try:
            # Navigate to create new title
            self.driver.get("https://kdp.amazon.com/en_US/title-setup/kindle")
            
            # Wait for the page to load
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "a-button-primary"))
            )
            
            # Click "Create New Title" or similar button
            create_btn = self.driver.find_element(
                By.XPATH, "//button[contains(text(), 'Create') or contains(text(), 'New')]"
            )
            create_btn.click()
            
            # Wait for redirect to edit page
            self.wait.until(
                EC.url_contains("title-setup")
            )
            
            return self.driver.current_url
            
        except Exception as e:
            logger.error(f"Failed to create new book: {e}")
            return None
    
    async def _fill_book_details(
        self, 
        metadata: KDPBookMetadata, 
        is_update: bool = False
    ) -> bool:
        """Fill in book details form."""
        try:
            # Title
            title_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "title"))
            )
            if not is_update:
                title_field.clear()
            title_field.send_keys(metadata.title)
            
            # Subtitle (if present)
            if metadata.subtitle:
                subtitle_field = self.driver.find_element(By.NAME, "subtitle")
                subtitle_field.clear()
                subtitle_field.send_keys(metadata.subtitle)
            
            # Series information
            if metadata.series_name:
                series_field = self.driver.find_element(By.NAME, "series_title")
                series_field.clear()
                series_field.send_keys(metadata.series_name)
                
                if metadata.series_number:
                    series_num_field = self.driver.find_element(By.NAME, "series_number")
                    series_num_field.clear()
                    series_num_field.send_keys(str(metadata.series_number))
            
            # Author
            author_field = self.driver.find_element(By.NAME, "author")
            author_field.clear()
            author_field.send_keys(metadata.author_name)
            
            # Description
            description_field = self.driver.find_element(By.NAME, "description")
            description_field.clear()
            description_field.send_keys(metadata.description)
            
            # Keywords
            if metadata.keywords:
                keyword_fields = self.driver.find_elements(By.CSS_SELECTOR, "input[name*='keyword']")
                for i, keyword in enumerate(metadata.keywords[:len(keyword_fields)]):
                    keyword_fields[i].clear()
                    keyword_fields[i].send_keys(keyword)
            
            # Categories
            if metadata.categories:
                # This would involve navigating the category selection process
                await self._select_categories(metadata.categories)
            
            # Language
            language_dropdown = Select(self.driver.find_element(By.NAME, "language"))
            language_dropdown.select_by_visible_text(metadata.language)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to fill book details: {e}")
            return False
    
    async def _upload_files(self, files: KDPUploadFiles) -> bool:
        """Upload manuscript and cover files."""
        try:
            # Upload manuscript
            manuscript_upload = self.driver.find_element(
                By.CSS_SELECTOR, "input[type='file'][accept*='pdf']"
            )
            manuscript_upload.send_keys(str(files.manuscript_file.absolute()))
            
            # Wait for manuscript upload to complete
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "upload-success"))
            )
            
            # Upload cover
            cover_upload = self.driver.find_element(
                By.CSS_SELECTOR, "input[type='file'][accept*='image']"
            )
            cover_upload.send_keys(str(files.cover_file.absolute()))
            
            # Wait for cover upload to complete
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "cover-preview"))
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload files: {e}")
            return False
    
    async def _set_pricing_and_territories(self, metadata: KDPBookMetadata) -> bool:
        """Set book pricing and territories."""
        try:
            # Navigate to pricing page
            next_btn = self.driver.find_element(
                By.XPATH, "//button[contains(text(), 'Next') or contains(text(), 'Continue')]"
            )
            next_btn.click()
            
            # Wait for pricing page
            self.wait.until(
                EC.presence_of_element_located((By.NAME, "list_price"))
            )
            
            # Set price
            price_field = self.driver.find_element(By.NAME, "list_price")
            price_field.clear()
            price_field.send_keys(str(metadata.price))
            
            # Select territories
            for territory in metadata.territories:
                try:
                    territory_checkbox = self.driver.find_element(
                        By.CSS_SELECTOR, f"input[value='{territory}']"
                    )
                    if not territory_checkbox.is_selected():
                        territory_checkbox.click()
                except NoSuchElementException:
                    logger.warning(f"Territory {territory} not found")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set pricing: {e}")
            return False
    
    async def _submit_for_publishing(self) -> PublishingResult:
        """Submit book for publishing."""
        try:
            # Click publish button
            publish_btn = self.driver.find_element(
                By.XPATH, "//button[contains(text(), 'Publish')]"
            )
            publish_btn.click()
            
            # Wait for confirmation
            self.wait.until(
                EC.any_of(
                    EC.presence_of_element_located((By.CLASS_NAME, "success-message")),
                    EC.presence_of_element_located((By.CLASS_NAME, "error-message"))
                )
            )
            
            # Check for success or error
            if self.driver.find_elements(By.CLASS_NAME, "success-message"):
                # Extract ASIN if available
                asin = self._extract_asin_from_page()
                
                return PublishingResult(
                    success=True,
                    asin=asin,
                    kdp_url=self.driver.current_url,
                    status="In Review"
                )
            else:
                error_msg = self.driver.find_element(By.CLASS_NAME, "error-message").text
                return PublishingResult(
                    success=False,
                    error_message=error_msg
                )
            
        except Exception as e:
            logger.error(f"Failed to submit for publishing: {e}")
            return PublishingResult(
                success=False,
                error_message=str(e)
            )
    
    def _extract_asin_from_page(self) -> Optional[str]:
        """Extract ASIN from current page if available."""
        try:
            # Look for ASIN in URL
            url = self.driver.current_url
            if "/title/" in url:
                asin = url.split("/title/")[1].split("/")[0]
                return asin
            
            # Look for ASIN in page content
            asin_elements = self.driver.find_elements(
                By.XPATH, "//*[contains(text(), 'ASIN')]"
            )
            for element in asin_elements:
                text = element.text
                # Extract ASIN pattern (10 characters, alphanumeric)
                import re
                match = re.search(r'ASIN[:\s]*([A-Z0-9]{10})', text)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract ASIN: {e}")
            return None
    
    async def close(self):
        """Clean up browser resources."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.logged_in = False
    
    def __del__(self):
        """Ensure browser is closed on cleanup."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass