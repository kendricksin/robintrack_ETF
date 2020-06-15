import GetOldTweets3 as got
import datetime
import re
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

username = 'robintrack'
count = 2000
# Creation of query object
tweetCriteria = got.manager.TweetCriteria().setUsername(username).setMaxTweets(count)

# Creation of list that contains all tweets
tweets = got.manager.TweetManager.getTweets(tweetCriteria)

# Creating list of chosen tweet data
user_tweets = [[tweet.date, tweet.text] for tweet in tweets]

# Regex all tweets, create dataframe
tick_ptn = '\$\w+'
stake_ptn = '\: [+-]\d+'

TICKER_DIC = {}
df = pd.DataFrame(columns=['date', 'ticker', 'stake'])
x = 0

for twt in tweets:
    ticker = re.findall(tick_ptn, twt.text)
    stake = re.findall(stake_ptn, twt.text)
    if (len(ticker) == len(stake)) & (len(ticker) > 0):
        for i, j in zip(ticker, stake):
            x += 1
            line = []
            line.append(i[1:])
            if j[2] == '+':
                line.append(int(j[3:]))
            elif j[2] == '-':
                line.append(int(j[2:]))
            else:
                line.append(0)
            if i[1:] in TICKER_DIC:
                TICKER_DIC[i[1:]] += 1
            else:
                TICKER_DIC[i[1:]] = 1
            line = [twt.date.replace(tzinfo=None)] + line
            df.loc[x] = line

new_date = []
for line in df.date:
    new_date.append(datetime.datetime(line.year, line.month, line.day, 0, 0))
df['n_date'] = new_date
df.set_index('n_date')
df.groupby('n_date')
n_date = list(dict.fromkeys(new_date))
df = df[df['n_date'] > datetime.date(2019,12,31)]
df.sort_values('n_date', ascending=True)
n_date.sort(reverse=False)

# Select only tickers traded more than 3 times, extract data from yahoo finance
TICKER_LIST = []
for k, v in TICKER_DIC.items():
    if v > 2:
        TICKER_LIST.append(k)

TICKERS = " ".join(TICKER_LIST)

data = yf.download(TICKERS, period="6mo", interval="1d")
data_dates = list(data.index)
data.fillna(0)

# For each day, all moves made (stake), buy/sell position porpotional to stake size, multiplied by Adjusted Close
positions = {}
def refresh_posn(pos_dic, tk, trade_pr):
    if tk in pos_dic:
        pos_dic[tk] += trade_pr
    else:
        pos_dic[tk] = trade_pr


# irregardless of size of purchases, buy top 1 share relative to today's price
# example (buy low, now high) when bought = 5, today's price = 10, traded = 1 - 5/10 = 0.5
# example (buy, high, now low) when bought = 15 today's price = 10, traded = 1 - 15/10 = -0.5
# example (sold low, now high) when sold = 5, today's price = 10, traded = 5/10 - 1 = -0.5
# example (sold high, now low) when sold = 15, today's price = 10, traded = 15/10 - 1 = 0.5

for n in n_date:
    try:
        day_tickers = df.loc[df['n_date'] == n]
        t_bought = sum(day_tickers.stake*(day_tickers.stake > 0))
        t_sold = sum(day_tickers.stake*(day_tickers.stake <= 0))
        for index, p in day_tickers.iterrows():
            if p.ticker in TICKER_LIST:
                if p.stake > 0:
                    trade = 1-(data['Adj Close'].loc[n, p.ticker])/(data['Adj Close'].loc[max(n_date), p.ticker])
                elif p.stake < 0:
                    trade = (data['Adj Close'].loc[n, p.ticker])/(data['Adj Close'].loc[max(n_date), p.ticker])-1
                else:
                    trade = 0
                refresh_posn(positions, p.ticker, trade)
    except KeyError:
        print(n)
        continue

# assuming each transaction was $1000 worth of stonks
total_investment = 0
highest = 0
lowest = 0
for k, v in positions.items():
    if v > 0:
        total_investment += v
    if v < 0:
        total_investment += v

# arrange positions by ranking
sorted_posn = sorted(positions.items(), key=lambda kv: kv[1])
print('best positions:')
print(sorted_posn[-5:])

print('worst positions:')
print(sorted_posn[:5])


# # stake adjusted
# for n in n_date:
#     try:
#         day_tickers = df.loc[df['n_date'] == n]
#         t_bought = sum(day_tickers.stake*(day_tickers.stake > 0))
#         t_sold = sum(day_tickers.stake*(day_tickers.stake <= 0))
#         for index, p in day_tickers.iterrows():
#             if p.ticker in TICKER_LIST:
#                 if p.stake > 0:
#                     trade = -p.stake/t_bought*(data['Adj Close'].loc[n, p.ticker]) # buy
#                 elif p.stake < 0:
#                     trade = p.stake/t_sold*(data['Adj Close'].loc[n, p.ticker]) # sell
#                 else:
#                     trade = 0
#                 refresh_posn(positions, p.ticker, trade)
#     except KeyError:
#         print(n)
#         continue