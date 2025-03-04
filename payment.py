import os
import stripe
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

# Import database models
from database import User, Subscription, Payment, UsageRecord

# Initialize Stripe
stripe.api_key = os.environ.get("STRIPE_API_KEY", "sk_test_sample_key")

# Define price IDs for different subscription tiers
SUBSCRIPTION_PRICES = {
    "standard": os.environ.get("STRIPE_STANDARD_PRICE_ID", "price_standard"),
    "premium": os.environ.get("STRIPE_PREMIUM_PRICE_ID", "price_premium"),
    "enterprise": os.environ.get("STRIPE_ENTERPRISE_PRICE_ID", "price_enterprise")
}

# Define token pricing for pay-as-you-go (cost per 1000 tokens)
MODEL_PRICING = {
    "claude37sonnet": {
        "input": 15.0,      # $15 per 1M tokens ($0.015 per 1K)
        "output": 75.0      # $75 per 1M tokens ($0.075 per 1K)
    },
    "deepseekr1": {
        "input": 5.0,       # $5 per 1M tokens ($0.005 per 1K)
        "output": 15.0      # $15 per 1M tokens ($0.015 per 1K)
    },
    "gemini2pro": {
        "input": 3.5,       # $3.50 per 1M tokens ($0.0035 per 1K)
        "output": 10.5      # $10.50 per 1M tokens ($0.0105 per 1K)
    },
    "default": {            # Default for any other model (like Ollama)
        "input": 1.0,       # $1 per 1M tokens ($0.001 per 1K) 
        "output": 2.0       # $2 per 1M tokens ($0.002 per 1K)
    }
}

# Discount rates for subscription tiers (percentage off pay-as-you-go rates)
TIER_DISCOUNTS = {
    "standard": 10,    # 10% discount
    "premium": 25,     # 25% discount
    "enterprise": 40   # 40% discount
}

