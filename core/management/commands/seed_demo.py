"""
Management command to create a demo user with sample transactions.
Usage: python manage.py seed_demo
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Transaction
from datetime import date, timedelta
import random
import decimal


class Command(BaseCommand):
    help = 'Creates a demo user with sample transaction data'

    def handle(self, *args, **options):
        # Create demo user
        username = 'demo'
        password = 'demo1234'
        
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            self.stdout.write(f'Demo user already exists: {username}')
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name='Alex',
                last_name='Demo',
                email='alex@fintrack.demo'
            )
            self.stdout.write(self.style.SUCCESS(f'Created demo user: {username}'))

        # Clear existing demo transactions
        Transaction.objects.filter(user=user).delete()

        today = date.today()
        transactions = []

        # Generate 3 months of data
        income_sources = ['salary', 'freelance', 'investment', 'bonus']
        expense_cats = ['food', 'transport', 'rent', 'shopping', 'entertainment', 'utilities', 'healthcare', 'subscriptions']

        for months_back in range(2, -1, -1):
            # Income transactions
            month_date = date(today.year, today.month, 1)
            if months_back > 0:
                for _ in range(months_back):
                    if month_date.month == 1:
                        month_date = date(month_date.year - 1, 12, 1)
                    else:
                        month_date = date(month_date.year, month_date.month - 1, 1)

            # Monthly salary
            transactions.append(Transaction(
                user=user, type='income', category='salary',
                amount=decimal.Decimal('3500.00'),
                date=date(month_date.year, month_date.month, 28),
                note='Monthly salary'
            ))

            # Freelance (occasional)
            if random.random() > 0.4:
                transactions.append(Transaction(
                    user=user, type='income', category='freelance',
                    amount=decimal.Decimal(str(random.randint(200, 800))),
                    date=date(month_date.year, month_date.month, random.randint(1, 25)),
                    note='Client project'
                ))

            # Expenses (8-14 per month)
            for _ in range(random.randint(8, 14)):
                cat = random.choice(expense_cats)
                amounts = {
                    'food': (20, 120), 'transport': (10, 80), 'rent': (800, 800),
                    'shopping': (30, 200), 'entertainment': (15, 60), 'utilities': (40, 120),
                    'healthcare': (20, 80), 'subscriptions': (8, 20)
                }
                lo, hi = amounts.get(cat, (10, 100))
                day = random.randint(1, 28)
                if day > 28: day = 28
                transactions.append(Transaction(
                    user=user, type='expense', category=cat,
                    amount=decimal.Decimal(str(random.randint(lo, hi))),
                    date=date(month_date.year, month_date.month, day),
                ))

        Transaction.objects.bulk_create(transactions)
        count = Transaction.objects.filter(user=user).count()

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Demo setup complete!\n'
            f'  Username: {username}\n'
            f'  Password: {password}\n'
            f'  Transactions: {count}\n'
        ))
