from pandas_datareader import data
import cufflinks as cf
import yfinance as yf
import matplotlib.pyplot as plt
import plotly
import pandas as pd
import plotly.offline as offline
import datetime as dt
import matplotlib.pyplot as plt 
#df = yf.download("MSFT", period = "1mo",interval = "5m")
from bs4 import BeautifulSoup
from pandas import json_normalize
import FundamentalAnalysis as fa
import requests
import numpy as np
import sklearn
from sklearn.linear_model import LinearRegression
import fxcmpy
import time

api_token = "YOUR API TOKEN FROM FXCM"

con = fxcmpy.fxcmpy(access_token = api_token,log_level = "error",server = "demo")




df = pd.DataFrame()
ohlcv_data = {}
return_df = {}
financial_dir =  {}


def get_financial_data(symbol):
	ticker = yf.Ticker(symbol)
	info = ticker.info
	df = json_normalize(info)
	df = df[["freeCashflow","targetLowPrice","debtToEquity","bookValue","forwardEps","sharesPercentSharesOut","trailingEps","sharesOutstanding"]]
	return df




def get_candles(SYMBOL,_period):
	ohlcv_data = {}
	tickers = SYMBOL
	for i in tickers:
		data = con.get_candles(i, period = _period, number = 125) # half year of trading
		ohlc = data.iloc[:,[0,1,2,3,8]]
		ohlc.columns = ["Open","Close","High","Low","Volume"]
		ohlc["returns"] = ohlc["Close"].pct_change()
		ohlcv_data[i] = ohlc
	return ohlcv_data


def get_price_data(symbol,n,_interval):
	temp = yf.download(symbol,period = n, interval = _interval)
	temp.dropna(inplace = True)
	returns_stock = temp.pct_change()
	returns_stock = returns_stock[returns_stock['Close'].notna()]

	return returns_stock["Close"]





def cost_of_equity(symbol,rf):


	#Cost of Equity
	ticker = yf.Ticker(symbol)
	spy = yf.Ticker("SPY")

	returns_stock = get_price_data(symbol,"1y","1d")
	
	returns_index = get_price_data("^GSPC","1y","1d")
	index_cum_prod = (1+returns_index).cumprod()
	n = len(index_cum_prod)/(252)
	CAGR_index = (index_cum_prod.tolist()[-1])**(1/n) - 1

	X = np.c_[returns_index]
	Y = np.c_[returns_stock]

	if len(X) == len(Y):

		lin_reg_model = sklearn.linear_model.LinearRegression().fit(X,Y)
		beta = lin_reg_model.coef_
		rm = CAGR_index # Assumed long ter market return
		#rf = 0.01375  # Later find an API for this value
		ke = rf + beta*(rm-rf)
	else:
		ke = None

	return ke[0][0]


def cost_of_debt(symbol):

	ticker = yf.Ticker(symbol)
	interest_exp = ticker.financials.T["Interest Expense"].iloc[0]
	#print(interest_exp)
	debt = ticker.info["totalDebt"]

	cost_of_debt = (-1)*interest_exp/debt
	#print(cost_of_debt)
	return cost_of_debt


def wacc(symbol):
	kd =cost_of_debt(symbol)
	ke = cost_of_equity(symbol,0.01) # rf = 1 %
	ticker = yf.Ticker(symbol)
	debt_to_equity = ticker.info["debtToEquity"]/100
	debt_perc = debt_to_equity/(1+debt_to_equity)
	equity_perc = 1- debt_perc
	wacc = kd*(1-0.23)*debt_perc + ke*(equity_perc)

	return wacc



def CF_data(symbol):
	ticker = yf.Ticker(symbol)

	df_quarterly = ticker.quarterly_cashflow
	df_quarterly = df_quarterly.T
	df_quarterly.to_csv("fcf_test.csv")
	df_quarterly["fcf"] = df_quarterly["Total Cash From Operating Activities"] - df_quarterly["Capital Expenditures"]*(-1)
	df_quarterly["fcfe"] = df_quarterly["fcf"]+ df_quarterly["Net Borrowings"]
	fcf = df_quarterly["fcf"].sum()
	fcfe = df_quarterly["fcfe"].sum()
	return fcf,fcfe

