"""Streaming validation of recorded history and mutable delivery projections."""
from .event_contract import (canonical_bytes, parse_json, validate_event, validate_input,
                             event_hash, INPUT_FIELDS, validate_time)


def validate_store(db, metadata, trust, anchor):
    # Imported at call time to keep public errors/results at the recorder boundary.
    from .audit_log import (GENESIS, MAX_ATTEMPTS, ValidationReport, IntegrityError,
                            _id, _integer, _digest, _hash, _IMMUTABLE, _trigger)

    def require(condition):
        if not condition:
            raise IntegrityError('invalid ledger history')

    def decoded(raw):
        value = parse_json(raw)
        require(canonical_bytes(value) == raw)
        return value

    def stored_event(event_id):
        row = db.execute('SELECT canonical FROM events WHERE event_id=?', (event_id,)).fetchone()
        require(row is not None)
        return decoded(row[0])

    require(db.execute('PRAGMA quick_check').fetchone()[0] == 'ok')
    require(db.execute('PRAGMA foreign_key_check').fetchone() is None)
    require(db.execute('SELECT count(*) FROM metadata').fetchone()[0] == 1)
    for table in _IMMUTABLE:
        for operation in ('update', 'delete'):
            row = db.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?",
                             (f'{table}_no_{operation}',)).fetchone()
            require(row is not None and row[0] == _trigger(table, operation))
    sequence, previous = 0, GENESIS
    for seq, event_id, raw, caller_raw in db.execute('SELECT sequence,event_id,canonical,caller FROM events ORDER BY sequence'):
        event = decoded(raw)
        validate_event(event)
        caller = decoded(caller_raw)
        validate_input(caller)
        require(caller == {key: event[key] for key in INPUT_FIELDS})
        require(seq == sequence + 1 == event['sequence'] and event_id == event['event_id'])
        require(event['ledger_id'] == metadata['ledger_id'] and event['node_id'] == metadata['node_id'])
        require(event['previous_hash'] == previous and event_hash(event) == event['event_hash'])
        require(event['outbox_id'] == event_id and event['initial_state'] == 'LOCAL')
        parent_id = event['correlation']['parent_event_id']
        if parent_id is not None:
            parent = stored_event(parent_id)
            require(parent['sequence'] < seq)
            for key in ('request_id', 'request_sha256', 'action_id', 'execution_id'):
                a, b = event['correlation'][key], parent['correlation'][key]
                require(a is None or b is None or a == b)
            if event['event_type'] == 'RECONCILIATION_FINDING':
                require(event['detail']['original_event_id'] == parent_id and
                        event['detail']['original_event_hash'] == parent['event_hash'])
        sequence, previous = seq, event['event_hash']
    event_count = sequence

    sequence, previous = 0, GENESIS
    projection_fields = {'event_id', 'event_hash', 'state', 'destination', 'attempts', 'retry_after_ms',
                         'last_error', 'receipt_ref', 'receipt_sha256', 'finding_event_id'}
    operations = {'LOCAL', 'SEALED', 'QUEUED', 'ATTEMPT', 'ACKNOWLEDGED', 'RECONCILED', 'SEAL_REQUESTED'}
    for seq, event_id, raw, digest in db.execute('SELECT sequence,event_id,canonical,transition_hash FROM transitions ORDER BY sequence'):
        t = decoded(raw)
        require(set(t) == {'version', 'sequence', 'previous_hash', 'operation', 'event_sequence', 'time', 'projection'})
        require(t['version'] == 'alice-outbox-transition-v1' and t['operation'] in operations)
        require(seq == sequence+1 == t['sequence'] and t['previous_hash'] == previous)
        require(_hash(b'ALICE-OUTBOX-v1\0', t) == digest)
        validate_time(t['time'])
        p = t['projection']
        require(set(p) == projection_fields)
        event = stored_event(event_id)
        require(p['event_id'] == event_id and p['event_hash'] == event['event_hash'] and t['event_sequence'] == event['sequence'])
        _integer(p['attempts'], 0, MAX_ATTEMPTS)
        _integer(p['retry_after_ms'], 0, 86400000)
        for key in ('destination', 'last_error', 'receipt_ref', 'finding_event_id'):
            if p[key] is not None:
                _id(p[key])
        if p['receipt_sha256'] is not None:
            _digest(p['receipt_sha256'])
        old = db.execute('SELECT canonical FROM transitions WHERE event_id=? AND sequence<? ORDER BY sequence DESC LIMIT 1', (event_id, seq)).fetchone()
        op = t['operation']
        if old is None:
            require(op == 'LOCAL')
            expected = dict(event_id=event_id, event_hash=event['event_hash'], state='LOCAL', destination=None,
                            attempts=0, retry_after_ms=0, last_error=None, receipt_ref=None,
                            receipt_sha256=None, finding_event_id=None)
        else:
            expected = decoded(old[0])['projection']
            if op == 'SEAL_REQUESTED':
                pass  # Durable sealing intent preserves the existing projection.
            elif op == 'SEALED':
                require(expected['state'] == 'LOCAL')
                expected['state'] = 'SEALED'
            elif op == 'QUEUED':
                require(expected['state'] == 'SEALED' and p['destination'] is not None)
                expected.update(state='QUEUED', destination=p['destination'])
            elif op == 'ATTEMPT':
                require(expected['state'] == 'QUEUED')
                expected.update(attempts=expected['attempts']+1, retry_after_ms=p['retry_after_ms'], last_error=p['last_error'])
            elif op == 'ACKNOWLEDGED':
                require(expected['state'] == 'QUEUED' and p['receipt_ref'] is not None and p['receipt_sha256'] is not None)
                expected.update(state='ACKNOWLEDGED', receipt_ref=p['receipt_ref'], receipt_sha256=p['receipt_sha256'])
            elif op == 'RECONCILED':
                require(expected['state'] == 'ACKNOWLEDGED' and p['finding_event_id'] is not None)
                finding = stored_event(p['finding_event_id'])
                require(finding['event_type'] == 'RECONCILIATION_FINDING' and
                        finding['detail']['original_event_id'] == event_id and finding['detail']['original_event_hash'] == event['event_hash'])
                expected.update(state='RECONCILED', finding_event_id=p['finding_event_id'])
            else:
                require(False)
        require(p == expected)
        sequence, previous = seq, digest
    transition_count = sequence

    require(db.execute('SELECT count(*) FROM outbox').fetchone()[0] == event_count)
    require(db.execute('SELECT count(DISTINCT event_id) FROM transitions').fetchone()[0] == event_count)
    for event_id, event_sequence, state, raw in db.execute('SELECT event_id,event_sequence,state,projection FROM outbox'):
        p = decoded(raw)
        row = db.execute('SELECT canonical FROM transitions WHERE event_id=? ORDER BY sequence DESC LIMIT 1', (event_id,)).fetchone()
        require(row is not None and decoded(row[0])['projection'] == p and p['state'] == state)
        require(stored_event(event_id)['sequence'] == event_sequence)

    cp_fields = {'version', 'sequence', 'ledger_id', 'node_id', 'covered_sequence', 'head_event_hash',
                 'transition_sequence', 'transition_hash', 'previous_checkpoint_digest', 'algorithm_id', 'key_id', 'time'}
    cp_sequence, previous_cp, covered, covered_trans = 0, GENESIS, 0, 0
    anchor_seen = anchor is None
    if anchor is not None:
        # Exact envelope identity after local verification. An anchor is supplied
        # out of band, never loaded as trust configuration from this database.
        canonical_bytes(anchor)
    for seq, raw, digest in db.execute('SELECT sequence,canonical,digest FROM checkpoints ORDER BY sequence'):
        cp = decoded(raw)
        require(set(cp) == {'body', 'signature', 'digest'})
        body = cp['body']
        require(set(body) == cp_fields and body['version'] == 'alice-checkpoint-v1')
        require(seq == cp_sequence+1 == body['sequence'])
        require(body['ledger_id'] == metadata['ledger_id'] and body['node_id'] == metadata['node_id'])
        require(body['previous_checkpoint_digest'] == previous_cp)
        _id(body['algorithm_id']); _id(body['key_id'])
        validate_time(body['time'])
        _integer(body['covered_sequence'], covered, event_count)
        _integer(body['transition_sequence'], covered_trans, transition_count)
        require(body['covered_sequence']-covered <= 64)
        require(type(cp['signature']) is str and 2 <= len(cp['signature']) <= 2048)
        signature = bytes.fromhex(cp['signature'])
        require(signature.hex() == cp['signature'])
        require(cp['digest'] == digest == _hash(b'ALICE-CHECKPOINT-DIGEST-v1\0', dict(body=body, signature=cp['signature'])))
        trust.verify(body['algorithm_id'], body['key_id'], b'ALICE-CHECKPOINT-v1\0'+canonical_bytes(body), signature)
        e = db.execute('SELECT canonical FROM events WHERE sequence=?', (body['covered_sequence'],)).fetchone()
        require(body['head_event_hash'] == (decoded(e[0])['event_hash'] if e else GENESIS))
        t = db.execute('SELECT transition_hash FROM transitions WHERE sequence=?', (body['transition_sequence'],)).fetchone()
        require(body['transition_hash'] == (t[0] if t else GENESIS))
        # Each newly covered event must have its SEALED transition included in
        # this checkpoint; no delivery projection may manufacture coverage.
        for (event_id,) in db.execute('SELECT event_id FROM events WHERE sequence>? AND sequence<=?', (covered, body['covered_sequence'])):
            sealed = False
            for (transition_raw,) in db.execute('SELECT canonical FROM transitions WHERE event_id=? AND sequence<=?', (event_id, body['transition_sequence'])):
                if decoded(transition_raw)['operation'] == 'SEALED':
                    sealed = True
            require(sealed)
        if anchor is not None and cp == anchor:
            anchor_seen = True
        cp_sequence, previous_cp = seq, digest
        covered, covered_trans = body['covered_sequence'], body['transition_sequence']
    require(anchor_seen)
    for event_sequence, state in db.execute('SELECT event_sequence,state FROM outbox'):
        require((event_sequence <= covered) == (state != 'LOCAL'))
    return ValidationReport(event_count, covered, transition_count, covered_trans, anchor is not None)
