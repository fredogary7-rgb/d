"""Génère des clés VAPID pour le Web Push."""

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from services.push_service import generate_vapid_keys

keys = generate_vapid_keys()
private_key = keys['VAPID_PRIVATE_KEY']
public_key = keys['VAPID_PUBLIC_KEY']

print('=== VAPID Keys Generated ===')
print(f'VAPID_PRIVATE_KEY={private_key}')
print(f'VAPID_PUBLIC_KEY={public_key}')

# Write to .vapid_keys.txt
with open('.vapid_keys.txt', 'w') as f:
    f.write(f'VAPID_PRIVATE_KEY={private_key}\n')
    f.write(f'VAPID_PUBLIC_KEY={public_key}\n')

print('Keys saved to .vapid_keys.txt')