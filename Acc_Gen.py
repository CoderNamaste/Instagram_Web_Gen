"""
Instagram Account Creator
Author: @CoderNamaste
"""

import os
import random
import string
import time
import logging
from typing import Optional, Dict, Tuple, Any
from dataclasses import dataclass
from enum import Enum

import names
from curl_cffi import requests as curl_requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ResponseStatus(Enum):
    """Enum for response status types"""
    SUCCESS = "ok"
    FAILURE = "fail"
    ACCOUNT_CREATED = "account_created"
    EMAIL_SENT = "email_sent"


@dataclass
class AccountCredentials:
    """Data class for storing account credentials"""
    username: str
    password: str
    email: str
    session_id: str
    csrf_token: str
    ds_user_id: str
    ig_did: str
    rur: str
    mid: str
    datr: str

    def __str__(self) -> str:
        return (
            f"Username: {self.username}\n"
            f"Password: {self.password}\n"
            f"Email: {self.email}\n"
            f"Session ID: {self.session_id}\n"
            f"CSRF Token: {self.csrf_token}\n"
            f"DS User ID: {self.ds_user_id}\n"
            f"IG DID: {self.ig_did}\n"
            f"RUR: {self.rur}\n"
            f"MID: {self.mid}\n"
            f"DATR: {self.datr}"
        )


