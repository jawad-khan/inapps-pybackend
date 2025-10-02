import logging
import time

import jwt
import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from .exceptions import AppStoreRequestException, AppStoreException

logger = logging.getLogger(__name__)



class Appstore:
    """
    Class to manage appstore api communications.
    Provides basic crud functionality for appstore products
    """

    base_url_v1 = "https://api.appstoreconnect.apple.com/v1/"
    base_url_v2 = "https://api.appstoreconnect.apple.com/v2/"

    def __init__(self, key_id, issuer_id, ios_bundle_id, private_key):
        self.key_id = key_id
        self.issuer_id = issuer_id
        self.ios_bundle_id = ios_bundle_id
        self.private_key = private_key


    def request_connect_store(self, url, headers, data=None, method="post", retries=1, backoff_factor=0.3):
        """ Hit connect store api with given url using retry strategy. """
        # Adding backoff and retries in case there is a connection error or server is busy.
        retries = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[502, 503, 504, 408, 429, 409],
            allowed_methods={'POST', "GET", "PUT", "PATCH"},
        )
        http = Session()
        http.mount('https://', HTTPAdapter(max_retries=retries))
        try:
            if method == "post":
                response = http.post(url, json=data, headers=headers)
            elif method == "put":
                response = http.put(url, data=data, headers=headers)
            elif method == "patch":
                response = http.patch(url, json=data, headers=headers)
            elif method == "delete":
                response = http.delete(url, headers=headers)
            elif method == "get":
                response = http.get(url, headers=headers)
            else:
                response = http.get(url, headers=headers)

            return response

        except requests.RequestException as exc:
            raise AppStoreRequestException(exc) from exc

    def get_auth_headers(self):
        """ returns auth headers to authenticate with appstore apis """

        payload = {
            "iss": self.issuer_id,
            "exp": round(time.time()) + 60 * 20,  # Token expiration time (20 minutes)
            "aud": "appstoreconnect-v1",
            "bid": self.ios_bundle_id
        }

        headers = {
            "kid": self.key_id,
            "typ": "JWT",
            "alg": "ES256"
        }

        private_key = self.private_key
        token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        return headers

    def get_all_ios_products(self, app_id, headers=None):
        """ Returns list of all inapp products. """
        headers = headers or self.get_auth_headers()
        products = []
        url =  '{}apps/{}/inAppPurchasesV2?limit=200'.format(self.base_url_v1, app_id)
        while url:
            logger.info("Getting products from {}".format(url))
            response = self.request_connect_store(url=url, headers=headers,method='get')
            api_data = response.json()
            products.extend(api_data['data'])
            url = api_data['links'].get('next')

        return products

    def create_ios_product(self, product, app_id):
        """
        Create in app ios product on connect store.

        Args:
            product (dict): {
                'price'(float): price of product
                'name'(str): name of this product
                id(str): product_id of this product, be careful once assigned it can't be changed.
                review_note(str): extra info for appstore reviewer(can be anything that can help in review process)
                type(str): e.g NON_CONSUMABLE, CONSUMABLE etc
                locale(str): e.g. en-US
                locale_name(str): can be a message on upgrade button or anything you want to set.
                locale_description(str): brief description for user while purchasing product.
                territory(str): e.g. USA
                image(dict): {file_name(str), file_size(int), file_path(str)}
            }
            app_id (str): apple id of app on appstore.

        Returns:
                id of the created product on store.

        Raises:
            AppStoreRequestException or AppStoreException exception with id of the created product.

        """

        headers = self.get_auth_headers()
        in_app_id = None
        try:
            in_app_id = self.create_inapp_purchase(product, app_id, headers)
            self.localize_inapp_purchase(in_app_id, product, headers)
            price_points = self.fetch_price_points(in_app_id, product.get('territory'), headers)
            price_point_id = self.select_price_point_id(in_app_id, price_points)
            self.apply_price_of_inapp_purchase(in_app_id, price_point_id, headers, product.get('territory'))
            self.upload_screenshot_of_inapp_purchase(in_app_id, product['image'], headers)
            territories = self.get_territories(headers)
            self.set_territories_of_in_app_purchase(in_app_id, territories, headers)
            self.submit_in_app_purchase_for_review(in_app_id, headers)
            return in_app_id
        except (AppStoreRequestException, AppStoreException) as e:
            raise type(e)(str(e), in_app_id) from e

    def create_inapp_purchase(self, product, app_id, headers=None):
        """ Create appstore product and returns its id. """
        headers = headers or self.get_auth_headers()

        url = self.base_url_v2 + "inAppPurchases"
        data = {
            "data": {
                "type": "inAppPurchases",
                "attributes": {
                    "name": product['name'],
                    "productId": product['id'],
                    "inAppPurchaseType": ['type'],
                    "reviewNote": product['review_note'],
                },
                "relationships": {
                    "app": {
                        "data": {
                            "type": "apps",
                            "id": app_id
                        }
                    }
                }
            }
        }
        response = self.request_connect_store(url=url, data=data, headers=headers)
        if response.status_code == 201:
            return response.json()["data"]["id"]

        raise AppStoreRequestException("Unable to create appstore product.")

    def localize_inapp_purchase(self, in_app_id, product, headers=None):
        """ Localize given in app product with given locale. """
        headers = headers or self.get_auth_headers()
        url = self.base_url_v1 + "inAppPurchaseLocalizations"
        data = {
            "data": {
                "type": "inAppPurchaseLocalizations",
                "attributes": {
                    "locale": product['locale'],
                    "name": product['locale_name'],
                    "description": product['locale_description'],
                },
                "relationships": {
                    "inAppPurchaseV2": {
                        "data": {
                            "type": "inAppPurchases",
                            "id": in_app_id
                        }
                    }
                }
            }
        }
        response = self.request_connect_store(url=url, data=data, headers=headers)
        if response.status_code != 201:
            raise AppStoreRequestException("Unable to localize purchase")

    def fetch_price_points(self, in_app_id, territory=None, headers=None):
        headers = headers or self.get_auth_headers()
        territory = territory or "USA"
        url = self.base_url_v2 + ("inAppPurchases/v2/inAppPurchases/{}/pricePoints?filter[territory]={}&include"
                                  "=territory&limit=8000").format(in_app_id, territory)

        response = self.request_connect_store(url=url, headers=headers, method='get')
        if response.status_code != 200:
            raise AppStoreRequestException("Couldn't fetch price points")

        return response.json()['data']

    def select_price_point_id(self, price_points, price, method='ceil'):
        nearest_price_id = None
        nearest_price = float('inf') if method == 'ceil' else float('-inf')
        for price_point in price_points:
            store_price = float(price_point['attributes']['customerPrice'])
            if method == 'equal':
                # There is a likely chance that this will result an AppStoreException
                # Since not all prices are available on appstore
                if store_price == price:
                    nearest_price = store_price
                    nearest_price_id = price_point['id']
            if method == "ceil":
                if nearest_price > store_price >= price:
                    nearest_price = store_price
                    nearest_price_id = price_point['id']
            elif method == "floor":
                if nearest_price < store_price <= price:
                    nearest_price = store_price
                    nearest_price_id = price_point['id']

        if nearest_price_id is None:
            raise AppStoreException("Unable to match appstore price.")

        return nearest_price_id

    def apply_price_of_inapp_purchase(self, in_app_id, nearest_price_id, territory=None, headers=None):
        headers = headers or self.get_auth_headers()
        territory = territory or "USA"
        url = self.base_url_v1 + "inAppPurchasePriceSchedules"
        data = {
                "data": {
                    "type": "inAppPurchasePriceSchedules",
                    "attributes": {},
                    "relationships": {
                        "inAppPurchase": {
                            "data": {
                                "type": "inAppPurchases",
                                "id": in_app_id
                            }
                        },
                        "manualPrices": {
                            "data": [
                                {
                                    "type": "inAppPurchasePrices",
                                    "id": "${price}"
                                }
                            ]
                        },
                        "baseTerritory": {
                            "data": {
                                "type": "territories",
                                "id": territory
                            }
                        }
                    }
                },
                "included": [
                    {
                        "id": "${price}",
                        "relationships": {
                            "inAppPurchasePricePoint": {
                                "data": {
                                    "type": "inAppPurchasePricePoints",
                                    "id": nearest_price_id
                                }
                            }
                        },
                        "type": "inAppPurchasePrices",
                        "attributes": {
                            "startDate": None
                        }
                    }
                ]
            }
        response = self.request_connect_store(url=url, data=data, headers=headers)

        if response.status_code != 201:
            raise AppStoreRequestException("Unable to apply price.")

    def upload_screenshot_of_inapp_purchase(self, in_app_id, image_attrs, headers=None):
        """ Upload screenshot for the given product. """
        headers = headers or self.get_auth_headers()
        url = self.base_url_v1 + "inAppPurchaseAppStoreReviewScreenshots"
        data = {
            "data": {
                "type": "inAppPurchaseAppStoreReviewScreenshots",
                "attributes": {
                    "fileName": image_attrs['file_name'],
                    "fileSize": image_attrs['file_size'],
                },
                "relationships": {
                    "inAppPurchaseV2": {
                        "data": {
                            "id": in_app_id,
                            "type": "inAppPurchases"
                        }
                    }
                }
            }
        }

        response = self.request_connect_store(url, headers, data=data)
        if response.status_code != 201:
            raise AppStoreRequestException("Unable to get screenshot url.")

        response1 = response.json()
        screenshot_id = response1['data']['id']
        url = response1['data']['attributes']['uploadOperations'][0]['url']
        image = open(image_attrs['file_path'], 'rb')
        img_headers = {'Content-Type': 'image/png'}
        response = self.request_connect_store(url, headers=img_headers, data=image.read(), method='put')
        if response.status_code != 200:
            raise AppStoreRequestException("Couldn't upload screenshot")

        url = self.base_url_v1 + "inAppPurchaseAppStoreReviewScreenshots/{}".format(screenshot_id)
        data = {
            "data": {
                "type": "inAppPurchaseAppStoreReviewScreenshots",
                "id": screenshot_id,
                "attributes": {
                    "uploaded": True,
                    "sourceFileChecksum": ""
                }
            }
        }

        response = self.request_connect_store(url, headers, data=data, method='patch')
        if response.status_code != 200:
            raise AppStoreRequestException("Unable to confirm screenshot.")

    def get_territories(self, headers=None):
        headers = headers or self.get_auth_headers()
        url = self.base_url_v1 + 'territories?limit=200'
        response = self.request_connect_store(url, headers, method='get')
        if response.status_code != 200:
            raise AppStoreRequestException("Unable to fetch territories")

        territories = [{'type': territory['type'], 'id': territory['id']}
                       for territory in response.json()['data']]
        return territories

    def set_territories_of_in_app_purchase(self, in_app_id, territories, headers=None):
        headers = headers or self.get_auth_headers()
        url = self.base_url_v1 + 'inAppPurchaseAvailabilities'
        data = {
            "data": {
                "type": "inAppPurchaseAvailabilities",
                "attributes": {
                    "availableInNewTerritories": True
                },
                "relationships": {
                    "availableTerritories": {
                        "data": territories
                    },
                    "inAppPurchase": {
                        "data": {
                            "id": in_app_id,
                            "type": "inAppPurchases"
                        }
                    }
                }
            }
        }

        response = self.request_connect_store(url, headers, data=data)

        if response.status_code != 201:
            raise AppStoreRequestException("Unable to modify territories of inapp product.")

    def submit_in_app_purchase_for_review(self, in_app_id, headers=None):
        headers = headers or self.get_auth_headers()
        url = self.base_url_v1 + "inAppPurchaseSubmissions"
        data = {
                "data": {
                    "type": "inAppPurchaseSubmissions",
                    "relationships": {
                        "inAppPurchaseV2": {
                            "data": {
                                "type": "inAppPurchases",
                                "id": in_app_id
                            }
                        }
                    }
                }
            }
        response = self.request_connect_store(url=url, data=data, headers=headers)
        if not response.status_code == 201:
            raise AppStoreRequestException("Couldn't submit purchase")
