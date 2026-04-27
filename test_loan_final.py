from django.test import Client
from django.contrib.auth.models import User
from decimal import Decimal
from core.models import Loan, LoanPayment

# Clean up any previous test users
User.objects.filter(username__startswith='multi_loan').delete()

u = User.objects.create_user(username='multi_loan_final', password='test123', email='ml@t.com', first_name='Multi')

Loan.objects.create(user=u, lender_name='X', amount=Decimal('10000.00'))
Loan.objects.create(user=u, lender_name='Y', amount=Decimal('20000.00'))
Loan.objects.create(user=u, lender_name='Z', amount=Decimal('15000.00'))

LoanPayment.objects.create(user=u, loan=Loan.objects.get(lender_name='X'), amount=Decimal('5000.00'))

client = Client()
client.force_login(u)

dash = client.get('/dashboard/')
loans = client.get('/loans/')

print('Dashboard Status:', dash.status_code)
print('Loans Status:', loans.status_code)
print('total_loaned:', loans.context['total_loaned'], '(expected: 45000)')
print('total_paid:', loans.context['total_paid'], '(expected: 5000)')
print('outstanding:', loans.context['outstanding'], '(expected: 40000)')
for ld in loans.context['loan_details']:
    print('  ' + ld['lender'] + ': borrowed ' + str(ld['borrowed']) + ', paid ' + str(ld['paid']) + ', due ' + str(ld['due']))
print('ALL TESTS OK')

# Cleanup
User.objects.filter(username='multi_loan_final').delete()