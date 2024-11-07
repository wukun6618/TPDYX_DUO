#encoding:gbk
'''
读取通达信自选股下单示例
重要：使用面单设置参数的时候一定要导入XML文件
XML的文件名一定要和策略的文件名一样
XML格式如下：目前还可以加入两个自定义控件

    <?xml version="1.0" encoding="utf-8"?>
<TCStageLayout>
    <control note="控件">
        <variable note="控件">
            <item position="" bind="stockPath_buy" value="C:\new_tdx\T0002\blocknew\GB.blk" note="选择txt文件的路径" name="买入股票池路径" type="intput"/>
            <item position="" bind="stockPath_sell" value="C:\new_tdx\T0002\blocknew\QX.blk" note="选择txt文件的路径" name="卖出股票池路径" type="intput"/>
            <item position="" bind="M_Start_Time" value="09:30:00" note="连续竞价监控开始时间" name="监控开始时间" type="intput"/>
            <item position="" bind="M_End_Time" value="02:57:00" note="连续竞价监控截止时间" name="监控截止时间" type="intput"/>
            <item position="" bind="Max_buynums" value="10" note="最大可买入股票的数量" name="最大可买入股票数" type="intput"/>
            <item position="" bind="Fundbal_AvailRate" value="0.05" note="单只买入股票占可用资金，,0.05即可用资金的5%" name="可用资金比例" type="intput"/>
        </variable>
    </control>
</TCStageLayout>

因为iquant选30只股会出现很卡的现象，所以会选择通达信用指标选一个股票池子
然后导入自己的策略选出一个iquant的池子，再从这个较小的池子选出股票
一 股票池（面单自己设定）：
1.C:\\new_tdx\\T0002\\gb.blk 2.C:\goldsun\T0002\blocknew\sell.blk

二 监控时间（面单自己设定）：
连续竞价：09:30:00 - 10:30:00

四 卖出条件
   若有卖出股票池且有持仓,   则全部卖出;


五 可调整参数：
01 可用资金 * 5%
02 最大买入股票数量

六：风险提示：
01 对应股票天当日发生除权事件(如：送股、配股、拆股等）—— 导致行情价产生跳变，程序处理不了；
七：特别提示：
该示例仅供技术参考，不可直接用于实盘，否则后果自负  量化技术交流与沟通：肖华平18180422359（手机/微信同号）。
'''
'''
#选择    账号    账号名称    登录状态    总资产           可用资金    账号密码    操作    账号类型
    510000000223            登录成功    500000.00       500000.00                       期货账号
    620000114082            登录成功    200002129.19    200002129.19                    股票账号
    620061121061            准备登录    0.00            0.00                            信用账号
    100010024567            准备登录    0.00            0.00                            股票期权账号
'''
import pandas as pd
import numpy as np
import datetime as dt
from iQuant_functools import *
import json
import requests
import time
import configparser
import xml.etree.ElementTree as ET
from xml.dom.minidom import parse
import os
import talib

pd.set_option('expand_frame_repr', False)  #不换行
pd.set_option('display.max_rows', 5000)     #最多显示数据的行数
pd.set_option('display.unicode.ambiguous_as_wide', True) # 中文字段对齐
pd.set_option('display.unicode.east_asian_width', True)
pd.set_option('display.float_format', lambda x: '%.3f' % x) # dataframe格式化输出

list_data_values                    = []#[[0,0, 0, 0, 0, 0,0,0,0,0,0,0,0,0,0,0,0,0,0]]
ATR_LEN                             = 5
YKB                                 = 3
Max_buynums                         = 2
DEFAULT_NUMBER_OF_POINTS            = 0.02
TRADE_DIRECT                        = 48



class b():
    pass
classlocal = b()

classlocal.printmoney_en            = 1
classlocal.printlocalhold_en        = 1
classlocal.sell_debug_inf_en        = 0
classlocal.checklist_debug_en       = 0 #打印本地自选股行情
classlocal.Index_time_debug_en      = 0
classlocal.Trade_init_debug_en      = 0 #
classlocal.model_df_level2_debug_en = 0 #模型选出列表购买列表
classlocal.JLZY_debug_en            = 0 #棘轮止盈打印
classlocal.huicedebug_en            = 0 #回测的时候打开，运行的时候关闭
classlocal.mp_debug_origin_en       = 0 #模型选出打印
classlocal.ZXCS_debug_en            = 0 #执行周期和次数打印
classlocal.h_data_debug_en          = 0 #打印执行选股前的行情数据
classlocal.TPDYX_debug_en           = 0 #debug信息打印
classlocal.TPDYX_STOP_DEBUG         = 0 #行情止损打印
classlocal.check_list               = ['SA00.ZF']
classlocal.check_list_debug_en      = 0 #自定义行情品种
classlocal.contract_debug_en        = 0 #打印合约信息
classlocal.barsincentry_debug_en    = 0 #打印合约信息
# -------------------------------------------#
# 行情设置开关
classlocal.lefthand_checken         = 1                 # 1 打开行情止损 0 关闭
classlocal.LongMarginRatio_add      = 0.45              # 在最低保证金基础增加的比例
classlocal.close_atr_trade_en       = 0                 #0：关掉ART 1:打开ATR行情止盈
classlocal.max_buy_nums             = Max_buynums
# -------------------------------------------#
# 数据类型
classlocal.p                        = 0                 # 绘图点用
classlocal.count                    = 0                 # 01 记录定时函数执行次数
classlocal.Period_Type              = '20m'
classlocal.trade_buy_record_dict    = {}                # 02 买入交易记录
classlocal.buy_code_count           = 0                 # 03 风控函数，防止买入过多。
classlocal.Reflash_buy_list         = 1

classlocal.LongMarginRatio_add      = 0.45              # 在最低保证金基础增加的比例

classlocal.write_cnt                = 0                 # 计时变量
classlocal.write_local_data         = 1                 # 0:不更新 1：写数据到本地，默认进去写一次，
classlocal.write_local_hold_data_freq = 50000           # 写数据到本地时间，只有实盘的时候这个时间才生效


classlocal.draw_df                  = pd.DataFrame()
# 0：无需刷新stock_level1_lsit 1:需要重新刷新stock_level1_lsit
classlocal.ATR_open_Length          = 4*ATR_LEN         # 图标bar线数量为20

classlocal.ATR_close_Length         = 3*ATR_LEN         # 图标Bar线数量为10
classlocal.M_HL                     = 3*ATR_LEN         # 中轴线参数设置为10

classlocal.MA_middle_length         = 184#99            # 中均线长度
classlocal.MA_long_length           = 215#144           # 长均线长度

classlocal.ATR                      = 0  # ATR平均真实波幅
classlocal.ATR_BuyK                 = 0  # 开多时ATR数值
classlocal.ATR_SellK                = 0  # 开空时ATR数值
classlocal.Price_BuyK               = 0  # 开多时的价格
classlocal.Price_SellK              = 0  # 开空时的价格
classlocal.close                    = 0  #
classlocal.open                     = 0  #
classlocal.low                      = 0  #
classlocal.highmax                  = 0  #
classlocal.lowmin                   = 0  #
classlocal.szxfd                    = 0.018 #
classlocal.modul_length             = 240 #多少日

#大阳线均线突破
classlocal.TPDYX_en                 = 1
classlocal.TPDYX                    = 0
classlocal.TPDYXsp                  = 8888
classlocal.volume                   = 0
classlocal.selTPDYX_stopcheck       = 0
classlocal.sellTPDYX_time           = 16    #买入后多久执行

################################################################################################
#1.总涨幅止盈
classlocal.Price_SellYA_Ratio       = 2    #涨到个点止盈,手动买入时生效
#2.时间止盈
classlocal.BarSinceEntrySet         = 200  #N天时间止损
#3.盈亏比预设
classlocal.Price_SetSellY_YKB       = YKB    #盈亏比设置为3
classlocal.Price_SetSellS           = DEFAULT_NUMBER_OF_POINTS  #默认止损,无论如何都会在
classlocal.Price_SetSellYratio      = DEFAULT_NUMBER_OF_POINTS*YKB  #
#3.5 盈亏比止盈触发后进行棘轮止盈
classlocal.Price_SellS1_ATRratio    = 15    #ATR棘轮止损默认
classlocal.Price_SellY1_ATRratio    = 0.02   #ATR 止盈 默认比例 越大约灵敏大
classlocal.TC_ATRratio              = 1.0


classlocal.Price_SellY              = 0     #棘轮止盈利开始价格
classlocal.Price_SellY1             = 0     #棘轮止盈止盈价格,根据ATR值相关

#classlocal.Price_SetSellY1          = 1     #
classlocal.Price_SellY_Flag         = 0     #第一阶段止盈达到
classlocal.TH_low                   = 5.9   #价格筛选下线单位元
classlocal.TH_High                  = 100    #价格筛选上线单位元
################################################################################################

classlocal.Kindex                   = 0     # 当前K线索引
classlocal.Lastkindextime           = ''     # 当前K线索引
classlocal.Lastkindextime_draw      = ''     # 用于画图

classlocal.Kindex_time              = 0     # 当前K线对应的时间
classlocal.zf_lastK                 = 0     # 当前K线对应的涨幅
classlocal.buy_list                 = []    #买入列表
classlocal.sell_list                = []    #卖出列表
classlocal.LeftMoey                 = 1     #剩余资金
classlocal.LeftMoeyLast             = 0     #上次剩余
classlocal.Total_market_cap         = 0     #持仓次市值
classlocal.Total_market_capLast     = 0     #上次持仓次市值
classlocal.sp_type                  = 'NONE'
classlocal.eastmoney_zx_name        = ''
classlocal.eastmoey_stockPath       = ''
classlocal.eastmoney_user_buy_list  = ''
classlocal.eastmoney_zx_name_list   = ''
classlocal.stockPath_hold           = ''
classlocal.user_buy_list            = ''


classlocal.trade_direction  = 'kong' #duo #kong
classlocal.code             = 'SA00.SF'
classlocal.kindextime       = '0'
classlocal.timetype         = '20m'
classlocal.tradetype        = 'open'  #open #close
classlocal.tradedata        = ''
classlocal.stop             = 0
classlocal.takeprofit       = 0

classlocal.last_price       = 0
classlocal.profit           = 0
classlocal.mediumprice      = 0
classlocal.tradestatus      = ''
classlocal.modle            = ''
classlocal.URLopen          = 'https://open.feishu.cn/open-apis/bot/v2/hook/fb5aa4f9-16b9-49f2-8e3b-2583ec3f3e3e'
classlocal.URLclose         = 'https://open.feishu.cn/open-apis/bot/v2/hook/fb5aa4f9-16b9-49f2-8e3b-2583ec3f3e3e'

# -------------------------------------------#
# -------------------------------------------#
# 判断类型
#classlocal.BuyPK    = False  # 开多条件
#classlocal.SellPK   = False  # 开空条件
#classlocal.BuyAK    = False  # 加多条件
#classlocal.SellAK   = False  # 加空条件
#classlocal.BuyA     = False  # 加仓使能
#classlocal.SellA    = False  # 加空使能
#classlocal.BuyS     = False  # 多头止损
#classlocal.SellS    = False  # 空头止损
#classlocal.BuyY     = False  # 空头止盈
classlocal.SellY    = False  # 多头止盈
classlocal.ISfirst  = True   # 多头止盈

