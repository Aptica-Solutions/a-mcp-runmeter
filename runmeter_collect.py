"""Import local assistant usage metadata once and publish an aggregate snapshot.

No prompts, responses, transcript paths, session titles, or raw identifiers are stored.
Only explicit source roots are scanned. Unknown model pricing remains null.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from datetime import datetime, timezone

VERSION = 1


def count(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError('Invalid token count')
    return value


def stamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp requires timezone')
    return parsed.astimezone(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def safe_name(value):
    return value if isinstance(value, str) and re.fullmatch(r'[a-zA-Z0-9._:/-]{1,120}', value) else 'unknown'


def lines(path, health):
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            if not line.endswith('\n'):
                health['partial_lines'] += 1
                continue
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    yield value
            except ValueError:
                health['invalid_lines'] += 1


def project_for(cwd, projects):
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        return 'unattributed', 'development'
    path = Path(cwd).resolve()
    matches = [p for p in projects if path.is_relative_to(Path(p['root']).resolve())]
    if not matches:
        return 'unattributed', 'development'
    selected = max(matches, key=lambda p:len(p['root']))
    return selected['project_id'], selected['environment']


def parse(path, source, projects, health):
    modern = False
    if source == 'codex':
        # Select one event family for the entire file. Never sum both native
        # per-response events and the legacy cumulative mirror.
        for item in lines(path, {'partial_lines':0, 'invalid_lines':0}):
            if item.get('type') == 'token_usage_record':
                modern = True
                break
    cwd = None
    model = 'unknown'
    session = digest(str(path.resolve()))
    previous = None
    records = {}
    for item in lines(path, health):
        try:
            kind = item.get('type')
            payload = item.get('payload') or {}
            if kind == 'session_meta':
                cwd = payload.get('cwd')
                session = payload.get('id') or payload.get('session_id') or session
            if kind == 'turn_context':
                model = safe_name(payload.get('model'))
                cwd = payload.get('cwd', cwd)
            if source == 'codex':
                if modern:
                    if kind != 'token_usage_record':
                        continue
                    u = payload.get('usage') or {}
                    identity = payload.get('response_id')
                    if not identity:
                        health['unsupported_events'] += 1
                        continue
                else:
                    if kind != 'event_msg' or payload.get('type') != 'token_count':
                        continue
                    totals = (payload.get('info') or {}).get('total_token_usage')
                    if not totals:
                        continue
                    current = {k:count(totals.get(k,0)) for k in ('input_tokens','output_tokens','cached_input_tokens','cache_write_input_tokens')}
                    if current == previous:
                        continue
                    # Do not infer a delta across a reset or a compacted history.
                    if previous and any(current[k] < previous[k] for k in current):
                        previous = current
                        health['unsupported_events'] += 1
                        continue
                    u = {k:current[k]-(previous or {}).get(k,0) for k in current}
                    previous = current
                    identity = f'{session}:{json.dumps(current,sort_keys=True)}'
                total = count(u.get('input_tokens',0))
                read = count(u.get('cached_input_tokens',0))
                write = count(u.get('cache_write_input_tokens',0))
                if read + write > total:
                    raise ValueError('Cache exceeds total input')
                metrics = {'uncached_input':total-read-write,'cache_read':read,'cache_write_5m':0,'cache_write_1h':0,'cache_write_unknown':write}
                output = count(u.get('output_tokens',0))
                provider = 'codex'
                time = stamp(item['timestamp'])
            else:
                message = item.get('message') or {}
                if not isinstance(message,dict) or message.get('role') != 'assistant' or not message.get('usage'):
                    continue
                identity = message.get('id')
                if not identity:
                    health['unsupported_events'] += 1
                    continue
                cwd = item.get('cwd',cwd)
                model = safe_name(message.get('model'))
                u = message['usage']
                cache = u.get('cache_creation') or {}
                write = count(u.get('cache_creation_input_tokens',0))
                w5 = count(cache.get('ephemeral_5m_input_tokens',0))
                w1 = count(cache.get('ephemeral_1h_input_tokens',0))
                if w5+w1 > write:
                    raise ValueError('Cache breakdown exceeds total')
                metrics = {'uncached_input':count(u.get('input_tokens',0)),'cache_read':count(u.get('cache_read_input_tokens',0)),'cache_write_5m':w5,'cache_write_1h':w1,'cache_write_unknown':write-w5-w1}
                total = sum(metrics.values())
                output = count(u.get('output_tokens',0))
                provider = 'anthropic'
                time = stamp(item['timestamp'])
            project, environment = project_for(cwd,projects)
            key = digest(f'{provider}:{identity}')
            record = {'key':key,'ts':time,'model':model,'agent':project,'environment':environment,'input_tokens':total,'output_tokens':output,'source':source,**metrics}
            # Streaming content blocks can repeat an identical message ID.
            # Keep component maxima rather than summing the repeated message.
            if key in records:
                old = records[key]
                for field in (*metrics,'output_tokens'):
                    record[field] = max(old[field],record[field])
                record['input_tokens'] = sum(record[k] for k in metrics)
                record['ts'] = min(old['ts'],record['ts'])
            records[key] = record
        except (ValueError,TypeError,KeyError,AttributeError):
            health['invalid_lines'] += 1
    return list(records.values())


def price(record, pricing):
    rates = pricing.get(record['model'])
    if not rates or record['cache_write_unknown']:
        return None
    total = 0.0
    for field in ('uncached_input','cache_read','cache_write_5m','cache_write_1h','output_tokens'):
        if not record[field]:
            continue
        rate = rates.get(field)
        if isinstance(rate,bool) or not isinstance(rate,(int,float)) or not math.isfinite(rate) or rate < 0:
            return None
        total += record[field]*rate/1_000_000
    return total


def connect(database):
    import server
    database.parent.mkdir(parents=True,exist_ok=True)
    if os.name != 'nt':
        database.parent.chmod(0o700)
    old = os.environ.get('RUNMETER_DB_PATH')
    try:
        os.environ['RUNMETER_DB_PATH'] = str(database)
        conn = server._connect()
    finally:
        if old is None: os.environ.pop('RUNMETER_DB_PATH',None)
        else: os.environ['RUNMETER_DB_PATH'] = old
    conn.executescript(Path(__file__).with_name('collector_schema.sql').read_text())
    conn.commit()
    return conn


def write_records(conn, records, pricing):
    if not conn.in_transaction: conn.execute("BEGIN IMMEDIATE")
    for original in records:
        r = dict(original)
        existing = conn.execute('SELECT run_id FROM collector_keys WHERE key=?',(r['key'],)).fetchone()
        if existing:
            old = conn.execute('SELECT * FROM runs WHERE id=?',(existing[0],)).fetchone()
            if old:
                previous_metrics = json.loads(old['metadata'] or '{}')
                for field in ('uncached_input','cache_read','cache_write_5m','cache_write_1h','cache_write_unknown'):
                    r[field] = max(r[field],previous_metrics.get(field,0))
                r['input_tokens'] = sum(r[k] for k in ('uncached_input','cache_read','cache_write_5m','cache_write_1h','cache_write_unknown'))
                r['output_tokens'] = max(r['output_tokens'],old['output_tokens'])
                r['ts'] = min(r['ts'],old['ts'])
                if old['agent'] != 'unattributed': r['agent'] = old['agent']
        metadata = json.dumps({k:r[k] for k in ('source','uncached_input','cache_read','cache_write_5m','cache_write_1h','cache_write_unknown')})
        tags = json.dumps(['collector:assistant-v1',f"source:{r['source']}",f"project:{r['agent']}",f"environment:{r['environment']}",'scope:development','classification:unknown'])
        values = (r['ts'],r['model'],r['agent'],r['input_tokens'],r['output_tokens'],price(r,pricing),tags,metadata)
        if existing and conn.execute('SELECT 1 FROM runs WHERE id=?',(existing[0],)).fetchone():
            conn.execute('UPDATE runs SET ts=?,model=?,agent=?,input_tokens=?,output_tokens=?,cost_usd=?,tags=?,metadata=? WHERE id=?',(*values,existing[0]))
        else:
            cursor = conn.execute('INSERT INTO runs(ts,model,agent,input_tokens,output_tokens,cost_usd,tags,metadata) VALUES(?,?,?,?,?,?,?,?)',values)
            conn.execute('INSERT OR REPLACE INTO collector_keys(key,run_id) VALUES(?,?)',(r['key'],cursor.lastrowid))


def bucket(rows):
    return {'rows':len(rows),'input_tokens':sum(r['input_tokens'] for r in rows),'output_tokens':sum(r['output_tokens'] for r in rows),'unpriced_rows':sum(r['cost_usd'] is None for r in rows),'cost_usd':sum(r['cost_usd'] or 0 for r in rows)}


def aggregate(conn,since,coverage):
    rows = [dict(r) for r in conn.execute('SELECT runs.* FROM runs JOIN collector_keys ON runs.id=collector_keys.run_id WHERE ts>=?',(since,))]
    def groups(key):
        names = sorted({r[key] for r in rows})
        return [{key:name,**bucket([r for r in rows if r[key]==name])} for name in names]
    empty = bucket([])
    return {'generated':datetime.now(timezone.utc).isoformat(),'window':{'first':min((r['ts'] for r in rows),default=None),'last':max((r['ts'] for r in rows),default=None)},'totals':{'in_baseline':bucket(rows)},'split':{'scheduled':empty,'interactive':empty,'unclassified':bucket(rows)},'by_workstream':groups('agent'),'by_model':groups('model'),'coverage':coverage,'note':'Local transcript usage only. Unknown prices are unpriced. Automation classification is unavailable.'}


def atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp = tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(value,stream,indent=2,allow_nan=False)
            stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def run(config):
    database = Path(config['database']).expanduser().resolve()
    summary = Path(config['summary']).expanduser().resolve()
    since = stamp(config['since'])
    projects = []
    for project in config.get('projects',[]):
        if project.get('require_opt_in'):
            choice_path = Path(project['root'])/'.aptica/ai-cost.json'
            if not choice_path.exists(): continue
            choice = json.loads(choice_path.read_text())
            if choice.get('mode') not in ('development','both'): continue
            if any(choice.get(key) != project[key] for key in ('project_id','environment')):
                raise ValueError('Project choice differs from host mapping')
        projects.append(project)
    for p in projects:
        if safe_name(p['project_id']) != p['project_id'] or safe_name(p['environment']) != p['environment']:
            raise ValueError('Invalid project labels')
        if database.is_relative_to(Path(p['root']).resolve()) or summary.is_relative_to(Path(p['root']).resolve()):
            raise ValueError('Telemetry must be external to source')
    pricing = config.get('pricing',{})
    conn = connect(database)
    project_connections = {}
    coverage = []
    try:
        for p in projects:
            target=Path(p['database']).expanduser().resolve()
            if target.is_relative_to(Path(p['root']).resolve()) or target == database:
                raise ValueError('Project store must be external and separate')
            project_connections[(p['project_id'],p['environment'])] = connect(target)
        # Configuration changes invalidate the scan cache, including newly enabled
        # projects and pricing. No raw paths are written into the cache.
        config_hash=digest(json.dumps({**config,'resolved_projects':projects},sort_keys=True))
        for source in config['sources']:
            name=source['kind']
            if name not in ('cowork','claude-code','codex'):
                raise ValueError('Unsupported source')
            root=Path(source['root']).expanduser().resolve()
            health={'source':name,'files':0,'updated_files':0,'partial_lines':0,'invalid_lines':0,'unsupported_events':0,'status':'ok' if root.is_dir() else 'missing'}
            if root.is_dir():
                for path in sorted(root.rglob('*.jsonl')):
                    if path.is_symlink():continue
                    health['files']+=1
                    stat=path.stat();key=digest(str(path));fingerprint=f'{VERSION}:{config_hash}:{stat.st_ino}:{stat.st_mtime_ns}:{stat.st_size}'
                    cached=conn.execute('SELECT fingerprint,health FROM collector_files WHERE key=?',(key,)).fetchone()
                    if cached and cached[0]==fingerprint:
                        file_health=json.loads(cached[1])
                    else:
                        file_health={'partial_lines':0,'invalid_lines':0,'unsupported_events':0}
                        records=parse(path,name,projects,file_health)
                        # Complete project writes before marking the global file
                        # done. A crash reruns safe upserts in every affected store.
                        for (project,env),pc in project_connections.items():
                            with pc:
                                write_records(pc,[r for r in records if r['agent']==project and r['environment']==env],pricing)
                        with conn:
                            write_records(conn,records,pricing)
                            conn.execute('INSERT OR REPLACE INTO collector_files VALUES(?,?,?)',(key,fingerprint,json.dumps(file_health)))
                        health['updated_files']+=1
                    for field,value in file_health.items():health[field]+=value
                if health['invalid_lines'] or health['unsupported_events']:health['status']='partial'
                elif not health['files']:health['status']='empty'
            coverage.append(health)
        result=aggregate(conn,since,coverage)
        atomic_json(summary,result)
        return {'generated':result['generated'],'rows':result['totals']['in_baseline']['rows'],'coverage':coverage}
    finally:
        conn.close()
        for pc in project_connections.values():pc.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(run(json.loads(args.config.read_text())),indent=2))


if __name__=='__main__':main()