class InstagramAccountCreator:
    """
    A class for automating Instagram account creation process.

    This class handles the complete flow of creating an Instagram account,
    including header generation, email verification, and account setup.
    """

    BASE_URL = "https://www.instagram.com"
    API_BASE_URL = f"{BASE_URL}/api/v1"

    def __init__(self, country: str = "US", language: str = "en", proxies: Optional[Dict] = None):
        """
        Initialize the Instagram Account Creator.

        Args:
            country: Country code (e.g., 'US', 'UK')
            language: Language code (e.g., 'en', 'es')
            proxies: Optional proxy configuration dictionary
        """
        self.country = country
        self.language = language
        self.proxies = proxies

        # Initialize session with Chrome impersonation
        self.session = curl_requests.Session()
        self.session.impersonate = 'chrome110'

        # Initialize headers
        self.headers = None
        self.user_agent = None

        logger.info(f"Initialized Instagram Account Creator for {country}-{language}")

    def _generate_user_agent(self) -> str:
        """
        Generate a random mobile user agent string.

        Returns:
            A randomized user agent string
        """
        android_version = random.randint(9, 13)
        device_code = ''.join(random.choices(string.ascii_uppercase, k=3))
        device_number = random.randint(111, 999)

        user_agent = (
            f'Mozilla/5.0 (Linux; Android {android_version}; {device_code}{device_number}) '
            f'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36'
        )

        return user_agent

    def _extract_value_from_html(self, html: str, start_marker: str, end_marker: str) -> Optional[str]:
        """
        Extract a value from HTML content between markers.

        Args:
            html: HTML content to parse
            start_marker: Starting marker string
            end_marker: Ending marker string

        Returns:
            Extracted value or None if not found
        """
        try:
            start_index = html.index(start_marker) + len(start_marker)
            end_index = html.index(end_marker, start_index)
            return html[start_index:end_index]
        except (ValueError, IndexError):
            return None

    def generate_headers(self) -> Dict[str, str]:
        """
        Generate necessary headers for Instagram API requests.

        Returns:
            Dictionary containing all required headers

        Raises:
            Exception: If header generation fails after multiple attempts
        """
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                logger.info(f"Generating headers (Attempt {attempt + 1}/{max_attempts})")

                # Generate user agent
                self.user_agent = self._generate_user_agent()

                # Initial request to get cookies
                initial_response = self.session.get(
                    self.BASE_URL,
                    headers={'user-agent': self.user_agent},
                    proxies=self.proxies,
                    timeout=30
                )

                # Extract necessary cookies and values
                js_datr = initial_response.cookies.get('datr')
                csrf_token = initial_response.cookies.get('csrftoken')
                ig_did = initial_response.cookies.get('ig_did')

                # Extract MID from response text
                mid = self._extract_value_from_html(
                    initial_response.text,
                    '{"mid":{"value":"',
                    '",'
                )

                if not all([js_datr, csrf_token, ig_did, mid]):
                    raise ValueError("Failed to extract required values from initial response")

                # Build initial headers for second request
                headers_step1 = {
                    'authority': 'www.instagram.com',
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'accept-language': f'{self.language}-{self.country},en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
                    'cookie': f'dpr=3; csrftoken={csrf_token}; mid={mid}; ig_nrcb=1; ig_did={ig_did}; datr={js_datr}',
                    'sec-ch-prefers-color-scheme': 'light',
                    'sec-ch-ua': '"Chromium";v="111", "Not(A:Brand";v="8"',
                    'sec-ch-ua-mobile': '?1',
                    'sec-ch-ua-platform': '"Android"',
                    'sec-fetch-dest': 'document',
                    'sec-fetch-mode': 'navigate',
                    'sec-fetch-site': 'none',
                    'sec-fetch-user': '?1',
                    'upgrade-insecure-requests': '1',
                    'user-agent': self.user_agent,
                    'viewport-width': '980',
                }

                # Second request to get app ID and rollout hash
                secondary_response = self.session.get(
                    self.BASE_URL,
                    headers=headers_step1,
                    proxies=self.proxies,
                    timeout=30
                )

                # Extract app ID and rollout hash
                app_id = self._extract_value_from_html(
                    secondary_response.text,
                    'APP_ID":"',
                    '"'
                )

                rollout_hash = self._extract_value_from_html(
                    secondary_response.text,
                    'rollout_hash":"',
                    '"'
                )

                if not all([app_id, rollout_hash]):
                    raise ValueError("Failed to extract app ID or rollout hash")

                # Build final headers
                self.headers = {
                    'authority': 'www.instagram.com',
                    'accept': '*/*',
                    'accept-language': f'{self.language}-{self.country},en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
                    'content-type': 'application/x-www-form-urlencoded',
                    'cookie': f'dpr=3; csrftoken={csrf_token}; mid={mid}; ig_nrcb=1; ig_did={ig_did}; datr={js_datr}',
                    'origin': self.BASE_URL,
                    'referer': f'{self.BASE_URL}/accounts/signup/email/',
                    'sec-ch-prefers-color-scheme': 'light',
                    'sec-ch-ua': '"Chromium";v="111", "Not(A:Brand";v="8"',
                    'sec-ch-ua-mobile': '?1',
                    'sec-ch-ua-platform': '"Android"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'user-agent': self.user_agent,
                    'viewport-width': '360',
                    'x-asbd-id': '198387',
                    'x-csrftoken': csrf_token,
                    'x-ig-app-id': app_id,
                    'x-ig-www-claim': '0',
                    'x-instagram-ajax': rollout_hash,
                    'x-requested-with': 'XMLHttpRequest',
                    'x-web-device-id': ig_did,
                }

                logger.info("Headers generated successfully")
                return self.headers

            except Exception as e:
                logger.error(f"Error generating headers (Attempt {attempt + 1}): {e}")
                if attempt == max_attempts - 1:
                    raise Exception(f"Failed to generate headers after {max_attempts} attempts") from e
                time.sleep(2)  # Wait before retry

    def get_username_suggestion(self, name: str, email: str) -> Optional[str]:
        """
        Get username suggestions from Instagram.

        Args:
            name: Base name for username generation
            email: Email address for the account

        Returns:
            A suggested username or None if failed
        """
        if not self.headers:
            raise ValueError("Headers not generated. Call generate_headers() first.")

        try:
            # Update headers with appropriate referer
            headers = self.headers.copy()
            headers['referer'] = f'{self.BASE_URL}/accounts/signup/birthday/'

            # Generate random suffix for name
            name_with_suffix = f"{name}{random.randint(1, 99)}"

            data = {
                'email': email,
                'name': name_with_suffix,
            }

            response = self.session.post(
                f'{self.API_BASE_URL}/web/accounts/username_suggestions/',
                headers=headers,
                data=data,
                proxies=self.proxies,
                timeout=30
            )

            response_json = response.json()

            if response_json.get('status') == ResponseStatus.SUCCESS.value:
                suggestions = response_json.get('suggestions', [])
                if suggestions:
                    username = random.choice(suggestions)
                    logger.info(f"Username suggestion obtained: {username}")
                    return username
            else:
                logger.error(f"Failed to get username suggestion: {response.text}")

        except Exception as e:
            logger.error(f"Error getting username suggestion: {e}")

        return None

    def send_verification_email(self, email: str) -> bool:
        """
        Send verification email to the provided address.

        Args:
            email: Email address to send verification to

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.headers:
            raise ValueError("Headers not generated. Call generate_headers() first.")

        try:
            device_id = self._extract_device_id_from_headers()

            data = {
                'device_id': device_id,
                'email': email,
            }

            response = self.session.post(
                f'{self.API_BASE_URL}/accounts/send_verify_email/',
                headers=self.headers,
                data=data,
                proxies=self.proxies,
                timeout=30
            )

            if f'"{ResponseStatus.EMAIL_SENT.value}":true' in response.text:
                logger.info(f"Verification email sent successfully to {email}")
                return True
            else:
                logger.error(f"Failed to send verification email: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending verification email: {e}")
            return False

    def validate_verification_code(self, email: str, code: str) -> Optional[str]:
        """
        Validate the verification code sent to email.

        Args:
            email: Email address
            code: Verification code received

        Returns:
            Signup code if validation successful, None otherwise
        """
        if not self.headers:
            raise ValueError("Headers not generated. Call generate_headers() first.")

        try:
            headers = self.headers.copy()
            headers['referer'] = f'{self.BASE_URL}/accounts/signup/emailConfirmation/'

            device_id = self._extract_device_id_from_headers()

            data = {
                'code': code,
                'device_id': device_id,
                'email': email,
            }

            response = self.session.post(
                f'{self.API_BASE_URL}/accounts/check_confirmation_code/',
                headers=headers,
                data=data,
                proxies=self.proxies,
                timeout=30
            )

            response_json = response.json()

            if response_json.get('status') == ResponseStatus.SUCCESS.value:
                signup_code = response_json.get('signup_code')
                logger.info("Verification code validated successfully")
                return signup_code
            else:
                logger.error(f"Failed to validate code: {response.text}")

        except Exception as e:
            logger.error(f"Error validating verification code: {e}")

        return None

    def _extract_device_id_from_headers(self) -> str:
        """Extract device ID (MID) from headers."""
        return self.headers['cookie'].split('mid=')[1].split(';')[0]

    def _generate_password(self, base_name: str) -> str:
        """
        Generate a secure password.

        Args:
            base_name: Base name to use in password

        Returns:
            Generated password
        """
        return f"{base_name.strip()}@{random.randint(111, 999)}"

    def _generate_birth_date(self) -> Tuple[int, int, int]:
        """
        Generate random birth date.

        Returns:
            Tuple of (month, day, year)
        """
        month = random.randint(1, 12)
        day = random.randint(1, 28)  # Safe for all months
        year = random.randint(1990, 2001)
        return month, day, year

    def create_account(self, email: str, signup_code: str) -> Optional[AccountCredentials]:
        """
        Create Instagram account with provided email and signup code.

        Args:
            email: Email address for the account
            signup_code: Signup code from email verification

        Returns:
            AccountCredentials object if successful, None otherwise
        """
        if not self.headers:
            raise ValueError("Headers not generated. Call generate_headers() first.")

        try:
            # Generate account details
            first_name = names.get_first_name()
            username = self.get_username_suggestion(first_name, email)

            if not username:
                logger.error("Failed to get username suggestion")
                return None

            password = self._generate_password(first_name)
            month, day, year = self._generate_birth_date()

            # Update headers
            headers = self.headers.copy()
            headers['referer'] = f'{self.BASE_URL}/accounts/signup/username/'

            # Prepare account creation data
            data = {
                'enc_password': f'#PWD_INSTAGRAM_BROWSER:0:{round(time.time())}:{password}',
                'email': email,
                'username': username,
                'first_name': first_name,
                'month': month,
                'day': day,
                'year': year,
                'client_id': self._extract_device_id_from_headers(),
                'seamless_login_enabled': '1',
                'tos_version': 'row',
                'force_sign_up_code': signup_code,
            }

            logger.info(f"Creating account with username: {username}")

            # Send account creation request
            response = self.session.post(
                f'{self.API_BASE_URL}/web/accounts/web_create_ajax/',
                headers=headers,
                data=data,
                proxies=self.proxies,
                timeout=30
            )

            # Check if account was created successfully
            if f'"{ResponseStatus.ACCOUNT_CREATED.value}":true' in response.text:
                logger.info("Account created successfully!")

                # Extract cookies and create credentials object
                credentials = AccountCredentials(
                    username=username,
                    password=password,
                    email=email,
                    session_id=response.cookies.get('sessionid', ''),
                    csrf_token=response.cookies.get('csrftoken', ''),
                    ds_user_id=response.cookies.get('ds_user_id', ''),
                    ig_did=response.cookies.get('ig_did', ''),
                    rur=response.cookies.get('rur', ''),
                    mid=self._extract_device_id_from_headers(),
                    datr=self.headers['cookie'].split('datr=')[1]
                )

                return credentials
            else:
                logger.error(f"Account creation failed: {response.text}")

        except Exception as e:
            logger.error(f"Error creating account: {e}")

        return None

    def run_account_creation_flow(self, email: str) -> Optional[AccountCredentials]:
        """
        Run the complete account creation flow.

        Args:
            email: Email address for the new account

        Returns:
            AccountCredentials if successful, None otherwise
        """
        try:
            # Step 1: Generate headers
            logger.info("Step 1: Generating headers...")
            self.generate_headers()

            # Step 2: Send verification email
            logger.info(f"Step 2: Sending verification email to {email}...")
            if not self.send_verification_email(email):
                logger.error("Failed to send verification email")
                return None

            # Step 3: Get verification code from user
            code = input("Enter the verification code sent to your email: ").strip()

            # Step 4: Validate code
            logger.info("Step 3: Validating verification code...")
            signup_code = self.validate_verification_code(email, code)

            if not signup_code:
                logger.error("Failed to validate verification code")
                return None

            # Step 5: Create account
            logger.info("Step 4: Creating account...")
            credentials = self.create_account(email, signup_code)

            if credentials:
                logger.info("Account created successfully!")
                return credentials
            else:
                logger.error("Failed to create account")
                return None

        except Exception as e:
            logger.error(f"Error in account creation flow: {e}")
            return None


def main():
    """Main function to demonstrate the Instagram account creator."""

    print("=" * 60)
    print("Instagram Account Creator")
    print("Tool Made By @NamasteCoder (Refactored)")
    print("=" * 60)

    # Initialize the account creator
    creator = InstagramAccountCreator(country='US', language='en')

    # Get email from user
    email = input("\nEnter your email address: ").strip()

    if not email:
        print("Email address is required!")
        return

    # Run the account creation flow
    print("\nStarting account creation process...")
    credentials = creator.run_account_creation_flow(email)

    if credentials:
        print("\n" + "=" * 60)
        print("ACCOUNT CREATED SUCCESSFULLY!")
        print("=" * 60)
        print("\nAccount Details:")
        print(credentials)
        print("=" * 60)

        # Optionally save credentials to file
        save_to_file = input("\nSave credentials to file? (y/n): ").strip().lower()
        if save_to_file == 'y':
            filename = f"instagram_{credentials.username}.txt"
            with open(filename, 'w') as f:
                f.write(str(credentials))
            print(f"Credentials saved to {filename}")
    else:
        print("\nAccount creation failed. Please check the logs for more details.")


if __name__ == "__main__":
    main()
