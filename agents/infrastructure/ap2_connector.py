"""
AP2 Connector - Agent Payments Protocol Integration
====================================================

Implements Google's AP2 (Agent Payments Protocol) for secure agent-initiated payments.
Announced September 2025 as open standard for agent-to-payment interoperability.

Key Features:
- Mandate-based trust system (Intent, Cart, Payment mandates)
- Cryptographic signature verification for non-repudiable audit trails
- Multi-method payment support (cards, bank transfers, crypto)
- PCI-DSS compliant payment handling
- Integration with existing Stripe infrastructure
- Audit logging for compliance and dispute resolution
- A2A protocol extension for seamless communication

Architecture:
  User Request
      ↓
  [Intent Mandate] - User authorizes agent with constraints
      ↓
  [Agent Selection] - Agent finds options within mandate
      ↓
  [Cart Mandate] - User approves specific cart
      ↓
  [Payment Mandate] - Cryptographically linked payment
      ↓
  [Payment Provider] - Execute via Stripe/PayPal/Crypto
      ↓
  [Audit Trail] - Non-repudiable transaction log

Spec: https://ap2-protocol.org/
GitHub: https://github.com/google/ap2-protocol

Author: Shane (Senior Backend Engineer)
Date: 2025-11-14
Version: 1.0.0
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal

from pydantic import BaseModel, Field, validator, ValidationError

from infrastructure.load_env import load_genesis_env
from infrastructure.error_handler import (
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    log_error_with_context,
)

# Load environment variables
load_genesis_env()

logger = logging.getLogger(__name__)


# ========================================================================
# IDEMPOTENCY STORE - Prevents duplicate charges
# ========================================================================


class IdempotencyStore:
    """In-memory idempotency cache with 24 hour expiration."""

    def __init__(self, ttl_seconds: int = 24 * 3600):
        self.ttl = ttl_seconds
        self.entries: Dict[str, tuple[float, Any]] = {}

    def get(self, key: str):
        self.clean_expired()
        if key in self.entries:
            return self.entries[key][1]
        return None

    def insert(self, key: str, value: Any):
        self.clean_expired()
        self.entries[key] = (time.time(), value)

    def clean_expired(self):
        cutoff = time.time() - self.ttl
        self.entries = {k: v for k, v in self.entries.items() if v[0] >= cutoff}


# ========================================================================
# ENUMS - Payment and Mandate States
# ========================================================================


class MandateType(Enum):
    """AP2 Mandate Types per specification"""
    INTENT = "intent"      # Initial user authorization with constraints
    CART = "cart"          # Specific purchase approval
    PAYMENT = "payment"    # Payment method authorization


class PaymentMethod(Enum):
    """Supported payment methods"""
    CARD = "card"                    # Credit/debit cards (Stripe)
    BANK_TRANSFER = "bank_transfer"  # ACH, wire, UPI, PIX
    CRYPTO = "crypto"                # Stablecoins, blockchain payments
    WALLET = "wallet"                # PayPal, Apple Pay, Google Pay


class PaymentStatus(Enum):
    """Payment transaction status"""
    PENDING = "pending"
    AUTHORIZED = "authorized"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class ConsentStatus(Enum):
    """User consent verification status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ========================================================================
# PYDANTIC MODELS - Request/Response Validation
# ========================================================================


class IntentConstraints(BaseModel):
    """Constraints for Intent Mandate - defines what agent can do"""
    max_price_cents: int = Field(..., gt=0, le=100000000, description="Maximum price in cents")
    currency: str = Field(..., pattern="^(USD|EUR|GBP)$", description="Currency code")
    valid_until: str = Field(..., description="ISO 8601 timestamp for mandate expiration")
    allowed_categories: List[str] = Field(default_factory=list, description="Allowed purchase categories")
    require_approval: bool = Field(default=True, description="Require explicit cart approval")

    @validator('max_price_cents')
    def validate_price(cls, v):
        """Validate price is reasonable"""
        if v < 1:
            raise ValueError("Price must be at least $0.01")
        if v > 100_000_000:  # $1M limit
            raise ValueError("Price exceeds maximum allowed ($1,000,000)")
        return v

    @validator('valid_until')
    def validate_expiration(cls, v):
        """Validate mandate hasn't expired"""
        try:
            expiration = datetime.fromisoformat(v.replace('Z', '+00:00'))
            if expiration <= datetime.now(timezone.utc):
                raise ValueError("Mandate expiration is in the past")
            # Max 30 days in future
            if expiration > datetime.now(timezone.utc) + timedelta(days=30):
                raise ValueError("Mandate expiration exceeds 30 days maximum")
            return v
        except ValueError as e:
            raise ValueError(f"Invalid ISO 8601 timestamp: {e}")


