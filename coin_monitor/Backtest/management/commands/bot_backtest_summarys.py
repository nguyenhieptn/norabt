from datetime import datetime
from dateutil import tz

from django.core.management.base import BaseCommand
from helper.Defaults import *
from helper.Data import *

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import subprocess


VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

class Command(BaseCommand):
    help = 'Run multi campaign'
    
    #python manage.py bot_backtest_summarys

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        listOfCamp = [
            # 'pair_trading_band_5m_2std',
            # 'pair_trading_band_5m_3std',
            # 'pair_trading_band_10m_2std',
            # 'pair_trading_band_10m_3std',
            # 'pair_trading_band_20m_2std',
            # 'pair_trading_band_20m_3std',
            # 'pair_trading_band_30m_2std',
            # 'pair_trading_band_30m_3std',
            # 'pair_trading_band_45m_2std',
            # 'pair_trading_band_45m_3std',
            # 'pair_trading_band_60m_2std',
            # 'pair_trading_band_60m_3std',
            # 'pair13_trading_band_5m_3std',
            # 'pair13_trading_band_10m_3std',
            # 'pair13_trading_band_30m_3std',
            # 'pair13_trading_band_45m_3std',
            # 'pair13_trading_band_60m_3std',
            # 'pair_trading_band_30m_3std_50',
            # 'pair_trading_band_30m_3std_unlimit',
            # 'pair_trading_band_30m_3std_100'
            
            # 'pair_trading_band_10m_mid',
            # 'pair_trading_band_10m_upper',
            # 'pair_trading_band_10m_lower',
            # 'pair_trading_band_40m_mid',
            # 'pair_trading_band_40m_upper',
            # 'pair_trading_band_40m_lower',
            # 'pairlong_trading_band_120m_upper',
            # 'pairlong_trading_band_120m_lower',
            # 'pairlong_trading_band_180m_upper',
            # 'pairlong_trading_band_180m_lower',
            # 'pairlong_trading_band_240m_upper',
            # 'pairlong_trading_band_240m_lower',
            
            'pair_trading_band_60m_fishing_normal',
            'pair_trading_band_60m_fishing_invert'
            
           
        ]
        
        # Process data
        summaryDatas = []
        self.pnlDataframe = []
        for camp in listOfCamp:
            print(f"Process campaign {camp}")
            sumData = self.handleCamp(camp)
            if(sumData is not None): summaryDatas.append(sumData)
        
        #Print summary data    
        summaryDatas = pd.DataFrame(summaryDatas)
        print(summaryDatas.to_string())
        
        
        #create figure
        pnlDataframe = pd.concat(self.pnlDataframe, axis=1)
        pnlDataframe = pnlDataframe.sort_index()
        pnlDataframe = pnlDataframe.fillna(0)
        
        # Create pnl figure
        fig = self.createFig('PNL')
        fileName = f'/home/ubuntu/api_gateway/api/publish/Plots/backtest_pnl.html'
        timex = pd.to_datetime(pnlDataframe.index.to_list(), unit='ms', utc=True).tz_convert(VN_TZ)
        for col in pnlDataframe.columns:
            print(f"Create chart {col}")
            fig.add_trace(go.Scattergl(
                x=timex,
                y=pnlDataframe[col],
                name=col,
            ), row=1, col=1)
        
        
        config = {}
        config.setdefault("showLink", False)
        config.setdefault("responsive", True)
        fig.write_html(
            fileName,
            config=config,
            auto_play=True,
            include_plotlyjs=True,
            include_mathjax=False,
            post_script=None,
            full_html=True,
            validate=True,
            animation_opts=None,
            auto_open=False,
            default_width='100%',
            default_height='100%',
        )
        
        # Create pnl cumsum
        fig = self.createFig('PNL')
        fileName = f'/home/ubuntu/api_gateway/api/publish/Plots/backtest_pnl_cumsum.html'
        timex = pd.to_datetime(pnlDataframe.index.to_list(), unit='ms', utc=True).tz_convert(VN_TZ)
        for col in pnlDataframe.columns:
            print(f"Create chart {col}")
            fig.add_trace(go.Scattergl(
                x=timex,
                y=pnlDataframe[col].cumsum(),
                name=col,
            ), row=1, col=1)
        
        
        config = {}
        config.setdefault("showLink", False)
        config.setdefault("responsive", True)
        fig.write_html(
            fileName,
            config=config,
            auto_play=True,
            include_plotlyjs=True,
            include_mathjax=False,
            post_script=None,
            full_html=True,
            validate=True,
            animation_opts=None,
            auto_open=False,
            default_width='100%',
            default_height='100%',
        )
        
        
        
    
    def handleCamp(self, campName):
        campaignCfg = campName
       
        resultModel = MongoModel('stock_backtest_result').setCollection(f"coin_{campaignCfg}")
        results = list(resultModel.collection.find({'bot_act_commission':{'$gt':0}}, {"_id":0, "orders":0, "bot_act_enter_data":0, "bot_act_exit_data":0}))
        if(len(results) == 0):
            print("No result")
            return
        
        results = pd.DataFrame(results)
        
        results['interval'] = results['bot_act_exit_time'] - results['bot_act_enter_time']
        
        meanInterval = results.loc[results['bot_act_commission'] > 0]['interval'].mean()//60000
        
        totalAction = len(results.loc[results['bot_act_commission'] > 0])
        totalTakeprofit = len(results.loc[results['bot_act_real_pnl'] > 0])
        totalStoploss = len(results.loc[results['bot_act_real_pnl'] < 0])
        totalQty = results['bot_act_qty'].sum()
        totalPNL = f"{round(results['bot_act_real_pnl'].sum()):,}"
        totalCommission = f"{round(results['bot_act_commission'].sum()):,}"
        maxTakeprofit = f"{round(results['bot_act_real_pnl'].max()):,}"
        maxStoploss = f"{round(results['bot_act_real_pnl'].min()):,}"
        winrate = round(totalTakeprofit * 100 / totalAction, 2)
        
        
        summary = {
            'Campaign': campaignCfg,
            'Total Action' :totalAction,
            'Total Takeprofit' :totalTakeprofit,
            'Total Stoploss' :totalStoploss,
            'Total Qty' :totalQty,
            'Total PNL' :totalPNL,
            'Total Commission' :totalCommission,
            'Max Takeprofit' :maxTakeprofit,
            'Max Stoploss' :maxStoploss,
            'Winrate': f"{winrate}%",
            "Interval": meanInterval,
            
        }
        
        pnlDf = results[['bot_act_exit_time', 'bot_act_real_pnl']].set_index('bot_act_exit_time').rename(columns={'bot_act_real_pnl': campName})
        self.pnlDataframe.append(pnlDf)
        
        return summary
            
    
    def createFig(self, title):
        
        fig = make_subplots(
            rows= 1, 
            cols=1, 
            shared_xaxes=True, 
            row_heights=[600],
            vertical_spacing=0.02,
            subplot_titles=[title]
        )
    
        fig.update_layout(
            
            # legend = dict(orientation = "h",   # show entries horizontally
            #     xanchor = "center",  # use center of legend as anchor
            #     x = 0.5), # put legend in center of x-axis

            hovermode="x unified",
            hoverdistance=10,
            margin=dict(b=20, t=40, l=0, r=0),
            

        )
        fig.update_yaxes(showspikes=True, spikemode='across', spikesnap='cursor',  spikedash='dot')
        fig.update_xaxes(showspikes=True, spikemode='across', spikesnap='cursor',  spikedash='dot')
        fig.update_traces(xaxis='x1')
        fig.update_xaxes(dict(
            type='category',
            categoryorder = 'category ascending',
            rangeslider = {'visible': False}
            # tickvals=list(df.index)[::NSKIP],
            # ticktext=list(df['day'])[::NSKIP],
        ))
        fig.update_annotations(font_size=8)    
        return fig
    
        
       
            
       

           
    
        





        
        
        
        

    
        
        





        

        

        







        

        


    