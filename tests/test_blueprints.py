#!/usr/bin/env python3
"""Test script to verify blueprint endpoints are registered correctly"""

import sys
sys.path.insert(0, '/Users/marty331/Dev/phil_select')

from app import app

print("=" * 70)
print("Blueprint Endpoint Test")
print("=" * 70)

with app.app_context():
    print("\n✅ Registered Blueprints:")
    for blueprint_name, blueprint in app.blueprints.items():
        print(f"  - {blueprint_name}")
    
    print("\n✅ All Registered Endpoints:")
    rules = sorted(app.url_map.iter_rules(), key=lambda r: r.rule)
    
    for rule in rules:
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        print(f"  {rule.rule:50} -> {rule.endpoint:40} [{methods}]")
    
    print("\n🔍 Checking specific endpoints:")
    test_endpoints = [
        'base_routes.index',
        'base_routes.preferences',
        'scoring_routes.scores',
        'scoring_routes.results',
        'admin_routes.admin',
        'admin_routes.logout',
        'survey_routes.survey',
        'program_routes.program_chart',
    ]
    
    for endpoint in test_endpoints:
        try:
            url = app.url_for(endpoint)
            print(f"  ✅ {endpoint:40} -> {url}")
        except Exception as e:
            print(f"  ❌ {endpoint:40} -> ERROR: {e}")

print("\n" + "=" * 70)
