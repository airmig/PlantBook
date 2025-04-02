import requests
from django.conf import settings
from django.core.cache import cache
import logging
import os
from dotenv import load_dotenv
import json
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class TrefleAPI:
    def __init__(self):
        self.base_url = 'https://trefle.io/api/v1'
        self.token = os.getenv('TREFLE_TOKEN')
        self.logger = logging.getLogger(__name__)
        
        if not self.token:
            raise ValueError("TREFLE_TOKEN environment variable must be set")
            
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
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

    def _get_wikipedia_image(self, scientific_name):
        """Get the first image from a Wikipedia page for a plant"""
        try:
            # Format the scientific name for the Wikipedia URL
            formatted_name = scientific_name.replace(' ', '_')
            url = f'https://en.wikipedia.org/wiki/{formatted_name}'
            
            self.logger.info(f"Fetching Wikipedia page: {url}")
            
            # Make a request to the Wikipedia page
            response = requests.get(url)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch Wikipedia page: {response.status_code}")
                return None
                
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find the first image in the article
            # First, look for the infobox image
            infobox = soup.find('table', class_='infobox')
            if infobox:
                img = infobox.find('img')
                if img and img.get('src'):
                    # Convert relative URL to absolute
                    img_url = img.get('src')
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = 'https://en.wikipedia.org' + img_url
                    self.logger.info(f"Found infobox image: {img_url}")
                    return img_url
            
            # If no infobox image, look for the first image in the article
            article = soup.find('div', class_='mw-parser-output')
            if article:
                for img in article.find_all('img'):
                    # Skip small icons and thumbnails
                    if img.get('width') and int(img.get('width', '0')) < 100:
                        continue
                    if img.get('src'):
                        # Convert relative URL to absolute
                        img_url = img.get('src')
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif img_url.startswith('/'):
                            img_url = 'https://en.wikipedia.org' + img_url
                        self.logger.info(f"Found article image: {img_url}")
                        return img_url
            
            self.logger.warning(f"No suitable image found for {scientific_name}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting Wikipedia image: {str(e)}")
            return None