def signal_values(DF,symbol):
	df = DF.copy()
	price = df["Close"].tolist()[-1]

	#price Estimate
	fcf,fcfe = CF_data(symbol)
	ke = cost_of_equity(symbol,0.01)
	_wacc = wacc(symbol)
	fin_data = get_financial_data(symbol)
	shares_out = fin_data["sharesOutstanding"].iloc[0]


	price_est_fcf = (fcf/_wacc)/shares_out
	price_est_fcfe = (fcfe/ke)/shares_out


	## P/E
	forward_eps = fin_data["forwardEps"].iloc[0]
	forward_PE = price/forward_eps
	## P/B
	book_value = fin_data["bookValue"].iloc[0]
	PB = price/book_value

	return price_est_fcf,price_est_fcfe,forward_PE,PB,price


def trade_signal(DF,l_s,symbol_1,symbol_2):
	df = DF.copy()

	df = df[symbol_2]
	fcf_price,fcfe_price,forward_PE,PB,price = signal_values(df,symbol_1)
	
	if l_s == "":
		if forward_PE < 10 and PB < 2 and fcf_price > price or fcfe_price > price:
			signal = "Buy Stock"
		else:
			signal ="No trade"

	elif l_s == "long":
		if forward_PE > 10 and PB > 2 and fcf_price < price or fcfe_price < price:
			signal = "Close"

		else:
			signal = "No trade"

	return signal,price


def main(stop_loss,limit_profit,qt): ## percentage terms . e.g.: 0.2 for a 20 % max loss 
	
	symbol_1 = ["AMZN","GOOG","AMD","FB","NVDA"]
	symbol_2 = ["AMZN.us","GOOG.us","AMD.us","FB.us","NVDA.us"]
	df = get_candles(symbol_2,"D1")
	open_pos = con.get_open_positions()

	for i in range(0,len(df)):
		try:
			long_short = ""
			if len(open_pos) >0:
				open_pos_ticker = open_pos[open_pos["currency"]== symbol_2[i]]
				if len(open_pos_ticker)>0:
					long_short = "long"
				else:
					pass


			signal,price = trade_signal(df,long_short,symbol_1[i],symbol_2[i])
			qt_amount = qt/price
			_stop_loss = (1-stop_loss)*price
			_limit_profit = (1+limit_profit)*price

			if signal == "Buy Stock":
				con.open_trade(symbol = symbol_2[i], is_buy = True, is_in_pips = False, amount =qt_amount ,time_in_force = "GTC", stop =_stop_loss,limit = _limit_profit,trailing_step = True,order_type = "AtMarket")
				print("Buy order for ticker {} ||| QT = {}".format(symbol_2[i],qt_amount))
			elif signal == "Close":
				con.close_all_for_symbol(symbol_2[i])
				print("Close order for ticker {} ||| QT = {}".format(symbol_2[i],qt_amount))

			elif signal == "No Trade":
				print("No trade Action in this iteration")

		except:
			print("Erro found, passing to next iteration")






starttime=time.time()
timeout = time.time() + 60*60*1  # 60 seconds times 60 meaning the script will run for 1 hr
while time.time() <= timeout:
	try:
		print("passthrough at ",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
		main(0.2,0.4,2000)
		time.sleep(300 - ((time.time() - starttime) % 300.0)) # 5 minute interval between each new execution
	except KeyboardInterrupt:
		print('\n\nKeyboard exception received. Exiting.')
		exit()

# Close all positions and exit
#for currency in pairs:
	#print("closing all positions for ",currency)
	#con.close_all_for_symbol(currency)
con.close()
