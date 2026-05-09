from django.db import models
from core.models.base import BaseModel
from core.models.system import Company

class InvoiceTemplate(BaseModel):
    """Configuration for dynamic invoice templates."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invoice_templates')
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)
    
    # Template configurations (stored as JSON for flexibility)
    config = models.JSONField(
        default=dict, 
        help_text="Template-specific settings: header_style, footer_text, color_theme, layout_type, show_qr, field_visibility_map"
    )
    
    # logo can be overridden from company logo
    logo_override = models.ImageField(upload_to='invoice/logos/', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Invoice Template'
        verbose_name_plural = 'Invoice Templates'
        ordering = ['-is_active', 'name']

    def __str__(self):
        return f"{self.company.name} - {self.name}"

    def save(self, *args, **kwargs):
        if self.is_active:
            # Ensure only one active template per company
            InvoiceTemplate.objects.filter(
                company=self.company, 
                is_active=True
            ).exclude(id=self.id).update(is_active=False)
        super().save(*args, **kwargs)
