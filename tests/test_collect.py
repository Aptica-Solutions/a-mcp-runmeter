import json
from pathlib import Path
import sqlite3
import pytest
import runmeter_collect as c

TS='2026-09-08T10:00:00Z'

def write(path,items):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(i)+'\n' for i in items))

def claude(id='msg_test',output=3,cwd='/synthetic/repo'):
    return {'type':'assistant','timestamp':TS,'cwd':cwd,'message':{'role':'assistant','id':id,'model':'synthetic','content':'PRIVATE CONTENT MUST NEVER BE STORED','usage':{'input_tokens':10,'output_tokens':output,'cache_read_input_tokens':20,'cache_creation_input_tokens':30,'cache_creation':{'ephemeral_5m_input_tokens':10,'ephemeral_1h_input_tokens':20}}}}

def config(tmp_path):
    return {'database':str(tmp_path/'data/host.db'),'summary':str(tmp_path/'data/summary.json'),'since':'2026-09-01T00:00:00Z','projects':[{'root':'/synthetic/repo','project_id':'synthetic-project','environment':'development','database':str(tmp_path/'project/development.db')}],'sources':[{'kind':'claude-code','root':str(tmp_path/'transcripts')}], 'pricing':{'synthetic':{'uncached_input':1,'output_tokens':2,'cache_read':0.1,'cache_write_5m':1.25,'cache_write_1h':2}}}

def rows(cfg):
    with sqlite3.connect(cfg['database']) as db:
        db.row_factory=sqlite3.Row
        return [dict(r) for r in db.execute('select * from runs')]

def test_repeated_streaming_blocks_and_replay_are_idempotent(tmp_path):
    cfg=config(tmp_path);p=tmp_path/'transcripts/session.jsonl'
    write(p,[claude(output=1),claude(output=3),claude(output=3)])
    c.run(cfg);c.run(cfg)
    r=rows(cfg);assert len(r)==1
    assert r[0]['input_tokens']==60 and r[0]['output_tokens']==3
    assert r[0]['cost_usd']==pytest.approx((10+2+12.5+40+6)/1e6)
    write(p,[claude(output=1),claude(output=7)])
    c.run(cfg);assert len(rows(cfg))==1 and rows(cfg)[0]['output_tokens']==7
    with sqlite3.connect(cfg['projects'][0]['database']) as db:
        assert db.execute('select count(*) from runs').fetchone()[0]==1
    assert 'PRIVATE' not in json.dumps(rows(cfg))
    summary=Path(cfg['summary']).read_text()
    assert 'PRIVATE' not in summary and 'msg_test' not in summary and '/synthetic' not in summary

def test_fork_duplicate_and_smaller_copy_do_not_double_or_reduce(tmp_path):
    cfg=config(tmp_path)
    write(tmp_path/'transcripts/a.jsonl',[claude(output=10)])
    write(tmp_path/'transcripts/b.jsonl',[claude(output=2)])
    c.run(cfg);assert len(rows(cfg))==1 and rows(cfg)[0]['output_tokens']==10

def test_codex_uses_native_events_once_and_does_not_add_reasoning(tmp_path):
    cfg=config(tmp_path);cfg['sources'][0]['kind']='codex'
    items=[{'type':'session_meta','payload':{'id':'thread','cwd':'/synthetic/repo'}},{'type':'turn_context','payload':{'model':'synthetic'}}]
    items += [{'type':'token_usage_record','timestamp':TS,'payload':{'response_id':'resp_test','usage':{'input_tokens':100,'cached_input_tokens':80,'output_tokens':20,'reasoning_output_tokens':15}}}]*2
    items += [{'type':'event_msg','timestamp':TS,'payload':{'type':'token_count','info':{'total_token_usage':{'input_tokens':100,'output_tokens':20}}}}]
    write(tmp_path/'transcripts/codex.jsonl',items);c.run(cfg)
    assert len(rows(cfg))==1
    assert rows(cfg)[0]['input_tokens']==100 and rows(cfg)[0]['output_tokens']==20

