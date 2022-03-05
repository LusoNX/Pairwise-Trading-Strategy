import fxcmpy
import numpy as np
from stocktrends import Renko
import statsmodels.api as sm
import time
import copy
import math
import pandas as pd 


# Code only runs during open market hours
api_token = "YOUR API KEY from FXCM"


## THIS IS A PAIRWISE TRADING BOTH

# Make sure you have the following symbols in the tradables list in FXCM.
stocks = ["SPX500","AMD.us","AMZN.us","BITF.us","BTBT.us","COIN.us","NVDA.us","FB.us","TTE.fr","WPL.au","XOM.us","GOOG.us","USOil","NGAS"] ## BNB WONT WORK because of precision problems
con = fxcmpy.fxcmpy(access_token = api_token,log_level = "error",server = "demo")



df = pd.DataFrame()
ohlcv_data = {}
return_df = {}

ohlcv_data = {}
def get_candles(SYMBOL,_period):
	tickers = SYMBOL
	for i in tickers:
		data = con.get_candles(i, period = _period, number = 125) # half year of trading
		ohlc = data.iloc[:,[0,1,2,3,8]]
		ohlc.columns = ["Open","Close","High","Low","Volume"]
		ohlc["returns"] = ohlc["Close"].pct_change()
		ohlcv_data[i] = ohlc

	return ohlcv_data





def corr_matrix(DATA):
	returns_df = pd.DataFrame()
	ohlcv_data = DATA.copy()
	pair_1 =[]
	for i in ohlcv_data:
		returns_df[i] = ohlcv_data[i]["returns"]
		pair_1.append(i)


	returns_df = pd.DataFrame.from_dict(returns_df)
	returns_df.dropna(inplace = True)
	returns_df.to_csv("returns.csv")
	corr = returns_df.corr()
	corr_replaced = corr.replace(1,0)
	corr_replaced =corr_replaced[corr_replaced > 0.70] ## Keep only correlations above 70 %
	corr_replaced.to_csv("corr_matrix.csv")



	pair_2 = []
	for x in corr_replaced.idxmax():
		pair_2.append(x)

	pair_1_new = []
	for i in range(0,len(pair_1)):
		if str(pair_2[i]) != "nan":
			pair_1_new.append(pair_1[i])

	pair_1_new = [x for x in pair_1_new if str(x) != 'nan'] ## REmove Nan Values
	pair_2 = [x for x in pair_2 if str(x) != 'nan']
	#pair_1_new.iloc[0,len(pair_1_new)/2]
	#pair_2 = 

	return pair_1_new[0:1],pair_2[0:1]



def pair_strategy(DF,x,y,ma_period):
	df = DF.copy()
	df_x = ohlcv_data[x][["Close","returns"]]
	df_x = pd.DataFrame.from_dict(df_x)
	df_x=df_x.rename(columns ={"Close": "pair_1_price", "returns": "pair_1_returns"} )

	df_y = ohlcv_data[y][["Close","returns"]]
	df_y = pd.DataFrame.from_dict(df_y)
	df_y=df_y.rename(columns ={"Close": "pair_2_price", "returns": "pair_2_returns"} )

	df_x_close = ohlcv_data[x]["Close"]
	df_y_close = ohlcv_data[y]["Close"]
	df_final = df_x_close-df_y_close
	df_final = pd.DataFrame.from_dict(df_final)
	df_final = df_final.rename(columns = {"Close":"Difference"})


	mean_spread = df_final.mean()
	std_spread = df_final.std()
	df_final["pair_zscore"] = (df_final - mean_spread) /std_spread
	df_final["pair_zscore_ma"] = df_final.pair_zscore.rolling(ma_period, min_periods = ma_period).mean()
	df_final = df_final.merge(df_x,on = "date")
	df_final = df_final.merge(df_y,on = "date")

	return df_final
	

def trade_signal(DF,l_s,std):
	df = DF.copy()
	print(df["pair_zscore"].tolist()[-1])

	if l_s == "":
		if df["pair_zscore"].tolist()[-1] > std:
			signal_pair_1 = "Sell_pair_1"
			#signal_pair_2 = "Buy_pair_2"
		elif df["pair_zscore"].tolist()[-1] < -std:

			signal_pair_1 = "Buy_pair_1"
			#signal_pair_2 = "Sell_pair_2"

	elif l_s == "long_pair_1":
		if df["pair_zscore"].tolist()[-1] > -std:
			signal_pair_1 = "Close"

		else:
			pass


	elif l_s == "short_pair_1":
		if df["pair_zscore"].tolist()[-1] < std:
			signal_pair_1 = "Close"
		elif df["pair_zscore"].tolist()[-1] > std:
			signal_pair_1 = "Keep_trade"

	#print("THis is the signal",signal_pair_1)
	return signal_pair_1



