from rest_framework.throttling import AnonRateThrottle


class OtpThrottle(AnonRateThrottle):
    scope = 'otp_throttle'