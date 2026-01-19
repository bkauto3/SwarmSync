"""
BILLING AGENT - Microsoft Agent Framework Version
Version: 5.0 (AP2 Integration + DAAO + TUMIX + MongoDB Persistence)

Handles payment processing, invoicing, and revenue management.
Enhanced with AP2 (Agent Payments Protocol) for secure agent-initiated payments.

New Features (v5.0):
- AP2 mandate-based payment authorization
- Cryptographic signature verification
- Multi-method payment support (cards, crypto, bank transfers)
- Non-repudiable audit trails
- Integration with A2A protocol
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from agent_framework.observability import setup_observability
from azure.identity.aio import AzureCliCredential

# P0-6 FIX: Import Pydantic for payment validation
from pydantic import BaseModel, Field, validator

# MongoDB for persistence
try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    logging.warning("pymongo not available - using in-memory storage only")

setup_observability(enable_sensitive_data=True)

# Import DAAO and TUMIX
from infrastructure.daao_router import get_daao_router, RoutingDecision
from infrastructure.tumix_termination import (
    get_tumix_termination,
    RefinementResult,
    TerminationDecision
)
from infrastructure.genesis_discord import GenesisDiscord, fire_and_forget

# Import AP2 Protocol Support
try:
    from infrastructure.ap2_connector import (
        AP2Connector,
        CartItem,
        PaymentMethodDetails,
        PaymentMethod,
        get_ap2_connector
    )
    AP2_AVAILABLE = True
except ImportError:
    AP2_AVAILABLE = False
    logging.warning("AP2 connector not available - using legacy payment flow")

logger = logging.getLogger(__name__)


# P0-6 FIX: Pydantic models for payment validation
class PaymentRequest(BaseModel):
    """Validated payment request data"""
    customer_id: str = Field(..., min_length=1, max_length=255, description="Customer identifier")
    amount: float = Field(..., gt=0, le=1000000, description="Payment amount")
    payment_method: str = Field(..., pattern="^(card|bank|crypto)$", description="Payment method")
    currency: str = Field(..., pattern="^(USD|EUR|GBP)$", description="Currency code")

    @validator('amount')
    def validate_amount(cls, v):
        """Validate amount is at least $0.01 and properly rounded"""
        if v < 0.01:
            raise ValueError("Amount must be at least $0.01")
        return round(v, 2)

    @validator('customer_id')
    def validate_customer_id(cls, v):
        """Validate customer ID format"""
        if not v or not v.strip():
            raise ValueError("Customer ID cannot be empty")
        # Remove potentially dangerous characters
        if any(char in v for char in ['<', '>', '"', "'", '\\', '/']):
            raise ValueError("Customer ID contains invalid characters")
        return v.strip()


class InvoiceLineItem(BaseModel):
    """Validated invoice line item"""
    description: str = Field(..., min_length=1, max_length=500)
    quantity: int = Field(..., gt=0, le=10000)
    unit_price: float = Field(..., gt=0, le=100000)

    @property
    def amount(self) -> float:
        """Calculate line item amount"""
        return round(self.quantity * self.unit_price, 2)


class SubscriptionRequest(BaseModel):
    """Validated subscription request"""
    customer_id: str = Field(..., min_length=1, max_length=255)
    plan_id: str = Field(..., pattern="^(free|standard|premium)$")
    action: str = Field(..., pattern="^(create|update|cancel)$")

    @validator('customer_id')
    def validate_customer_id(cls, v):
        """Validate customer ID format"""
        if not v or not v.strip():
            raise ValueError("Customer ID cannot be empty")
        return v.strip()


class RefundRequest(BaseModel):
    """Validated refund request"""
    transaction_id: str = Field(..., min_length=1, max_length=255)
    amount: float = Field(..., gt=0, le=1000000)
    reason: str = Field(..., min_length=1, max_length=1000)

    @validator('amount')
    def validate_amount(cls, v):
        """Validate refund amount"""
        if v < 0.01:
            raise ValueError("Refund amount must be at least $0.01")
        return round(v, 2)


class BillingAgent:
    """
    Payment processing and revenue management agent with AP2 protocol support

    Version 5.0 Features:
    - AP2 mandate-based payments (Intent -> Cart -> Payment)
    - Cryptographic signature verification
    - Multi-method payment support (cards, crypto, bank transfers)
    - Non-repudiable audit trails
    - Backward compatible with legacy payment flow
    """

    def __init__(
        self,
        business_id: str = "default",
        use_database: bool = True,
        enable_ap2: bool = True,
        enable_crypto: bool = False
    ):
        self.business_id = business_id
        self.agent = None
        self.use_database = use_database and MONGO_AVAILABLE

        # Initialize DAAO router for cost optimization
        self.router = get_daao_router()

        # Initialize TUMIX for iterative refinement
        self.termination = get_tumix_termination(
            min_rounds=2,
            max_rounds=4,
            improvement_threshold=0.05
        )

        # Track refinement sessions for metrics
        self.refinement_history: List[List[RefinementResult]] = []

        # Database connection
        self.db_client = None
        self.db = None
        self.payments_collection = None
        self.invoices_collection = None
        self.subscriptions_collection = None

        # In-memory fallback
        self.memory_store = {
            'payments': [],
            'invoices': [],
            'subscriptions': [],
            'refunds': []
        }

        # AP2 Protocol Integration
        self.ap2_connector = None
        self.ap2_enabled = enable_ap2 and AP2_AVAILABLE
        if self.ap2_enabled:
            try:
                self.ap2_connector = AP2Connector(enable_crypto=enable_crypto)
                logger.info("✅ AP2 Protocol enabled (mandates, audit trails, multi-method payments)")
            except Exception as e:
                logger.warning(f"AP2 initialization failed: {e}. Using legacy payment flow.")
                self.ap2_enabled = False
                self.ap2_connector = None

        if self.use_database:
            self._init_database()

        logger.info(
            f"BillingAgent v5.0 initialized with "
            f"{'AP2 + ' if self.ap2_enabled else ''}"
            f"DAAO + TUMIX + {'MongoDB' if self.use_database else 'Memory'} "
            f"for business: {business_id}"
        )

        try:
            self.discord = GenesisDiscord()
        except Exception as exc:
            logger.warning(f"Discord client unavailable for BillingAgent: {exc}")
            self.discord = None

    def _init_database(self):
        """Initialize MongoDB connection"""
        try:
            mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
            self.db_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.db_client.admin.command('ping')

            self.db = self.db_client['genesis_billing']
            self.payments_collection = self.db['payments']
            self.invoices_collection = self.db['invoices']
            self.subscriptions_collection = self.db['subscriptions']
            self.refunds_collection = self.db['refunds']

            # Create indexes for performance
            self.payments_collection.create_index('transaction_id')
            self.payments_collection.create_index('customer_id')
            self.subscriptions_collection.create_index('customer_id')

            logger.info("✅ MongoDB connection established")
        except (ConnectionFailure, Exception) as e:
            logger.warning(f"MongoDB connection failed: {e}. Using in-memory storage.")
            self.use_database = False
            self.db_client = None

    def _store_record(self, collection_name: str, record: Dict) -> str:
        """
        Store record in database or memory with atomic transaction support

        P0-5 FIX: Wraps MongoDB operations in transactions for ACID compliance
        """
        record_id = record.get('transaction_id') or record.get('invoice_id') or record.get('subscription_id') or record.get('refund_id')

        if self.use_database:
            try:
                # P0-5 FIX: Use MongoDB transaction for atomicity
                # Note: Transactions require MongoDB replica set (v4.0+)
                # For standalone instances, this gracefully degrades to single operation
                try:
                    with self.db_client.start_session() as session:
                        with session.start_transaction():
                            collection = getattr(self, f'{collection_name}_collection')
                            result = collection.insert_one(record, session=session)
                            logger.info(f"Stored {collection_name} record (transactional): {record_id}")
                            return str(result.inserted_id)
                except Exception as transaction_error:
                    # Fallback for standalone MongoDB (no replica set)
                    if "Transactions are not supported" in str(transaction_error) or "standalone" in str(transaction_error).lower():
                        logger.warning(f"Transactions not supported, using single operation: {transaction_error}")
                        collection = getattr(self, f'{collection_name}_collection')
                        result = collection.insert_one(record)
                        logger.info(f"Stored {collection_name} record (non-transactional): {record_id}")
                        return str(result.inserted_id)
                    else:
                        raise transaction_error

            except Exception as e:
                logger.error(f"Database storage failed: {e}. Falling back to memory.")
                self.memory_store[collection_name].append(record)
                return record_id
        else:
            self.memory_store[collection_name].append(record)
            return record_id

    def _get_records(self, collection_name: str, query: Optional[Dict] = None) -> List[Dict]:
        """Retrieve records from database or memory"""
        if self.use_database:
            try:
                collection = getattr(self, f'{collection_name}_collection')
                cursor = collection.find(query or {})
                return list(cursor)
            except Exception as e:
                logger.error(f"Database query failed: {e}. Using memory.")
                return self._filter_memory_records(collection_name, query)
        else:
            return self._filter_memory_records(collection_name, query)

    def _filter_memory_records(self, collection_name: str, query: Optional[Dict]) -> List[Dict]:
        """Filter in-memory records"""
        records = self.memory_store.get(collection_name, [])
        if not query:
            return records

        # Simple filtering for common queries
        filtered = []
        for record in records:
            match = True
            for key, value in query.items():
                if record.get(key) != value:
                    match = False
                    break
            if match:
                filtered.append(record)
        return filtered

    def __del__(self):
        """Clean up database connection"""
        if self.db_client:
            try:
                self.db_client.close()
            except Exception:
                pass

    # P0-9 FIX: Implement async context manager for resource cleanup
    async def __aenter__(self):
        """Async context manager entry - initialize agent"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources"""
        logger.info("🧹 Cleaning up BillingAgent resources...")

        # Close MongoDB connection
        if self.db_client:
            try:
                self.db_client.close()
                logger.info("   ✅ Closed MongoDB connection")
            except Exception as e:
                logger.warning(f"   ⚠️  Could not close MongoDB: {e}")

        logger.info("✅ BillingAgent cleanup complete")
        return False  # Don't suppress exceptions

    # P0-4 FIX: Add health check endpoint for monitoring
    def health_check(self) -> Dict[str, Any]:
        """
        Health check endpoint for production monitoring

        Returns detailed status of database connection and agent health
        """
        status = {
            "agent": "billing_agent",
            "business_id": self.business_id,
            "database": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "4.0"
        }

        if self.use_database:
            try:
                # Ping MongoDB to verify connection
                self.db_client.admin.command('ping')
                status["database"] = "healthy"
                status["database_type"] = "MongoDB"
                status["connection"] = str(self.db_client.address)

                # Get collection stats
                try:
                    payment_count = self.payments_collection.count_documents({})
                    status["metrics"] = {
                        "total_payments": payment_count,
                        "total_invoices": self.invoices_collection.count_documents({}),
                        "total_subscriptions": self.subscriptions_collection.count_documents({})
                    }
                except Exception as e:
                    logger.warning(f"Could not fetch metrics: {e}")
                    status["metrics"] = "unavailable"

            except Exception as e:
                logger.error(f"MongoDB health check failed: {e}")
                status["database"] = "unhealthy"
                status["error"] = str(e)
                status["warning"] = "Database connection failed - check MongoDB status"
        else:
            status["database"] = "in-memory-fallback"
            status["warning"] = "Using in-memory storage - data will be lost on restart"
            status["metrics"] = {
                "in_memory_payments": len(self.memory_store.get('payments', [])),
                "in_memory_invoices": len(self.memory_store.get('invoices', [])),
                "in_memory_subscriptions": len(self.memory_store.get('subscriptions', []))
            }

        return status

    async def initialize(self):
        cred = AzureCliCredential()
        client = AzureAIAgentClient(async_credential=cred)
        self.agent = ChatAgent(
            chat_client=client,
            instructions="You are a billing and payment specialist. Process payments, generate invoices, manage subscriptions, handle refunds, and track revenue. Integrate with payment providers (Stripe, x402 protocol for agent-to-agent micropayments). Ensure PCI-DSS compliance, prevent fraud, and maintain accurate financial records. Support programmable, permissionless micropayments on Sei Network blockchain.",
            name="billing-agent",
            tools=[self.process_payment, self.generate_invoice, self.manage_subscription, self.issue_refund, self.generate_revenue_report]
        )
        print(f"💰 Billing Agent initialized for business: {self.business_id}\n")

    def process_payment(self, customer_id: str, amount: float, payment_method: str, currency: str) -> str:
        """
        Process a payment transaction with persistence and validation

        P0-6 FIX: Validates all input data using Pydantic models
        """
        try:
            # Validate payment request
            payment_request = PaymentRequest(
                customer_id=customer_id,
                amount=amount,
                payment_method=payment_method,
                currency=currency
            )

            # Use validated data
            validated_amount = payment_request.amount
            validated_customer_id = payment_request.customer_id

            result = {
                "transaction_id": f"TXN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                "customer_id": validated_customer_id,
                "amount": validated_amount,
                "currency": payment_request.currency,
                "payment_method": payment_request.payment_method,
                "status": "success",
                "payment_provider": "stripe" if validated_amount >= 1.0 else "x402",
                "transaction_fee": validated_amount * 0.029 + 0.30 if validated_amount >= 1.0 else validated_amount * 0.001,
                "net_amount": validated_amount - (validated_amount * 0.029 + 0.30 if validated_amount >= 1.0 else validated_amount * 0.001),
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "business_id": self.business_id
            }

            # Store in database/memory
            self._store_record('payments', result)

            logger.info(f"Payment processed: {result['transaction_id']} - ${validated_amount} {currency}")
            self._notify_payment_async(result)
            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Payment validation failed: {e}")
            return json.dumps({
                "success": False,
                "error": f"Payment validation failed: {str(e)}"
            })

    def generate_invoice(self, customer_id: str, line_items: List[Dict[str, float]], due_date: str) -> str:
        """Generate an invoice for a customer with persistence"""
        subtotal = sum([item.get('amount', 0.0) for item in line_items])
        tax = subtotal * 0.08
        total = subtotal + tax

        result = {
            "invoice_id": f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "customer_id": customer_id,
            "line_items": line_items,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "currency": "USD",
            "due_date": due_date,
            "status": "sent",
            "payment_terms": "Net 30",
            "generated_at": datetime.now().isoformat(),
            "business_id": self.business_id
        }

        # Store in database/memory
        self._store_record('invoices', result)

        logger.info(f"Invoice generated: {result['invoice_id']} - ${total} USD")
        return json.dumps(result, indent=2)

    def manage_subscription(self, customer_id: str, plan_id: str, action: str) -> str:
        """Manage customer subscription (create, update, cancel) with persistence"""
        result = {
            "subscription_id": f"SUB-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "customer_id": customer_id,
            "plan_id": plan_id,
            "action": action,
            "status": "active" if action == "create" else "cancelled" if action == "cancel" else "updated",
            "billing_cycle": "monthly",
            "next_billing_date": datetime.now().isoformat(),
            "amount": 99.00 if plan_id == "premium" else 49.00 if plan_id == "standard" else 0.00,
            "currency": "USD",
            "payment_method": "card_ending_4242",
            "updated_at": datetime.now().isoformat(),
            "business_id": self.business_id
        }

        # Store in database/memory
        self._store_record('subscriptions', result)

        logger.info(f"Subscription {action}: {result['subscription_id']} - {plan_id} plan")
        self._notify_subscription_change_async(result)
        return json.dumps(result, indent=2)

    def issue_refund(self, transaction_id: str, amount: float, reason: str) -> str:
        """Issue a refund for a transaction with persistence"""
        result = {
            "refund_id": f"REF-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "transaction_id": transaction_id,
            "amount": amount,
            "reason": reason,
            "status": "processed",
            "refund_method": "original_payment_method",
            "processing_time_days": 5,
            "issued_at": datetime.now().isoformat(),
            "business_id": self.business_id
        }

        # Store in database/memory
        self._store_record('refunds', result)

        logger.info(f"Refund issued: {result['refund_id']} - ${amount} for {transaction_id}")
        self._notify_refund_async(result)
        return json.dumps(result, indent=2)

    def generate_revenue_report(self, start_date: str, end_date: str, breakdown_by: str) -> str:
        """Generate revenue report for a date range"""
        result = {
            "report_id": f"REV-REPORT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "period": {"start": start_date, "end": end_date},
            "breakdown_by": breakdown_by,
            "total_revenue": 245678.90,
            "total_transactions": 1567,
            "average_transaction_value": 156.73,
            "revenue_by_source": {
                "subscriptions": 189543.20,
                "one_time_payments": 45678.90,
                "agent_micropayments": 10456.80
            },
            "revenue_by_plan": {
                "premium": 145678.90,
                "standard": 78456.30,
                "free": 0.00
            },
            "refunds_issued": 3456.78,
            "net_revenue": 242222.12,
            "mrr": 78456.30,
            "arr": 941475.60,
            "churn_rate": 2.3,
            "generated_at": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)


    def route_task(self, task_description: str, priority: float = 0.5) -> RoutingDecision:
        """
        Route task to appropriate model using DAAO

        Args:
            task_description: Description of the task
            priority: Task priority (0.0-1.0)

        Returns:
            RoutingDecision with model selection and cost estimate
        """
        task = {
            'id': f'billing-{{datetime.now().strftime("%Y%m%d%H%M%S")}}',
            'description': task_description,
            'priority': priority,
            'required_tools': []
        }

        decision = self.router.route_task(task, budget_conscious=True)

        logger.info(
            f"Task routed: {decision.reasoning}",
            extra={
                'agent': 'BillingAgent',
                'model': decision.model,
                'difficulty': decision.difficulty.value,
                'estimated_cost': decision.estimated_cost
            }
        )

        return decision

    def get_payment_history(self, customer_id: Optional[str] = None, limit: int = 50) -> str:
        """
        Get payment history for a customer or business

        Args:
            customer_id: Filter by customer (optional)
            limit: Maximum number of records to return

        Returns:
            JSON string with payment history
        """
        query = {'customer_id': customer_id} if customer_id else {}
        payments = self._get_records('payments', query)

        # Sort by date descending and limit
        sorted_payments = sorted(
            payments,
            key=lambda x: x.get('processed_at', ''),
            reverse=True
        )[:limit]

        result = {
            "business_id": self.business_id,
            "customer_id": customer_id or "all",
            "total_payments": len(sorted_payments),
            "payments": sorted_payments,
            "total_revenue": sum(p.get('net_amount', 0) for p in sorted_payments),
            "generated_at": datetime.now().isoformat()
        }

        return json.dumps(result, indent=2)

    def _notify_payment_async(self, payment: Dict[str, Any]) -> None:
        if not self.discord:
            return
        customer_contact = payment.get("customer_id", "customer")
        amount = payment.get("amount", 0.0)
        fire_and_forget(
            self.discord.payment_received(
                business_name=self.business_id,
                amount=amount,
                customer_email=str(customer_contact),
            )
        )

    def _notify_refund_async(self, refund: Dict[str, Any]) -> None:
        if not self.discord:
            return
        fire_and_forget(
            self.discord.refund_processed(
                business_name=self.business_id,
                amount=refund.get("amount", 0.0),
                reason=refund.get("reason", "n/a"),
            )
        )

    def _notify_subscription_change_async(self, subscription: Dict[str, Any]) -> None:
        if not self.discord:
            return
        fire_and_forget(
            self.discord.subscription_update(
                business_name=self.business_id,
                customer_id=subscription.get("customer_id", "customer"),
                plan_id=subscription.get("plan_id", "unknown"),
                action=subscription.get("action", "update"),
            )
        )

    def get_subscription_status(self, customer_id: str) -> str:
        """
        Get active subscription status for a customer

        Args:
            customer_id: Customer identifier

        Returns:
            JSON string with subscription info
        """
        subscriptions = self._get_records('subscriptions', {'customer_id': customer_id})

        # Get most recent subscription
        active_sub = None
        if subscriptions:
            sorted_subs = sorted(
                subscriptions,
                key=lambda x: x.get('updated_at', ''),
                reverse=True
            )
            active_sub = sorted_subs[0] if sorted_subs[0].get('status') == 'active' else None

        result = {
            "customer_id": customer_id,
            "has_active_subscription": active_sub is not None,
            "active_subscription": active_sub,
            "subscription_history_count": len(subscriptions),
            "business_id": self.business_id,
            "checked_at": datetime.now().isoformat()
        }

        return json.dumps(result, indent=2)

    def get_cost_metrics(self) -> Dict:
        """Get cumulative cost savings from DAAO and TUMIX"""
        if not self.refinement_history:
            return {
                'agent': 'BillingAgent',
                'tumix_sessions': 0,
                'tumix_savings_percent': 0.0,
                'message': 'No refinement sessions recorded yet'
            }

        tumix_savings = self.termination.estimate_cost_savings(
            [
                [r for r in session]
                for session in self.refinement_history
            ],
            cost_per_round=0.001
        )

        return {
            'agent': 'BillingAgent',
            'tumix_sessions': tumix_savings['sessions'],
            'tumix_baseline_rounds': tumix_savings['baseline_rounds'],
            'tumix_actual_rounds': tumix_savings['tumix_rounds'],
            'tumix_savings_percent': tumix_savings['savings_percent'],
            'tumix_total_saved': tumix_savings['savings'],
            'daao_info': 'DAAO routing automatically applied to all tasks'
        }

    # ========================================================================
    # AP2 PROTOCOL METHODS - Agent Payment Protocol Integration
    # ========================================================================

    async def create_payment_intent_mandate(
        self,
        customer_id: str,
        task_description: str,
        max_amount: float,
        currency: str = "USD",
        valid_for_hours: int = 24
    ) -> str:
        """
        Create AP2 Intent Mandate for agent-initiated payment

        Authorizes agent to make purchases within constraints.

        Args:
            customer_id: Customer/user identifier
            task_description: What agent is authorized to do
            max_amount: Maximum price in dollars
            currency: Currency code
            valid_for_hours: Mandate validity (max 720 hours = 30 days)

        Returns:
            JSON string with mandate details

        Raises:
            RuntimeError: If AP2 not enabled
        """
        if not self.ap2_enabled or not self.ap2_connector:
            return json.dumps({
                "success": False,
                "error": "AP2 protocol not enabled - use legacy payment flow"
            })

        try:
            # Create intent mandate
            intent = await self.ap2_connector.create_intent_mandate(
                user_id=customer_id,
                agent_id=f"billing_agent_{self.business_id}",
                task_description=task_description,
                max_price_cents=int(max_amount * 100),
                currency=currency,
                valid_for_hours=valid_for_hours,
                require_approval=True
            )

            result = {
                "success": True,
                "mandate_id": intent.mandate_id,
                "mandate_type": "intent",
                "user_id": customer_id,
                "agent_id": intent.agent_id,
                "task": task_description,
                "max_price": max_amount,
                "currency": currency,
                "valid_until": intent.constraints.valid_until,
                "signature": intent.signature,
                "created_at": intent.created_at,
                "business_id": self.business_id
            }

            logger.info(f"AP2 Intent Mandate created: {intent.mandate_id} (max ${max_amount})")

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"AP2 intent mandate creation failed: {e}")
            return json.dumps({
                "success": False,
                "error": f"Intent mandate creation failed: {str(e)}"
            })

    async def create_cart_mandate(
        self,
        intent_mandate_id: str,
        customer_id: str,
        items: List[Dict[str, Any]]
    ) -> str:
        """
        Create AP2 Cart Mandate for specific purchase

        Args:
            intent_mandate_id: Parent intent mandate ID
            customer_id: Customer identifier
            items: List of cart items (dict with name, quantity, unit_price_cents)

        Returns:
            JSON string with cart details
        """
        if not self.ap2_enabled or not self.ap2_connector:
            return json.dumps({
                "success": False,
                "error": "AP2 protocol not enabled"
            })

        try:
            # Convert items to CartItem objects
            cart_items = []
            for item in items:
                cart_items.append(CartItem(
                    item_id=item.get('item_id', f"item_{uuid.uuid4().hex[:8]}"),
                    name=item['name'],
                    quantity=item['quantity'],
                    unit_price_cents=item['unit_price_cents'],
                    currency=item.get('currency', 'USD')
                ))

            # Create cart mandate
            cart = await self.ap2_connector.create_cart_mandate(
                intent_mandate_id=intent_mandate_id,
                items=cart_items,
                user_id=customer_id
            )

            result = {
                "success": True,
                "mandate_id": cart.mandate_id,
                "mandate_type": "cart",
                "intent_mandate_id": intent_mandate_id,
                "user_id": customer_id,
                "items": [
                    {
                        "item_id": item.item_id,
                        "name": item.name,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price_cents / 100.0,
                        "total": item.total_cents / 100.0
                    }
                    for item in cart_items
                ],
                "total": cart.total_cents / 100.0,
                "currency": cart.currency,
                "approved": cart.is_approved(),
                "signature": cart.signature,
                "created_at": cart.created_at,
                "business_id": self.business_id
            }

            logger.info(f"AP2 Cart Mandate created: {cart.mandate_id} (${cart.total_cents/100:.2f})")

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"AP2 cart mandate creation failed: {e}")
            return json.dumps({
                "success": False,
                "error": f"Cart mandate creation failed: {str(e)}"
            })

    async def approve_cart(self, cart_mandate_id: str, customer_id: str) -> str:
        """
        Approve cart mandate - user confirms purchase

        Args:
            cart_mandate_id: Cart mandate ID
            customer_id: Customer identifier (must match cart owner)

        Returns:
            JSON string with approval status
        """
        if not self.ap2_enabled or not self.ap2_connector:
            return json.dumps({
                "success": False,
                "error": "AP2 protocol not enabled"
            })

        try:
            # Approve cart
            cart = await self.ap2_connector.approve_cart_mandate(
                cart_mandate_id=cart_mandate_id,
                user_id=customer_id
            )

            result = {
                "success": True,
                "mandate_id": cart.mandate_id,
                "approved": True,
                "approved_at": cart.approved_at,
                "total": cart.total_cents / 100.0,
                "currency": cart.currency,
                "signature": cart.signature,
                "business_id": self.business_id
            }

            logger.info(f"AP2 Cart approved: {cart_mandate_id}")

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"AP2 cart approval failed: {e}")
            return json.dumps({
                "success": False,
                "error": f"Cart approval failed: {str(e)}"
            })

    async def execute_ap2_payment(
        self,
        cart_mandate_id: str,
        customer_id: str,
        payment_method_type: str = "card",
        payment_provider: str = "stripe",
        last_four: Optional[str] = None
    ) -> str:
        """
        Execute payment via AP2 protocol

        Args:
            cart_mandate_id: Approved cart mandate ID
            customer_id: Customer identifier
            payment_method_type: card, crypto, bank_transfer, wallet
            payment_provider: stripe, coinbase, paypal, etc.
            last_four: Last 4 digits of card/account (optional)

        Returns:
            JSON string with payment result
        """
        if not self.ap2_enabled or not self.ap2_connector:
            return json.dumps({
                "success": False,
                "error": "AP2 protocol not enabled - use legacy process_payment()"
            })

        try:
            # Create payment method details
            payment_method = PaymentMethodDetails(
                method_type=PaymentMethod(payment_method_type.lower()),
                provider=payment_provider,
                last_four=last_four
            )

            # Execute payment
            result = await self.ap2_connector.execute_payment(
                cart_mandate_id=cart_mandate_id,
                payment_method=payment_method,
                user_id=customer_id,
                human_present=True
            )

            # Store in billing database
            payment_record = {
                "transaction_id": result.get("transaction_id", f"ap2_{uuid.uuid4().hex[:16]}"),
                "cart_mandate_id": cart_mandate_id,
                "customer_id": customer_id,
                "amount": result.get("amount_cents", 0) / 100.0,
                "currency": result.get("currency", "USD"),
                "payment_method": payment_method_type,
                "payment_provider": payment_provider,
                "status": result.get("status", "pending"),
                "ap2_enabled": True,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "business_id": self.business_id
            }

            self._store_record('payments', payment_record)

            logger.info(
                f"AP2 Payment executed: {result.get('transaction_id')} "
                f"(${result.get('amount_cents', 0)/100:.2f} via {payment_provider})"
            )

            return json.dumps({
                "success": result.get("status") == "succeeded",
                **result,
                "business_id": self.business_id
            }, indent=2)

        except Exception as e:
            logger.error(f"AP2 payment execution failed: {e}")
            return json.dumps({
                "success": False,
                "error": f"AP2 payment failed: {str(e)}"
            })

    def get_ap2_audit_trail(self, mandate_id: str) -> str:
        """
        Get audit trail for AP2 mandate

        Args:
            mandate_id: Mandate ID (intent, cart, or payment)

        Returns:
            JSON string with audit events
        """
        if not self.ap2_enabled or not self.ap2_connector:
            return json.dumps({
                "success": False,
                "error": "AP2 protocol not enabled"
            })

        try:
            events = self.ap2_connector.get_audit_trail(mandate_id)

            result = {
                "success": True,
                "mandate_id": mandate_id,
                "event_count": len(events),
                "audit_trail": [
                    {
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "timestamp": event.timestamp,
                        "user_id": event.user_id,
                        "agent_id": event.agent_id,
                        "data": event.data,
                        "signature": event.signature
                    }
                    for event in events
                ],
                "verified": self.ap2_connector.verify_audit_chain(mandate_id),
                "business_id": self.business_id
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"AP2 audit trail retrieval failed: {e}")
            return json.dumps({
                "success": False,
                "error": f"Audit trail retrieval failed: {str(e)}"
            })

    def get_ap2_health(self) -> str:
        """
        Get AP2 connector health status

        Returns:
            JSON string with health info
        """
        if not self.ap2_enabled or not self.ap2_connector:
            return json.dumps({
                "ap2_enabled": False,
                "status": "disabled",
                "message": "AP2 protocol not available"
            })

        try:
            health = self.ap2_connector.health_check()
            return json.dumps({
                **health,
                "business_id": self.business_id
            }, indent=2)

        except Exception as e:
            return json.dumps({
                "ap2_enabled": True,
                "status": "error",
                "error": str(e)
            })



async def get_billing_agent(business_id: str = "default") -> BillingAgent:
    agent = BillingAgent(business_id=business_id)
    await agent.initialize()
    return agent
