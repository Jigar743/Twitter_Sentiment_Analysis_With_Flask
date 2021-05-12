import tweepy
import jsonpickle
import json
import csv
import time
import os.path
import pandas as pd
import re
from afinn import Afinn
from textblob import TextBlob
from matplotlib import pyplot as plt

from flask import Flask, redirect, url_for, request, render_template
app = Flask(__name__)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/sendtopic', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        hashtag = request.form['nm']
        return redirect(url_for('tweet_analysis', topic=hashtag))
    else:
        hashtag = request.args.get('nm')
        return redirect(url_for('tweet_analysis', topic=hashtag))

@app.route('/tweet_analysis/<topic>')
def tweet_analysis(topic):
    API_KEY = "LwU63GB3BFrQHRdepwXjGY2FO"
    API_SECRET = "5j0gVfZ9fh8f8lmUtc0eyeKG4wU0U7y2g1Pja085jtrlNdarzk"
    ACCESS_TOKEN = "1370641391596965891-vNKvTn1ElBcl6iYjkWg7ReeBMjRbKg"
    ACCESS_TOKEN_SECRET = "f3qw6nI0giR41M7IyAUBQIoxTfe4NJihdjmLLOVhRPjqz"
    auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)
    print(api.me().name)

    # Collection Tweets

    st = time.time()
    API_KEY = "LwU63GB3BFrQHRdepwXjGY2FO"
    API_SECRET = "5j0gVfZ9fh8f8lmUtc0eyeKG4wU0U7y2g1Pja085jtrlNdarzk"

    auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True,
                     wait_on_rate_limit_notify=True)

    tweetsPerQuery = 100
    max_tweets = 3500000
    fName = os.path.join(topic + ".txt")

    since_id = None
    max_id = -1
    tweet_count = 0
    print("Downloading the tweeets..takes some time..")

    search_query = "#"+topic
    x = 0
    with open(fName, 'w') as f:
        print("Downloading hashtag " + search_query)
        while (tweet_count < max_tweets):
            try:
                if (max_id <= 0):
                    if (not since_id):
                        new_tweets = api.search(
                            q=search_query, count=tweetsPerQuery, lang="en", tweet_mode='extended')

                    else:
                        new_tweets = api.search(q=search_query, count=tweetsPerQuery, lang="en", tweet_mode='extended',
                                                since_id=since_id)
                else:
                    if (not since_id):
                        new_tweets = api.search(q=search_query, count=tweetsPerQuery, lang="en", tweet_mode='extended',
                                                max_id=str(max_id - 1))
                    else:
                        new_tweets = api.search(q=search_query, count=tweetsPerQuery, lang="en", tweet_mode='extended',
                                                max_id=str(max_id - 1), since_id=since_id)

                if (not new_tweets):
                    print("No more tweets found!!")
                    break

                for tweet in new_tweets:
                    f.write(jsonpickle.encode(
                        tweet._json, unpicklable=False) + '\n')
                    tweet_count += len(new_tweets)
                    print("Successfully downloaded {0} tweets".format(
                        tweet_count))
                    max_id = new_tweets[-1].id

            except tweepy.TweepError as e:
                print("Some error!!:" + str(e))
                break
    end = time.time()

    print("A total of {0} tweets are downloaded and saved to {1}".format(
        tweet_count, fName))
    print("Total time taken is ", end - st, "seconds.")

    # Coverting to csv
    f = open(topic + r'.csv', 'a', encoding='utf-8')
    csvWriter = csv.writer(f)
    headers = ['full_text', 'retweet_count', 'user_followers_count', 'favorite_count', 'place', 'coordinates', 'geo',
               'id_str']
    csvWriter.writerow(headers)

    for inputFile in [os.path.join(topic + '.txt')]:
        tweets = []
        for line in open(inputFile, 'r'):
            tweets.append(json.loads(line))

        count_lines = 0
        for tweet in tweets:
            try:
                csvWriter.writerow([tweet['full_text'], tweet['retweet_count'], tweet['user']['followers_count'],
                                    tweet['favorite_count'], tweet['place'], tweet['coordinates'], tweet['geo'],
                                    str(tweet['id_str'])])
                count_lines += 1
            except Exception as e:
                print(e)
        print(count_lines)

    df = pd.read_csv(topic + r'.csv', encoding='unicode_escape')
    df.head()
    print("Total tweets: ", len(df.index))

    # Removing Duplicates
    serlis = df.duplicated(['full_text']).tolist()
    print("Duplicate Tweets: ", serlis.count(True))
    df = df.drop_duplicates(['full_text'])
    print("Unique Tweets: ", len(df.index))
    df = df.drop(['place', 'coordinates', 'geo', 'id_str'], axis=1)
    df.to_csv(topic+r'_unique.csv')
    # Cleaning Tweets
    df = pd.read_csv(topic+r'_unique.csv')
    for i in range(len(df)):
        txt = df.loc[i]["full_text"]
        txt = re.sub(r'@[A-Z0-9a-z_:]+', '', txt)  # username-tags
        txt = re.sub(r'^[RT]+', '', txt)  # RT-tags
        txt = re.sub('https?://[A-Za-z0-9./]+', '', txt)  # URLs
        txt = re.sub("[^a-zA-Z]", " ", txt)  # hashtags
        df.at[i, "full_text"] = txt
    df.to_csv(topic + r'_tweetclean.csv')

    # Afinn Classification
    df = pd.read_csv(topic + r'_tweetclean.csv', encoding='unicode_escape')
    af = Afinn()
    count_total = 0
    count_pos = 0
    count_neut = 0

    count_neg = 0
    li_af = []
    for i in range(len(df.index)):
        sent = str(df.loc[i]['full_text'])
        if (af.score(sent) > 0):
            count_pos = count_pos + 1
            count_total = count_total + 1
            li_af.append(1)
        elif (af.score(sent) < 0):
            count_neg = count_neg + 1
            count_total = count_total + 1
            li_af.append(-1)
        else:
            li_af.append(0)
            count_total = count_total + 1
            count_neut += 1

    print("Afinn")
    print("Total tweets:", len(df.index))
    print("Total tweets with sentiment:", count_total)
    print("positive tweets:", count_pos)
    print("negative tweets:", count_neg)
    print("neutral tweets:", count_neut)

    # fig = plt.figure()
    # ax = fig.add_axes([0, 0, 1, 1])
    # ax.axis('equal')
    # sents1 = ['Positive', 'Negative', 'Nuetral']
    # score1 = [count_pos, count_neg, count_neut]
    # ax.pie(score1, labels=sents1, autopct='%1.2f%%')
    # plt.title("Affinn")
    # plt.show()
    result = {'pos': count_pos, 'neg': count_neg,
              'nuet': count_neut, 'total_tweets_collect': tweet_count, 'your_topic': topic}
    return render_template("result.html", result=result)


if __name__ == '__main__':
    app.run('0.0.0.0', 8085)
