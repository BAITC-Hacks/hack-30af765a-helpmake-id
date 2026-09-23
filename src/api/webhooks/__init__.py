"""Webhooks package.

Add one module per external provider::

    src/api/webhooks/stripe.py   — inbound Stripe events
    src/api/webhooks/sendgrid.py — outbound email adapter

Modules here are external protocol adapters only — they authenticate,
parse, and map payloads. Business logic belongs in controllers.
"""
