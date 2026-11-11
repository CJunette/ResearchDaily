#!/usr/bin/env python3
"""Private reading evidence ledger; semantic interpretation remains an agent task."""
import argparse
import datetime as dt
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def connect(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE, payload TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS hypotheses(id TEXT PRIMARY KEY, definition TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'candidate');
      CREATE TABLE IF NOT EXISTS evidence(hypothesis_id TEXT REFERENCES hypotheses(id), record_id TEXT REFERENCES records(id), message_index INTEGER, quote TEXT, relation TEXT, rationale TEXT, UNIQUE(hypothesis_id,record_id,message_index,quote,relation));
      CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY, hypothesis_id TEXT REFERENCES hypotheses(id), status TEXT, reason TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    ''')
    return db


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def required(value, fields):
    if any(not isinstance(value.get(k), str) or not value[k].strip() for k in fields):
        raise ValueError('Required non-empty text: ' + ', '.join(fields))


def ingest(db, record):
    required(record, ('id', 'paper_id', 'topic', 'read_date'))
    dt.date.fromisoformat(record['read_date'])
    if not record.get('messages'):
        raise ValueError('Conversation messages required')
    for message in record['messages']:
        required(message, ('role', 'text'))
        if message['role'] not in ('user', 'assistant'):
            raise ValueError('Separate actual user/assistant turns before import')
    payload = packed(record)
    existing = db.execute('SELECT payload FROM records WHERE id=?', (record['id'],)).fetchone()
    if existing:
        if existing['payload'] != payload:
            raise ValueError('Records are immutable; use a new ID for an independent record')
        return {'record_id': record['id'], 'reused': True}
    fingerprint = hashlib.sha256(packed({k:v for k,v in record.items() if k != 'id'}).encode()).hexdigest()
    duplicate = db.execute('SELECT id FROM records WHERE fingerprint=?', (fingerprint,)).fetchone()
    if duplicate:
        return {'record_id': duplicate['id'], 'reused': True}
    db.execute('INSERT INTO records VALUES (?,?,?)', (record['id'], fingerprint, payload))
    return {'record_id': record['id'], 'reused': False}


def observe(db, hypothesis):
    required(hypothesis, ('id', 'preference', 'scope', 'alternative_explanations'))
    hid = hypothesis['id']
    definition = packed({k:hypothesis[k] for k in ('preference', 'scope', 'alternative_explanations')})
    old = db.execute('SELECT definition FROM hypotheses WHERE id=?', (hid,)).fetchone()
    if old and old['definition'] != definition:
        raise ValueError('Hypothesis definitions are immutable; create a new hypothesis')
    db.execute('INSERT OR IGNORE INTO hypotheses(id,definition) VALUES (?,?)', (hid, definition))
    if not hypothesis.get('evidence'):
        raise ValueError('Quoted evidence required')
    for item in hypothesis['evidence']:
        required(item, ('record_id', 'quote', 'relation', 'rationale'))
        record = db.execute('SELECT payload FROM records WHERE id=?', (item['record_id'],)).fetchone()
        if not record:
            raise ValueError('Import the source record first')
        messages = json.loads(record['payload'])['messages']
        index = item.get('message_index')
        if type(index) is not int or not 0 <= index < len(messages):
            raise ValueError('Invalid message index')
        message = messages[index]
        if message['role'] != 'user' or item['quote'] not in message['text']:
            raise ValueError('Evidence must quote an actual user turn exactly')
        if item['relation'] not in ('support', 'holdout', 'contradict'):
            raise ValueError('Invalid evidence relation')
        db.execute('INSERT OR IGNORE INTO evidence VALUES (?,?,?,?,?,?)', (hid,item['record_id'],index,item['quote'],item['relation'],item['rationale']))
        if item['relation'] == 'contradict':
            active = db.execute("SELECT 1 FROM hypotheses WHERE id=? AND status='active'", (hid,)).fetchone()
            if active:
                decide(db, hid, 'suspended', 'New contradictory evidence requires contextual review')
    return inspect(db, hid)[0]


def inspect(db, hid=None):
    rows = db.execute('SELECT * FROM hypotheses' + (' WHERE id=?' if hid else '') + ' ORDER BY id', (hid,) if hid else ()).fetchall()
    result = []
    for row in rows:
        evidence = [dict(e) for e in db.execute('SELECT e.*, r.payload FROM evidence e JOIN records r ON r.id=e.record_id WHERE hypothesis_id=?', (row['id'],))]
        for e in evidence:
            e['record'] = json.loads(e.pop('payload'))
        support = [e['record'] for e in evidence if e['relation'] == 'support']
        papers = {r['paper_id'] for r in support}
        dates = {r['read_date'] for r in support}
        topics = {r['topic'] for r in support}
        holdout = any(e['relation'] == 'holdout' and e['record']['paper_id'] not in papers and dates and e['record']['read_date'] > max(dates) for e in evidence)
        contradictions = any(e['relation'] == 'contradict' for e in evidence)
        ready = len(papers) >= 4 and len(topics) >= 3 and len(dates) >= 3 and holdout and not contradictions
        item = {'id':row['id'], **json.loads(row['definition']), 'status':row['status'], 'gate_passed':ready,
                'coverage':{'supporting_papers':len(papers),'topics':len(topics),'dates':len(dates),'later_holdout':bool(holdout),'counterevidence':contradictions}}
        if hid:
            item['evidence'] = evidence
            item['decisions'] = [dict(d) for d in db.execute('SELECT status,reason,created_at FROM decisions WHERE hypothesis_id=? ORDER BY id', (hid,))]
        result.append(item)
    return result


def decide(db, hid, status, reason):
    if status not in ('active', 'suspended', 'rejected') or not reason.strip():
        raise ValueError('Decision needs a status and contextual rationale')
    rows = inspect(db, hid)
    if not rows:
        raise ValueError('Unknown hypothesis')
    if status == 'active' and not rows[0]['gate_passed']:
        raise ValueError('Insufficient independent evidence, missing later holdout, or counterevidence present')
    db.execute('UPDATE hypotheses SET status=? WHERE id=?', (status, hid))
    db.execute('INSERT INTO decisions(hypothesis_id,status,reason) VALUES (?,?,?)', (hid,status,reason))
    return {'id':hid, 'status':status}


def profile(db):
    return {'preferences':[{'id':h['id'], 'preference':h['preference'], 'scope':h['scope']} for h in inspect(db) if h['status'] == 'active' and h['gate_passed']]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=ROOT / 'data/reading-preferences.sqlite')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('ingest', 'observe'):
        commands.add_parser(name).add_argument('path', type=Path)
    commands.add_parser('profile')
    commands.add_parser('inspect').add_argument('--id')
    decision = commands.add_parser('decide')
    decision.add_argument('id')
    decision.add_argument('status', choices=('active','suspended','rejected'))
    decision.add_argument('--reason', required=True)
    args = parser.parse_args()
    db = connect(args.db)
    try:
        with db:
            if args.command in ('ingest','observe'):
                data = json.loads(args.path.read_text(encoding='utf-8'))
                result = (ingest if args.command == 'ingest' else observe)(db, data)
            elif args.command == 'decide':
                result = decide(db, args.id, args.status, args.reason)
            else:
                result = profile(db) if args.command == 'profile' else inspect(db, args.id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, sqlite3.Error, OSError, TypeError) as error:
        parser.exit(1, str(error) + '\n')
    finally:
        db.close()


if __name__ == '__main__':
    main()