###################################start###########################################################################
#
###################################start###########################################################################
def init(ContextInfo):
    #---------------------------------------------------------------------------
    #*为了编译不报错定义了如下变量的初始值，
    #1.如果用实盘需要修改下面参数
    #2.实盘的时候可以将这些参数屏蔽掉从XML导入的控件输入初始值，
    #建议用这种方式设置交易初始值
    #global Tradehistory
    global local_hold
    global classlocal

    global deleted_rows
    #current_hold = local_hold_data_frame_init()
    if classlocal.huicedebug_en :
        account             = 'test'
    else :
        account             = '510000165852'
    accountType             = 'FUTURE'
    eastmoey_stockPath      = 'C:\\eastmoney\\swc8\\config\\User\\9489316496536486\\StockwayStock.ini'
    stockPath_sell          = 'C:\\new_tdx\\T0002\\blocknew\\QX.blk'
    stockholdingpath        = 'C:\\Users\\wukun\\Desktop\\tradehistory\\localhold_duo.csv'
    user_buy_list_path      = 'C:\\Users\\wukun\\Desktop\\tradehistory\\userbuylist_duo.csv'
    stockrecord             = 'C:\\Users\\wukun\\Desktop\\tradehistory\\trade_record_duo.csv'


    M_Start_Time            = "09:25:00"
    M_End_Time              = "02:57:00"
    singel_zf_lastK         = 0.03
    eastmoney_user_buy_list = ['SFT']# ['FUTURE']
    if classlocal.huicedebug_en:
        eastmoney_zx_name_listt =['FT1','FT2','FT3','FT4','FT5','FT6','FT7',\
                                'FT8','FT9','FTA','FTB','FTC','FTD','FTE']
        #eastmoney_zx_name_listt = ['FT1']
    else:
        eastmoney_zx_name_listt =['FT1','FT2','FT3','FT4','FT5','FT6','FT7',\
                                'FT8','FT9','FTA','FTB','FTC','FTD','FTE']
        eastmoney_zx_name_listt = ['FT1']
    #当前K线的对应的下标从0开始
    #---------------------------------------------------------------------------
    # 账号为模型交易界面选择账号
    ContextInfo.accID           = str(account)
    ContextInfo.accountType     = str(accountType).upper()
    ContextInfo.set_account(ContextInfo.accID)
    ContextInfo.val_TrueRange   =[]
    now_time                    = dt.datetime.now().strftime('%Y%m%d')
    #print(type(now_time))
    # 01_采用run_time定时驱动函数
    # ===========周期函数====================
    #print('\n',G_df)
    #print(f'\ninit执行: {dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    # 周期函数 (每隔5S，执行MyHandlebar一次)
    current_time = (dt.datetime.now()).strftime('%Y%m%d%H%M') + '00'
    ContextInfo.run_time('MyHandlebar', '5nSecond', current_time, "SH")

    # 02_可调参数,从界面读取
    classlocal.eastmoey_stockPath    = eastmoey_stockPath          #买入股票路径
    classlocal.stockPath_sell        = stockPath_sell             #卖出股票路径
    classlocal.stockPath_hold        = stockholdingpath           #持仓保存路径
    classlocal.user_buy_list_path    = user_buy_list_path              #手动加自选的记录路径
    classlocal.stockPath_recordh     = stockrecord                #本地交易记录保存
    #classlocal.max_buy_nums          = Max_buynums                #最大可买入股票数量
    #classlocal.max_singbuy_price     = max_singbuy_price          #单只最高买入最大金额
    #classlocal.buy_avail_rate        = Fundbal_AvailRate          #单只支票买入金额_(可用资金*classlocal.buy_avail_rate(0.10))

    classlocal.monitor_start_time    = M_Start_Time               #监控开始时间
    classlocal.monitor_end_time      = M_End_Time                 #监控开始时间
    classlocal.stockPath_sell        = stockPath_sell             #卖出股票路径
    #classlocal.Total_drawdown_ratio  = drawdown_ratio             #调整持仓交易总金额
    classlocal.zf_lastK              = singel_zf_lastK            #最后一日个股涨幅
    #classlocal.eastmoney_zx_name     = eastmoney_zx_name          #自选分组的名字
    classlocal.eastmoney_zx_name_list = eastmoney_zx_name_listt   #自选分组名字
    classlocal.eastmoney_user_buy_list = eastmoney_user_buy_list   #自选分组名字
    GlobalVariiable(ContextInfo)
    #从本地读取数据
    local_hold      = read_local_hold_data(classlocal.stockPath_hold,False)
    #Tradehistory    = read_local_hold_data(classlocal.stockPath_recordh,False)
    if(classlocal.printlocalhold_en and not local_hold.empty):
        print(f'local_hold_INTI:\n{local_hold}')

    '''
    4.enum_EEntrustStatus //委托状态
    ENTRUST_STATUS_WAIT_END:        0; //委托状态已经在ENTRUST_STATUS_CANCELED或以上，但是
    成交数额还不够，等成交回报来
    ENTRUST_STATUS_UNREPORTED :     48; // 未报
    ENTRUST_STATUS_WAIT_REPORTING : 49; // 待报
    ENTRUST_STATUS_REPORTED :       50; // 已报
    ENTRUST_STATUS_REPORTED_CANCEL :51; // 已报待撤
    ENTRUST_STATUS_PARTSUCC_CANCEL :52; // 部成待撤
    ENTRUST_STATUS_PART_CANCEL :    53; // 部撤
    ENTRUST_STATUS_CANCELED :       54; // 已撤
    ENTRUST_STATUS_PART_SUCC :      55; // 部成
    ENTRUST_STATUS_SUCCEEDED :      56; // 已成
    ENTRUST_STATUS_JUNK :           57; // 废单
    ENTRUST_STATUS_DETERMINED :     86; //已确认
    ENTRUST_STATUS_UNKNOWN :        255; // 未知
    '''
    #查询当日委托记录
    found_list  = []
    obj_list    = get_trade_detail_data(ContextInfo.accID,'FUTURE','position')
    orders      = get_trade_detail_data(ContextInfo.accID, ContextInfo.accountType, 'order')
    for order in orders:
        if  (order.m_strRemark in '读取通达信自选股下单示例') and \
            ('卖出'         not in order.m_strOptName)     and \
            (order.m_nOrderStatus in (48,49,50,51,52,53,55,56)):
            #order.m_strRemark("order.m_strRemark:",order.m_strRemark)
            #m_strInstrumentID 证券代码 m_strExchangeID：交易所
            #m_strOptName 买卖的标记    m_nOrderStatus 委托状态
            #m_nDirection ：EEntrustBS 类型,操作,多空,期货多空 股票买卖永远是48，其他的dir同理
            code = str(order.m_strInstrumentID)+'.'+str(order.m_strExchangeID)
            print(code,order.m_strOptName,order.m_nOrderStatus,order.m_nDirection)
            #code：000001.sz
            if code not in found_list:
                found_list.append(code)
            #委托数据更新到买入字典
            if code not in classlocal.trade_buy_record_dict.keys():
                classlocal.trade_buy_record_dict[code] = ['委托记录', '读取通达信自选股下单示例']
    #print(f'\n当日委托股票数据：{found_list}')
    #print('\nA：',A)
###################################start###########################################################################
#周期函数 (每隔5S，执行MyHandlebar一次)，'5nSecond'
###################################start###########################################################################
def MyHandlebar(ContextInfo):
    #print(f'\n周期函数执行handlebar:  第{classlocal.count}次')
    classlocal.write_cnt +=  1
    if classlocal.write_cnt >= classlocal.write_local_hold_data_freq:
        classlocal.write_local_data = 1
        classlocal.write_cnt = 0
    else:

        classlocal.write_local_data = 0
    pass
