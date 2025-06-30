import asyncio
import logging
import os
import pytest
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestSignIn:
    """Test class for sign-in functionality"""
    
    @pytest.mark.asyncio
    async def test_sign_in_flow(self):
        """
        Test the sign-in flow by:
        1. Navigating to localhost:5000
        2. Clicking the Sign In button
        3. Entering username in the #username field
        4. Clicking the #submit button
        """
        # Get username from environment variable
        username = os.getenv('TEST_USERNAME')
        if not username:
            pytest.fail("TEST_USERNAME environment variable is required")
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to the main page
            logger.info("Navigating to localhost:5000...")
            await page.goto("http://localhost:5000", timeout=30000)
            
            # Wait for and click the Sign In button
            logger.info("Looking for Sign In button...")
            sign_in_button = page.locator('[data-test-sign-in-button]')
            await sign_in_button.wait_for(timeout=10000)
            await sign_in_button.click()
            
            # Wait for navigation to sign-in page
            logger.info("Waiting for sign-in page to load...")
            await page.wait_for_load_state('networkidle')
            
            # Enter username
            logger.info(f"Entering username: {username}")
            username_field = page.locator('#username')
            await username_field.wait_for(timeout=10000)
            await username_field.fill(username)
            
            # Click submit button
            logger.info("Clicking submit button...")
            submit_button = page.locator('#submit')
            await submit_button.wait_for(timeout=10000)
            await submit_button.click()
            
            # Wait for the page to respond after submit
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            logger.info("Sign-in flow completed successfully!")
            
            await browser.close()