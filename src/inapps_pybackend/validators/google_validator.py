import logging

from inapppy import GooglePlayVerifier, errors

logger = logging.getLogger(__name__)


class GooglePlayValidator:
    def __init__(self, credentials):
        self.google_bundle_id = credentials.get('google_app_bundle_id')
        self.google_service_account_key_file = credentials.get('google_service_account_key_file')

    def validate(self, purchase_token, product):
        """
        Takes purchase token and product as arguments and validates that
        product is already purchased from the Google Play API.
        """
        verifier = GooglePlayVerifier(
           self.google_bundle_id,
            self.google_service_account_key_file,
        )
        try:
            response = verifier.verify_with_result(purchase_token, product, is_subscription=False)
            result = {'raw_response': response.raw_response}
        except errors.GoogleError as exc:
            logger.error('Purchase validation failed %s', exc)
            result = {
                'error': exc.raw_response,
                'message': exc.message
            }
        return result
