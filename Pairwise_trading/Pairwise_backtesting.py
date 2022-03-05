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
import plotly.express as px

end  = dt.datetime.today()
period = dt.timedelta(250)
start = end-period

stocks = ["BTC-USD","ETH-USD","ADA-USD","LUNA1-USD","ATOM-USD","DOT-USD","LTC-USD"]
df = pd.DataFrame()
ohlcv_data = {}
return_df = {}

def get_data(stocks,n,_interval):
	for i in stocks:
		temp = yf.download(i,period = n, interval = _interval)
		temp.dropna(inplace = True)
		ohlcv_data[i] = temp
		ohlcv_data[i].dropna(inplace = True)
		ohlcv_data[i]["returns"] = ohlcv_data[i]["Adj Close"].pct_change()

	return ohlcv_data



## Buy and Hold benchmark
def buy_and_hold(DATA):
	ohlcv_data = DATA.copy()
	cum_return = pd.DataFrame()
	for i in ohlcv_data:

		ohlcv_data[i]["cum_return"] = (1+ohlcv_data[i]["returns"]).cumprod()
		ohlcv_data[i]["cum_return_perc"] = (1/len(ohlcv_data))*ohlcv_data[i]["cum_return"]
		cum_return[i] = ohlcv_data[i]["cum_return_perc"]

	cum_return["total_cum_return"] = cum_return.sum(axis =1)
	cum_return["total_cum_return"].plot()
	n = len(cum_return)/(252)
	CAGR = (cum_return["total_cum_return"].tolist()[-1])**(1/n) - 1

	return CAGR




def corr_matrix(DATA):
	returns_df = pd.DataFrame()
	ohlcv_data = DATA.copy()
	pair_1 =[]
	for i in ohlcv_data:
		returns_df[i] = ohlcv_data[i]["returns"]
		pair_1.append(i)


	returns_df = pd.DataFrame.from_dict(returns_df)
	returns_df.dropna(inplace = True)
	corr = returns_df.corr()
	corr_replaced = corr.replace(1,0)
	pair_2 = []
	for x in corr_replaced.idxmax():
		pair_2.append(x)


	return pair_1,pair_2






def pair_strategy(DF,x,y,ma_period):
	df = DF.copy()
	df_x = ohlcv_data[x][["Adj Close","returns"]]
	df_x = pd.DataFrame.from_dict(df_x)
	df_x=df_x.rename(columns ={"Adj Close": "pair_1_price", "returns": "pair_1_returns"} )

	df_y = ohlcv_data[y][["Adj Close","returns"]]
	df_y = pd.DataFrame.from_dict(df_y)
	df_y=df_y.rename(columns ={"Adj Close": "pair_2_price", "returns": "pair_2_returns"} )

	df_x_close = ohlcv_data[x]["Adj Close"]
	df_y_close = ohlcv_data[y]["Adj Close"]
	df_final = df_x_close-df_y_close
	df_final = pd.DataFrame.from_dict(df_final)
	df_final = df_final.rename(columns = {"Adj Close":"Difference"})


	mean_spread = df_final.mean()
	std_spread = df_final.std()
	df_final["pair_zscore"] = (df_final - mean_spread) /std_spread
	df_final["pair_zscore_ma"] = df_final.pair_zscore.rolling(ma_period, min_periods = ma_period).mean()
	df_final = df_final.merge(df_x,on = "Date")
	df_final = df_final.merge(df_y,on = "Date")

	return df_final
	



def backtest(DF,std_deviation):
	df = DF.copy()
	pair_1,pair_2 = corr_matrix(df)
	pair_dict = {}
	pair_1_signal = {}
	pair_1_return = {}
	pair_2_signal = {}
	pair_2_return = {}
	pair_symbol_list = []
	for i in range(1,len(pair_1)):
		pair_symbol = pair_1[i] + "/" + pair_2[i]
		pair_dict[pair_symbol] = pair_strategy(df,pair_1[i],pair_2[i],5)
		pair_symbol_list.append(pair_symbol)
		pair_1_return[pair_symbol] = [0]
		pair_2_return[pair_symbol] = [0]
	for x in pair_dict:
		pair_1_signal[x] = ""
		pair_2_signal[x] = ""
		open_price_1 = [0]
		open_price_2 = [0]
		for i in range(1,len(pair_dict[x])):
			
			if pair_1_signal[x] == "" :
				pair_1_return[x].append(0)
				pair_2_return[x].append(0)
				if pair_dict[x]["pair_zscore"][i] < -std_deviation:
					pair_1_signal[x] = "Buy"
					open_price_1 = pair_dict[x]["pair_1_price"][i]

					pair_2_signal[x]= "Sell"
					open_price_2 = pair_dict[x]["pair_2_price"][i]

				elif pair_dict[x]["pair_zscore"][i] > std_deviation:
					pair_1_signal[x] = "Sell"
					pair_2_signal[x]= "Buy"
					open_price_1 = pair_dict[x]["pair_1_price"][i]
					open_price_2 = pair_dict[x]["pair_2_price"][i]

			elif pair_1_signal[x] == "Buy" :
				if pair_dict[x]["pair_zscore"][i] > -std_deviation:
					pair_1_signal[x] = ""
					pair_1_return[x].append((pair_dict[x]["pair_1_price"][i]/open_price_1)-1)

					pair_2_signal[x]= ""
					pair_2_return[x].append((pair_dict[x]["pair_2_price"][i] -open_price_2)*(-1)/open_price_2)
				else:
					pass

			elif pair_1_signal[x] == "Sell" :
				if pair_dict[x]["pair_zscore"][i] < std_deviation:
					pair_1_signal[x] = ""
					pair_1_return[x].append((pair_dict[x]["pair_1_price"][i]-open_price_1)*(-1)/open_price_1)

					pair_2_signal[x]= ""
					pair_2_return[x].append((pair_dict[x]["pair_2_price"][i]/open_price_2)-1)
				else:
					pass

	return pair_1_return, pair_2_return
	




def main():
	df = get_data(stocks,"1y","1d")
	pair_1_return, pair_2_return = backtest(df,1)

	for i in pair_1_return and pair_2_return:
		df_return_1 = pd.DataFrame(pair_1_return[i])
		df_return_1["cum_return"] = (1+df_return_1).cumprod()
		df_return_1.to_csv("pair_1_return.csv")
		df_return_2 = pd.DataFrame(pair_2_return[i])
		df_return_2["cum_return"] = (1+df_return_2).cumprod()
		df_final_return_a = df_return_1["cum_return"]*0.5 + df_return_2["cum_return"]*0.5
		values = df_final_return_a.values

		df_final_return = pd.DataFrame(values, columns = [i])
		df_final_return.to_csv("test.csv")
		n = len(df_return_2)/(252)
		CAGR = ((df_final_return_a.tolist()[-1])**(1/n) - 1)*100
		print("The CAGR for pair {} is : {}%".format(i,CAGR))

		plt.plot(df_final_return)
		plt.show()


main()