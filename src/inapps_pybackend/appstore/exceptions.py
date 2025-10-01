class AppStoreRequestException(Exception):
    def __init__(self, message, inapp_id=None):
        super().__init__(message)
        self.inapp_id = inapp_id


class AppStoreException(Exception):
    def __init__(self, message, inapp_id=None):
        super().__init__(message)
        self.inapp_id = inapp_id