## FOR THIS CODE TO WORK, BOTH TICKERS MUST BE ACTIVELY TRADING


def main(qt):

	try:
	
		df = get_candles(stocks,"D1")
		pair_1,pair_2 = corr_matrix(df)
		open_pos = con.get_open_positions()
		for i in range(0,len(pair_1)):
			long_short = ""
			if len(open_pos) >0:
				open_pos_cur_1 = open_pos[open_pos["currency"]== pair_1[i]]
				open_pos_cur_2 = open_pos[open_pos["currency"]== pair_2[i]]
				print(open_pos_cur_1["isBuy"].tolist()[0])
				#print(type(open_pos_cur_1["isBuy"].tolist()[0]))
				print(open_pos_cur_2["isBuy"].tolist()[0])
				#print(type(open_pos_cur_1["isBuy"].tolist()[0]))
				if len(open_pos_cur_1)>0 and len(open_pos_cur_2)>0:
					if open_pos_cur_1["isBuy"].tolist()[0] == True  and open_pos_cur_2["isBuy"].tolist()[0] == False :
						long_short = "long_pair_1"
					
					elif open_pos_cur_1["isBuy"].tolist()[0] == False and open_pos_cur_2["isBuy"].tolist()[0] == True : 
						long_short = "short_pair_1"
					
				#elif len(open_pos_cur_2) >0:
				#	if  open_pos_cur_2["isBuy"].tolist()[0] == True:
				#		long_short = "short_pair_1"
				#	elif  open_pos_cur_2["isBuy"].tolist()[0] == False:
				#		long_short = "long_pair_1"

			df_strat = pair_strategy(df,pair_1[i],pair_2[i],5)
			qt_pair_1 = qt/(df[pair_1[i]]["Close"].tolist()[-1])
			price_1 =df[pair_1[i]]["Close"].tolist()[-1]
			qt_pair_2 = qt/(df[pair_2[i]]["Close"].tolist()[-1])
			price_2 = df[pair_2[i]]["Close"].tolist()[-1]

			print(long_short)
			signal = trade_signal(df_strat,long_short,1)
			print(signal)
			if signal =="Buy_pair_1":
				print("Signal for Buy Pair 1")
				con.open_trade(symbol = pair_1[i], is_buy = True, is_in_pips = True, amount = qt_pair_1,time_in_force = "GTC",
					stop = -100,trailing_step = True,order_type = "AtMarket")
				con.open_trade(symbol = pair_2[i], is_buy = False, is_in_pips = True, amount = qt_pair_2,time_in_force = "GTC",
					stop = -100,trailing_step = True,order_type = "AtMarket")

				print("New LONG Position Ticker : {} | QT :{}".format(pair_1[i],qt_pair_1))
				print("New SHORT Position Ticker : {} | QT :{}".format(pair_2[i],qt_pair_2))

			elif signal =="Sell_pair_1":
				print("Signal for Sell Pair 1")
				con.open_trade(symbol = pair_1[i], is_buy = False, is_in_pips = True, amount = qt_pair_1,time_in_force = "GTC",
					stop = -100,trailing_step = True,order_type = "AtMarket")
				con.open_trade(symbol = pair_2[i], is_buy = True, is_in_pips = True, amount = qt_pair_2,time_in_force = "GTC",
					stop = -100,trailing_step = True,order_type = "AtMarket")

				print("New SHORT Position Ticker : {} | QT :{}".format(pair_1[i],qt_pair_1))
				print("New LONG Position Ticker : {} | QT :{}".format(pair_2[i],qt_pair_2))

			elif signal =="Close":
				con.close_all_for_symbol(pair_1[i])
				con.close_all_for_symbol(pair_2[i])
				print("Position closed for {} AND {}".format(pair_1[i],pair_2[i]))

			elif signal == "Keep_trade":
				pass

	except:
		print("error Encountered... Skipping Iteration")



starttime=time.time()
timeout = time.time() + 60*60*1  # 60 seconds times 60 meaning the script will run for 1 hr
while time.time() <= timeout:
	try:
		print("passthrough at ",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
		main(5000) # Quantity to invest
		time.sleep(30 - ((time.time() - starttime) % 30.0)) # 5 minute interval between each new execution
	except KeyboardInterrupt:
		print('\n\nKeyboard exception received. Exiting.')
		exit()

# Close all positions and exit
#for currency in pairs:
	#print("closing all positions for ",currency)
	#con.close_all_for_symbol(currency)
con.close()










## PROBLEM : DISCOVER HOW TO MAKE THE TIME_TRADE OUTSIDE THE WHILE LOOP SO IT DOES NOT RESET TO ZERO AT EACH ITERATION
