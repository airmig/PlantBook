import requests
from django.conf import settings
from django.core.cache import cache
import logging
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class TrefleAPI:
    def __init__(self):
        self.base_url = settings.TREFLE_API_BASE_URL
        self.token = settings.TREFLE_API_TOKEN
        logger.info(f"Initialized TrefleAPI with base URL: {self.base_url}")

    def _make_request(self, endpoint, params=None):
        """Make a request to the Trefle API with caching"""
        url = f"{self.base_url}/{endpoint}"
        cache_key = f"trefle_{endpoint}_{str(params)}"
        
        # Initialize params if None
        if params is None:
            params = {}
        
        # Add token to params
        params['token'] = self.token
        
        logger.info(f"Making request to Trefle API: {url}")
        logger.debug(f"Request parameters: {params}")
        
        # Try to get from cache first
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.info(f"Cache hit for endpoint: {endpoint}")
            return cached_response

        logger.info(f"Cache miss for endpoint: {endpoint}, making API request")
        
        try:
            # Make the API request
            response = requests.get(url, params=params)
            
            # Log response details for debugging
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            logger.debug(f"Response content: {response.text[:500]}...")  # Log first 500 chars of response
            
            # Check for authentication error
            if response.status_code == 401:
                logger.error("Authentication failed. Token may be invalid or expired.")
                raise requests.exceptions.RequestException("Authentication failed. Please check your API token.")
            
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully received response from {endpoint}")
            logger.debug(f"Response data: {data}")
            
            # Cache the response for 1 hour
            cache.set(cache_key, data, 3600)
            logger.info(f"Cached response for endpoint: {endpoint}")
            
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to {endpoint}: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response text: {e.response.text}")
            raise

    def check_authentication(self):
        """Check if the API token is valid"""
        try:
            # Try to make a simple request to check authentication
            # Using a simpler endpoint that doesn't require complex parameters
            response = self._make_request('kingdoms', {'page': 1})
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication check failed: {str(e)}")
            return False

    def search_plants(self, query, page=1, per_page=20):
        """Search for plants"""
        # Check authentication before searching
        if not self.check_authentication():
            raise requests.exceptions.RequestException("API authentication failed. Please check your API token.")
            
        params = {
            'q': query,
            'page': page,
            'per_page': per_page
        }
        return self._make_request('plants/search', params)

    def get_plant(self, plant_id):
        """Get detailed information about a specific plant"""
        try:
            logger.info(f"Fetching plant details for ID: {plant_id}")
            endpoint = f'plant/{plant_id}'
            response = self._make_request(endpoint, 'GET')
            
            logger.debug(f"Raw API response for plant {plant_id}: {response}")
            
            if not response:
                logger.error(f"Empty response for plant {plant_id}")
                return None
                
            # Ensure we have the expected data structure
            if not isinstance(response, dict):
                logger.error(f"Unexpected response type for plant {plant_id}: {type(response)}")
                return None
                
            if 'data' not in response:
                logger.error(f"No 'data' field in response for plant {plant_id}")
                return None
                
            return response
            
        except Exception as e:
            logger.error(f"Error fetching plant {plant_id}: {str(e)}")
            raise

    def get_plant_images(self, plant_id):
        """Get images for a specific plant"""
        return self._make_request(f'plants/{plant_id}/images')

    def get_plant_distribution(self, plant_id):
        """Get distribution information for a specific plant"""
        return self._make_request(f'plants/{plant_id}/distribution')

    def get_plant_sources(self, plant_id):
        """Get sources for a specific plant"""
        return self._make_request(f'plants/{plant_id}/sources')

    def get_plant_species(self, plant_id):
        """Get species information for a specific plant"""
        return self._make_request(f'plants/{plant_id}/species')

    def list_kingdoms(self, page=1):
        """List all kingdoms"""
        params = {'page': page}
        return self._make_request('kingdoms', params)

    def list_subkingdoms(self, page=1):
        """List all subkingdoms"""
        params = {'page': page}
        return self._make_request('subkingdoms', params)

class PermaPeopleAPI:
    """Class to handle PermaPeople API requests"""
    
    def __init__(self):
        self.base_url = 'https://permapeople.org/api'
        self.key_id = os.getenv('PERMAPEOPLE_KEY_ID')
        self.key_secret = os.getenv('PERMAPEOPLE_KEY_SECRET')
        
        if not self.key_id or not self.key_secret:
            logger.error("PermaPeople API credentials not found in environment variables")
            raise ValueError("PermaPeople API credentials not configured")
    
    def _make_request(self, endpoint, method='POST', data=None):
        """Make a request to the PermaPeople API"""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'x-permapeople-key-id': self.key_id,
            'x-permapeople-key-secret': self.key_secret
        }
        
        try:
            logger.info(f"Making {method} request to PermaPeople API: {url}")
            logger.debug(f"Request data: {data}")
            
            if method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            else:
                # For GET requests, pass data as params
                response = requests.get(url, params=data, headers=headers)
            
            # Log response details for debugging
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            logger.debug(f"Response content: {response.text[:500]}...")  # Log first 500 chars
            
            response.raise_for_status()
            
            try:
                json_response = response.json()
                logger.debug(f"Parsed JSON response: {json_response}")
                return json_response
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON response: {str(e)}")
                logger.error(f"Raw response content: {response.text}")
                raise
            
        except requests.exceptions.RequestException as e:
            logger.error(f"PermaPeople API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    raise Exception(f"PermaPeople API error: {error_data.get('msg', str(e))}")
                except json.JSONDecodeError:
                    logger.error(f"Raw error response: {e.response.text}")
                    raise Exception(f"PermaPeople API request failed: {str(e)}")
            raise Exception(f"PermaPeople API request failed: {str(e)}")
    
    def search_plants(self, query):
        """Search for plants using the PermaPeople API"""
        data = {'q': query}
        return self._make_request('search', data=data)
    
    def get_plant(self, plant_id):
        """Get detailed information about a specific plant"""
        endpoint = f'plants/{plant_id}'
        return self._make_request(endpoint, method='GET')

# Create a singleton instance
trefle_api = TrefleAPI()

# Initialize the API client
permapeople_api = PermaPeopleAPI() 