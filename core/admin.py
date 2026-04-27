from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'category', 'amount', 'date', 'created_at']
    list_filter = ['type', 'category', 'date']
    search_fields = ['user__username', 'category', 'note']
    ordering = ['-date']
