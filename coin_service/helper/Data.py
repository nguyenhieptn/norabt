import pandas as pd
from datetime import datetime
from dateutil import tz

VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

def splitCollName(startTime, stopTime, symbol, tail):
    '''
    return list of day and start/stop time
    [{
        date: '2022_06_01',
        collection: '2022_06_01_BTCUSDT_tail',
        startTime: 1654072377214
        stopTime: 1653695999999
    }]
    '''

    if(startTime >= stopTime): return []
    
    hs = 60*60*1000

    hourRange = range(startTime, stopTime + hs, hs)

    data = pd.DataFrame({"time": hourRange})
    data.loc[data['time'] > stopTime, 'time'] = stopTime
    
    data['startTime'] = data['time']//hs * hs
    data['stopTime'] = (data['time']//hs + 1) * hs - 1
    data.loc[data['stopTime'] > stopTime, 'stopTime'] = stopTime
    data.loc[data['startTime'] < startTime, 'startTime'] = startTime
    
    data['date'] = data['time'].apply(lambda x: datetime.fromtimestamp(x/1000, tz=VN_TZ).strftime('%Y_%m_%d'))
    
    data = data.groupby(['date']).agg({
        'date': 'last',
        'startTime': 'first',
        'stopTime': 'last'
    })

    data['collection'] = data['date'] + f"_{symbol}_{tail}"

    return data.to_dict(orient="records")

def ftx2binance(symbol:str):
    ftxInBinance = ['1INCH-PERP', 'AAVE-PERP', 'ADA-PERP', 'ALGO-PERP', 'ALICE-PERP', 'ALPHA-PERP', 'APE-PERP', 'AR-PERP', 'ATOM-PERP', 'AUDIO-PERP', 'AVAX-PERP', 'AXS-PERP', 'BAL-PERP', 'BAND-PERP', 'BAT-PERP', 'BCH-PERP', 'BNB-PERP', 'BTC-PERP', 'C98-PERP', 'CELO-PERP', 'CHR-PERP', 'CHZ-PERP', 'COMP-PERP', 'CRV-PERP', 'CVC-PERP', 'CVX-PERP', 'DASH-PERP', 'DEFI-PERP', 'DENT-PERP', 'DOGE-PERP', 'DOT-PERP', 'DYDX-PERP', 'EGLD-PERP', 'ENJ-PERP', 'ENS-PERP', 'EOS-PERP', 'ETC-PERP', 'ETH-PERP', 'FIL-PERP', 'FLM-PERP', 'FLOW-PERP', 'FTM-PERP', 'FTT-PERP', 'GAL-PERP', 'GALA-PERP', 'GMT-PERP', 'GRT-PERP', 'HBAR-PERP', 'HNT-PERP', 'HOT-PERP', 'ICP-PERP', 'ICX-PERP', 'IMX-PERP', 'IOST-PERP', 'IOTA-PERP', 'JASMY-PERP', 'KAVA-PERP', 'KNC-PERP', 'KSM-PERP', 'LDO-PERP', 'LINA-PERP', 'LINK-PERP', 'LRC-PERP', 'LTC-PERP', 'LUNA2-PERP', 'MANA-PERP', 'MATIC-PERP', 'MKR-PERP', 'MTL-PERP', 'NEAR-PERP', 'NEO-PERP', 'OMG-PERP', 'ONE-PERP', 'ONT-PERP', 'OP-PERP', 'PEOPLE-PERP', 'QTUM-PERP', 'RAY-PERP', 'REEF-PERP', 'REN-PERP', 'ROSE-PERP', 'RSR-PERP', 'RUNE-PERP', 'RVN-PERP', 'SAND-PERP', 'SC-PERP', 'SKL-PERP', 'SNX-PERP', 'SOL-PERP', 'SPELL-PERP', 'SRM-PERP', 'STG-PERP', 'STMX-PERP', 'STORJ-PERP', 'SUSHI-PERP', 'SXP-PERP', 'THETA-PERP', 'TLM-PERP', 'TOMO-PERP', 'TRX-PERP', 'UNI-PERP', 'VET-PERP', 'WAVES-PERP', 'XEM-PERP', 'XLM-PERP', 'XMR-PERP', 'XRP-PERP', 'XTZ-PERP', 'YFI-PERP', 'ZEC-PERP', 'ZIL-PERP', 'ZRX-PERP']
    if symbol in ftxInBinance:    
        return symbol.replace("-PERP", "USDT")
    specialSymbolMapping = {
        "LUNC-PERP": "1000LUNCUSDT",
        "SHIB-PERP": "1000SHIBUSDT"        
    }
    if symbol in specialSymbolMapping:
        return specialSymbolMapping[symbol]

    raise Exception(f"Symbol {symbol} not exits in Binance")