###################################start###########################################################################
#主图Tick 触发
###################################start###########################################################################
def handlebar(ContextInfo):
    global Sell_list
    global account_df
    global handlebarcnt
    global Buy_df
    global model_df_level2

    if classlocal.huicedebug_en != 1:
        if not ContextInfo.is_last_bar():
            return

    local_hold                  = read_local_hold_data(classlocal.stockPath_hold,False)
    if classlocal.ISfirst :
        classlocal.ISfirst      = False
        Sell_list               = []
        handlebarcnt            = 0
        # 获取当前账户的资金信息
        #测试的时候暂时放这里
        Buy_df                  = pd.DataFrame()
        model_df_level2         = pd.DataFrame()
       
        classlocal.Lastkindextime_draw = classlocal.Lastkindextime
    if ContextInfo.is_last_bar():
        os.remove(classlocal.stockPath_hold)
    account_df                  = account_info(ContextInfo)
    #print('account_df.index',account_df.index)
    #剩余资金
    classlocal.LeftMoey         = account_df.loc[0]['总资产'] - account_df.loc[0]['总市值']
    #总市值
    classlocal.Total_market_cap = account_df.loc[0]['总资产']
    classlocal.LeftMoey         = decimal_places_are_rounded(classlocal.LeftMoey,2)
    classlocal.Total_market_cap = decimal_places_are_rounded(classlocal.Total_market_cap,2)

    zjlyl = account_df.loc[0]['总市值']/account_df.loc[0]['总资产']
    if zjlyl >= 0.5:
        print('account_df.loc[0][总市值]:\n',account_df.loc[0]['总市值'])
    if not local_hold.empty :
        if(classlocal.printlocalhold_en and not local_hold.empty):
            print('LeftMoey        :',classlocal.LeftMoey)
            print('Total_market_cap:',classlocal.Total_market_cap)
            print('本地读到的持仓:\n',local_hold)

    Kindex                      = ContextInfo.barpos
    classlocal.p                 = ContextInfo.get_net_value(Kindex)                         #该索引策略回测的净值，后面绘图使用
    index_time                  = timetag_to_datetime(ContextInfo.get_bar_timetag(Kindex),'%Y%m%d')

    if (classlocal.Period_Type[-1] == 'd'):
        index_time              = timetag_to_datetime(ContextInfo.get_bar_timetag(Kindex),'%Y%m%d')
    elif (classlocal.Period_Type[-1] == 'm'):
        index_time              = timetag_to_datetime(ContextInfo.get_bar_timetag(Kindex),'%Y%m%d%H%M%S')
    now_time                    = dt.datetime.now().strftime('%H:%M:%S')
    classlocal.Kindex           = Kindex
    classlocal.Kindex_time      = index_time
    if classlocal.Index_time_debug_en :
        print('\nKindex:',Kindex)
        print('index_time:',index_time)
        print('now_time:',now_time)
        print('classlocal.Period_Type:',classlocal.Period_Type)
    if Kindex > 1:
        clum = 0
        classlocal.count += 1
        #----------------------------------------------------------------------------------------------------------
        obj_list = get_trade_detail_data(ContextInfo.accID,'FUTURE','position')
        for obj in obj_list:
            if classlocal.contract_debug_en:
                print_position_data(obj)

            code = obj.m_strInstrumentID + '.' + obj.m_strExchangeID
            #----------------------------------------
            #更新上次数据到local_hold_df dataframe
            uptate_local_hold_prama(code)
            #----------------------------------------
            #local_hold.loc[code,'Buy_time']           = obj.m_strOpenDate
           # local_hold.loc[code,'Price_BuyK']         = obj.m_dOpenPrice
            local_hold.loc[code,'Tradingday']         = obj.m_strTradingDay
            local_hold.loc[code,'mLast_KIndex']       = Kindex
            local_hold.loc[code,'Price_BuyK']         = decimal_places_are_rounded(obj.m_dOpenPrice,2)
            local_hold.loc[code,'strInstrumentID']    = obj.m_strExchangeID
            local_hold.loc[code,'nVolume']            = obj.m_nVolume
            local_hold.loc[code,'nCanUseVolume']      = obj.m_nCanUseVolume
            local_hold.loc[code,'dProfitRate']        = decimal_places_are_rounded(obj.m_dProfitRate,2)
            local_hold.loc[code,'PositionProfit']     = decimal_places_are_rounded(obj.m_dPositionProfit,2)
            #local_hold.loc[code,'dPositionCost']      = int(obj.m_dPositionCost)
            #dPositionCost = local_hold.loc[code,'dPositionCost']
            #print('dPositionCost',dPositionCost)
            local_hold.loc[code,'dMarketValue']       = decimal_places_are_rounded(obj.m_dMarketValue,2)
            local_hold.loc[code,'dLastPrice']         = decimal_places_are_rounded(obj.m_dLastPrice,2)
            local_hold.loc[code,'tradedirection']     = TRADE_DIRECT
            #账户代码持仓方向
            remote_tradedirection                     =  obj.m_nDirection
            #open_price                                = local_hold.loc[code,'Price_BuyK']
            #-----------------------------------------------------------------------------------------------------
            Price_SellY1_debug = local_hold.loc[code,'Price_SellY1']
            
            if code in model_df_level2.index:
                if code in local_hold.index:
                    list_clolums2 = ['Kindex','Tradingday','Price_SellS','Price_SellY','ATR_BuyK']
                    #print('model_df_level2\n',model_df_level2)
                    #print('local_hold-updating\n',local_hold)
                    for clum in list_clolums2 :
                        #print('clum:\n',clum)
                        local_hold.loc[code,'BarSinceEntry']    = 0
                        local_hold.loc[code,'mBuy_KIndex']      = classlocal.Kindex
                        local_hold.loc[code,'mLast_KIndex']     = classlocal.Kindex
                        local_hold.loc[code,'Buy_time']         = classlocal.Kindex_time
                        local_hold.loc[code,'Tradingday']       = classlocal.Kindex_time
                        local_hold_Price_SellY1                 = model_df_level2.loc[code,'Price_SellY']*(1+classlocal.Price_SetSellS*2)
                        local_hold.loc[code,'Price_SellY1']     = decimal_places_are_rounded(local_hold_Price_SellY1,2)
                        local_hold_Price_SellS1                 = model_df_level2.loc[code,'Price_SellS']
                        local_hold.loc[code,'Price_SellS1']     = decimal_places_are_rounded(local_hold_Price_SellS1,2)
                        local_hold.loc[code,clum]               = model_df_level2.loc[code,clum]
                        #print('local_hold-updating\n',local_hold)
                    #无需重新策略选股 无需重新写初始交易计划
                    #classlocal.Reflash_buy_list = 0
                    #更新完删除掉
                    model_df_level2.drop(code,inplace=True)
                    if code in Buy_df.index:
                        Buy_df.drop(code,inplace=True)
                    print('更新初始持仓信息\n',local_hold)
                    ##print('model_df_level2_end_drop_code\n',model_df_level2)
            #-----------------------------------------------------------------------------------------------------
            #之所以不查云端的是因为，可能存在多空都存在，不确定是什么值
            tradedirection      = float(local_hold.loc[code,'tradedirection'])
            #如果此时读到的不是多就跳过此次判断，不去执行
            if remote_tradedirection != TRADE_DIRECT:
               #多持仓就丢掉这行
               local_hold.drop(code,inplace=True)
               continue
            local_hold.loc[code,'tradedirection']   = remote_tradedirection
            
            mLast_KIndex        = float(local_hold.loc[code,'mLast_KIndex'])
            mBuy_KIndex         = float(local_hold.loc[code,'mBuy_KIndex'])
            BarSinceEntry       = float(local_hold.loc[code,'BarSinceEntry'])
            Price_SellY         = float(local_hold.loc[code,'Price_SellY'])
            Price_SellY1        = float(local_hold.loc[code,'Price_SellY1'])
            Price_SellS         = float(local_hold.loc[code,'Price_SellS'])
            Price_SellS1        = float(local_hold.loc[code,'Price_SellS1'])
            Price_BuyK          = float(local_hold.loc[code,'Price_BuyK'])
            Buy_time            = (local_hold.loc[code,'Buy_time'])
            Buy_time            = float(Buy_time)
            ATR_BuyK            = float(local_hold.loc[code,'ATR_BuyK'])
            ATR_Start_time      = local_hold.loc[code,'ATR_Start_time']
            Price_SellY_Flag    = float(local_hold.loc[code,'Price_SellY_Flag'])
            ATR_Start_time      = float(ATR_Start_time)

            Price_SellY1_debug  = local_hold.loc[code,'Price_SellY1']
            #print('Price_SellY1_debug2:',Price_SellY1_debug)
            #print('code:',code)

            if(pd.isna(Price_SellY_Flag)) :
                Price_SellY_Flag                        = 0
                local_hold.loc[code,'Price_SellY_Flag'] = 0
            if(pd.isna(mLast_KIndex)) :
                mLast_KIndex                            = 0
                local_hold.loc[code,'mLast_KIndex']     = 0

            if(pd.isna(mBuy_KIndex)) :
                mBuy_KIndex                             = 0
                local_hold.loc[code,'mBuy_KIndex']      = 0
            if(pd.isna(BarSinceEntry)) :
                #BarSinceEntry = int(BarSinceEntry)
                BarSinceEntry                           = 0
                local_hold.loc[code,'BarSinceEntry']    = 0
            if(pd.isna(Price_SellY)) :
                Price_SellY                             = 0
                local_hold.loc[code,'Price_SellY']      = 0
            if(pd.isna(Price_SellY1)) :
                Price_SellY1                            = 0
                local_hold.loc[code,'Price_SellY1']     = 0
            if(pd.isna(Price_SellS)) :
                Price_SellS                             = 0
                local_hold.loc[code,'Price_SellS']      = 0
            if(pd.isna(Price_SellS1)) :
                Price_SellS1                            = 0
                local_hold.loc[code,'Price_SellS1']     = 0
            if(pd.isna(Price_BuyK)) :
                Price_BuyK                              = 0
                local_hold.loc[code,'Price_BuyK']       = 0
            if(pd.isna(Buy_time)) :
                Buy_time                                = 0
                local_hold.loc[code,'Buy_time']         = '0'
            if(pd.isna(ATR_BuyK)) :
                ATR_BuyK                                = 0
                local_hold.loc[code,'ATR_BuyK']         = 0
            if pd.isna(ATR_Start_time):
                ATR_Start_time                          = 0
                local_hold.loc[code,'ATR_Start_time']   = 0
            if pd.isna(tradedirection):
                tradedirection                          = 0
                local_hold.loc[code,'tradedirection']   = TRADE_DIRECT

            mLast_KIndex                                = int(mLast_KIndex)
            #--------------------------------------------------------------
            Buy_time                                    = int(Buy_time)
            #--------------------------------------------------------------
            #Price_SellY1_debug                          = local_hold.loc[code,'Price_SellY1']
            #print('Price_SellY1_debug3:',Price_SellY1_debug)
            #print('code:',code)
            #-------------------------------------------------------------------------------------------------------
            #在交易时间开仓
            if(obj.m_nCanUseVolume == 0) and (obj.m_nVolume) and \
                ( Buy_time == 0 ):
                local_hold.loc[code,'Buy_time']       = int(index_time)
                local_hold.loc[code,'BarSinceEntry']  = 1
                local_hold.loc[code,'mBuy_KIndex']    = Kindex

            #在交易至少一天后检测到有持仓,但是没有买入时间,就认为当天买入的票
            elif(obj.m_nCanUseVolume) and (obj.m_nVolume) and \
                (Buy_time == 0 ):
                local_hold.loc[code,'Buy_time']       = int(index_time)
                local_hold.loc[code,'BarSinceEntry']  = 1
                local_hold.loc[code,'mBuy_KIndex']    = Kindex
                #print(local_hold.loc[code,'BarSinceEntry'])
                #print(local_hold.loc[code,'Buy_time'])
            #有持仓,有开盘,有开仓天数
            elif(obj.m_nCanUseVolume) and (obj.m_nCanUseVolume) and \
                (Buy_time != 0 ):
                #次日运行本地的主图index和当前K线index会差1,
                #将K线当前索引更新到每只代码里
                #print('Kindex',Kindex)
                #print('BarSinceEntry',BarSinceEntry)
                #if(mLast_KIndex < Kindex):
                    #实盘打开判断只有是交易日的时候才可以计算 BarSinceEntry的值
                    #if(local_hold.loc[code,'Tradingday']==index_time):
                if(mBuy_KIndex == 0):
                    local_hold.loc[code,'mBuy_KIndex']   = Kindex
            mBuy_KIndex                                  = local_hold.loc[code,'mBuy_KIndex']
            local_hold.loc[code,'BarSinceEntry']         = Kindex - mBuy_KIndex
            local_hold.loc[code,'mLast_KIndex']          = Kindex
            
            if classlocal.barsincentry_debug_en:
                print('code:',code)
                print('Kindex:',obj.m_nCanUseVolume)
                print('mBuy_KIndex:',obj.m_nVolume)
                print('Buy_time:',Buy_time)
                print('Kindex:',Kindex)
                print('mBuy_KIndex:',mBuy_KIndex)
                print('BarSinceEntry:',local_hold.loc[code,'BarSinceEntry'])
                #local_hold = local_hold.fillna(0)
            #else :
            #在buy_list中
            #======================================================================================
            #以下部分核心止盈止损部分
            #======================================================================================
            #开仓价格
            Price_BuyK          = local_hold.loc[code,'Price_BuyK']
            #当前价格
            Last_Price_t        = obj.m_dLastPrice
            Last_Price          = decimal_places_are_rounded(Last_Price_t,2)
            #预设止盈位置
            Price_SellY         = local_hold.loc[code,'Price_SellY']
            #预设止盈ATR
            Price_SellY1        = local_hold.loc[code,'Price_SellY1']
            #第一止盈位置 默认0.08
            Price_SetSellYratio      = classlocal.Price_SetSellYratio
            #第二止盈位置
            Price_SellS1_t      = local_hold.loc[code,'Price_SellS1']
            Price_SellS1        = decimal_places_are_rounded(Price_SellS1_t,2)
            #开仓后第一次进来
            Price_SellY_Flag    = local_hold.loc[code,'Price_SellY_Flag']
            #据开仓多久
            BarSinceEntry       = local_hold.loc[code,'BarSinceEntry']

            Price_SellY1_t      = local_hold.loc[code,'Price_SellY1']
            Price_SellY1        = decimal_places_are_rounded(Price_SellY1_t,2)
            #单只收益率
            ProfitRate          = local_hold.loc[code,'dProfitRate']
            #配置止损
            Price = 0
            if local_hold.loc[code,'Price_SellS'] <= 0 or pd.isna(Price_SellS):
                Price = Price_BuyK * (1 - classlocal.Price_SetSellS)
                local_hold.loc[code,'Price_SellS']      = decimal_places_are_rounded(Price,2)

                #预设第二止损位置
                local_hold.loc[code,'Price_SellS1']     = local_hold.loc[code,'Price_SellS']

            if local_hold.loc[code,'Price_SellY'] <= 0 or pd.isna(Price_SellY):
                local_hold.loc[code,'Price_SellY_Flag'] = 0
                #第一止盈位置
                Price = Price_BuyK * (Price_SetSellYratio+1)
                local_hold.loc[code,'Price_SellY']      = decimal_places_are_rounded(Price,2)
                #Price_SellY1初始值
                local_hold.loc[code,'Price_SellY1']     = local_hold.loc[code,'Price_SellY']
            #给第二止损位置赋初值
            if local_hold.loc[code,'Price_SellS1'] <= 0 or pd.isna(Price_SellS1):
                Price = Price_BuyK * (1 - classlocal.Price_SetSellS)
                local_hold.loc[code,'Price_SellS1']     = decimal_places_are_rounded(Price,2)
            #给第二止盈位置赋初值
            if local_hold.loc[code,'Price_SellY1'] <= 0 or pd.isna(Price_SellY):
                Price = local_hold.loc[code,'Price_SellY']
                local_hold.loc[code,'Price_SellY1']     = decimal_places_are_rounded(Price,2)
            Price_SellY1_debug = local_hold.loc[code,'Price_SellY1']
            #print('Price_SellY1_debug4:',Price_SellY1_debug)
            #print('code:',code)
            #开仓止损如果没有按照系统比例设置
            Price_SellS     = local_hold.loc[code,'Price_SellS']
            ##预设第二止损位置
            Price_SellS1    = local_hold.loc[code,'Price_SellS1']
            Price_SellY     = local_hold.loc[code,'Price_SellY']
            Price_SellY1    = local_hold.loc[code,'Price_SellY1']
            #---------------------------------------------------------------------------------------------------------------------------
            ############################################################################################################################
            #这个区域部分是公共的获取行情信息，输出的数据格式是np.arry
            ############################################################################################################################

            endtime             = classlocal.Kindex_time
            length1             = classlocal.modul_length+5
            period_t            = classlocal.Period_Type
            code_list           = [code]
            if(classlocal.ZXCS_debug_en):
                print('codemain:',code)
                print('period_t:',period_t)
                print('endtime:',endtime)
                print('length1:',length1)

            h_data_init         = ContextInfo.get_market_data_ex(['close','high','open','low','volume'],\
                                code_list,period = period_t,end_time = endtime,count = length1,\
                                dividend_type='front', fill_data=True, subscribe = True)
            code_list           = []
            period_t        = classlocal.Period_Type
            if (period_t[-1] == 'm'):
                    #endtime_t = endtime[-6:-2]
                    #print('endtime_t:\n',endtime_t)
                    if 1:#( "0900" < endtime_t < "1500"):
                        h_data_code         = h_data_init[code]
                        h_data              = h_data_code.loc[h_data_code['volume'] != 0]
                        if classlocal.h_data_debug_en:
                            print('h_data_t:\n',h_data)
                        closes              = h_data['close']
                        lows                = h_data['low']
                        highs               = h_data['high']
                        opens               = h_data['open']
                        volumes             = h_data['volume']
                    else:
                        closes              = h_data[code]['close']
                        lows                = h_data[code]['low']
                        highs               = h_data[code]['high']
                        opens               = h_data[code]['open']
                        volumes             = h_data[code]['volume']
            elif period_t[-1] =="d":
                closes              = h_data[code]['close']
                lows                = h_data[code]['low']
                highs               = h_data[code]['high']
                opens               = h_data[code]['open']
                volumes             = h_data[code]['volume']
            else :
                closes              = h_data[code]['close']
                lows                = h_data[code]['low']
                highs               = h_data[code]['high']
                opens               = h_data[code]['open']
                volumes             = h_data[code]['volume']
            ############################################################################################################################
            #
            #买入后多少天后方向走坏了
            ML_length1              = classlocal.MA_middle_length + 9
            ML_length2              = classlocal.MA_middle_length

            MA_closes               = Convert_the_market_data_type(closes,lows,ML_length1)
            #昨日13日收盘价均值
            MA_middle               = np.mean(MA_closes[-(ML_length2 - 1):-1])
            MA_middle_7             = np.mean(MA_closes[-(ML_length2 + 7):-7])
            #昨日34日收盘价均值
            MA_long                 = np.mean(MA_closes[-(ML_length2 - 1):-1])
            MA_long_7               = np.mean(MA_closes[-(ML_length2 + 7):-7])

            sell_TPDYX_stopcheck    = MA_middle < MA_middle_7    #均线朝下检查离场

            lefthand                = sell_TPDYX_stopcheck and (BarSinceEntry >= classlocal.sellTPDYX_time)
            if classlocal.TPDYX_STOP_DEBUG:
                print('\ncode:',code)
                print(f'MA_middle:{MA_middle},MA_middle_7:{MA_middle_7},MA_long:{MA_long},MA_long_7:{MA_long_7}')
                print('\nlefthand:',lefthand)
                print('\nselTPDYX_stopcheck :',sell_TPDYX_stopcheck)
                print('\nBarSinceEntry:',BarSinceEntry)
                print('\nsellTPDYX_time:',classlocal.sellTPDYX_time)
            #均线朝下的时候卖出
            if (lefthand == True) and \
               (classlocal.lefthand_checken):
                classlocal.sp_type = '行情止损'
                Sell_list.append(code)
            ############################################################################################################################
            ############################################################################################################################
            #---------------------------------------------------------------------------------------------------------------------------
            #第一阶段
            #达到第一止盈位置,进来一次就不会再进来,本地上也会更新
            if (Last_Price > Price_SellY) and (Price_SellY_Flag == 0):
                local_hold.loc[code,'Price_SellY_Flag']         = 1
                local_hold.loc[code,'ATR_Start_time']           = index_time
                local_hold.loc[code,'mBuy_KIndex']              = Kindex
                local_hold.loc[code,'BarSinceEntry']            = 0
                #据开仓多久
                BarSinceEntry                                   = 0
                Price_SellY_Flag                                = 1
                if classlocal.close_atr_trade_en == 0:
                    Price_SellY_Flag                                = 0
                    Sell_list.append(code)
            #---------------------------------------------------------------------------------------------------------------------------
            #print('Price_SellY_Flag',Price_SellY_Flag)
            if Price_SellY_Flag :
                if classlocal.JLZY_debug_en:
                    print('进入棘轮止盈持仓信息:\n',local_hold)
                #第二阶段
                #在盈利达到Price_SetSellY%时执行棘轮止损
                ATR_Start_time  = local_hold.loc[code,'ATR_Start_time']
                ATR_BuyK        = local_hold.loc[code,'ATR_BuyK']
                ML_length       = classlocal.M_HL
                ML_closes       = Convert_the_market_data_type(closes,lows,ML_length)
                ML_lows         = Convert_the_market_data_type(lows,lows,ML_length)
                ML_highs        = Convert_the_market_data_type(highs,lows,ML_length)
                HSLS            = highs + lows
                ML_HSLS         = Convert_the_market_data_type(HSLS,lows,ML_length)
                #MLlength天内的高点低点平均值
                ML_value        = np.mean(ML_HSLS) / 2
                #当日最低的价格
                LowPrice        = ML_lows[-1]
                #当前中轴线参数和ATR结算时的参数保持一致
                ATR_close_length = ML_length
                classlocal_ATR  = calculate_ATR(ML_highs,ML_lows,ML_closes,ATR_close_length)*classlocal.TC_ATRratio
                classlocal.ATR  = decimal_places_are_rounded(classlocal_ATR,2)
                #第一次ATR的值
                if int(ATR_BuyK) == 0 or int(ATR_Start_time) == 0:
                    ATR_BuyK                        = classlocal.ATR
                    local_hold.loc[code,'ATR_BuyK'] = ATR_BuyK

                #为了防止第一次进来没有ATR的情况
                ATR_BuyK                            = local_hold.loc[code,'ATR_BuyK']
                #核心算法
                #多止盈：当日最低价和中值的最低值 + 开仓时均线数量乘以倍数的当前ATR
                SellY1ratio                         = classlocal.Price_SellY1_ATRratio
                Price_SellY1                        = min(LowPrice,ML_value) + BarSinceEntry * SellY1ratio * classlocal.ATR
                Price_SellY1                        = decimal_places_are_rounded(Price_SellY1,2)
                local_hold.loc[code,'Price_SellY1'] = Price_SellY1
                #收盘大于开仓价格加上买入时ATR值 并且 收盘小于等于止盈价格
                classlocal.SellY1                   = (Last_Price > (Price_BuyK + ATR_BuyK)) and (Last_Price <= Price_SellY1)
                #ATR止损条件,多头止损线
                #默认值2
                SellS1Ratio                         = classlocal.Price_SellS1_ATRratio
                Price_SellS1_t                      = Price_SellY - SellS1Ratio*ATR_BuyK
                Price_SellS1                        = decimal_places_are_rounded(Price_SellS1_t,2)
                local_hold.loc[code,'Price_SellS1'] = Price_SellS1
                #平多：当前收盘大于止损价格
                classlocal.SellS1                   = Last_Price < Price_SellS1
                if classlocal.SellS1 or classlocal.SellY1 :
                    if code not in Sell_list:
                        #放入卖出列表
                        #print(code,'棘轮止损')
                        if classlocal.SellS1 and BarSinceEntry:
                            classlocal.sp_type = '棘轮止损'
                        elif classlocal.SellY1 and BarSinceEntry:
                            classlocal.sp_type = '棘轮止赢'
                        else:
                            classlocal.sp_type = '棘轮退出'
                        #print(f'classlocal.SellS1:{classlocal.SellS1}\nclasslocal.SellY1:{classlocal.SellY1}')
                        Sell_list.append(code)
                if classlocal.JLZY_debug_en:
                    print('退出棘轮止盈持仓信息:',local_hold)
                            #执行卖出操作

            #---------------------------------------------------------------------------------------------------------------------------
            #持续监控
            #print(code)
            #print(f'classlocal.Price_SellS:\n{classlocal.Price_SellS}')
            if (Last_Price < Price_SellS ) and BarSinceEntry:
                if code not in Sell_list:
                    #放入卖出列表
                    #print(code,'空间止损')
                    classlocal.sp_type = '模型止损'
                    Sell_list.append(code)
                    #print(f'ProfitRate:\n{ProfitRate}')
            #时间止损
            #持仓大于classlocal.BarSinceEntrySet天(49)收益未达到classlocal.Price_SetSell(>8%)将进行自动止损-时间成本
            #print(f'时间止损:\n{BarSinceEntry},{classlocal.BarSinceEntrySet},{Price_SellS},{Last_Price},{Price_SellY}')

            #Price_SellY1_debug = local_hold.loc[code,'Price_SellY1']
            #print('Price_SellY1_debug6:',Price_SellY1_debug)
            #print('code:',code)
            if (Price_SellY_Flag == 0) and (BarSinceEntry > classlocal.BarSinceEntrySet) and (Last_Price < Price_SellY):
                if code not in Sell_list:
                    #放入卖出列表
                    classlocal.sp_type = '时间止损'
                    #print(code,'时间止损')
                    Sell_list.append(code)
            #翻倍止盈
            if Last_Price > ((classlocal.Price_SellYA_Ratio +1)* Price_BuyK) and Price_BuyK and BarSinceEntry:
                if code not in Sell_list:
                    #放入卖出列表
                    #空间止损
                    classlocal.sp_type = '翻倍止盈'
                    #print('ProfitRate',ProfitRate)
                    #print(code,'翻倍止盈')
                    Sell_list.append(code)
            if classlocal.sell_debug_inf_en :
                if Sell_list:
                    print(code)
                    print(index_time)
                    print('\nBarSinceEntry:',BarSinceEntry)
                    print('\nclasslocal.BarSinceEntrySet:',classlocal.BarSinceEntrySet)
                    print('\nPrice_SellY:',Price_SellY)
                    print('\nPrice_SellS:',Price_SellS)
                    print('\nPrice_SellS1:',Price_SellS1)
                    print('\nPrice_SellY1:',Price_SellY1)
                    print('\nLast_Price:',Last_Price)
        #卖出的票从dataframe中删除掉
        #deleted_rows = 0
        for code in local_hold.index :
            nCanUseVolume = (local_hold.loc[code,'nCanUseVolume'])
            nVolume       = (local_hold.loc[code,'nVolume'])
            dMarketValue  = (local_hold.loc[code,'dMarketValue'])
            if( nCanUseVolume== 0) and \
                ( nVolume== 0) and ( dMarketValue== 0):
                #print("drop_hang",code)
                # 将删除的行单独保存在新的DataFrame
                #如果当当天有卖记录卖出记录
                deleted_rows = local_hold.loc[code]
                #print(f'deleted_rows:{deleted_rows}')
                # 删除指定的行
                local_hold.drop(code,inplace=True)
                #之前有过持仓记录仪需要合并两次数据
                #if code in Tradehistory.index :
                #    Tradehistory.loc[code]  = deleted_rows + Tradehistory.loc[code]
                #else :
                    #如果没有持仓直接加入末尾
                #    Tradehistory_df         = Tradehistory.append(deleted_rows, ignore_index=False)
                #删除已卖出的卖出列表,防止后面再卖出
                if code in Sell_list:
                    Sell_list.remove(code)
                # print(f'Sell_list:\n{Sell_list}')

        #有新增卖出进行本地记录,没有新默认值为0不会进来
        #if not deleted_rows.empty:
        #    print(f'Tradehistory_df:\n{Tradehistory_df}')
        #    write_local_hold_data(Tradehistory_df,classlocal.stockPath_recordh,True)
        
        stockpath = classlocal.eastmoey_stockPath
        eastmoney_zx_name_list = classlocal.eastmoney_zx_name_list
        model_df_level2.drop(model_df_level2.index, inplace=True)

        for eastmoney_zx_name in eastmoney_zx_name_list:
            mdfl2 = Perform_stock_picks(ContextInfo,stockpath,eastmoney_zx_name,model_df_level2)
            #print('mdfl2:\n',mdfl2)
            if not mdfl2.empty:
                #
                model_df_level2 = model_df_level2.append(mdfl2)
            else :
                model_df_level2 = model_df_level2
        if classlocal.ZXCS_debug_en:
            print(f'\n周期函数执行:  第{classlocal.count}次')
            print('K线时间:',index_time)
            print(f'\n当前时间: {dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        #------------------------------------------------------------------------------
        # 删除停牌的票
        if classlocal.model_df_level2_debug_en and not model_df_level2.empty:
            print(f'model_df_level2—start:\n{model_df_level2}')
        if ContextInfo.accountType != 'FUTURE':
            if not model_df_level2.empty:
                for code in model_df_level2.index:
                    if ContextInfo.is_suspended_stock(code):
                        model_df_level2.drop(code,inplace=True)
        if classlocal.model_df_level2_debug_en and not model_df_level2.empty:
            print(f'模型最终选出列表:\n{model_df_level2}')
        #--------------------------------------------------------------------------
    handlebarcnt +=1
    if(classlocal.printlocalhold_en and not local_hold.empty):
        print(f'买卖前持仓信息:\n{local_hold}')

    #------------------------------------------------------------------------------
    #开多
    open_long_position(model_df_level2,ContextInfo)
    #------------------------------------------------------------------------------
    #平多
    close_long_position(ContextInfo,Sell_list,local_hold)
    #------------------------------------------------------------------------------
    if(classlocal.printlocalhold_en and not local_hold.empty):
        print(f'买卖后持仓信息:\n{local_hold}')
    #------------------------------------------------------------------------------
    #实盘生效
    if classlocal.huicedebug_en == 0:
        if classlocal.write_local_data:
            write_local_hold_data(local_hold,classlocal.stockPath_hold,True)
    else:
        write_local_hold_data(local_hold,classlocal.stockPath_hold,True)
    #写数据到本地
    #------------------------------------------------------------------------------
    if classlocal.huicedebug_en:
        #保存交易数据,回测的时候打开
        df1                = classlocal.draw_df
        df2                = tYield_tracking_calculations_and_presentations(classlocal)
        
        draw_df            = df1.append(df2, ignore_index=True)
        classlocal.draw_df = draw_df
       # write_local_hold_data(draw_df,classlocal.stockPath_recordh,True)

###################################start###########################################################################
#eastmoney_buy_list
#此函数的功能是手动添加自选买入
#执行步骤先从ini文件读取到信息，然后将详细写入本地csv表格中:
# 1.code 2.加入时间（标记非交易时间加入的） 3.写入表格 4.假如表格的时间是与现在相同，那么选择买入，否则输出列表不包含这个
#买入检测有效
###################################start###########################################################################
def eastmoney_buy_list_check(current_time_in,getstockpath, user_buy_list_name,tradingday):
    user_buy_list       = []
    # 01_读取待买入股票数据
    current_time         = current_time_in[-6:]#取后六位
    #白天
    daytrade_time       = (current_time >= '090000') and (current_time < '101500') and \
       (current_time >= '103000') and (current_time < '113000') and \
       (current_time >= '133000') and (current_time < '150000')
    #晚上
    night_trade_time_A  = (current_time >= '210000') and (current_time < '230000')
    night_trade_time_B  = (current_time >= '230000') and (current_time < '235959') or \
                          (current_time >= '000000') and (current_time < '013000')
    night_trade_time_C  = (current_time >= '013000') and (current_time < '023000')

    #在trading时间内去读本地数据
    if (daytrade_time or daytrade_time or night_trade_time_A  or night_trade_time_B or night_trade_time_C) & tradingday:
        #从INC获取自选
        check_list                      = parse_ini_file(getstockpath,user_buy_list_name)
        if len(check_list)>0:
            print('check_list_print:\n',check_list)
        for code in check_list:
            #查询是否本地持仓
            local_holded_contract       =  g_query.get_total_holding(code)
            #本地已在就不买
            if (local_holded_contract != code):
                code_t                  = code[2:]
                if night_trade_time_C:
                    #沪金 银
                    if code_t   == 'au' or 'ag':
                        user_buy_list               =  user_buy_list.append(code)
                if night_trade_time_B:
                    #铜 铝 氧化铝 锌 铅 镍 锡
                    if code_t   == 'cu' or 'al' or 'ao' or 'zn' or 'pb' or 'ni' or 'sn' or \
                                   'ss' or 'au' or 'ag':
                        user_buy_list               =  user_buy_list.append(code)
                #21:00 -23:00
                if night_trade_time_A:
                    if code_t =='cu' or 'al' or 'ao' or 'zn' or 'pb' or 'ni' or 'sn' or \
                                'ss' or 'au' or 'ag' or 'rb' or 'hc' or 'fu' or 'bu' or \
                                'ru' or 'br' or 'sp' or 'a2' or 'b2' or 'y2' or \
                                'm2' or 'p2' or 'c2' or 'cs' or 'rr' or 'jm' or \
                                'j2' or 'i2' or 'pg' or 'l2' or 'v2' or 'eg' or 'pp' or \
                                'eb' or 'lh' or 'FG' or 'TA' or 'PR' or \
                                'PX' or 'MA' or 'SA' or 'SH' or \
                                'SR' or 'CF' or 'CY' or 'OL' or 'RM' or \
                                'lc' or 'nr' or 'lu' :
                        user_buy_list               =  user_buy_list.append(code)
                if daytrade_time:
                    user_buy_list               =  user_buy_list.append(code)
        #------------------------------------------------------------------------------
    return user_buy_list
###################################start###########################################################################
#多头开仓
###################################start###########################################################################
def open_long_position(model_df_level2,ContextInfo):
    #------------------------------------------------------------------------------------------------
    #print(f'sell_list:\n{Sell_list}')
    if not model_df_level2.empty :
        #model_df_level2 的index
        #根据列'ATR_BuyK'的值进行升序排序
        #print(f'model_df_level2.index\n,{model_df_level2.index}')
        #model_df_level2 = model_df_level2.sort_values(by='ATR_BuyK',ascending=False)
        m_df_l2_list                 = model_df_level2.index.tolist()
        Buy_df                       = position_opening_calculat(ContextInfo,m_df_l2_list)
        if  not Buy_df.empty:
            buy_list                 = Buy_df.index.tolist()
            td                       = classlocal.Kindex_time
            #获取数据
            length                   = 8
            h_data                   = ContextInfo.get_market_data_ex(['close'],\
                buy_list,period = classlocal.Period_Type,end_time = td,count = (length),\
                dividend_type = 'front', fill_data = True, subscribe = True)
            #------------------------------------------------------------------------------------------
            #以下是买入操作code行所引 code_se,行索引对应的数据
            #hold_count                = 0
            classlocal.buy_code_count = 0
            #print(f'model_df_level2:\n{model_df_level2}')
            print(f'Buy_df:\n{Buy_df}')
            print('多头进入下单')
            for code in Buy_df.index:
                #print('code:',code)
                # 买入条件: 防止重复买入股票  and 防止下单金额过多  and 没有持仓 小于单只最大金额 and 现价大于1
                # 查询持仓
                totalStock              = 0
                #查询是否本地持仓
                totalStock              =  g_query.get_total_holding(code)
                #print('totalStock:',totalStock)
                #已经持仓的数量
                holded_num              = len(local_hold.index)
                #print('holded_num:',holded_num)
                #持仓和买入计数
                holding_num             = classlocal.buy_code_count + holded_num
                #print('holding_num:',holding_num)

                closes                  = h_data[code]['close']
                close                   = np.array(closes)
                buy_pricet              = close[-1]
                buy_price               = buy_pricet
                availableStock          = Buy_df.loc[code,'SingleNum']
                availableStock          = int(availableStock)
                #availableStock          = 1
                signal_stock_money      = availableStock * buy_price
                remark          = '【{}】买入{}共{}股{}元'.format(classlocal.Kindex_time,code,availableStock,signal_stock_money)
                opType          = 0                      # 0：开多
                orderType       = 1101                   #单股、单账号、普通、股/手方式下单
                accountid       = ContextInfo.accID      #账号
                orderCode       = code                   #代码
                prType          = 5                      #对手价（对方盘口一档价）
                price           = buy_price              #开仓价格#实际无效
                volume          = availableStock         #availableStock         #买入1手数
                strategyName    = remark                 #"七星开多"#remark                 #策略名称
                quickTrade      = 1                      #立即触发下单,1：历史触发在实盘不会执行，2：历史触发在实盘会执行
                userOrderId     = "888888"
                order_now       = 2                      # 0 等K线走完再下单 1或者2 立即下单 
                                                         # 因为条件筛选中往前退了一根线，所以要立即下单
                #signal_stock_money     = decimal_places_are_rounded(signal_stock_moneyt,2)
                print(f'local_hold.index:{local_hold.index}')
                print(f'code:{code},signal_stock_money:{signal_stock_money},availableStock:{availableStock},holded_num:{holded_num},totalStock:{totalStock},holding_num:{holding_num}')
                if  (totalStock == 0)\
                    and (code not in local_hold.index) \
                    and(code not in classlocal.trade_buy_record_dict.keys())\
                    and (classlocal.buy_code_count < (classlocal.max_buy_nums)) \
                    and (buy_price > 1) and (holding_num < classlocal.max_buy_nums):

                    if signal_stock_money>=500:

                        print(f'买入：{orderCode,volume}')
                        # 用对手价 1 手买入开仓
                        #buy_open(orderCode, volume, 'COMPETE', ContextInfo, accountID)
                        #passorder(opType, orderType, accountid, orderCode, prType, price, volume,strategyName,quickTrade, userOrderId, ContextInfo)
                        #passorder(0,     1101,     'test',     target,      5,     -1,  10, ContextInfo)
                        #passorder(opType, orderType, accountid, orderCode, prType,  -1,volume, ContextInfo)
                        # 开多
                        passorder(opType, orderType, accountid, orderCode,prType,0.0,volume,order_now,ContextInfo)
                        #对手价、金额下单
                        classlocal.buy_code_count             += 1
                        #print(remark)
                        print('下单成功')
                        #主图标记买点
                        ContextInfo.draw_text(1>0,classlocal.p+0.1*classlocal.p,"B")                       #绘图买入信号
                        #删除买入列表
                        Buy_df.drop(code,inplace=True)
                        #classlocal.trade_buy_record_dict[code] = [classlocal.Kindex_time,availableStock]
                    else:
                        print('下单失败，单笔金额小于400元')
                        model_df_level2.drop(code,inplace=True)
                        Buy_df.drop(code,inplace=True)
                else:
                    print('下单失败')
                    model_df_level2.drop(code,inplace=True)
                    Buy_df.drop(code,inplace=True)
                    if(totalStock != 0):
                        print('证券账户上有持仓')
                    if(code  in local_hold.index):
                        print('本地记录着持仓')
                    #if(code  in classlocal.trade_buy_record_dict.keys()):
                        #print('当日买过一次')
                    if(classlocal.buy_code_count >= (10*classlocal.max_buy_nums)):
                        print('超过买入次数100次')
                    if(buy_price < 1) :
                        print('价格无效')
                    if(holding_num >= classlocal.max_buy_nums):
                        print(f'超过持仓规定{classlocal.max_buy_nums}支')
                print(f'code:{code},signal_stock_money:{signal_stock_money},availableStock:{availableStock},holded_num:{holded_num},totalStock:{totalStock},holding_num:{holding_num}')
            print('结束下单')

###################################start###########################################################################
#
#平多头
###################################start###########################################################################
def close_long_position(ContextInfo,Sell_list_t,local_hold):
    if(Sell_list_t):
        td                  = classlocal.Kindex_time
        #获取数据
        length              = 3
        h_data              = ContextInfo.get_market_data_ex(['close'],\
            Sell_list_t,period = classlocal.Period_Type,end_time = td,count=(length),\
            dividend_type='front', fill_data=True, subscribe = True)
        #print('h_data',h_data)
        print('Sell_list_t:\n',Sell_list_t)
        print('进入卖出')
        for code in Sell_list_t:
            # 可用股数
            availableStock  = g_query.get_available_holding(code)
            availableStock  = int(availableStock)

            opType          = 7                      # 1：平左多 7：平多,优先平昨
            orderType       = 1101                   #单股、单账号、普通、股/手方式下单
            accountid       = ContextInfo.accID      #账号
            orderCode       = code                   #代码
            prType          = 5                      #对手价（对方盘口一档价）
            volume          = availableStock         #买入手数
            strategyName    = "七星平仓"              #策略名称
            quickTrade      = 1                      #立即触发下单,1：历史触发在实盘不会执行，2：历史触发在实盘会执行
            userOrderId     = "666666"

            closes          = h_data[code]['close']
            close           = np.array(closes)
            sell_pricet     = close[-1]
            #取小数点后两位
            sell_price      = decimal_places_are_rounded(sell_pricet,2)
            price           = sell_price
            sell_style      = 'BUY1'

            order_now       = 1                      # 0 等K线走完再下单 1或者2 立即下单 
                                                     # 止损碰到就要走，所以立即下单
           # availableStock  = g_query.get_available_holding(code)
            position_info = get_trade_detail_data(accountid, 'FUTURE', 'position')
            for obj in position_info:
                availableStock = obj.m_nVolume
                print('code',code)
                print('availableStock',availableStock)
            availableStock  = int(availableStock)
            volume          = availableStock         #平仓手数

            #print(f'\nopType:{opType},orderType:{orderType},account:{account},prType:{prType},sell_price:{sell_price},volume:{volume}')
            if availableStock == 0 :
                availableStock = 0
                #print('【{}】{}卖出手数为0，不发生卖出行为'.format(classlocal.Kindex_time,stk_code))
                print('code',code)
                print('卖出失败，可用为0手')
                print('卖出类型:',classlocal.sp_type)
            else:
                print('code',code)
                print('正在卖出')
                remark = '【{}】 期货账户：{}-卖出{}共{}股{}元'.format(classlocal.Kindex_time,classlocal.sp_type,code,availableStock,decimal_places_are_rounded(sell_price*availableStock,2))
                #msg    = f"投资备注_{stk_code}_资金账号:{ContextInfo.accID}_卖出金额:{sell_price*availableStock}_{classlocal.Kindex_time}"
                #          卖出   按手数买入  账号   代码  卖5价  价格     可用手数
                #passorder(opType, orderType, accountid, orderCode, prType, price, volume,strategyName,quickTrade, userOrderId, ContextInfo)
                
                # 平空，优先平昨
                #passorder(9,       1101,      C.accID, 'a2501.DF',     5,  0.0,    1,      2,          C)
                # 平空，优先平昨
                passorder(opType,  orderType, accountid, orderCode, prType,  0.0,  volume, order_now,   ContextInfo)
                print('PositionProfit:\n',local_hold.loc[code,'PositionProfit'])
                if local_hold.loc[code,'PositionProfit']>0:
                    ContextInfo.draw_text(1>0,classlocal.p-0.1*classlocal.p,"zy")
                else:
                    ContextInfo.draw_text(1>0,classlocal.p+0.1*classlocal.p,"zs")


                classlocal.trade_direction  = 'duo' 
                classlocal.code             = code
                classlocal.kindextime       = td
                classlocal.timetype         = '15m'
                classlocal.tradetype        = 'close'  #open #close
                classlocal.tradedata        = ''
                classlocal.stop             = 0
                classlocal.takeprofit       = 0

                classlocal.last_price       = price
                classlocal.profit           = local_hold.loc[code,'PositionProfit']
                classlocal.mediumprice      = 0
                classlocal.tradestatus      = ''
                classlocal.modle            = 'RED_TPDYX'
                send_message_to_feishu(classlocal)
                local_hold.loc[code,'nCanUseVolume'] = 0
                local_hold.loc[code,'nVolume']       = 0
                local_hold.loc[code,'dMarketValue']  = 0
                local_hold.drop(code,inplace=True)
                Sell_list_t.remove(code)
                print('remark:\n',remark)
        print('结束卖出')
        print('local_hold_sell_end:\n',local_hold)
###################################start###########################################################################
# 获取资金账号信息#
# 从服务器获取持仓信息
###################################start###########################################################################
def account_info(ContextInfo):
    account_df                                = pd.DataFrame()
    account_list                              = get_trade_detail_data(ContextInfo.accID, 'FUTURE', 'account')
    #列出数据和数据下标，一般用在 for 循环当中
    for index, obj in enumerate(account_list):
        account_df.loc[index, '总资产']        = obj.m_dBalance
        account_df.loc[index, '总市值']        = obj.m_dStockValue
        account_df.loc[index, '可用余额']      = obj.m_dAvailable
        account_df.loc[index, '当前交易日']    = obj.m_strTradingDate
        account_df.loc[index, '持仓盈亏']      = obj.m_dPositionProfit
    if classlocal.printmoney_en :
        print(f'资金账号信息:\n{account_df}')
    #syl = (obj.m_dBalance - 200000000)/200000000
    #print('收益率:',syl)
    return account_df

###################################start###########################################################################
#将上次的买入信息同步到本地，因为买入不一定持仓，所以在账户上查询到有持仓才进行更新
###################################start###########################################################################
def uptate_local_hold_prama(code):
    #for code in Buy_df.index:
    #code 传进来就是
    #一有持仓就将止损止盈给local_hold 传进去
    clum = 0
    #print('uptate_local_hold_prama:\n')
    #print('local_hold-start_update\n',local_hold)
    if code in model_df_level2.index:
        if code in local_hold.index:
            list_clolums2 = ['Kindex','Tradingday','Price_SellS','Price_SellY','ATR_BuyK','tradedirection']
            for clum in list_clolums2 :
                #print('clum:\n',clum)
                local_hold.loc[code,'BarSinceEntry']    = 0
                local_hold.loc[code,'mBuy_KIndex']      = classlocal.Kindex
                local_hold.loc[code,'mLast_KIndex']     = classlocal.Kindex
                local_hold.loc[code,'Buy_time']         = int(classlocal.Kindex_time)
                local_hold.loc[code,'Tradingday']       = classlocal.Kindex_time
                local_hold.loc[code,clum]               = model_df_level2.loc[code,clum]
                #print('local_hold-updating\n',local_hold)
            #无需重新策略选股 无需重新写初始交易计划
            #classlocal.Reflash_buy_list = 0
            #更新完删除掉
            model_df_level2.drop(code,inplace=True)
            Buy_df.drop(code,inplace=True)
    #买完删除
    #print('local_hold-stop_update\n',local_hold)
 ###################################start###########################################################################
#获取合约的保证金以便计算手数，get_instrumentdetail 返回的是一个字典
#保证金=报价*交易单位*保证金比例=2000*10*10%=2000元
###################################start###########################################################################   
def get_signal_margin(optioncode,ContextInfo):
    instrumentdetail_dict = ContextInfo.get_instrumentdetail(optioncode)
    LongMarginRatio       = instrumentdetail_dict['LongMarginRatio']    #多头保证金
    PreClose              = instrumentdetail_dict['PreClose']
    #PriceTick:最小变价单位
    PriceTick             = instrumentdetail_dict['PriceTick']
    ShortMarginRatio      = instrumentdetail_dict['ShortMarginRatio']   #空头保证金比例
    #VolumeMultiple:合约乘数
    VolumeMultiple        = instrumentdetail_dict['VolumeMultiple']
    #VolumeMultiple        = 0.20
    #保证金
    LongMargin            = (PreClose * PriceTick * VolumeMultiple * LongMarginRatio)/100
    LongMargin            = LongMargin * (1+ classlocal.LongMarginRatio_add)
    LongMargin            = decimal_places_are_rounded(LongMargin,4)

    if classlocal.contract_debug_en:
        print('instrumentdetail_dict:\n',instrumentdetail_dict)
        print('LongMargin:\n',LongMargin)
    return LongMargin
###################################start###########################################################################
#非常重要:仓位管理函数 默认单只股票占仓位的1/10
###################################start###########################################################################
def position_opening_calculat(ContextInfo,buy_list):

    list_data_values    = [0,0,0,0]
    list_clolumsp       = ['Kindex','Kindex_time','SingleNum']
    dit1 = dict(zip(range(0,0), list_data_values))
    #转置矩阵
    M_df = pd.DataFrame(dit1,list_clolumsp).T

    LeftMoey            = classlocal.LeftMoey
    Totalmoney          = classlocal.Total_market_cap
    signal_stock_money_maxt = Totalmoney /classlocal.max_buy_nums
    #单只最高可分配金额,
    signal_stock_money_max  = decimal_places_are_rounded(signal_stock_money_maxt,2)

    if signal_stock_money_max > 0:
        for code in buy_list :
            margin_t    = get_signal_margin(code,ContextInfo)
            margin      = decimal_places_are_rounded(margin_t,3)

            #最大可买金额/当前金额
            single_buy_max                   = int(signal_stock_money_max/margin) 
            LeftMoey                         = LeftMoey - signal_stock_money_max

            if LeftMoey <= 0:
                LeftMoey = 0
            classlocal.LeftMoey             = LeftMoey
            #剩余金额够买剩下的,就分配手数
            M_df.loc[code,'Kindex']         = classlocal.Kindex
            M_df.loc[code,'Kindex_time']    = classlocal.Kindex_time
            M_df.loc[code,'SingleNum']      = single_buy_max
            if single_buy_max >= 1 :
                M_df.loc[code,'SingleNum']  = single_buy_max
            else :
                M_df.loc[code,'SingleNum']  = 0
    return M_df
#查询股份/可用资金等

#get_trade_detail_data:取交易明细数据函数
#get_assure_contract:取标的担保明细
#get_enable_short_contract:取可融券明细
###################################start###########################################################################
#
###################################start###########################################################################
def GlobalVariiable(ContextInfo):
    #global关键字的作用是可以使得一个局部变量为全局变量。
    global g_query
    accountKey  = Account(ContextInfo.accID, ContextInfo.accountType)
    func        = [get_trade_detail_data, get_assure_contract, get_enable_short_contract]
    g_query     = Query_Details(accountKey, func, ContextInfo)

###################################start###########################################################################
#加载待卖出股票
###################################start###########################################################################
def load_sell_stock(stockPath_sell):
    path        = r""+stockPath_sell+""
    code_list   = getblkfile(path)
    return code_list
###################################start###########################################################################
#
###################################start###########################################################################
def sell_all_holding_Stock(ContextInfo) :
    # 卖出条件: 卖出表
    if (code in ContextInfo.code_list_sell):
        # 可用股数
        availableStock = g_query.get_available_holding(code)
        if availableStock>0:
            msg = f"投资备注_{code}_资金账号:{ContextInfo.accID}_卖出数量:{availableStock}_{now_time}"
            #print(msg)
            #对手价、数量下单
            passorder(24, 1101, ContextInfo.accID, code, 14, 0, availableStock, msg, 2, '读取通达信自选股下单示例', ContextInfo)
            #移除卖出列表
            ContextInfo.code_list_sell.remove(code)
            #print(ContextInfo.code_list_sell)
        else :
            print('nosell_stock')
    else :
        print('nosell_stock')
###################################start###########################################################################
#
###################################start###########################################################################
###################################start###########################################################################
#回调低突破大阳线
###################################start###########################################################################
def TPDYX_checkout(MA1_short,MA1_short7,MA2_long,MA2_long7):
    close           = classlocal.close
    open            = classlocal.open
    low             = classlocal.low[-10:]
    high            = classlocal.high[-10:]

    highmax         = max(high)    #classlocal.highmax                                           #6日最高点
    lowmin          = classlocal.lowmin                                                          #20日最低点

    DTCS            = (MA1_short > MA2_long) and (MA2_long > MA2_long7)                          #均线多头朝上
    YXSC            = (close[-2] > MA2_long) and (open[-2] < MA2_long) and\
                      (close[-2]>open[-2])  #阳线上穿
    JRZGD           = high[-2] >= highmax   #突破这天就是近日最高点
    low_12          = min(low[-2],low[-3],low[-4],low[-5])

    righthand       = DTCS and YXSC and JRZGD
    if classlocal.TPDYX_debug_en:
        if righthand:
            print("\nDTCS:",DTCS)
            print("\nYXSC:",YXSC)
            print("\nRZGD:",JRZGD)
            print("\nhigh[-2]:",high[-2])
            print("\nhigh:",high)
            print("\nhighmax:",highmax)

            print("\nlow_12:",low_12)
            print("\low:",low)
        #print("\nselTPDYX_stopcheck:",classlocal.selTPDYX_stopcheck)

    classlocal.TPDYX    =  0
    if (righthand):
        classlocal.TPDYX    = 1
        classlocal.TPDYXsp  = low_12
    else:
        classlocal.TPDYX    = 0
        classlocal.TPDYXsp  = 8888
###################################start###########################################################################

###################################start###########################################################################
def compare_values_min(value1, value2):
    if value1 < value2:
        return value1
    else:
        return value2
###################################start###########################################################################
#
###################################start###########################################################################
def compare_values_max(value1, value2):
    if value1 > value2:
        return value1
    else:
        return value2
###################################start###########################################################################
#
###################################start###########################################################################
def Calculate_SellY_According_to_SP(last_price,sp_price,Profit_loss_ratio):
    Price_SellY     = 0
    Price_SellY_t   = last_price + (last_price - sp_price)*Profit_loss_ratio
    Price_SellY     = decimal_places_are_rounded(Price_SellY_t,4)
    if (classlocal.Trade_init_debug_en):
        print(f'last_price\n,{last_price}')
        print(f'sp_price\n,{sp_price}')
        print(f'Price_SellY\n,{Price_SellY}')

    return Price_SellY
###################################start###########################################################################
#执行选股
###################################start###########################################################################
def Perform_stock_picks(ContextInfo,stockpath,eastmoney_zx_name,compare_df):
    m_df_lv2 = pd.DataFrame()
    #index_time = classlocal.Kindex_time
    # 01_读取待买入股票数据
    check_list= parse_ini_file(stockpath,eastmoney_zx_name)
    if classlocal.check_list_debug_en:
        check_list = classlocal.check_list
    model_record_df     = pd.DataFrame()
    # ============ 执行时间 ======================
    if check_list:
        if check_list:
            model_record_dftt = model_process(ContextInfo,check_list)
            if classlocal.mp_debug_origin_en and not model_record_dftt.empty:
                print('\本地列表\n:',check_list)
                print('\n模型选出进入\n:',model_record_dftt)
                print('compare_df\n:',compare_df)
            if not model_record_dftt.empty:
                try:
                    if classlocal.Reflash_buy_list :
                        for code in model_record_dftt.index:
                            if code not in compare_df.index:
                                if m_df_lv2.empty:
                                   m_df_lv2 = model_record_dftt
                            else :
                                if code not in compare_df.index:
                                    if code not in m_df_lv2.index:
                                        m_df_lv2 = m_df_lv2+model_record_dftt
                except AttributeError:
                    print("索引不能转换为列表")
        else :
            m_df_lv2    = model_record_df
    if classlocal.mp_debug_origin_en and not model_record_dftt.empty:
        print('模型选出退出\n:',m_df_lv2)
    return m_df_lv2

###################################start###########################################################################
#Convert_the_market_data_type
#输入tradedatas得到一个arry,可以用来计算ATR和均线,当最小最有效时才计算
###################################start###########################################################################
def Convert_the_market_data_type(tradedatas,tradedata_lows,length):
    tradedata_nparry                = []
    tradedatas                      = tradedatas[-length:]
    lows                            = tradedata_lows[-length:]
    lowmin                          = lows.min()
    if lowmin > 0 :
        tradedata_nparry            = np.array(tradedatas)

    return tradedata_nparry
###################################start###########################################################################
#calculate_ATR:计算length 周期内的平均波幅
#输入:high 是一定周期内的最高值是一个pd.serious 不单单是一个值
#输出:ATR 平均真实波幅
###################################start###########################################################################
def calculate_ATR(high,low,close,length):
    #print('\nstart')
    if length == 0:
        return 0
    #print('\n length',length)
    #print('\n high',high)
    list_TR = []
    for j in range(-(length-1),0) :
        HL = abs(high[-j]   -  low[-j])
        HC = abs(high[-j]   -  close[-(j+1)])
        CL = abs(low[-j]    -  close[-(j+1)])
        list_TR.append(max(HL,HC,CL))
        j += 1
    #print(list_TR)
    ATR     = (pd.Series(list_TR)).mean()
    #print(f'ATR:{ATR}')
    ATR     = decimal_places_are_rounded(ATR,2)
    return ATR

###################################start###########################################################################
#get_market_data_ex_modify
#去掉源数据里面成交量为0的行，因为“ContextInfo.get_market_data_ex”中把非交易时间的数据
#都写成最后一次的数据，但是成交量为0，所以删掉成交量为0的也就是休市的时间
#所以实际的采样周期会低设置的采样周期
###################################start###########################################################################
def get_market_data_ex_modify(ContextInfo,check_list,period_t,endtime,length):
    #当获取交易数据为5m或者15m是需要向前获取数据
    if(len(endtime)>=16) and (period_t[-1] == 'm'):
        endtime_t = endtime[-6:-2]
        if( "1015" < endtime_t < "1030") and period_t == '5m':
            length = length+3
        elif( "1015" < endtime_t < "1030") and period_t == '15m':
            length = length+1
    h_data              = ContextInfo.get_market_data_ex(['close','high','open','low','volume'],\
                          check_list,period = period_t,end_time=endtime,count=length,\
                          dividend_type='front', fill_data=True, subscribe = True)
    if classlocal.h_data_debug_en:
        print('h_data:\n',h_data)
    return h_data
###################################start###########################################################################

###################################start###########################################################################
def model_process(ContextInfo,check_list):
    endtime_t = '000000'
    list_data_values    = [0,0,0,0]

    list_clolums        = ['Kindex','Tradingday','Price_SellS','Price_SellY','ATR_BuyK','tradedirection']
    dit1                = dict(zip(range(0,0), list_data_values))
    #转置矩阵
    G_df                = pd.DataFrame(dit1,list_clolums).T
    index               = classlocal.Kindex
    endtime             = classlocal.Kindex_time
    td                  = classlocal.Kindex_time
    #获取数据           #
    length1             = classlocal.modul_length+5
    period_t            = classlocal.Period_Type
    h_data_init         = ContextInfo.get_market_data_ex(['close','high','open','low','volume'],\
                        check_list,period = period_t,end_time=endtime,count=length1,\
                        dividend_type='front', fill_data=True, subscribe = True)
    #h_data_t              = get_market_data_ex_modify(ContextInfo,code,period_t,endtime,length1)

    if classlocal.h_data_debug_en:
        print('check_list:\n',check_list)
        print('period_t:\n',period_t)
        print('endtime:\n',endtime)
        print('length1:\n',length1)
        print('h_data:\n',h_data_init)
    h_data = h_data_init
    #处理数据
    #输出列表:买入列别:止损:七根线最低值
    lowmin              = 0

    for code in check_list:
        if (period_t[-1] == 'm'):
            #endtime_t = endtime[-6:-2]
            #print('endtime_t:\n',endtime_t)
            if 1:#( "0900" < endtime_t < "1500"):
                h_data_code         = h_data_init[code]
                h_data              = h_data_code.loc[h_data_code['volume'] != 0]
                if classlocal.h_data_debug_en:
                    print('h_data_t:\n',h_data)
                closes              = h_data['close']
                lows                = h_data['low']
                highs               = h_data['high']
                opens               = h_data['open']
                volumes             = h_data['volume']
            else:
                closes              = h_data[code]['close']
                lows                = h_data[code]['low']
                highs               = h_data[code]['high']
                opens               = h_data[code]['open']
                volumes             = h_data[code]['volume']
        elif period_t[-1] =="d":
            closes              = h_data[code]['close']
            lows                = h_data[code]['low']
            highs               = h_data[code]['high']
            opens               = h_data[code]['open']
            volumes             = h_data[code]['volume']
        else :
            closes              = h_data[code]['close']
            lows                = h_data[code]['low']
            highs               = h_data[code]['high']
            opens               = h_data[code]['open']
            volumes             = h_data[code]['volume']

        #closes_opens_dict   = closes - opens
        closemin            = closes.min()
        openmin             = opens.min()
        #34日
        len                 = 20                    #classlocal.modul_length
        lowmin              = lows[-len:].min()
        #暂时改为6日的最高点
        highmax             = highs[-8:].max()

        highmax             = decimal_places_are_rounded(highmax,3)
        lowmin              = decimal_places_are_rounded(lowmin,3)
        #print(code,closes)
        if(classlocal.checklist_debug_en):
            print(f'period_t[-1]\n{period_t[-1]}')
            #print(f'endtime_t\n{endtime_t}')
            print(f'h_data\n{h_data}')
            print(f'h_data\n{type(h_data)}')
            print(f'closemin\n{closemin}')
            print(f'openmin\n{openmin}')
            print(f'lowmin\n{lowmin}')
            print(f'highmax\n{highmax}')

        rows        = h_data.shape[0] 
        if  rows< classlocal.MA_long_length + 9:
            if classlocal.TPDYX_debug_en:
                print(f'code:{code},行数:{rows}')
                print(f'计算均线数据长度不够结束本次筛选\n')

            continue

        if((closemin > 0) and (openmin > 0) and (lowmin > 0) and highmax):
            #print('G_df.loc[code,'Price_SellS']:',G_df.loc[code,'Price_SellS'])
            #转成数组可以按照index取值
            close   = np.array(closes)
            low     = np.array(lows)
            high    = np.array(highs)
            open    = np.array(opens)
            volume  = np.array(volumes)
            #print(code,close)
            #opens_serious        = np.array(opens)
            #closes_opens_serious = np.array(closes_opens_dict)
            #closes_opens         = closes_opens_serious
            classlocal.close     = close
            classlocal.open      = open
            classlocal.low       = low
            classlocal.high      = high
            classlocal.highmax   = highmax
            classlocal.lowmin    = lowmin
            classlocal.volume    = volume

            #昨日13日收盘价均值
            MA_middle                = np.mean(close[-classlocal.MA_middle_length-1:-1])
            MA_middle_7              = np.mean(close[-(classlocal.MA_middle_length+7):-7])
            #昨日34日收盘价均值
            MA_long                 = np.mean(close[-classlocal.MA_long_length-1:-1])
            MA_long_7               = np.mean(close[-(classlocal.MA_long_length+7):-7])
            TPDYX                   = 0
            if classlocal.TPDYX_en:
                MA1_short                    = MA_middle
                MA1_short7                   = MA_middle_7
                MA2_long                     = MA_long
                MA2_long7                    = MA_long_7
                TPDYX_checkout(MA1_short,MA1_short7,MA2_long,MA2_long7)
                TPDYX                        = classlocal.TPDYX
                TPDYXsp                      = classlocal.TPDYXsp
            last_price                       = close[-1]
            #---------------------------------------------------------------------------------------
            ART_length                       = classlocal.ATR_open_Length
            if TPDYX:
                G_df.loc[code,'Price_SellS'] = decimal_places_are_rounded(TPDYXsp,2)
                buy_atr                      = calculate_ATR(high,low,close,ART_length)
                G_df.loc[code,'ATR_BuyK']    = buy_atr
                G_df.loc[code,'Tradingday']  = td
                sp_price                     = G_df.loc[code,'Price_SellS']
                Profit_loss_ratio            =  classlocal.Price_SetSellY_YKB
                zf_zy                        = Calculate_SellY_According_to_SP(last_price,sp_price,Profit_loss_ratio)
                takeprofit                    = decimal_places_are_rounded(zf_zy,2)
                G_df.loc[code,'Price_SellY'] = takeprofit
                G_df.loc[code,'Kindex']      = int(index)
                G_df.loc[code,'tradedirection']        = TRADE_DIRECT  # 48 多 49 ：空

                classlocal.trade_direction  = 'duo' #duo #kong
                classlocal.code             = code
                classlocal.kindextime       = endtime
                classlocal.timetype         = '15m'
                classlocal.tradetype        = 'open'  #open #close
                classlocal.tradedata        = ''
                classlocal.stop             = sp_price
                classlocal.takeprofit        = takeprofit

                classlocal.last_price       = last_price
                classlocal.profit           = 0
                mediumpricet                = (high[-1] - low[-1])/2 + last_price
                mediumprice                 = decimal_places_are_rounded(mediumpricet,3)
                classlocal.mediumprice      = mediumprice
                classlocal.tradestatus      = ''
                classlocal.modle            = 'RED_TPDYX'
                #防止多次发送，只发送一次
                if (classlocal.Lastkindextime != classlocal.kindextime[:-2]):
                    send_message_to_feishu(classlocal)
                    classlocal.Lastkindextime    == classlocal.kindextime[:-2]
    return G_df
###################################start###########################################################################
#calculate_ATR_from_buy_time:计算length 周期内的平均波幅
#输入:ContextInfo
#buytime:开仓时间
#输出:
###################################start###########################################################################
def calculate_ATR_from_buy_time(ContextInfo,buytime,code) :
    td          = buytime
    check_list  = code
    buy_atr     = 0
    length      = classlocal.ATR_open_Length
    h_data      = ContextInfo.get_market_data_ex(['close','high','open','low'],\
        check_list,period = classlocal.Period_Type,end_time = td,count = (8+length),\
        dividend_type='front', fill_data=True, subscribe = True)
    closes      = h_data[code]['close']
    lows        = h_data[code]['low']
    highs       = h_data[code]['high']
    opens       = h_data[code]['open']
    lowmin      = lows.min()
    if lowmin > 0 :
        close   = np.array(closes)
        low     = np.array(lows)
        high    = np.array(highs)
        buy_atr = calculate_ATR(high,low,close,length)
    #print(f'ATR_dict\n,{ATR_dict}')
    buy_atr     = decimal_places_are_rounded(buy_atr,2)
    return buy_atr
###################################start###########################################################################
#上证所 SH
#深交所 SZ
#大商所 DF 114.
#郑商所 ZF 115.
#上期所 SF 113.
#中金所 IF 220.
#广期所 GF 225
#外部自定义市场 ED
###################################start###########################################################################
def modify_elements(elements):
    modified_elements = []
    for elem in elements:
        if elem.startswith('1.'):
            modified_elements.append(elem[2:] + '.SH')
        elif elem.startswith('0.'):
            modified_elements.append(elem[2:] + '.SZ')
        elif elem.startswith('114.'):
            modified_elements.append(elem[2:] + '.DF')
        elif elem.startswith('115.'):
            modified_elements.append(elem[2:] + '.ZF')
        elif elem.startswith('113.'):
            modified_elements.append(elem[2:] + '.SF')
        elif elem.startswith('220.'):
            modified_elements.append(elem[2:] + '.IF')
        elif elem.startswith('225.'):
            modified_elements.append(elem[2:] + '.GF')
        else:
            modified_elements.append(elem[2:] + '.ED')
    return modified_elements

def parse_ini_file(file_path,ZX):
    config      = configparser.ConfigParser()
    v           = config.read(file_path,encoding='utf-16')
    v           = config.sections()
    # 读取INI文件中的值
    #print('v',v)

    value       = config.get('\\SelfSelect', ZX)
    output_list = value.split(',')
    #print(output_list)
    modified_elements = modify_elements(output_list)
    #print(modified_elements)
    stockcode   = list(filter(None, modified_elements))
    lst         = stockcode
    stockcode   = list(map(lambda s: s[2:], lst))
    lst         = stockcode.pop()
    #print(stockcode)
    return stockcode

###################################start###########################################################################
#
###################################start###########################################################################
# 写入CSV文件
def write_to_csv(data,file_path,index1):
    data.to_csv(file_path, index = index1)

# 读取CSV文件
def read_from_csv(file_path,index1):
    df = pd.read_csv(file_path)
    #将Code列设置为索引,前提是本地列一定要有"Code"
    local_hold = df.set_index(keys='Code', drop=True)
    return local_hold

def local_hold_data_frame_init():
    global locallist_clolums
    list_data_values  = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,]
    locallist_clolums = ['Code','Price_SellY_Flag','BarSinceEntry','Price_SellY','Price_SellY1','Price_SellS',\
                        'Price_SellS1','dLastPrice','dProfitRate','Buy_time','nVolume','nCanUseVolume',\
                        'PositionProfit','ATR_Start_time','dMarketValue','Tradingday','Price_BuyK','mBuy_KIndex','mLast_KIndex','strInstrumentID','ATR_BuyK','tradedirection']
    dit1 = dict(zip(range(0,0), list_data_values))
    #转置矩阵
    G_df = pd.DataFrame(dit1,locallist_clolums).T
    return G_df

