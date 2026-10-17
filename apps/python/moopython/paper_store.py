"""Transactional paper experiments and durable audit inputs, outside quote retention."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import zlib
from .market_store import SnapshotStore
from .paper_engine import initialize,advance,summarize
from . import paper_engine,paper_strategies


def encode(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':'))


def engine_hash():
    # Frozen applications ship these two source files as audit resources as well.
    source=''.join(Path(module.__file__).with_suffix('.py').read_text(encoding='utf-8')
                   for module in (paper_engine,paper_strategies))
    return hashlib.sha256(source.encode('utf-8')).hexdigest()


class PaperStore:
    def __init__(self,store=None): self.store=store or SnapshotStore()

    def list(self):
        with self.store.connect() as db:
            return [dict(id=r[0],name=r[1],mode=r[2],created_at=r[3]) for r in db.execute(
                'SELECT id,name,mode,created_at FROM paper_experiments ORDER BY id DESC')]

    @staticmethod
    def _input(db,experiment_id,payload,observed):
        raw=encode(payload).encode()
        return db.execute('INSERT INTO paper_inputs(experiment_id,observed_at,checksum,payload) VALUES (?,?,?,?)',
                          (experiment_id,observed,hashlib.sha256(raw).hexdigest(),zlib.compress(raw))).lastrowid

    @staticmethod
    def _records(db,experiment_id,input_id,rows,fills):
        for fill in fills:
            db.execute('''INSERT INTO paper_fills(experiment_id,client_id,session_date,symbol,side,quantity,price,fee,input_id,evidence)
                          VALUES (?,?,?,?,?,?,?,?,?,?)''',
                       (experiment_id,fill['client_id'],fill['date'],fill['symbol'],fill['side'],fill['quantity'],fill['price'],fill['fee'],input_id,encode(fill)))
        for row in rows:
            db.execute('INSERT INTO paper_valuations(experiment_id,client_id,session_date,input_id,evidence) VALUES (?,?,?,?,?)',
                       (experiment_id,row['client_id'],row['date'],input_id,encode(row)))

    def create(self,name,payload,config,observed_at=None,mode='forward',start=None):
        observed=observed_at or datetime.now(timezone.utc).isoformat()
        if not isinstance(name,str) or not name.strip(): raise ValueError('Paper experiment needs a name')
        config=dict(config,engine_sha256=engine_hash())
        state=initialize(payload,config,observed,mode,start)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            experiment_id=db.execute('INSERT INTO paper_experiments(name,mode,created_at,configuration,state) VALUES (?,?,?,?,?)',
                                    (name.strip(),mode,observed,encode(config),encode(state))).lastrowid
            input_id=self._input(db,experiment_id,payload,observed)
            for client in state['clients']:
                db.execute('INSERT INTO paper_clients(experiment_id,client_id,strategy,initial_capital) VALUES (?,?,?,?)',
                           (experiment_id,client['id'],client['strategy'],config['initial_capital']))
            anchors=[dict(client_id=c['id'],date=state['last_date'],nav=c['nav'],cash=c['cash'],
                          contributions=c['contributions'],net_pnl=0,return_pct=0,drawdown_pct=0,exposure_pct=0,
                          deposit=c['contributions'],fees=0,slippage=0,realized_pnl=0,closed_trades=0,wins=0,
                          positions={},decision=c['pending'],corporate_actions=[]) for c in state['clients']]
            self._records(db,experiment_id,input_id,anchors,[])
        return self.report(experiment_id)

    def load(self,experiment_id):
        with self.store.connect() as db:
            row=db.execute('SELECT name,state,revision FROM paper_experiments WHERE id=?',(experiment_id,)).fetchone()
        if row is None: raise ValueError('Unknown paper experiment')
        return row[0],json.loads(row[1]),row[2]

    def update(self,experiment_id,payload,observed_at=None):
        observed=observed_at or datetime.now(timezone.utc).isoformat()
        name,before,revision=self.load(experiment_id)
        if before['config']['engine_sha256']!=engine_hash(): raise ValueError('Paper implementation changed; create a new experiment to keep versions separate')
        state,rows,fills=advance(before,payload,observed)
        if rows:
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                current=db.execute('SELECT revision FROM paper_experiments WHERE id=?',(experiment_id,)).fetchone()[0]
                if current!=revision: raise RuntimeError('Another process updated this experiment; retry with its latest state')
                input_id=self._input(db,experiment_id,payload,observed)
                self._records(db,experiment_id,input_id,rows,fills)
                db.execute('UPDATE paper_experiments SET state=?,revision=revision+1 WHERE id=?',(encode(state),experiment_id))
        result=self.report(experiment_id)
        result['new_valuations']=len(rows); result['new_fills']=len(fills)
        return result

    def report(self,experiment_id):
        # Consistent read: state, ledger and evidence come from one SQLite snapshot.
        with self.store.connect() as db:
            db.execute('BEGIN')
            row=db.execute('SELECT name,state FROM paper_experiments WHERE id=?',(experiment_id,)).fetchone()
            if row is None: raise ValueError('Unknown paper experiment')
            history=[json.loads(r[0]) for r in db.execute('SELECT evidence FROM paper_valuations WHERE experiment_id=? ORDER BY session_date,client_id',(experiment_id,))]
            fills=[json.loads(r[0]) for r in db.execute('SELECT evidence FROM paper_fills WHERE experiment_id=? ORDER BY session_date,id',(experiment_id,))]
        result=summarize(json.loads(row[1]),history,fills)
        result.update(id=experiment_id,name=row[0],history=history,fills=fills)
        return result

    def audit_input(self,input_id):
        with self.store.connect() as db:
            row=db.execute('SELECT checksum,payload FROM paper_inputs WHERE id=?',(input_id,)).fetchone()
        if row is None: raise ValueError('Unknown paper input')
        raw=zlib.decompress(row[1])
        if hashlib.sha256(raw).hexdigest()!=row[0]: raise RuntimeError('Paper input checksum mismatch')
        return json.loads(raw)
