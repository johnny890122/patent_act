"""
Tests for i18n / language-aware endpoints (Phase 9.5/9.6)
"""
import sys
import os
import requests
import json
from db.models import Database
from services.inventory import QuestionInventory

BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5001')

def test_inventory_count_en():
    inv = QuestionInventory()
    count = inv.count_available_questions('MCQ', 'new', lang='en')
    print(f"Available (en, MCQ, new): {count}")
    assert isinstance(count, int)


def test_create_session_en():
    payload = {
        "type": "MCQ",
        "mode": "new",
        "count": 2,
        "lang": "en"
    }
    resp = requests.post(f"{BASE_URL}/quiz/session", json=payload)
    print('status', resp.status_code)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert 'questions' in data
    # If questions exist, they should carry language metadata when available
    qs = data.get('questions', [])
    for q in qs:
        if 'lang' in q:
            assert q['lang'] == 'en'
