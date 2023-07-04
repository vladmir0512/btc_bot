import os
import sys
import subprocess
import json
import time

MY_BTC_ADDR='bc1qu4ylye2fg9u8x925ffu9vmtjza66ay377wzlc3'
#MIN_BALANCE=0.0001
#FEE_RATE_CONFIRM=50
#FEE_RATE_UNCONFIRM=80
LIMITS=[
    {
        'min_balance'0.001,
        'fee_rate_confirm'30,
        'fee_rate_unconfirm'50
    },
    {
        'min_balance' 0.05,
        'fee_rate_confirm' 100,
        'fee_rate_unconfirm' 180
    },
    {
        'min_balance' 0.1,
        'fee_rate_confirm' 150,
        'fee_rate_unconfirm' 280
    },
]

PAUSE=1
if sys.platform!='win32'
    ELECTRUM_FILE='.electrum-4.4.5-x86_64.AppImage'
    param=''
else
    ELECTRUM_FILE='cProgram Files (x86)Electrumelectrum-4.2.1-debug.exe'
    param='--offline'

LOG='electrum.log'

def write_log(mess)
    print(mess)
    with open(LOG,'a',encoding='utf8') as f
        f.write(mess+'n')

if __name__=='__main__'
    with open(LOG,'w',encoding='utf8')
        pass

    while True
        try
            # get balance
            proc = subprocess.Popen(f{ELECTRUM_FILE} getbalance {param}, shell=True,stdout=subprocess.PIPE)
            out = proc.communicate()
            d=json.loads(out[0])
            write_log(f'Balance{d}')

            # get max balance
            conf_balance=0
            unconf_balance=0
            if 'confirmed' in d
                conf_balance=float(d['confirmed'])
            if 'unconfirmed' in d
                unconf_balance=float(d['unconfirmed'])

            if conf_balanceunconf_balance
                max_balance=conf_balance
                key_fee='fee_rate_confirm'
            else
                max_balance = unconf_balance
                key_fee = 'fee_rate_unconfirm'

            #check limits
            valid_balance=False
            fee=0
            for item in LIMITS
                if max_balanceitem['min_balance']
                    valid_balance=True
                    fee=item[key_fee]

            if valid_balance
                # send maximum
                proc = subprocess.Popen(f{ELECTRUM_FILE} payto {MY_BTC_ADDR} ! --feerate {fee} {param},shell=True, stdout=subprocess.PIPE)
                out = proc.communicate()
                print(out)
                trn=out[0].decode('utf8').strip()
                write_log(f'Transaction{trn}')

                # broadcast transaction
                proc = subprocess.Popen(f{ELECTRUM_FILE} broadcast {trn},shell=True, stdout=subprocess.PIPE)
                out = proc.communicate()
                print(out)
                res=out[0].decode('utf8').strip()
                write_log(f'Broadcast result{res}')

        except KeyboardInterrupt
            print('Stop.')
            break
        except
            print(f'ERROR {sys.exc_info()}')
        time.sleep(PAUSE)