class PermaPeopleAPI:
    def __init__(self):
        self.base_url = 'https://permapeople.org/api'
        self.key_id = os.getenv('PERMAPEOPLE_KEY_ID')
        self.key_secret = os.getenv('PERMAPEOPLE_KEY_SECRET')
        
        if not self.key_id or not self.key_secret:
            raise ValueError("PERMAPEOPLE_KEY_ID and PERMAPEOPLE_KEY_SECRET environment variables must be set")
            
        self.headers = {
            'Content-Type': 'application/json',
            'x-permapeople-key-id': self.key_id,
            'x-permapeople-key-secret': self.key_secret
        }
        self.logger = logging.getLogger(__name__)

    def _get_wikipedia_image(self, scientific_name):
        """Get the first image from a Wikipedia page for a plant"""
        try:
            # Format the scientific name for the Wikipedia URL
            formatted_name = scientific_name.replace(' ', '_')
            url = f'https://en.wikipedia.org/wiki/{formatted_name}'
            
            self.logger.info(f"Fetching Wikipedia page: {url}")
            
            # Make a request to the Wikipedia page
            response = requests.get(url)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch Wikipedia page: {response.status_code}")
                return None
                
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find the first image in the article
            # First, look for the infobox image
            infobox = soup.find('table', class_='infobox')
            if infobox:
                img = infobox.find('img')
                if img and img.get('src'):
                    # Convert relative URL to absolute
                    img_url = img.get('src')
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = 'https://en.wikipedia.org' + img_url
                    self.logger.info(f"Found infobox image: {img_url}")
                    return img_url
            
            # If no infobox image, look for the first image in the article
            article = soup.find('div', class_='mw-parser-output')
            if article:
                for img in article.find_all('img'):
                    # Skip small icons and thumbnails
                    if img.get('width') and int(img.get('width', '0')) < 100:
                        continue
                    if img.get('src'):
                        # Convert relative URL to absolute
                        img_url = img.get('src')
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif img_url.startswith('/'):
                            img_url = 'https://en.wikipedia.org' + img_url
                        self.logger.info(f"Found article image: {img_url}")
                        return img_url
            
            self.logger.warning(f"No suitable image found for {scientific_name}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting Wikipedia image: {str(e)}")
            return None

    def _make_request(self, method, endpoint, params=None, data=None):
        """Make an HTTP request to the PermaPeople API with detailed logging."""
        url = f"{self.base_url}/{endpoint}"
        self.logger.info(f"Making {method} request to {url}")
        if params:
            self.logger.info(f"Request params: {params}")
        if data:
            self.logger.info(f"Request data: {data}")

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data
            )
            self.logger.info(f"Response status code: {response.status_code}")
            self.logger.info(f"Response headers: {response.headers}")
            self.logger.info(f"Response content: {response.text[:1000]}")  # Log first 1000 chars

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Error response: {e.response.text}")
            raise

    def search_plants(self, query):
        """Search for plants using the PermaPeople API"""
        try:
            self.logger.info(f"Searching plants with query: {query}")
            response = self._make_request('POST', 'search', data={'q': query})
            
            self.logger.info(f"Raw API response: {response}")
            
            if not response:
                self.logger.error("Empty response from search API")
                return []
                
            # Extract and format the search results
            results = []
            
            # Log the structure of the response
            self.logger.info(f"Response type: {type(response)}")
            self.logger.info(f"Response keys: {response.keys() if isinstance(response, dict) else 'Not a dict'}")
            
            # Try different possible response structures
            if isinstance(response, dict):
                if 'data' in response:
                    plants_data = response['data']
                elif 'plants' in response:
                    plants_data = response['plants']
                else:
                    plants_data = [response]
            elif isinstance(response, list):
                plants_data = response
            else:
                self.logger.error(f"Unexpected response type: {type(response)}")
                return []
            
            self.logger.info(f"Plants data type: {type(plants_data)}")
            self.logger.info(f"Number of plants found: {len(plants_data) if isinstance(plants_data, list) else 'Not a list'}")
            
            for plant in plants_data:
                self.logger.info(f"Processing plant: {plant}")
                # Log the structure of each plant
                self.logger.info(f"Plant keys: {plant.keys() if isinstance(plant, dict) else 'Not a dict'}")
                
                # Try to extract data from different possible structures
                if isinstance(plant, dict):
                    plant_id = plant.get('id')
                    if not plant_id:
                        continue
                        
                    # Get detailed plant information
                    try:
                        detailed_plant = self._make_request('GET', f'plants/{plant_id}')
                        self.logger.info(f"Detailed plant info: {detailed_plant}")
                        
                        if not detailed_plant:
                            continue
                            
                        # Create a base plant object with the main fields
                        plant_data = {
                            'id': plant_id,
                            'name': detailed_plant.get('name'),
                            'scientific_name': detailed_plant.get('scientific_name'),
                            'description': detailed_plant.get('description', ''),
                            'image_url': detailed_plant.get('image_url', ''),
                            'link': detailed_plant.get('link', ''),
                            'slug': detailed_plant.get('slug', ''),
                            'data': detailed_plant.get('data', [])
                        }
                        
                        # Check if there's a Wikipedia link in the data
                        wikipedia_url = None
                        for item in plant_data['data']:
                            if item.get('key', '').lower() == 'wikipedia':
                                wikipedia_url = item.get('value', '')
                                break
                        
                        # If there's a Wikipedia link, try to get the first image
                        if wikipedia_url and plant_data['scientific_name']:
                            try:
                                wikipedia_image = self._get_wikipedia_image(plant_data['scientific_name'])
                                if wikipedia_image:
                                    plant_data['wikipedia_image'] = wikipedia_image
                            except Exception as e:
                                self.logger.error(f"Error fetching Wikipedia image: {str(e)}")
                        
                        results.append(plant_data)
                        
                    except Exception as e:
                        self.logger.error(f"Error fetching details for plant {plant_id}: {str(e)}")
                        continue
            
            self.logger.info(f"Processed {len(results)} plants")
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching plants: {str(e)}")
            self.logger.exception("Full traceback:")
            return []
    
    def get_plant(self, plant_id):
        """Get detailed information about a specific plant"""
        try:
            self.logger.info(f"Fetching plant details for ID: {plant_id}")
            response = self._make_request('GET', f'plants/{plant_id}')
            self.logger.info(f"Plant details response: {response}")
            
            if not response:
                self.logger.error("Empty response from API")
                return None
                
            # Extract plant details according to the API documentation
            plant_data = {
                'id': response.get('id'),
                'type': response.get('type'),
                'scientific_name': response.get('scientific_name'),
                'name': response.get('name'),
                'version': response.get('version'),
                'description': response.get('description'),
                'link': response.get('link'),
                'parent_id': response.get('parent_id'),
                'slug': response.get('slug'),
                'updated_at': response.get('updated_at'),
                'created_at': response.get('created_at'),
                'data': response.get('data', [])
            }
            
            # Extract specific details from the data array
            for item in plant_data['data']:
                if isinstance(item, dict):
                    key = item.get('key', '').lower().replace(' ', '_')
                    value = item.get('value', '')
                    plant_data[key] = value
            
            return plant_data
            
        except Exception as e:
            self.logger.error(f"Error in get_plant: {str(e)}")
            return None


# Initialize the API client
permapeople_api = PermaPeopleAPI() 