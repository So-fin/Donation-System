from django.urls import path
from .views import *

urlpatterns = [
    path('send-otp/', UserOtpView.as_view(), name='send-otp'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('razorpay-donation-order/', RazorpayLinkView.as_view(), name='create-razorpay-order'),
    path('create-order-webhook/', CreateRazorpayOrderWebhook.as_view(), name='create-order-webhook'),
    path('donation-history/', DonationHistoryView.as_view(), name='donation-history'),
    path('donation-visualization/', DonationVisualizationView.as_view(), name='donation-visualization'),
]
