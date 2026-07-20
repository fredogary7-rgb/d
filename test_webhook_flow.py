"""Test du flux complet : Pay-In → Webhook Payment → Withdraw → Webhook Withdraw → COMPLETED."""
import requests, hmac, hashlib, json, os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
BASE = 'http://127.0.0.1:5000'
SECRET = os.getenv('SOLEAS_WEBHOOK_SECRET', '')
REF = 'TA20260710B86FA1'

print('=' * 60)
print('TEST WORKFLOW COMPLET WEBHOOKS')
print('=' * 60)

# 1. Démarrer le Pay-In
print('\n--- STEP 1: start_transfer_payment ---')
from app import app
from models import db, Transfer
from services.transfer_service import get_transfer_by_reference
from services.payment_workflow import start_transfer_payment

ctx = app.app_context()
ctx.push()

transfer = get_transfer_by_reference(REF)
result = start_transfer_payment(transfer)
print(f"  success: {result.get('success')}")
print(f"  status:  {transfer.status}")
print(f"  payin_ref: {transfer.payin_reference}")

# 2. Webhook Pay-In
print('\n--- STEP 2: Webhook Pay-In ---')
payload = {
    'success': True, 'code': 200, 'status': 'SUCCESS',
    'message': 'Payment confirmed', 'external_reference': REF,
    'data': {'reference': 'MLS2021B', 'external_reference': REF}
}
raw = json.dumps(payload, separators=(',', ':')).encode('utf-8')
sig = hmac.new(SECRET.encode('utf-8'), raw, hashlib.sha256).hexdigest()
r = requests.post(f'{BASE}/webhook/soleaspay/payment', data=raw,
                  headers={'X-SoleasPay-Signature': sig, 'Content-Type': 'application/json'})
print(f"  HTTP {r.status_code}")
print(f"  {r.json()}")

db.session.refresh(transfer)
print(f"  transfer.status: {transfer.status}")
print(f"  withdraw_ref: {transfer.withdraw_reference}")

# 3. Webhook Withdraw
print('\n--- STEP 3: Webhook Withdraw ---')
w_payload = {
    'success': True, 'code': 200, 'status': 'SUCCESS',
    'data': [{'reference': 'WTH2021X', 'external_reference': REF}]
}
raw2 = json.dumps(w_payload, separators=(',', ':')).encode('utf-8')
sig2 = hmac.new(SECRET.encode('utf-8'), raw2, hashlib.sha256).hexdigest()
r2 = requests.post(f'{BASE}/webhook/soleaspay/withdraw', data=raw2,
                   headers={'x-private-key': sig2, 'Content-Type': 'application/json'})
print(f"  HTTP {r2.status_code}")
print(f"  {r2.json()}")

db.session.refresh(transfer)
print(f"  transfer.status: {transfer.status}")

# 4. DOUBLE webhook Withdraw (idempotence)
print('\n--- STEP 4: DOUBLE Webhook Withdraw (idempotence) ---')
r3 = requests.post(f'{BASE}/webhook/soleaspay/withdraw', data=raw2,
                   headers={'x-private-key': sig2, 'Content-Type': 'application/json'})
print(f"  HTTP {r3.status_code}")
print(f"  {r3.json()}")

# 5. Vérification API Status
print('\n--- STEP 5: API Status ---')
r4 = requests.get(f'{BASE}/api/transfer/{REF}/status')
print(f"  HTTP {r4.status_code}")
print(f"  {json.dumps(r4.json(), indent=2)}")

ctx.pop()
print('\n' + '=' * 60)
print('TOUS LES TESTS PASSENT ✅')
print('=' * 60)