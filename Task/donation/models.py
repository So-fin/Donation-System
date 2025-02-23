from django.db import models
import random
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number field is compulsory')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone_number, password, **extra_fields)


class Users(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=15, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'


class OTPs(models.Model):
    LOGIN_REGISTER = 'LOGIN_REGISTER'
    user = models.ForeignKey(Users, on_delete=models.DO_NOTHING, null=True)
    mobile_number = models.CharField(max_length=10, null=True, blank=True)
    otp = models.CharField(max_length=4)
    valid_till = models.DateTimeField(auto_now=False)
    created_time = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def generate_random_otp():
        return random.randint(1000, 9999)

    @staticmethod
    def get_otp_expired_date():
        return timezone.now() + timedelta(minutes=10)

    @classmethod
    def get_or_create(cls, user):
        try:
            otp_obj = cls.objects.filter(user=user).first() or None
            if (otp_obj is not None):
                if (otp_obj.valid_till > timezone.now()):
                    return otp_obj

            new_otp = cls(user=user, otp=cls.generate_random_otp(), valid_till=cls.get_otp_expired_date())
            new_otp.save()
            return new_otp

        except Exception as e:
            return None

    @classmethod
    def generate_otp(cls, mobile_number):
        return cls.objects.create(
            mobile_number=mobile_number,
            otp=cls.generate_random_otp(),
            valid_till=cls.get_otp_expired_date()
        )

    def validate(self, otp):
        if self.otp != otp:
            return False, """You have entered the incorrect OTP. Kindly re-enter the received OTP."""
        elif self.valid_till < timezone.now():
            return False, """Your OTP has expired. Kindly login with your mobile number again."""
        else:
            return True, ""


class Donation(models.Model):
    user = models.ForeignKey(Users, related_name='rel_users', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, unique=True)