###################################start###########################################################################
#
###################################start###########################################################################
def write_local_hold_data(data,file_path,index1):
    # 检查文件是否存在
    try:
        with open(file_path, 'r'):
            pass
    except FileNotFoundError:
        # 文件不存在，创建新文件,没有数据空文件
        df_empty = pd.DataFrame()
        df_empty.to_csv(file_path, index=index1)

    # 写入数据到CSV文件
    write_to_csv(data,file_path,index1)
    return data

###################################start###########################################################################
#
###################################start###########################################################################
def read_local_hold_data(file_path,index1):
    # 检查文件是否存在
    try:
        with open(file_path, 'r'):
            pass
    except FileNotFoundError:
        # 文件不存在，创建新文件,没有数据空文件
        #df_empty = pd.DataFrame()
        df_empty = local_hold_data_frame_init()
        df_empty.to_csv(file_path, index=index1)

    data         = read_from_csv(file_path,index1)
    return data

###################################start###########################################################################
#
###################################start###########################################################################
def decimal_places_are_rounded(floatdata,div):
    floatdata   = round(floatdata, div)
    floatdata   = '{:.2f}'.format(floatdata)
    floatdata   = float(floatdata)
    return floatdata
###################################start###########################################################################
#
###################################start###########################################################################
def dict_into_dataframe(data_dict,cloums):
    """
        字典转换成Dataframe或Series
    """
    if len(data_dict) == 0:
        return {}
    if len(data_dict) >= 1:
        data_df = pd.DataFrame(data_dict)
        data_df = data_df.T[cloums]
        #data_df.rename(columns ={'lastPrice':'最新价', 'lastClose': '昨收价'}, inplace = True)
    return data_df