def test_legacy_codex_cumulative_mirrors_and_resets(tmp_path):
    cfg=config(tmp_path);cfg['sources'][0]['kind']='codex'
    items=[{'type':'session_meta','payload':{'id':'thread','cwd':'/synthetic/repo'}}]
    for n in (100,100,150,10,20):
        items.append({'type':'event_msg','timestamp':TS,'payload':{'type':'token_count','info':{'total_token_usage':{'input_tokens':n,'output_tokens':n//10}}}})
    write(tmp_path/'transcripts/codex.jsonl',items);result=c.run(cfg)
    assert sum(r['input_tokens'] for r in rows(cfg))==160
    assert result['coverage'][0]['unsupported_events']==1

def test_unknown_cache_price_is_not_assumed(tmp_path):
    cfg=config(tmp_path);item=claude();item['message']['usage'].pop('cache_creation')
    write(tmp_path/'transcripts/session.jsonl',[item]);c.run(cfg)
    assert rows(cfg)[0]['cost_usd'] is None

def test_missing_roots_and_partial_lines_are_visible(tmp_path):
    cfg=config(tmp_path);result=c.run(cfg);assert result['coverage'][0]['status']=='missing'
    p=tmp_path/'transcripts/session.jsonl';write(p,[claude()])
    with p.open('a') as f:f.write('{incomplete')
    result=c.run(cfg);assert result['coverage'][0]['partial_lines']==1
    assert len(rows(cfg))==1

def test_unknown_models_are_unpriced_and_unclassified(tmp_path):
    cfg=config(tmp_path);cfg['pricing']={}
    write(tmp_path/'transcripts/session.jsonl',[claude()]);c.run(cfg)
    summary=json.loads(Path(cfg['summary']).read_text())
    assert summary['totals']['in_baseline']['unpriced_rows']==1
    assert summary['split']['unclassified']['rows']==1
    assert summary['split']['scheduled']['rows']==summary['split']['interactive']['rows']==0

def test_existing_manual_rows_are_preserved_and_excluded_from_host_export(tmp_path):
    cfg=config(tmp_path);conn=c.connect(Path(cfg['database']))
    conn.execute("INSERT INTO runs(ts,model,input_tokens,output_tokens) VALUES(?,?,?,?)",(TS,'manual',123,456));conn.commit();conn.close()
    write(tmp_path/'transcripts/session.jsonl',[claude()]);c.run(cfg)
    assert len(rows(cfg))==2
    assert json.loads(Path(cfg['summary']).read_text())['totals']['in_baseline']['rows']==1

def test_new_project_config_reprocesses_cached_files(tmp_path):
    cfg=config(tmp_path);project=cfg['projects'].pop()
    write(tmp_path/'transcripts/session.jsonl',[claude()]);c.run(cfg)
    cfg['projects'].append(project);c.run(cfg)
    with sqlite3.connect(project['database']) as db:assert db.execute('select count(*) from runs').fetchone()[0]==1

def test_source_storage_rejected(tmp_path):
    cfg=config(tmp_path);cfg['projects'][0]['root']=str(tmp_path)
    with pytest.raises(ValueError,match='external'):c.run(cfg)


def test_confirmed_project_opt_out_stops_future_project_writes(tmp_path):
    cfg=config(tmp_path);project=cfg['projects'][0]
    project['root']=str(tmp_path/'repo');project['require_opt_in']=True
    choice=Path(project['root'])/'.aptica/ai-cost.json';choice.parent.mkdir(parents=True)
    data={'mode':'development','project_id':project['project_id'],'environment':project['environment']}
    choice.write_text(json.dumps(data))
    write(tmp_path/'transcripts/session.jsonl',[claude(id='first',cwd=project['root'])]);c.run(cfg)
    data['mode']='none';choice.write_text(json.dumps(data))
    write(tmp_path/'transcripts/session.jsonl',[claude(id='first',cwd=project['root']),claude(id='second',cwd=project['root'])]);c.run(cfg)
    with sqlite3.connect(project['database']) as db:assert db.execute('select count(*) from runs').fetchone()[0]==1
    data['mode']='development';choice.write_text(json.dumps(data));c.run(cfg)
    with sqlite3.connect(project['database']) as db:assert db.execute('select count(*) from runs').fetchone()[0]==2


@pytest.mark.parametrize('inputs,expected',[(272000,0.272010),(272001,0.544017)])
def test_context_price_boundary_includes_cache_and_entire_output(inputs,expected):
    record={'model':'test','input_tokens':inputs,'uncached_input':0,'cache_read':inputs,'cache_write_5m':0,'cache_write_1h':0,'cache_write_unknown':0,'output_tokens':2}
    pricing={'test':{'uncached_input':10,'cache_read':1,'output_tokens':5,'long_context':{'above_input_tokens':272000,'rates':{'uncached_input':20,'cache_read':2,'output_tokens':7.5}}}}
    assert c.price(record,pricing)==pytest.approx(expected)


def test_missing_long_context_rate_remains_unpriced():
    record={'model':'test','input_tokens':3,'uncached_input':3,'cache_read':0,'cache_write_5m':0,'cache_write_1h':0,'cache_write_unknown':0,'output_tokens':2}
    pricing={'test':{'uncached_input':1,'output_tokens':1,'long_context':{'above_input_tokens':2}}}
    assert c.price(record,pricing) is None
