"""
Subscription management and auto-charge functionality
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import Salon, Plan
from app.core.payment import charge_subscription
import logging

logger = logging.getLogger(__name__)


def check_and_process_expired_subscriptions(db: Session):
    """
    Check for expired subscriptions and either:
    1. Charge the card if auto_debit is enabled
    2. Downgrade to free plan if auto_debit is disabled or charge fails
    """
    # Get all salons with active subscriptions
    salons = db.query(Salon).filter(
        Salon.is_active == 1,
        Salon.subscription_end_date <= datetime.utcnow()
    ).all()
    
    results = {
        'checked': 0,
        'charged': 0,
        'downgraded': 0,
        'errors': []
    }
    
    for salon in salons:
        results['checked'] += 1
        
        # Skip if already on free plan
        if salon.plan_id:
            plan = db.query(Plan).filter(Plan.id == salon.plan_id).first()
            if plan and plan.name.lower() == 'free':
                continue
        
        try:
            # If auto_debit is enabled, attempt to charge
            if salon.auto_debit == 1:
                logger.info(f"Attempting auto-charge for salon {salon.id}")
                charge_result = charge_subscription(salon, db)
                
                if charge_result['success']:
                    # Successfully charged - extend subscription
                    results['charged'] += 1
                    extend_subscription(salon, db)
                    logger.info(f"Successfully charged salon {salon.id}")
                else:
                    # Charge failed - downgrade to free
                    results['downgraded'] += 1
                    downgrade_to_free_plan(salon, db)
                    logger.warning(f"Charge failed for salon {salon.id}, downgraded to free")
            else:
                # Auto-debit disabled - downgrade to free
                results['downgraded'] += 1
                downgrade_to_free_plan(salon, db)
                logger.info(f"Auto-debit disabled for salon {salon.id}, downgraded to free")
                
        except Exception as e:
            logger.error(f"Error processing salon {salon.id}: {str(e)}")
            results['errors'].append({
                'salon_id': salon.id,
                'error': str(e)
            })
            # On error, downgrade to free for safety
            try:
                downgrade_to_free_plan(salon, db)
            except Exception as inner_e:
                logger.error(f"Failed to downgrade salon {salon.id}: {str(inner_e)}")
    
    db.commit()
    return results


def extend_subscription(salon: Salon, db: Session):
    """
    Extend subscription for one billing cycle
    """
    if salon.billing_cycle == 'monthly':
        salon.subscription_start_date = datetime.utcnow()
        salon.subscription_end_date = datetime.utcnow() + timedelta(days=30)
    elif salon.billing_cycle == 'yearly':
        salon.subscription_start_date = datetime.utcnow()
        salon.subscription_end_date = datetime.utcnow() + timedelta(days=365)
    
    db.add(salon)
    logger.info(f"Extended subscription for salon {salon.id} until {salon.subscription_end_date}")


def downgrade_to_free_plan(salon: Salon, db: Session):
    """
    Downgrade salon to free plan
    """
    # Find free plan
    free_plan = db.query(Plan).filter(Plan.name == 'Free').first()
    
    if not free_plan:
        logger.error("Free plan not found in database!")
        return
    
    salon.plan_id = free_plan.id
    salon.subscription_start_date = datetime.utcnow()
    salon.subscription_end_date = None  # Free plan has no end date
    
    db.add(salon)
    logger.info(f"Downgraded salon {salon.id} to free plan")


def get_subscription_status(salon: Salon) -> dict:
    """
    Get current subscription status for a salon
    """
    now = datetime.utcnow()
    
    status = {
        'is_active': salon.is_active == 1,
        'plan_id': salon.plan_id,
        'billing_cycle': salon.billing_cycle,
        'auto_debit': salon.auto_debit == 1,
        'subscription_start': salon.subscription_start_date,
        'subscription_end': salon.subscription_end_date,
    }
    
    if salon.subscription_end_date:
        days_remaining = (salon.subscription_end_date - now).days
        status['days_remaining'] = days_remaining
        status['is_expired'] = days_remaining < 0
    else:
        status['days_remaining'] = None
        status['is_expired'] = False
    
    return status