###################################start###########################################################################
#df1代表从云端读到的数据 df2为本地路径上的数据
#取云端的持仓列表,然后将本地的自定义数据更新到云端df1上(这个是一个暂存数据)
###################################start###########################################################################
def print_position_data(obj) :
    #最新价
    print('obj.m_dLastPrice',               obj.m_dLastPrice)
    #当前单只股票市值
    print('obj.m_dMarketValue',             obj.m_dMarketValue)
    #单只持仓总花费
    print('obj.m_dPositionCost',            obj.m_dPositionCost)
    #单只持仓利润
    print('obj.m_dPositionProfit',          obj.m_dPositionProfit)
    #单只持仓利润率
    print('obj.m_dProfitRate',              obj.m_dProfitRate)
    #可用手数
    print('obj.m_nCanUseVolume',            obj.m_nCanUseVolume)
    #总手数
    print('obj.m_nVolume',                  obj.m_nVolume)
    #交易所 例如SZ
    print('obj.m_strExchangeID',            obj.m_strExchangeID)
    #交易所 深交所
    print('obj.m_strExchangeName',          obj.m_strExchangeName)
    #持仓股票代码 002064
    print('obj.m_strInstrumentID',          obj.m_strInstrumentID)
    #持仓股票名 华峰化学
    print('obj.m_strInstrumentName',        obj.m_strInstrumentName)
    #交易日
    print('obj.m_strTradingDay',            obj.m_strTradingDay)
    # 查看有哪些属性字段
    print('obj.m_bIsToday',                obj.m_bIsToday)
    print('obj.m_dAvgOpenPrice',           obj.m_dAvgOpenPrice)
    print('obj.m_dCloseAmount',            obj.m_dCloseAmount)
    print('obj.m_dCloseProfit',            obj.m_dCloseProfit)
    print('obj.m_dFloatProfit',            obj.m_dFloatProfit)
    print('obj.m_dInstrumentValue',        obj.m_dInstrumentValue)
    print('obj.m_dLastSettlementPrice',    obj.m_dLastSettlementPrice)
    print('obj.m_dMargin',                 obj.m_dMargin)
    print('obj.m_dOpenPrice',obj.m_dOpenPrice)
    print('obj.m_dRealUsedMargin',obj.m_dRealUsedMargin)
    print('obj.m_dRedemptionVolume',obj.m_dRedemptionVolume)
    print('obj.m_dReferenceRate',obj.m_dReferenceRate)
    print('obj.m_dRoyalty',obj.m_dRoyalty)
    print('obj.m_dSettlementPrice',obj.m_dSettlementPrice)
    print('obj.m_dSingleCost',obj.m_dSingleCost)
    print('obj.m_dStaticHoldMargin',obj.m_dStaticHoldMargin)
    print('obj.m_dStockLastPrice',obj.m_dStockLastPrice)
    print('obj.m_dStructFundVol',obj.m_dStructFundVol)
    print('obj.m_dTotalCost',obj.m_dTotalCost)
    print('obj.m_eFutureTradeType',obj.m_eFutureTradeType)
    print('obj.m_eSideFlag',obj.m_eSideFlag)
    print('obj.m_nCidIncrease',obj.m_nCidIncrease)
    print('obj.m_nCidIsDelist',obj.m_nCidIsDelist)
    print('obj.m_nCidRateOfCurrentLine',obj.m_nCidRateOfCurrentLine)
    print('obj.m_nCidRateOfTotalValue',obj.m_nCidRateOfTotalValue)
    print('obj.m_nCloseVolume',obj.m_nCloseVolume)
    print('obj.m_nCoveredVolume',obj.m_nCoveredVolume)
    print('obj.m_nDirection',obj.m_nDirection)
    print('obj.m_nEnableExerciseVolume',obj.m_nEnableExerciseVolume)
    print('obj.m_nFrozenVolume',obj.m_nFrozenVolume)
    print('obj.m_nHedgeFlag',obj.m_nHedgeFlag)
    print('obj.m_nLegId',obj.m_nLegId)
    print('obj.m_nOnRoadVolume',obj.m_nOnRoadVolume)
    print('obj.m_nOptCombUsedVolume',obj.m_nOptCombUsedVolume)
    print('obj.m_nPREnableVolume',obj.m_nPREnableVolume)
    print('obj.m_nSettledAmt',obj.m_nSettledAmt)
    print('obj.m_nStrategyID',obj.m_nStrategyID)
    print('obj.m_nYesterdayVolume',obj.m_nYesterdayVolume)
    print('obj.m_strAccountID',obj.m_strAccountID)
    print('obj.m_strAccountKey',obj.m_strAccountKey)
    print('obj.m_strComTradeID',obj.m_strComTradeID)
    print('obj.m_strExpireDate',obj.m_strExpireDate)
    print('obj.m_strOpenDate',obj.m_strOpenDate)
    print('obj.m_strProductID',obj.m_strProductID)
    print('obj.m_strProductName',obj.m_strProductName)
    print('obj.m_strStockHolder',obj.m_strStockHolder)
    print('obj.m_strTradeID',obj.m_strTradeID)
    print('obj.m_xtTag',obj.m_xtTag)

