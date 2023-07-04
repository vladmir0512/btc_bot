from common import *
import requests
import sys,os
import sqlite3
import argparse
import time
import datetime
import subprocess

ELECTRUM_FILE = './electrum-4.4.5-x86_64.AppImage'

NODE_URL=f'http://{rpcuser}:{rpcpassword}@{rpcbind}:{rpcport}'
LOG='mempool.log'

CREATE_TBL = "CREATE TABLE tmp (addr VARCHAR(100) PRIMARY KEY NOT NULL UNIQUE ON CONFLICT IGNORE,prefix VARCHAR(10), pk VARCHAR(100))"
DB_NAME='btc.db'

CREATE_TBL_TRX = "CREATE TABLE tmp (thash VARCHAR(100) PRIMARY KEY NOT NULL UNIQUE ON CONFLICT IGNORE)"

def write_log(data):
    print(data)
    with open(LOG,'a',encoding='utf-8') as f:
        f.write(f'{datetime.datetime.now()}\t{data}\n')

class DBControllerTrx:
    def __init__(self):
        self.conn=sqlite3.connect("file::memory:?cache=shared", uri=True,detect_types=sqlite3.PARSE_DECLTYPES)
        self.creat_tables()

    def insert_trx(self,thash):
        cur=self.conn.cursor()
        try:
            cur.execute('insert into tmp values (?)',(thash,))
            self.conn.commit()
        except:
            self.conn.rollback()
            raise

    def thash_in_db(self,thash):
        cur=self.conn.cursor()
        r=cur.execute('select thash from tmp where thash=?',(thash,)).fetchone()
        return r

    def __del__(self):
        self.conn.close()

    def creat_tables(self):
        cur=self.conn.cursor()
        try:
            sqls=CREATE_TBL_TRX.split(';')
            for s in sqls:
                try:
                    cur.execute(s)
                    self.conn.commit()
                except:
                    self.conn.rollback()

        except:
            self.conn.rollback()
            raise

class DBController:
    def __init__(self):
        #self.conn=sqlite3.connect("file::memory:?cache=shared", uri=True,detect_types=sqlite3.PARSE_DECLTYPES)
        if os.path.isfile(DB_NAME):
            self.conn=sqlite3.connect(DB_NAME, uri=True,detect_types=sqlite3.PARSE_DECLTYPES)
        else:
            self.conn = sqlite3.connect(DB_NAME, uri=True, detect_types=sqlite3.PARSE_DECLTYPES)
            self.creat_tables()

    def insert_addr(self,addr,prefix,pk):
        cur=self.conn.cursor()
        try:
            cur.execute('insert into tmp values (?,?,?)',(addr,prefix,pk))
            #self.conn.commit()
        except:
            self.conn.rollback()
            raise

    def addr_in_db(self,addr):
        cur=self.conn.cursor()
        r=cur.execute('select addr,prefix,pk from tmp where addr=?',(addr,)).fetchone()
        return r

    def __del__(self):
        self.conn.close()

    def creat_tables(self):
        cur=self.conn.cursor()
        try:
            sqls=CREATE_TBL.split(';')
            for s in sqls:
                try:
                    cur.execute(s)
                    self.conn.commit()
                except:
                    self.conn.rollback()

        except:
            self.conn.rollback()
            raise
    def commit(self):
        self.conn.commit()


def send_rpc(method,params):
    headers = {'content-type': 'application/json'}
    #'{"jsonrpc": "1.0", "id": "curltest", "method": "getrawmempool", "params": [true]}'
    rpc_input={
        "jsonrpc": "2.0", "id": "0",
        "method":method,
        "params":params
    }

    response = requests.post(
        NODE_URL,
        json=rpc_input,
        headers=headers,
        timeout=10)
    if response.status_code==200:
        return response.json()['result']

def getrawmempool():
    res=send_rpc('getrawmempool',[False])
    return res

def getrawtransaction(tid):
    res=send_rpc('getrawtransaction',[tid,True])
    return res

def send_tg(text):
    try:
        res = requests.get(TG_URL % (BOT_TOKEN, TG_CHAT_ID, text))
    except:
        print(sys.exc_info())

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-a',default=None)
    args = parser.parse_args()

    db=DBController()
    if args.a is not None:
        print('Save input to DB file...')
        c=0
        i=0
        for line in open(args.a, 'r', encoding='utf-8'):
            try:
                addr,prefix,pk = line.strip().split(':')
                db.insert_addr(addr,prefix,pk)
                c+=1
                i+=1
                print(f'Add {i} records',end='\r')
                if c>=10000:
                    c=0
                    db.commit()
            except:
                pass
        db.commit()

        print(f'Add {i} records')

    print('Start main cycle...')
    db_tr=DBControllerTrx()
    prev_mempool=[]
    while True:
        try:
            trxs=getrawmempool()
            print(f'{len(trxs)} transactions in Mempool')
            for tid in trxs:
                if tid in prev_mempool:
                    continue
                if db_tr.thash_in_db(tid) is not None:
                    print('ignore tid=',tid)
                    continue
                #db_tr.insert_trx(tid)
                trx=getrawtransaction(tid)
                for vout in trx['vout']:
                    try:
                        addr=vout['scriptPubKey']['address']
                        v=vout['value']
                        #print(addr)
                        res=db.addr_in_db(addr)
                        if res is not None:
                            addr,prefix,pk=res
                            msg=f'Mempool:\n' \
                                f'{addr}:{prefix}:{pk}\n' \
                                f'{v} BTC'
                            write_log(msg)
                            proc = subprocess.Popen(f"{ELECTRUM_FILE} importprivkey {prefix}:{pk}",
                                                    shell=True,
                                                    stdout=subprocess.PIPE)
                            #send_tg(msg)
                            db_tr.insert_trx(tid)
                    except:
                        pass
            prev_mempool=trxs.copy()
            time.sleep(1)
        except KeyboardInterrupt:
            break
        except:
            pass
            #print(f'ERROR GLOBAL: {sys.exc_info()}')