class PaymentService:
    """
    Handles payment processing and subscription management with Stripe
    """
    
    @staticmethod
    def create_customer(db: Session, user: User, payment_method_id: Optional[str] = None) -> str:
        """
        Create a new Stripe customer
        
        Args:
            db: Database session
            user: User object
            payment_method_id: Optional Stripe payment method ID
            
        Returns:
            Stripe customer ID
        """
        try:
            # Create the customer in Stripe
            customer_data = {
                "email": user.email,
                "name": user.username,
                "metadata": {
                    "user_id": user.id
                }
            }
            
            if payment_method_id:
                customer_data["payment_method"] = payment_method_id
                
            customer = stripe.Customer.create(**customer_data)
            
            # Create or update subscription record in database
            subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
            
            if not subscription:
                subscription = Subscription(
                    user_id=user.id,
                    plan="free",
                    stripe_customer_id=customer.id,
                    status="active"
                )
                db.add(subscription)
            else:
                subscription.stripe_customer_id = customer.id
                
            db.commit()
            
            return customer.id
            
        except stripe.error.StripeError as e:
            db.rollback()
            raise e
    
    @staticmethod
    def create_subscription(db: Session, user: User, plan: str, payment_method_id: str) -> Dict[str, Any]:
        """
        Create a new subscription for a user
        
        Args:
            db: Database session
            user: User object
            plan: Subscription plan ("standard", "premium", "enterprise")
            payment_method_id: Stripe payment method ID
            
        Returns:
            Subscription details
        """
        try:
            # Get subscription from database
            subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
            
            if not subscription:
                # Create customer first
                customer_id = PaymentService.create_customer(db, user, payment_method_id)
            else:
                customer_id = subscription.stripe_customer_id
                
                # If no customer ID, create one
                if not customer_id:
                    customer_id = PaymentService.create_customer(db, user, payment_method_id)
            
            # Get price ID for the plan
            price_id = SUBSCRIPTION_PRICES.get(plan)
            if not price_id:
                raise ValueError(f"Invalid plan: {plan}")
                
            # Create the subscription in Stripe
            stripe_subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                payment_behavior="default_incomplete",
                payment_settings={"save_default_payment_method": "on_subscription"},
                expand=["latest_invoice.payment_intent"],
                metadata={"user_id": user.id}
            )
            
            # Update subscription record in database
            if not subscription:
                subscription = Subscription(
                    user_id=user.id,
                    plan=plan,
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=stripe_subscription.id,
                    status=stripe_subscription.status,
                    current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
                    current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end)
                )
                db.add(subscription)
            else:
                subscription.plan = plan
                subscription.stripe_subscription_id = stripe_subscription.id
                subscription.status = stripe_subscription.status
                subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
                subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
                
            db.commit()
            
            # Return subscription details with client secret for payment confirmation
            return {
                "subscription_id": stripe_subscription.id,
                "client_secret": stripe_subscription.latest_invoice.payment_intent.client_secret,
                "plan": plan,
                "status": stripe_subscription.status
            }
            
        except (stripe.error.StripeError, ValueError) as e:
            db.rollback()
            raise e
    
    @staticmethod
    def cancel_subscription(db: Session, user: User) -> Dict[str, Any]:
        """
        Cancel a user's subscription
        
        Args:
            db: Database session
            user: User object
            
        Returns:
            Result of cancellation
        """
        try:
            # Get subscription from database
            subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
            
            if not subscription or not subscription.stripe_subscription_id:
                raise ValueError("No active subscription found")
                
            # Cancel the subscription in Stripe
            canceled_subscription = stripe.Subscription.delete(
                subscription.stripe_subscription_id
            )
            
            # Update subscription status in database
            subscription.status = canceled_subscription.status
            db.commit()
            
            return {
                "subscription_id": canceled_subscription.id,
                "status": canceled_subscription.status
            }
            
        except (stripe.error.StripeError, ValueError) as e:
            db.rollback()
            raise e
    
    @staticmethod
    def calculate_usage_cost(db: Session, usage_record: UsageRecord, user: User) -> float:
        """
        Calculate the cost of a usage record based on token count and model
        
        Args:
            db: Database session
            usage_record: Usage record
            user: User object
            
        Returns:
            Cost in USD
        """
        # Get subscription tier for discount
        subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        tier = subscription.plan if subscription else "free"
        
        # Get pricing for the model
        model_pricing = MODEL_PRICING.get(usage_record.model.lower(), MODEL_PRICING["default"])
        
        # Calculate base cost
        input_tokens = usage_record.system_prompt_tokens + usage_record.user_prompt_tokens
        output_tokens = usage_record.response_tokens
        
        # Cost per token (convert from cost per 1K tokens)
        input_cost_per_token = model_pricing["input"] / 1_000_000
        output_cost_per_token = model_pricing["output"] / 1_000_000
        
        # Calculate total cost
        base_cost = (input_tokens * input_cost_per_token) + (output_tokens * output_cost_per_token)
        
        # Apply tier discount if applicable
        discount = TIER_DISCOUNTS.get(tier, 0) / 100
        final_cost = base_cost * (1 - discount)
        
        return final_cost
    
    @staticmethod
    def record_usage_and_bill(db: Session, user: User, usage_record: UsageRecord) -> Dict[str, Any]:
        """
        Record usage and bill the user if they're on a usage-based plan
        
        Args:
            db: Database session
            user: User object
            usage_record: Usage record
            
        Returns:
            Billing result
        """
        try:
            # Calculate cost
            cost = PaymentService.calculate_usage_cost(db, usage_record, user)
            usage_record.cost = cost
            db.commit()
            
            # Get subscription to check if pay-as-you-go billing is needed
            subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
            
            if not subscription or subscription.plan == "pay-as-you-go":
                # Only bill immediately for pay-as-you-go plans
                # For subscription plans, billing is handled by Stripe subscription
                
                # Check if the cost is above the minimum billing threshold ($0.10)
                if cost >= 0.10:
                    # Create a payment intent
                    payment_intent = stripe.PaymentIntent.create(
                        amount=int(cost * 100),  # Convert to cents
                        currency="usd",
                        customer=subscription.stripe_customer_id if subscription else None,
                        metadata={
                            "user_id": user.id,
                            "usage_record_id": usage_record.id
                        },
                        description=f"API usage: {usage_record.tokens_used} tokens with {usage_record.model}"
                    )
                    
                    # Record the payment
                    payment = Payment(
                        user_id=user.id,
                        stripe_payment_id=payment_intent.id,
                        amount=cost,
                        status="pending",
                        payment_method="card",
                        description=f"API usage: {usage_record.tokens_used} tokens with {usage_record.model}"
                    )
                    db.add(payment)
                    db.commit()
                    
                    return {
                        "payment_intent_id": payment_intent.id,
                        "client_secret": payment_intent.client_secret,
                        "amount": cost,
                        "tokens": usage_record.tokens_used
                    }
            
            # For subscription plans or costs below threshold, just return the usage details
            return {
                "cost": cost,
                "tokens": usage_record.tokens_used,
                "model": usage_record.model
            }
            
        except stripe.error.StripeError as e:
            db.rollback()
            raise e
    
    @staticmethod
    def handle_webhook(payload: Dict[str, Any], signature: str, db: Session) -> Dict[str, Any]:
        """
        Handle Stripe webhook events
        
        Args:
            payload: Webhook payload
            signature: Stripe signature header
            db: Database session
            
        Returns:
            Result of webhook processing
        """
        try:
            # Verify webhook signature
            webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_sample")
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
            
            # Handle different event types
            if event["type"] == "invoice.payment_succeeded":
                invoice = event["data"]["object"]
                subscription_id = invoice.get("subscription")
                
                if subscription_id:
                    # Update subscription status
                    subscription = db.query(Subscription).filter(
                        Subscription.stripe_subscription_id == subscription_id
                    ).first()
                    
                    if subscription:
                        subscription.status = "active"
                        db.commit()
                
            elif event["type"] == "invoice.payment_failed":
                invoice = event["data"]["object"]
                subscription_id = invoice.get("subscription")
                
                if subscription_id:
                    # Update subscription status
                    subscription = db.query(Subscription).filter(
                        Subscription.stripe_subscription_id == subscription_id
                    ).first()
                    
                    if subscription:
                        subscription.status = "past_due"
                        db.commit()
                
            elif event["type"] == "customer.subscription.updated":
                subscription_data = event["data"]["object"]
                subscription_id = subscription_data.get("id")
                
                if subscription_id:
                    # Update subscription details
                    subscription = db.query(Subscription).filter(
                        Subscription.stripe_subscription_id == subscription_id
                    ).first()
                    
                    if subscription:
                        subscription.status = subscription_data.get("status")
                        subscription.current_period_start = datetime.fromtimestamp(subscription_data.get("current_period_start"))
                        subscription.current_period_end = datetime.fromtimestamp(subscription_data.get("current_period_end"))
                        db.commit()
                
            elif event["type"] == "customer.subscription.deleted":
                subscription_data = event["data"]["object"]
                subscription_id = subscription_data.get("id")
                
                if subscription_id:
                    # Update subscription status
                    subscription = db.query(Subscription).filter(
                        Subscription.stripe_subscription_id == subscription_id
                    ).first()
                    
                    if subscription:
                        subscription.status = "canceled"
                        db.commit()
                
            # Return success
            return {"status": "success", "event": event["type"]}
            
        except (stripe.error.SignatureVerificationError, ValueError) as e:
            db.rollback()
            raise e 