###################################start###########################################################################
#飞书发送函数
#开仓和平仓输入参数不同
###################################start###########################################################################
from datetime import datetime

def open_payload_set(modle,trade_direction,tradedata,lastprice,stop,takeprofit,mediumprice):
    if trade_direction == 'duo':
        Head_color = 'Purple'
    else:
        Head_color = 'Orange'
    # 构建卡片消息
    card_message = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": False },
                "header": {"template":     "{}".format(Head_color), "title": {"tag": "plain_text", "content": "{}".format(tradedata),}},

            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content":"modle         :{}".format(modle),
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content":"lastprice      :{}".format(lastprice),
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content":"mediumprice :{}".format(mediumprice),
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content":"stop            :{}".format(stop),
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content":"takeprofit       :{}".format(takeprofit),
                    }
                }

            ]
        }
    }
    return card_message


def close_payload_set(modle,tradedata,lastprice,stop,takeprofit,profit):
    if profit >= 0 :
        Head_color = 'red'
    else :
        Head_color = 'green'
    # 构建卡片消息
    card_message = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": False },
                "header": {"template":     "{}".format(Head_color), "title": {"tag": "plain_text", "content": "{}".format(tradedata),}},
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content":"modle      :{}".format(modle),
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content":"lastprice   :{}".format(lastprice),
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content":"Stop        :{}".format(stop),
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content":"takeprofit   :{}".format(takeprofit),
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content":"profit       :{}".format(profit),
                    }
                }

            ]
        }
    }
    return card_message

