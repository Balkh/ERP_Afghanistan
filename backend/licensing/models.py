from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


def validate_device_fingerprint(value):
    if not isinstance(value, dict):
        raise ValidationError('Device fingerprint must be a dictionary.')
    required_fields = ['cpu_id', 'mac_address', 'disk_serial', 'device_id']
    for field in required_fields:
        if field not in value:
            raise ValidationError(f'Device fingerprint missing required field: {field}')


class DeviceLicense(models.Model):
    license_key = models.CharField(max_length=255, unique=True)
    device_fingerprint = models.JSONField(validators=[validate_device_fingerprint])
    device_id = models.CharField(max_length=64, unique=True)
    signed_license = models.TextField(blank=True)
    license_type = models.CharField(max_length=50, default='pharmacy_erp')
    issued_date = models.DateField(default=timezone.now)
    expires_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    issued_to = models.CharField(max_length=255, blank=True)
    company_name = models.CharField(max_length=255, blank=True, default='')
    features = models.JSONField(default=list, blank=True)
    max_branches = models.IntegerField(default=1)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'licensing_devicelicense'
        verbose_name = 'Device License'
        verbose_name_plural = 'Device Licenses'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.license_key} - {self.device_id[:16]}..."

    def is_expired(self):
        if self.expires_date is None:
            return False
        return timezone.now().date() > self.expires_date

    def is_valid(self):
        return self.is_active and not self.is_expired()

    def matches_device(self, fingerprint_dict):
        if not isinstance(fingerprint_dict, dict):
            return False
        required = ['cpu_id', 'mac_address', 'disk_serial']
        for field in required:
            if field not in fingerprint_dict:
                return False
        from licensing.utils import generate_device_id
        provided = generate_device_id(
            fingerprint_dict['cpu_id'],
            fingerprint_dict['mac_address'],
            fingerprint_dict['disk_serial']
        )
        return self.device_id == provided

    def save(self, *args, **kwargs):
        if not self.device_id and self.device_fingerprint:
            from licensing.utils import generate_device_id
            fp = self.device_fingerprint
            self.device_id = generate_device_id(
                fp.get('cpu_id', ''),
                fp.get('mac_address', ''),
                fp.get('disk_serial', '')
            )
        super().save(*args, **kwargs)


class TrialSession(models.Model):
    device_id = models.CharField(max_length=64, unique=True)
    device_fingerprint = models.JSONField(default=dict)
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    extended = models.BooleanField(default=False)
    access_count = models.IntegerField(default=1)

    TRIAL_DAYS = 10

    class Meta:
        db_table = 'licensing_trialsession'
        verbose_name = 'Trial Session'
        verbose_name_plural = 'Trial Sessions'
        ordering = ['-started_at']

    def __str__(self):
        return f"Trial({self.device_id[:16]}...) expires {self.expires_at.date()}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def days_remaining(self):
        remaining = (self.expires_at - timezone.now()).days
        return max(0, remaining)

    @classmethod
    def get_or_create_for_device(cls, device_id, fingerprint):
        trial = cls.objects.filter(device_id=device_id).first()
        if trial:
            trial.access_count += 1
            trial.save(update_fields=['access_count'])
            return trial, False
        from datetime import timedelta
        trial = cls(
            device_id=device_id,
            device_fingerprint=fingerprint,
            expires_at=timezone.now() + timedelta(days=cls.TRIAL_DAYS),
        )
        trial.save()
        return trial, True

    @classmethod
    def get_active_trial(cls, device_id):
        trial = cls.objects.filter(device_id=device_id).first()
        if trial and not trial.is_expired():
            return trial
        return None