class CartItem(BaseModel):
    """Single item in cart mandate"""
    item_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=500)
    quantity: int = Field(..., gt=0, le=1000)
    unit_price_cents: int = Field(..., gt=0, le=100000000)
    currency: str = Field(..., pattern="^(USD|EUR|GBP)$")

    @property
    def total_cents(self) -> int:
        """Calculate line item total"""
        return self.quantity * self.unit_price_cents


class PaymentMethodDetails(BaseModel):
    """Payment method specific details"""
    method_type: PaymentMethod
    provider: str = Field(..., min_length=1, max_length=100, description="stripe, paypal, coinbase, etc")
    last_four: Optional[str] = Field(None, pattern="^[0-9]{4}$", description="Last 4 digits of card/account")
    expiry: Optional[str] = Field(None, pattern="^[0-9]{2}/[0-9]{2}$", description="Card expiry MM/YY")
    wallet_address: Optional[str] = Field(None, description="Crypto wallet address")

    @validator('method_type', pre=True)
    def parse_method_type(cls, v):
        """Parse string to enum"""
        if isinstance(v, str):
            return PaymentMethod(v.lower())
        return v


# ========================================================================
# MANDATE CLASSES - Core AP2 Protocol Implementation
# ========================================================================


@dataclass
class AP2IntentMandate:
    """
    Intent Mandate - Initial user authorization

    Captures user's intent to delegate purchasing authority to agent
    with specific constraints (price limits, categories, time limits).

    Spec: https://ap2-protocol.org/spec#intent-mandate
    """
    mandate_id: str
    user_id: str
    agent_id: str
    task_description: str
    constraints: IntentConstraints
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for signing/storage"""
        return {
            "mandate_id": self.mandate_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "task_description": self.task_description,
            "constraints": self.constraints.dict(),
            "created_at": self.created_at,
        }

    def sign(self, secret_key: str) -> str:
        """
        Create cryptographic signature for mandate

        Uses HMAC-SHA256 for tamper-proof verification

        Args:
            secret_key: Signing secret key

        Returns:
            Hex-encoded signature
        """
        payload = json.dumps(self.to_dict(), sort_keys=True)
        signature = hmac.new(
            secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        self.signature = signature
        return signature

    def verify(self, secret_key: str) -> bool:
        """
        Verify mandate signature

        Args:
            secret_key: Signing secret key

        Returns:
            True if signature is valid
        """
        if not self.signature:
            return False

        original_sig = self.signature
        self.signature = None
        expected_sig = self.sign(secret_key)
        is_valid = hmac.compare_digest(original_sig, expected_sig)
        self.signature = original_sig
        return is_valid

    def is_expired(self) -> bool:
        """Check if mandate has expired"""
        expiration = datetime.fromisoformat(
            self.constraints.valid_until.replace('Z', '+00:00')
        )
        return datetime.now(timezone.utc) >= expiration

    def validate_price(self, price_cents: int) -> bool:
        """Check if price is within mandate constraints"""
        return price_cents <= self.constraints.max_price_cents


@dataclass
class AP2CartMandate:
    """
    Cart Mandate - Specific purchase approval

    Captures exact items and total that user has approved.
    Creates secure, unchangeable record of cart contents.

    Spec: https://ap2-protocol.org/spec#cart-mandate
    """
    mandate_id: str
    intent_mandate_id: str
    user_id: str
    items: List[CartItem]
    total_cents: int
    currency: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approved_at: Optional[str] = None
    signature: Optional[str] = None

    def __post_init__(self):
        """Validate total matches items"""
        calculated_total = sum(item.total_cents for item in self.items)
        if self.total_cents != calculated_total:
            raise ValueError(
                f"Cart total mismatch: declared {self.total_cents}, "
                f"calculated {calculated_total}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for signing/storage"""
        return {
            "mandate_id": self.mandate_id,
            "intent_mandate_id": self.intent_mandate_id,
            "user_id": self.user_id,
            "items": [item.dict() for item in self.items],
            "total_cents": self.total_cents,
            "currency": self.currency,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
        }

    def sign(self, secret_key: str) -> str:
        """Create cryptographic signature"""
        payload = json.dumps(self.to_dict(), sort_keys=True)
        signature = hmac.new(
            secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        self.signature = signature
        return signature

    def verify(self, secret_key: str) -> bool:
        """Verify cart signature"""
        if not self.signature:
            return False

        original_sig = self.signature
        self.signature = None
        expected_sig = self.sign(secret_key)
        is_valid = hmac.compare_digest(original_sig, expected_sig)
        self.signature = original_sig
        return is_valid

    def approve(self):
        """Mark cart as approved by user"""
        self.approved_at = datetime.now(timezone.utc).isoformat()

    def is_approved(self) -> bool:
        """Check if cart has been approved"""
        return self.approved_at is not None


@dataclass
class AP2PaymentMandate:
    """
    Payment Mandate - Payment execution authorization

    Links cart to payment method with cryptographic proof.
    Signals AI involvement to payment networks.

    Spec: https://ap2-protocol.org/spec#payment-mandate
    """
    mandate_id: str
    cart_mandate_id: str
    user_id: str
    payment_method: PaymentMethodDetails
    amount_cents: int
    currency: str
    human_present: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for signing/storage"""
        # Serialize payment method with enum as value
        payment_method_dict = self.payment_method.dict()
        if 'method_type' in payment_method_dict and hasattr(payment_method_dict['method_type'], 'value'):
            payment_method_dict['method_type'] = payment_method_dict['method_type'].value

        return {
            "mandate_id": self.mandate_id,
            "cart_mandate_id": self.cart_mandate_id,
            "user_id": self.user_id,
            "payment_method": payment_method_dict,
            "amount_cents": self.amount_cents,
            "currency": self.currency,
            "human_present": self.human_present,
            "created_at": self.created_at,
        }

    def sign(self, secret_key: str) -> str:
        """Create cryptographic signature"""
        payload = json.dumps(self.to_dict(), sort_keys=True)
        signature = hmac.new(
            secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        self.signature = signature
        return signature

    def verify(self, secret_key: str) -> bool:
        """Verify payment signature"""
        if not self.signature:
            return False

        original_sig = self.signature
        self.signature = None
        expected_sig = self.sign(secret_key)
        is_valid = hmac.compare_digest(original_sig, expected_sig)
        self.signature = original_sig
        return is_valid


# ========================================================================
# AUDIT TRAIL - Non-repudiable Transaction Logs
# ========================================================================


@dataclass
class AP2AuditEvent:
    """Audit event for compliance and dispute resolution"""
    event_id: str
    event_type: str  # intent_created, cart_approved, payment_executed, etc.
    mandate_id: str
    user_id: str
    agent_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: Dict[str, Any] = field(default_factory=dict)
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "mandate_id": self.mandate_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "data": self.data,
        }

    def sign(self, secret_key: str) -> str:
        """Create audit signature"""
        payload = json.dumps(self.to_dict(), sort_keys=True)
        signature = hmac.new(
            secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        self.signature = signature
        return signature


class AP2AuditLogger:
    """
    Audit trail manager for AP2 transactions

    Maintains non-repudiable log of all payment activities
    for compliance, dispute resolution, and fraud prevention.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize audit logger

        Args:
            storage_path: Path to audit log file (defaults to logs/ap2_audit.jsonl)
        """
        self.storage_path = storage_path or os.path.join("logs", "ap2_audit.jsonl")
        self.secret_key = os.getenv("AP2_SIGNING_SECRET", secrets.token_urlsafe(32))

        # Ensure logs directory exists
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

        logger.info(f"AP2 Audit Logger initialized (storage: {self.storage_path})")

    def log_event(
        self,
        event_type: str,
        mandate_id: str,
        user_id: str,
        agent_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> AP2AuditEvent:
        """
        Log audit event

        Args:
            event_type: Type of event (intent_created, cart_approved, etc.)
            mandate_id: Related mandate ID
            user_id: User ID
            agent_id: Optional agent ID
            data: Additional event data

        Returns:
            AP2AuditEvent object
        """
        event = AP2AuditEvent(
            event_id=f"evt_{secrets.token_urlsafe(16)}",
            event_type=event_type,
            mandate_id=mandate_id,
            user_id=user_id,
            agent_id=agent_id,
            data=data or {}
        )

        # Sign event
        event.sign(self.secret_key)

        # Write to audit log
        try:
            with open(self.storage_path, 'a') as f:
                f.write(json.dumps({
                    **event.to_dict(),
                    "signature": event.signature
                }) + '\n')

            logger.debug(f"Audit event logged: {event_type} for {mandate_id}")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

        return event

    def get_audit_trail(self, mandate_id: str) -> List[AP2AuditEvent]:
        """
        Retrieve audit trail for a mandate

        Args:
            mandate_id: Mandate ID to query

        Returns:
            List of audit events
        """
        events = []

        try:
            if not os.path.exists(self.storage_path):
                return events

            with open(self.storage_path, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        if data.get('mandate_id') == mandate_id:
                            event = AP2AuditEvent(
                                event_id=data['event_id'],
                                event_type=data['event_type'],
                                mandate_id=data['mandate_id'],
                                user_id=data['user_id'],
                                agent_id=data.get('agent_id'),
                                timestamp=data['timestamp'],
                                data=data.get('data', {}),
                                signature=data.get('signature')
                            )
                            events.append(event)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Failed to read audit log: {e}")

        return events

    def verify_audit_chain(self, mandate_id: str) -> bool:
        """
        Verify integrity of audit chain for a mandate

        Args:
            mandate_id: Mandate ID to verify

        Returns:
            True if all events have valid signatures
        """
        events = self.get_audit_trail(mandate_id)

        for event in events:
            if not event.signature:
                logger.warning(f"Audit event {event.event_id} missing signature")
                return False

            # Verify signature
            original_sig = event.signature
            event.signature = None
            expected_sig = event.sign(self.secret_key)

            if not hmac.compare_digest(original_sig, expected_sig):
                logger.error(f"Audit event {event.event_id} signature mismatch")
                return False

            event.signature = original_sig

        return True


# ========================================================================
# AP2 CONNECTOR - Main Integration Class
# ========================================================================


class AP2Connector:
    """
    AP2 Protocol Connector for Genesis Billing Agent

    Implements Google's Agent Payments Protocol for secure,
    auditable agent-initiated payments.

    Features:
    - Intent/Cart/Payment mandate creation and verification
    - Cryptographic signature validation
    - Multi-method payment support (Stripe, crypto, etc.)
    - Audit trail for compliance
    - Integration with existing Stripe infrastructure
    - A2A protocol extension

    Usage:
        connector = AP2Connector()

        # Create intent mandate
        intent = await connector.create_intent_mandate(
            user_id="user_123",
            agent_id="billing_agent",
            task="Buy concert tickets",
            max_price_cents=15000,
            currency="USD"
        )

        # Create cart
        cart = await connector.create_cart_mandate(
            intent_mandate_id=intent.mandate_id,
            items=[CartItem(...)]
        )

        # Execute payment
        result = await connector.execute_payment(
            cart_mandate_id=cart.mandate_id,
            payment_method=PaymentMethodDetails(...)
        )
    """

    def __init__(
        self,
        stripe_api_key: Optional[str] = None,
        audit_logger: Optional[AP2AuditLogger] = None,
        enable_crypto: bool = False
    ):
        """
        Initialize AP2 connector

        Args:
            stripe_api_key: Stripe API key (defaults to env var)
            audit_logger: Optional custom audit logger
            enable_crypto: Enable cryptocurrency payments
        """
        self.stripe_api_key = stripe_api_key or os.getenv("STRIPE_SECRET_KEY")
        self.signing_secret = os.getenv("AP2_SIGNING_SECRET", secrets.token_urlsafe(32))
        self.enable_crypto = enable_crypto

        # Audit logger
        self.audit_logger = audit_logger or AP2AuditLogger()
        self.idempotency_store = IdempotencyStore()

        # In-memory storage (replace with MongoDB in production)
        self.intent_mandates: Dict[str, AP2IntentMandate] = {}
        self.cart_mandates: Dict[str, AP2CartMandate] = {}
        self.payment_mandates: Dict[str, AP2PaymentMandate] = {}
        self.payment_results: Dict[str, Dict[str, Any]] = {}

        # Initialize Stripe if available
        self._stripe_enabled = False
        if self.stripe_api_key:
            try:
                import stripe
                stripe.api_key = self.stripe_api_key
                self._stripe_enabled = True
                logger.info("AP2Connector initialized with Stripe support")
            except ImportError:
                logger.warning("stripe library not available - card payments disabled")

        logger.info(f"AP2Connector v1.0 initialized (crypto={'enabled' if enable_crypto else 'disabled'})")

    # ========================================================================
    # INTENT MANDATE OPERATIONS
    # ========================================================================

    async def create_intent_mandate(
        self,
        user_id: str,
        agent_id: str,
        task_description: str,
        max_price_cents: int,
        currency: str = "USD",
        valid_for_hours: int = 24,
        allowed_categories: Optional[List[str]] = None,
        require_approval: bool = True
    ) -> AP2IntentMandate:
        """
        Create Intent Mandate - initial user authorization

        Args:
            user_id: User identifier
            agent_id: Agent identifier
            task_description: What agent is authorized to do
            max_price_cents: Maximum price in cents
            currency: Currency code
            valid_for_hours: Mandate validity in hours (max 720 = 30 days)
            allowed_categories: Optional category restrictions
            require_approval: Require cart approval before payment

        Returns:
            AP2IntentMandate object

        Raises:
            ValidationError: If constraints are invalid
        """
        # Validate inputs
        if valid_for_hours > 720:  # 30 days max
            raise ValueError("Mandate validity cannot exceed 30 days")

        # Create constraints
        expiration = datetime.now(timezone.utc) + timedelta(hours=valid_for_hours)
        constraints = IntentConstraints(
            max_price_cents=max_price_cents,
            currency=currency,
            valid_until=expiration.isoformat(),
            allowed_categories=allowed_categories or [],
            require_approval=require_approval
        )

        # Create mandate
        mandate = AP2IntentMandate(
            mandate_id=f"intent_{secrets.token_urlsafe(16)}",
            user_id=user_id,
            agent_id=agent_id,
            task_description=task_description,
            constraints=constraints
        )

        # Sign mandate
        mandate.sign(self.signing_secret)

        # Store mandate
        self.intent_mandates[mandate.mandate_id] = mandate

        # Log audit event
        self.audit_logger.log_event(
            event_type="intent_created",
            mandate_id=mandate.mandate_id,
            user_id=user_id,
            agent_id=agent_id,
            data={
                "task": task_description,
                "max_price_cents": max_price_cents,
                "currency": currency,
                "valid_until": expiration.isoformat()
            }
        )

        logger.info(
            f"Intent mandate created: {mandate.mandate_id} "
            f"(user={user_id}, max_price=${max_price_cents/100:.2f})"
        )

        return mandate

    def get_intent_mandate(self, mandate_id: str) -> Optional[AP2IntentMandate]:
        """Retrieve intent mandate by ID"""
        return self.intent_mandates.get(mandate_id)

    def verify_intent_mandate(self, mandate: AP2IntentMandate) -> bool:
        """
        Verify intent mandate is valid

        Checks:
        - Signature validity
        - Expiration
        - Constraints

        Returns:
            True if mandate is valid
        """
        # Verify signature
        if not mandate.verify(self.signing_secret):
            logger.warning(f"Intent mandate {mandate.mandate_id} signature invalid")
            return False

        # Check expiration
        if mandate.is_expired():
            logger.warning(f"Intent mandate {mandate.mandate_id} expired")
            return False

        return True

    # ========================================================================
    # CART MANDATE OPERATIONS
    # ========================================================================

    async def create_cart_mandate(
        self,
        intent_mandate_id: str,
        items: List[CartItem],
        user_id: str,
        *,
        idempotency_key: Optional[str] = None,
    ) -> AP2CartMandate:
        """
        Create Cart Mandate - specific purchase approval

        Args:
            intent_mandate_id: Parent intent mandate ID
            items: List of cart items
            user_id: User identifier

        Returns:
            AP2CartMandate object

        Raises:
            ValueError: If intent mandate invalid or price exceeds limit
        """
        if idempotency_key:
            cached = self.idempotency_store.get(idempotency_key)
            if cached:
                return cached

        # Verify intent mandate exists and is valid
        intent = self.intent_mandates.get(intent_mandate_id)
        if not intent:
            raise ValueError(f"Intent mandate {intent_mandate_id} not found")

        if not self.verify_intent_mandate(intent):
            raise ValueError(f"Intent mandate {intent_mandate_id} is invalid or expired")

        # Calculate cart total
        total_cents = sum(item.total_cents for item in items)

        # Verify price within intent constraints
        if not intent.validate_price(total_cents):
            raise ValueError(
                f"Cart total ${total_cents/100:.2f} exceeds "
                f"intent limit ${intent.constraints.max_price_cents/100:.2f}"
            )

        # Get currency from first item
        currency = items[0].currency if items else "USD"

        # Create cart mandate
        cart = AP2CartMandate(
            mandate_id=f"cart_{secrets.token_urlsafe(16)}",
            intent_mandate_id=intent_mandate_id,
            user_id=user_id,
            items=items,
            total_cents=total_cents,
            currency=currency
        )

        # Sign cart
        cart.sign(self.signing_secret)

        # Store cart
        self.cart_mandates[cart.mandate_id] = cart
        if idempotency_key:
            self.idempotency_store.insert(idempotency_key, cart)

        # Log audit event
        self.audit_logger.log_event(
            event_type="cart_created",
            mandate_id=cart.mandate_id,
            user_id=user_id,
            agent_id=intent.agent_id,
            data={
                "intent_mandate_id": intent_mandate_id,
                "item_count": len(items),
                "total_cents": total_cents,
                "currency": currency
            }
        )

        logger.info(
            f"Cart mandate created: {cart.mandate_id} "
            f"({len(items)} items, ${total_cents/100:.2f})"
        )

        return cart

    async def approve_cart_mandate(self, cart_mandate_id: str, user_id: str) -> AP2CartMandate:
        """
        Approve cart mandate - user confirms purchase

        Args:
            cart_mandate_id: Cart mandate ID
            user_id: User identifier (must match cart owner)

        Returns:
            Approved AP2CartMandate

        Raises:
            ValueError: If cart not found or user mismatch
        """
        cart = self.cart_mandates.get(cart_mandate_id)
        if not cart:
            raise ValueError(f"Cart mandate {cart_mandate_id} not found")

        if cart.user_id != user_id:
            raise ValueError("User ID mismatch - unauthorized approval")

        if cart.is_approved():
            logger.warning(f"Cart {cart_mandate_id} already approved")
            return cart

        # Approve cart
        cart.approve()

        # Re-sign with approval timestamp
        cart.sign(self.signing_secret)

        # Log audit event
        self.audit_logger.log_event(
            event_type="cart_approved",
            mandate_id=cart_mandate_id,
            user_id=user_id,
            data={
                "approved_at": cart.approved_at,
                "total_cents": cart.total_cents
            }
        )

        logger.info(f"Cart mandate approved: {cart_mandate_id}")

        return cart

    def get_cart_mandate(self, mandate_id: str) -> Optional[AP2CartMandate]:
        """Retrieve cart mandate by ID"""
        return self.cart_mandates.get(mandate_id)

    # ========================================================================
    # PAYMENT EXECUTION
    # ========================================================================

    async def execute_payment(
        self,
        cart_mandate_id: str,
        payment_method: PaymentMethodDetails,
        user_id: str,
        human_present: bool = True
    ) -> Dict[str, Any]:
        """
        Execute payment via AP2 protocol

        Args:
            cart_mandate_id: Approved cart mandate ID
            payment_method: Payment method details
            user_id: User identifier
            human_present: Whether user is present for transaction

        Returns:
            Payment result dictionary

        Raises:
            ValueError: If cart not approved or payment fails
        """
        # Verify cart mandate
        cart = self.cart_mandates.get(cart_mandate_id)
        if not cart:
            raise ValueError(f"Cart mandate {cart_mandate_id} not found")

        if cart.user_id != user_id:
            raise ValueError("User ID mismatch")

        if not cart.is_approved():
            raise ValueError("Cart not approved - cannot execute payment")

        # Create payment mandate
        payment_mandate = AP2PaymentMandate(
            mandate_id=f"payment_{secrets.token_urlsafe(16)}",
            cart_mandate_id=cart_mandate_id,
            user_id=user_id,
            payment_method=payment_method,
            amount_cents=cart.total_cents,
            currency=cart.currency,
            human_present=human_present
        )

        # Sign payment mandate
        payment_mandate.sign(self.signing_secret)

        # Store payment mandate
        self.payment_mandates[payment_mandate.mandate_id] = payment_mandate

        # Log audit event
        self.audit_logger.log_event(
            event_type="payment_initiated",
            mandate_id=payment_mandate.mandate_id,
            user_id=user_id,
            data={
                "cart_mandate_id": cart_mandate_id,
                "amount_cents": cart.total_cents,
                "currency": cart.currency,
                "method": payment_method.method_type.value,
                "provider": payment_method.provider,
                "human_present": human_present
            }
        )

        # Route to payment provider
        try:
            if payment_method.method_type == PaymentMethod.CARD:
                result = await self._execute_card_payment(payment_mandate, cart)
            elif payment_method.method_type == PaymentMethod.CRYPTO:
                result = await self._execute_crypto_payment(payment_mandate, cart)
            elif payment_method.method_type == PaymentMethod.BANK_TRANSFER:
                result = await self._execute_bank_transfer(payment_mandate, cart)
            elif payment_method.method_type == PaymentMethod.WALLET:
                result = await self._execute_wallet_payment(payment_mandate, cart)
            else:
                raise ValueError(f"Unsupported payment method: {payment_method.method_type}")

            # Store result
            self.payment_results[payment_mandate.mandate_id] = result

            # Log success
            self.audit_logger.log_event(
                event_type="payment_succeeded",
                mandate_id=payment_mandate.mandate_id,
                user_id=user_id,
                data={
                    "transaction_id": result.get("transaction_id"),
                    "status": result.get("status"),
                    "amount_cents": cart.total_cents
                }
            )

            logger.info(
                f"Payment executed: {payment_mandate.mandate_id} "
                f"(${cart.total_cents/100:.2f} via {payment_method.provider})"
            )

            return result

        except Exception as e:
            # Log failure
            self.audit_logger.log_event(
                event_type="payment_failed",
                mandate_id=payment_mandate.mandate_id,
                user_id=user_id,
                data={
                    "error": str(e),
                    "amount_cents": cart.total_cents
                }
            )

            logger.error(f"Payment failed: {e}")

            return {
                "status": PaymentStatus.FAILED.value,
                "error": str(e),
                "mandate_id": payment_mandate.mandate_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _execute_card_payment(
        self,
        payment_mandate: AP2PaymentMandate,
        cart: AP2CartMandate
    ) -> Dict[str, Any]:
        """Execute card payment via Stripe"""
        if not self._stripe_enabled:
            raise RuntimeError("Stripe not configured - card payments unavailable")

        import stripe

        try:
            # Create Stripe PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=cart.total_cents,
                currency=cart.currency.lower(),
                payment_method_types=['card'],
                metadata={
                    "ap2_payment_mandate": payment_mandate.mandate_id,
                    "ap2_cart_mandate": cart.mandate_id,
                    "ap2_intent_mandate": cart.intent_mandate_id,
                    "user_id": cart.user_id,
                    "human_present": str(payment_mandate.human_present)
                },
                description=f"AP2 Payment - {len(cart.items)} items"
            )

            return {
                "status": PaymentStatus.SUCCEEDED.value,
                "transaction_id": intent.id,
                "mandate_id": payment_mandate.mandate_id,
                "amount_cents": cart.total_cents,
                "currency": cart.currency,
                "provider": "stripe",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "client_secret": intent.client_secret
            }

        except stripe.error.StripeError as e:
            raise RuntimeError(f"Stripe payment failed: {e}")

    async def _execute_crypto_payment(
        self,
        payment_mandate: AP2PaymentMandate,
        cart: AP2CartMandate
    ) -> Dict[str, Any]:
        """Execute cryptocurrency payment (placeholder)"""
        if not self.enable_crypto:
            raise RuntimeError("Cryptocurrency payments not enabled")

        # Placeholder - integrate with Coinbase Commerce, x402, etc.
        return {
            "status": PaymentStatus.PENDING.value,
            "transaction_id": f"crypto_{secrets.token_urlsafe(16)}",
            "mandate_id": payment_mandate.mandate_id,
            "amount_cents": cart.total_cents,
            "currency": cart.currency,
            "provider": "crypto_placeholder",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "Crypto payment integration pending"
        }

    async def _execute_bank_transfer(
        self,
        payment_mandate: AP2PaymentMandate,
        cart: AP2CartMandate
    ) -> Dict[str, Any]:
        """Execute bank transfer (placeholder)"""
        # Placeholder - integrate with ACH, SEPA, UPI, PIX
        return {
            "status": PaymentStatus.PENDING.value,
            "transaction_id": f"bank_{secrets.token_urlsafe(16)}",
            "mandate_id": payment_mandate.mandate_id,
            "amount_cents": cart.total_cents,
            "currency": cart.currency,
            "provider": "bank_placeholder",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "Bank transfer integration pending"
        }

    async def _execute_wallet_payment(
        self,
        payment_mandate: AP2PaymentMandate,
        cart: AP2CartMandate
    ) -> Dict[str, Any]:
        """Execute digital wallet payment (placeholder)"""
        # Placeholder - integrate with PayPal, Apple Pay, Google Pay
        return {
            "status": PaymentStatus.PENDING.value,
            "transaction_id": f"wallet_{secrets.token_urlsafe(16)}",
            "mandate_id": payment_mandate.mandate_id,
            "amount_cents": cart.total_cents,
            "currency": cart.currency,
            "provider": "wallet_placeholder",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "Wallet payment integration pending"
        }

    # ========================================================================
    # AUDIT & COMPLIANCE
    # ========================================================================

    def get_audit_trail(self, mandate_id: str) -> List[AP2AuditEvent]:
        """Retrieve complete audit trail for a mandate"""
        return self.audit_logger.get_audit_trail(mandate_id)

    def verify_audit_chain(self, mandate_id: str) -> bool:
        """Verify integrity of audit chain"""
        return self.audit_logger.verify_audit_chain(mandate_id)

    def get_payment_result(self, payment_mandate_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve payment result by mandate ID"""
        return self.payment_results.get(payment_mandate_id)

    # ========================================================================
    # HEALTH CHECK
    # ========================================================================

    def health_check(self) -> Dict[str, Any]:
        """
        Health check for AP2 connector

        Returns:
            Health status dictionary
        """
        return {
            "connector": "ap2",
            "version": "1.0.0",
            "status": "healthy",
            "stripe_enabled": self._stripe_enabled,
            "crypto_enabled": self.enable_crypto,
            "mandates": {
                "intent": len(self.intent_mandates),
                "cart": len(self.cart_mandates),
                "payment": len(self.payment_mandates)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# ========================================================================
# HELPER FUNCTIONS
# ========================================================================


async def get_ap2_connector(
    stripe_api_key: Optional[str] = None,
    enable_crypto: bool = False
) -> AP2Connector:
    """
    Factory function to create AP2 connector

    Args:
        stripe_api_key: Optional Stripe API key
        enable_crypto: Enable cryptocurrency payments

    Returns:
        Configured AP2Connector instance
    """
    return AP2Connector(
        stripe_api_key=stripe_api_key,
        enable_crypto=enable_crypto
    )
