# Subscription Auto-Charge System

## Overview
Automated subscription management that handles billing renewals and plan downgrades.

## How It Works

### Auto-Debit Enabled
When a salon's subscription expires and they have **auto-debit enabled**:
1. System attempts to charge their saved payment method
2. If successful: Subscription is extended for another billing cycle
3. If failed: Account is downgraded to Free plan

### Auto-Debit Disabled
When auto-debit is **disabled** or no payment method exists:
- Account is automatically downgraded to Free plan on expiration

## Backend Components

### Core Modules

**`app/core/subscription_manager.py`**
- `check_and_process_expired_subscriptions()` - Main processing function
- `extend_subscription()` - Extends subscription after successful payment
- `downgrade_to_free_plan()` - Downgrades to free plan
- `get_subscription_status()` - Get current subscription status

**`app/core/payment.py`**
- `charge_subscription()` - Charges the payment method
- `validate_payment_method()` - Validates saved payment info
- **TODO**: Integrate with actual payment gateway (Stripe, PayPal, etc.)

**`app/api/v1/endpoints/subscriptions.py`**
- `POST /subscriptions/process-expired` - Process all expired subscriptions
- `GET /subscriptions/status/{salon_id}` - Get subscription status

## Setup

### 1. Add to Cron Job (Production)
```bash
# Run daily at 2 AM
0 2 * * * curl -X POST http://your-api/api/v1/subscriptions/process-expired \
  -H "Authorization: Bearer YOUR_SUPERADMIN_TOKEN"
```

### 2. Manual Trigger (Development)
```bash
curl -X POST http://localhost:8000/api/v1/subscriptions/process-expired \
  -H "Authorization: Bearer YOUR_SUPERADMIN_TOKEN"
```

### 3. Payment Gateway Integration

Update `app/core/payment.py` with your payment provider:

#### Stripe Example
```python
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

charge = stripe.Charge.create(
    amount=int(amount * 100),
    currency='usd',
    customer=salon.stripe_customer_id,
    description=f'Subscription renewal for {salon.name}'
)
```

#### Required Database Fields
Add to `salons` table:
- `stripe_customer_id` (String) - Stripe customer ID
- `payment_method_id` (String) - Payment method ID

## Frontend Changes

### Settings Page
Clear explanation added in Billing Settings section:

> **Auto-Debit:** When enabled, your subscription fee will be automatically charged to your saved payment method when your billing period renews. If disabled or payment fails, your account will be downgraded to the Free plan until payment is made manually.

## Testing

### Test Expired Subscription Flow
```python
# Set a salon's subscription to expired
salon.subscription_end_date = datetime.utcnow() - timedelta(days=1)
salon.auto_debit = 1
db.commit()

# Run processor
results = check_and_process_expired_subscriptions(db)
```

## Security
- Only superadmins can trigger subscription processing
- All charges are logged
- Failed charges trigger automatic downgrades
- Errors are caught and logged

## Monitoring

Check results after processing:
```json
{
  "status": "success",
  "results": {
    "checked": 10,
    "charged": 7,
    "downgraded": 3,
    "errors": []
  }
}
```

## Future Enhancements
- [ ] Email notifications for successful/failed charges
- [ ] Grace period before downgrade (e.g., 3 days)
- [ ] Retry failed charges automatically
- [ ] Payment method update reminders
- [ ] Invoice generation
