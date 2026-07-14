#!/usr/bin/env python3
"""Protect all undefined variables in dashboard.html with Jinja |default filters."""

with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    # Ligne 447: country_flags.get -> (country_flags|default({})).get
    (
        '{{ country_flags.get(tx.recipient_country, ',
        '{{ (country_flags|default({})).get(tx.recipient_country, '
    ),
    # Ligne 447: country_names.get dans le tableau
    (
        '{{ country_names.get(tx.recipient_country, tx.recipient_country',
        '{{ (country_names|default({})).get(tx.recipient_country, tx.recipient_country'
    ),
    # Ligne 568: country_names.get dans la timeline
    (
        '{{ country_names.get(tx.recipient_country, tx.recipient_country or ',
        '{{ (country_names|default({})).get(tx.recipient_country, tx.recipient_country or '
    ),
    # Stats: total_sent
    (
        '{{ "{:,.0f}".format(total_sent) }}',
        '{{ "{:,.0f}".format(total_sent|default(0)) }}'
    ),
    # Stats: total_received
    (
        '{{ "{:,.0f}".format(total_received) }}',
        '{{ "{:,.0f}".format(total_received|default(0)) }}'
    ),
    # Stats: tx_count
    (
        '{{ tx_count }}',
        '{{ tx_count|default(0) }}'
    ),
    # Stats: beneficiary_count
    (
        '{{ beneficiary_count }}',
        '{{ beneficiary_count|default(0) }}'
    ),
]

count = 0
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        count += 1
        print(f'  OK: replaced occurrence of variable')
    else:
        print(f'  SKIP: not found (maybe already replaced)')

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\nDone. {count}/{len(replacements)} replacements applied.')