# 向飞书机器人发送卡片消息和天气
def send_message_to_feishu(classlocal):
    # 设置请求头,指定消息格式为JSON
    # 飞书自定义机器人
    '''
    classlocal.trade_direction  = 'close' #duo #kong
    classlocal.code             = 'SA00.SF'
    classlocal.kindextime       = '20241014135000'
    classlocal.timetype         = '15m'
    classlocal.tradetype        = 'open'  #open #close
    '''
    tradestatus             = classlocal.tradestatus 
    code                    = classlocal.code 
    date_string             = classlocal.kindextime
    date_object             = datetime.strptime(date_string, "%Y%m%d%H%M%S")
    # 转换回字符串
    new_date_string         = date_object.strftime("%Y-%m-%d %H:%M")
    kindextime              = new_date_string
    timetype                = classlocal.timetype
    trade_direction         = classlocal.trade_direction # 
    tradetype               = classlocal.tradetype       # 

    stop                    = classlocal.stop
    takeprofit               = classlocal.takeprofit
    lastprice               = classlocal.last_price
    profit                  = classlocal.profit
    modle                   = classlocal.modle
    #duo
    if trade_direction == 'duo':
        #open
        if tradetype == 'open':
            mediumprice  = (lastprice - stop)/2 + stop
            opentype     = 'open'
            tradedata    = opentype +' '+ trade_direction +' '+ code + ' '+ timetype + ' ' + kindextime + ' ' + tradestatus
            payload      = open_payload_set(modle,trade_direction,tradedata,lastprice,stop,takeprofit,mediumprice)
            url1             = classlocal.URLopen
        #close
        else:
            opentype     = 'close'
            tradedata    = opentype +' '+ trade_direction +' '+ code + ' '+ timetype + ' ' + kindextime + ' ' + tradestatus
            payload      = close_payload_set(modle,tradedata,lastprice,stop,takeprofit,profit)
            url1             = classlocal.URLclose
    #kong
    else :
                #open
        if tradetype == 'open':
            mediumprice  = (stop - lastprice)/2 + lastprice
            opentype     = 'open'
            tradedata    = opentype +' '+ trade_direction +' '+ code + ' '+ timetype + ' ' + kindextime + ' ' + tradestatus
            payload      = open_payload_set(modle,trade_direction,tradedata,lastprice,stop,takeprofit,mediumprice)
            url1             = classlocal.URLopen
        #close
        else:
            opentype     = 'close'
            tradedata    = opentype +' '+ trade_direction +' '+ code + ' '+ timetype + ' ' + kindextime + ' ' + tradestatus
            payload      = close_payload_set(modle,tradedata,lastprice,stop,takeprofit,profit)
            url1             = classlocal.URLclose

    headers1                = {'Content-Type': 'application/json'}
    try:
        response                = requests.post( url = url1, json = payload, headers = headers1)  # 发送POST请求
    
        if response.status_code == 200:  # 判断返回状态码是否为200(请求成功)
            response.raise_for_status()  # 如果响应状态码不是200，主动抛出异常
            #print("消息发送成功：", response.text)
        else:
            print('发送失败')
    except requests.exceptions.RequestException as e:
        print("发送失败：", e)

