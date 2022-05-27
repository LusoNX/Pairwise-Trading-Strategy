# Trading-Strategies

In this project I present the application of the trading strategy “Pairwise Trading”. The goal of the strategy is in identifying stocks with high correlation 
coefficients. Once they are identified, the bot will be responsible to evaluation if such correlation is sustained over time, or decreases, 
in order to only open positions in highly correlated stocks. 
The idea behind pairwise trading is that if two stocks are highly correlated, 
any deviations from their “central trend mean” should eventually revert, creating entry opportunities for trading. 
For example,  stock A and B are trading in an upward trend with a correlation of nearly 90 %, and suddenly stock B drops by 10 % while stock A rises by 1 %, 
we should buy B and sell A. 

Of course, the strategy, in its simpler format, is not considering the idiosyncratic risk associated with the drop-in price of B (the reason why it dropped),
which can reflect a fundamental change, justifying the widening of the performance of the two stocks, 
and consequently a reason for the strategy to no longer be viable. Nevertheless, the bot will find different stocks for the strategy, 
implying that the risk of unique events for a particular stock is reduced (via diversification). 

The 1st file “Pairwise Trading BOT_STOCKS.py”, relates to the implementation of the strategy by using FXCM API to create the connection, retrieve the relevant information, analyze the statistics and to execute the trades. 
1.	The most correlated symbols are extracted using the corr_matrix() function. 

2.	The strategy is created by standardization of the difference in returns between the two stocks, by running the pair_strategy() function.

3.	The trade signal is formed by calling the pair_strategy() function. The trader is free in setting up the number of standard deviations(sd) 
     away from “center” of the standardized values. Smaller sd  imply a larger frequency of trades, and more proneness for errors. 
     Larger sd imply lower frequency of trades and less proneness of errors, but in turn, may never be executed, because the differences in 
     returns may never be that high. 
     
4.	Finally, the main() function is responsible to set all up and running, with qt being the amount of quantity(value) desired for each position. 

The code will run by the defined timeout variable. For example, if timeout is set to 1 hour, the bot will trade for 1 hour.  
The bot can be shut down, by simply blocking the script. 

The 2nd file “Pairwise_backtesting.py”, relates to the backtesting of the applicable strategies and uses Yahoo Finance API to extract the price data. 
Similar to the above, correlation and signal are created, but only the signal is estimated in a rolling window manner. 
The correlation is static based on the last value, which an improvement that can (should) be made in future versions. 
