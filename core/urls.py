from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('signup/verify/', views.signup_verify_otp, name='signup_verify_otp'),
    path('signup/resend/', views.signup_resend_otp, name='signup_resend_otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password reset routes
    path('forgot-password/', views.forgot_password_request, name='forgot_password'),
    path('forgot-password/verify/', views.verify_otp, name='verify_otp'),
    path('forgot-password/reset/', views.reset_password, name='reset_password'),
    
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('add-income/', views.add_income_view, name='add_income'),
    path('add-expense/', views.add_expense_view, name='add_expense'),
    path('transactions/', views.transactions_view, name='transactions'),
    path('transactions/edit/<int:pk>/', views.edit_transaction_view, name='edit_transaction'),
    path('transactions/delete/<int:pk>/', views.delete_transaction_view, name='delete_transaction'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('expense-insights/', views.expense_insights_view, name='expense_insights'),
    path('loans/', views.loans_view, name='loans'),
    path('add-loan/', views.add_loan_view, name='add_loan'),
    path('loan-payment/', views.loan_payment_view, name='loan_payment'),
    path('loans/edit/<int:pk>/', views.edit_loan_view, name='edit_loan'),
    path('loans/delete/<int:pk>/', views.delete_loan_view, name='delete_loan'),
    path('receivables/', views.receivables_view, name='receivables'),
    path('add-receivable/', views.add_receivable_view, name='add_receivable'),
    path('receivable-payment/', views.receivable_payment_view, name='receivable_payment'),
    path('receivables/edit/<int:pk>/', views.edit_receivable_view, name='edit_receivable'),
    path('receivables/delete/<int:pk>/', views.delete_receivable_view, name='delete_receivable'),

    # Payment Reminders
    path('reminders/', views.reminders_view, name='reminders'),
    path('reminders/add/', views.add_reminder_view, name='add_reminder'),
    path('reminders/edit/<int:pk>/', views.edit_reminder_view, name='edit_reminder'),
    path('reminders/delete/<int:pk>/', views.delete_reminder_view, name='delete_reminder'),
    path('reminders/entry/<int:pk>/pay/', views.mark_reminder_paid_view, name='mark_reminder_paid'),
    path('reminders/entry/<int:pk>/unpay/', views.unmark_reminder_paid_view, name='unmark_reminder_paid'),

    # Profile management routes
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    path('profile/delete-picture/', views.delete_profile_picture_view, name='delete_profile_picture'),
]