import matplotlib.pyplot as plt
def tYield_tracking_calculations_and_presentations(classlocal):
    list_data_values        = [0,0,0,0]
    classlocal.Total_market_cap
    list_clolums            = ['Tradingday','Profit_loss_ratio','ATR_Take_Profit','Num',\
                           'Total_market_cap_base','Total_market_cap','Total_market_cap','profit','Yield']
    dit1                    = dict(zip(range(0,0), list_data_values))
    #转置矩阵
    G_df                    = pd.DataFrame(dit1,list_clolums).T

    Tradingday              = classlocal.Kindex_time
    Profit_loss_ratio       = YKB
    ATR_Take_Profit         = classlocal.close_atr_trade_en
    Num                     = Max_buynums
    Total_market_cap_base   = 50000
    Total_market_cap        = classlocal.Total_market_cap
    profit                  = classlocal.Total_market_cap - Total_market_cap_base
    Yield                   = profit/Total_market_cap_base

    G_df.loc[Tradingday,'Tradingday']               = int(Tradingday)

    G_df.loc[Tradingday,'Profit_loss_ratio']        = Profit_loss_ratio
    G_df.loc[Tradingday,'ATR_Take_Profit']          = Profit_loss_ratio
    G_df.loc[Tradingday,'Num']                      = ATR_Take_Profit
    G_df.loc[Tradingday,'Total_market_cap_base']    = Num
    G_df.loc[Tradingday,'Total_market_cap']         = Total_market_cap
    G_df.loc[Tradingday,'profit']                   = profit
    G_df.loc[Tradingday,'Yield']                    = Yield

    return G_df





