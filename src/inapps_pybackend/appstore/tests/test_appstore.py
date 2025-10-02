import mock
import pytest

from ..appstore import Appstore
from ..exceptions import AppStoreException, AppStoreRequestException


@mock.patch('src.inapps_pybackend.appstore.appstore.jwt.encode', return_value='Test token')
@pytest.mark.django_db
class TestAppstore:
    """ Tests for ios product creation on appstore. """

    def setup_method(self):
        self.test_app_id = 'test_app_id'
        self.appstore = Appstore(
            key_id="KID",
            issuer_id="ISS",
            ios_bundle_id="BID",
            private_key="PRIV",
        )
        self.test_product = {
            'price':    100,
            'name': 'test_product',
            'id':   'test_id',
            'review_note':  'review_note',
            'type': 'CONSUMABLE',
            'locale':   'en - US',
            'locale_name':  'Upgrade product',
            'locale_description':   'This will unlock features for you',
            'territory':    'USA',
            'image':
                {
                    'file_name':    'test.png',
                    'file_size': 1122,
                    'file_path': 'abc/test.png'
                }

    }


    @mock.patch('src.inapps_pybackend.appstore.appstore.Appstore.create_inapp_purchase', return_value='12345')
    @mock.patch('src.inapps_pybackend.appstore.appstore.Appstore.localize_inapp_purchase')
    @mock.patch('src.inapps_pybackend.appstore.appstore.Appstore.fetch_price_points')
    @mock.patch('src.inapps_pybackend.appstore.appstore.Appstore.select_price_point_id')
    @mock.patch('src.inapps_pybackend.appstore.appstore.Appstore.apply_price_of_inapp_purchase')
    @mock.patch('src.inapps_pybackend.appstore.appstore.Appstore.upload_screenshot_of_inapp_purchase')
    @mock.patch('src.inapps_pybackend.appstore.appstore.Appstore.get_territories')
    @mock.patch('src.inapps_pybackend.appstore.appstore.Appstore.set_territories_of_in_app_purchase')
    @mock.patch('src.inapps_pybackend.appstore.appstore.Appstore.submit_in_app_purchase_for_review', return_value=None)
    def test_create_ios_product(self, _1, _2, _3, _4, _5, _6, _7, _8, _9, _10):
        result = self.appstore.create_ios_product(self.test_product, self.test_app_id)
        assert result == '12345'

    def test_create_ios_product_with_failure(self, _):
        with pytest.raises(AppStoreRequestException):
            self.appstore.create_ios_product(self.test_product, self.test_app_id)

    def test_get_auth_headers(self, _):
        """
        Test auth headers are returned in required format
        """
        headers = {
            "Authorization": "Bearer Test token",
            "Content-Type": "application/json"
        }
        assert self.appstore.get_auth_headers() == headers

    def test_create_inapp_purchase(self, _):
        """
        Test create in app product call and its exception working properly.
        """

        with mock.patch('src.inapps_pybackend.appstore.appstore.requests.Session.post') as post_call:
            post_call.return_value.status_code = 201
            self.appstore.create_inapp_purchase(self.test_product, self.test_app_id)
            create_url = 'https://api.appstoreconnect.apple.com/v2/inAppPurchases'
            assert post_call.call_args[0][0] == create_url
            with pytest.raises(AppStoreRequestException):
                post_call.return_value.status_code = 500
                self.appstore.create_inapp_purchase(self.test_product, self.test_app_id)

    def test_localize_inapp_purchase(self, _):
        """
        Test localize in app product call and its exception working properly.
        """
        with mock.patch('src.inapps_pybackend.appstore.appstore.requests.Session.post') as post_call:
            post_call.return_value.status_code = 201
            self.appstore.localize_inapp_purchase('123', self.test_product)
            localize_url = 'https://api.appstoreconnect.apple.com/v1/inAppPurchaseLocalizations'
            assert post_call.call_args[0][0] == localize_url

            with pytest.raises(AppStoreRequestException):
                post_call.return_value.status_code = 500
                self.appstore.localize_inapp_purchase('234', self.test_product)

    def test_apply_price_of_inapp_purchase(self, _):
        """
        Test applying price on in app product call and its exception working properly.
        """
        with mock.patch('src.inapps_pybackend.appstore.appstore.requests.Session.post') as post_call:
            post_call.return_value.status_code = 201
            self.appstore.apply_price_of_inapp_purchase('123', '345')
            price_url = 'https://api.appstoreconnect.apple.com/v1/inAppPurchasePriceSchedules'
            assert post_call.call_args[0][0] == price_url

            with pytest.raises(AppStoreRequestException):
                post_call.return_value.status_code = 500
                self.appstore.apply_price_of_inapp_purchase('123', '345')

    def test_upload_screenshot_of_inapp_purchase(self, _):
        """
        Test image uploading call for app product and its exception working properly.
        """
        with mock.patch('src.inapps_pybackend.appstore.appstore.requests.Session.post') as post_call, \
                mock.patch('src.inapps_pybackend.appstore.appstore.requests.Session.put') as put_call, \
                mock.patch('src.inapps_pybackend.appstore.appstore.requests.Session.patch') as patch_call, \
                mock.patch('src.inapps_pybackend.appstore.appstore.open'):

            with pytest.raises(AppStoreRequestException):
                post_call.return_value.status_code = 500
                self.appstore.upload_screenshot_of_inapp_purchase('123', self.test_product['image'])

            post_call.return_value.status_code = 201
            post_call.return_value.json.return_value = {
                'data': {
                    'id': '1234',
                    'attributes': {
                        'uploadOperations': [
                            {'url': 'https://image-url.com'}
                        ]
                    }
                }
            }

            with pytest.raises(AppStoreRequestException):
                self.appstore.upload_screenshot_of_inapp_purchase('123', self.test_product['image'])

            put_call.return_value.status_code = 200

            with pytest.raises(AppStoreRequestException):
                # Make sure it doesn't select higher price point
                self.appstore.upload_screenshot_of_inapp_purchase('123', self.test_product['image'])

            patch_call.return_value.status_code = 200

            self.appstore.upload_screenshot_of_inapp_purchase('123', self.test_product['image'])
            img_url = 'https://api.appstoreconnect.apple.com/v1/inAppPurchaseAppStoreReviewScreenshots'
            assert post_call.call_args[0][0] == img_url

            assert put_call.call_args[0][0] == 'https://image-url.com'
            img_headers = {'Content-Type': 'image/png'}
            assert put_call.call_args[1]['headers'] == img_headers

            img_patch_url = 'https://api.appstoreconnect.apple.com/v1/inAppPurchaseAppStoreReviewScreenshots/1234'
            assert patch_call.call_args[0][0] == img_patch_url

    def test_set_territories_of_in_app_purchase(self, _):
        """
        Test applying price on in app product call and its exception working properly.
        """
        with mock.patch('src.inapps_pybackend.appstore.appstore.requests.Session.post') as post_call:
            territories = {
                "data": [
                    {
                        "type": "territories",
                        "id": "AFG",
                        "attributes": {
                            "currency": "USD"
                        },
                        "links": {
                            "self": "https://api.appstoreconnect.apple.com/v1/territories/AFG"
                        }
                    },
                    {
                        "type": "territories",
                        "id": "AGO",
                        "attributes": {
                            "currency": "USD"
                        },
                        "links": {
                            "self": "https://api.appstoreconnect.apple.com/v1/territories/AGO"
                        }
                    }
                ]
            }
            with pytest.raises(AppStoreRequestException):
                post_call.return_value.status_code = 500
                self.appstore.set_territories_of_in_app_purchase('100', territories)

            post_call.return_value.status_code = 201
            self.appstore.set_territories_of_in_app_purchase('100', territories)
            territory_url = 'https://api.appstoreconnect.apple.com/v1/inAppPurchaseAvailabilities'
            assert post_call.call_args[0][0] == territory_url

    def test_submit_in_app_purchase_for_review(self, _):
        """
        Test submitting in app product call and its exception working properly.
        """
        with mock.patch('src.inapps_pybackend.appstore.appstore.requests.Session.post') as post_call:
            with pytest.raises(AppStoreRequestException):
                post_call.return_value.status_code = 500
                self.appstore.submit_in_app_purchase_for_review('100')

            post_call.return_value.status_code = 201
            submit_url = 'https://api.appstoreconnect.apple.com/v1/inAppPurchaseSubmissions'
            assert post_call.call_args[0][0] == submit_url

    def test_select_price_point_id(self, _):
        price_points = [
            {"id": "id1", "attributes": {"customerPrice": "0.0"}},
            {"id": "id2", "attributes": {"customerPrice": "1.0"}},
            {"id": "id3", "attributes": {"customerPrice": "2.0"}},
            {"id": "id4", "attributes": {"customerPrice": "3.0"}},
            {"id": "id5", "attributes": {"customerPrice": "4.0"}},
            {"id": "id6", "attributes": {"customerPrice": "5.0"}},
            {"id": "id7", "attributes": {"customerPrice": "6.0"}},
            {"id": "id8", "attributes": {"customerPrice": "7.0"}},
            {"id": "id9", "attributes": {"customerPrice": "8.0"}},
            {"id": "id10", "attributes": {"customerPrice": "9.0"}},
        ]
        assert self.appstore.select_price_point_id(price_points, 3, "equal") == "id4"
        assert self.appstore.select_price_point_id(price_points, 3, "ceil") == "id4"
        assert self.appstore.select_price_point_id(price_points, 3, "floor") == "id4"
        assert self.appstore.select_price_point_id(price_points, 5.5, "ceil") == "id7"
        assert self.appstore.select_price_point_id(price_points, 5.5, "floor") == "id6"
        with pytest.raises(AppStoreException):
            assert self.appstore.select_price_point_id(price_points, 10, "ceil") == "id7"
