from io import BytesIO
from django.http import HttpResponse
from matplotlib import pyplot as plt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import throttle_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate, login
from .send_sms import send_sms
from .razorpay_manager import RazorPayManager
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.db import transaction
from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Users, OTPs, Donation
import pandas as pd
from .serializers import DonationSerializer
from Task.throttles import OtpThrottle

class UserOtpView(APIView):
    """Generate OTP and send via Fast2SMS"""
    queryset = OTPs.objects.all()

    @throttle_classes([OtpThrottle])
    @transaction.atomic
    def post(self, request):
        mobile_number = request.data.get('mobile_number')
        if not mobile_number:
            return Response({"error": "Mobile number is required"}, status=status.HTTP_400_BAD_REQUEST)

        otp = OTPs.generate_otp(mobile_number)
        message = f"Your OTP code is: {otp.otp}."

        try:
            send_sms(mobile_number, message)
            return Response({"message": "OTP sent successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserLoginView(APIView):
    """Authenticate user via OTP and return auth token"""
    @transaction.atomic
    def post(self, request):
        mobile_number = request.data.get('mobile_number')
        otp_value = request.data.get('otp')

        if not mobile_number or not otp_value:
            return Response({"error": "Mobile number and OTP are required"}, status=status.HTTP_400_BAD_REQUEST)

        otp = OTPs.objects.filter(mobile_number=mobile_number).last()

        is_valid, msg = otp.validate(otp.otp)
        if otp is None or not is_valid:
            return Response({"error": msg}, status=status.HTTP_406_NOT_ACCEPTABLE)

        try:
            user, created = Users.objects.get_or_create(phone_number=mobile_number, defaults={"password": otp_value})
            if created:
                user.set_password(otp_value)
                user.save()

            user = authenticate(username=mobile_number, password=otp_value)
            if user is None:
                return Response({"error": "Authentication failed"}, status=status.HTTP_401_UNAUTHORIZED)

            login(request, user)
            token, _ = Token.objects.get_or_create(user=user)

            return Response({"auth_token": token.key}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RazorpayLinkView(APIView):
    """Generate Razorpay payment link"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, **kwargs):
        try:
            link = RazorPayManager(request).create_link()
            return Response({"razorpay_payment_link": link}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateRazorpayOrderWebhook(APIView):
    """Handle Razorpay payment webhook"""
    serializer_class = DonationSerializer

    def post(self, request):
        try:
            payment_data = request.data.get('payload', {}).get('payment', {}).get('entity', {})
            notes = payment_data.get('notes', {})

            if not notes.get('amount'):
                return Response({"error": "Invalid payment data"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                amount = float(notes.get('amount'))
                if amount <= 0:
                    return Response({"error": "Invalid payment amount"}, status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({"error": "Invalid amount format"}, status=status.HTTP_400_BAD_REQUEST)

            serializer = self.serializer_class(data=notes)
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Payment donated successfully"}, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DonationHistoryView(generics.ListAPIView):
    """List donation history with filters"""
    serializer_class = DonationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['user', 'date', 'amount']
    ordering_fields = ['date', 'amount']
    search_fields = ['transaction_id']

    def get_queryset(self):
        return Donation.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page else queryset, many=True)
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)


class DonationVisualizationView(generics.GenericAPIView):
    """Generate donation visualization as a bar chart"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            donations = Donation.objects.filter(user=request.user).values('date', 'amount')
            if not donations.exists():
                return Response({"error": "No donation data available"}, status=status.HTTP_400_BAD_REQUEST)

            df = pd.DataFrame(donations)

            if df.empty:
                return Response({"error": "No valid donation data"}, status=status.HTTP_400_BAD_REQUEST)

            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            df.dropna(inplace=True)

            if df.empty:
                return Response({"error": "No valid data after processing"}, status=status.HTTP_400_BAD_REQUEST)

            df['date'] = df['date'].dt.to_period('M')
            df = df.groupby('date')['amount'].sum()

            plt.figure(figsize=(10, 5))
            df.plot(kind='bar')
            plt.title('Monthly Donations')
            plt.xlabel('Month')
            plt.ylabel('Total Amount')
            plt.grid(axis='y')

            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            return HttpResponse(buffer.getvalue(), content_type='image/png')

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
