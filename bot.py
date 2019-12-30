import config
from user import User
import datetime
import time
import re
import tweepy
import pickle
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

class TwitterBot:

    RELEVANT_SCREEN_NAMES_FILE = 'cool_people_screenames.txt'
    UNFOLLOW_QUEUE_PKL = 'unfollow_queue.pickle'

    LOGIN_URL = 'https://twitter.com/'
    LIKES_URL_TEMPLATE = 'https://twitter.com/{}/status/{}/likes'
    # https://help.twitter.com/en/using-twitter/twitter-follow-limit
    DAILY_FOLLOW_LIMIT = 24
    HOURLY_FOLLOW_LIMIT = DAILY_FOLLOW_LIMIT // 24
    threshold = 30 # minutes

    def __init__(self, username, password):
        auth = tweepy.OAuthHandler(config.consumer_key, config.consumer_secret)
        auth.set_access_token(config.access_token, config.access_token_secret)
        # credentials
        self.username = username
        self.password = password
        # tools
        self.driver = webdriver.Chrome()
        self.api = tweepy.API(auth)
        try:
            with open(self.UNFOLLOW_QUEUE_PKL, 'rb') as pkl:
                self.unfollow_queue = pickle.load(pkl)
        except EOFError:
            self.unfollow_queue = []
        self.cool_people = self._get_cool_peole_ids()

    def login(self):
        driver = self.driver
        driver.get(self.LOGIN_URL)
        time.sleep(3)

        username = driver.find_element_by_name('session[username_or_email]')
        password = driver.find_element_by_name('session[password]')
        username.clear()
        password.clear()
        username.send_keys(self.username)
        password.send_keys(self.password)
        password.send_keys(Keys.RETURN)
        time.sleep(3)

    def do_your_thing(self):
        print('FOLLOWING STAGE')
        tweets = self._get_relevant_tweets()
        for tweet in tweets:
            print('HOURLY_FOLLOW_LIMIT:', self.HOURLY_FOLLOW_LIMIT)
            if not self.HOURLY_FOLLOW_LIMIT:
                break
            tweet_id, screen_name = tweet.id, tweet.user.screen_name
            print(f'{screen_name}: {tweet.text}')
            liked_screen_names = self._get_liked_screen_names(screen_name, tweet_id)
            ids = self._screen_names_to_ids(liked_screen_names)
            print(ids)
            for id in ids:
                if not self.HOURLY_FOLLOW_LIMIT:
                    break
                self.follow(id)
        self._add_hourly_follow_limit()
        self._update_unfollow_pkl()
        print('FINISHED FOLLOWING STAGE')

    def follow(self, user_id):
        try:
            self.api.create_friendship(user_id=user_id)
        except tweepy.TweepError as e:
            print(e)
            print(f'Error from follow(): {user_id} caused error')
        else:
            self.unfollow_queue.append(User(user_id, datetime.datetime.utcnow()))
            self.HOURLY_FOLLOW_LIMIT -= 1

    def unfollow(self):
        print('UNFOLLOWING STAGE')
        time_bound = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        while self.unfollow_queue and self.unfollow_queue[0].created_at <= time_bound:
            user = self.unfollow_queue.pop(0)
            try:
                self.api.destroy_friendship(user_id=user.id)
            except tweepy.TweepError as e:
                print(e)
                print(f'Error from unfollow(): {user.id} caused error')
        self._update_unfollow_pkl()
        print('FINISHED UNFOLLOWING STAGE')

    def _update_unfollow_pkl(self):
        print('\tUPDATING UNFOLLOW PICKLE')
        with open(self.UNFOLLOW_QUEUE_PKL, 'wb') as pkl:
            pickle.dump(self.unfollow_queue, pkl)
        print('\tFINISHED UPDATING UNFOLLOW PICKLE')

    def _add_hourly_follow_limit(self):
        self.HOURLY_FOLLOW_LIMIT += self.DAILY_FOLLOW_LIMIT // 24

    def reset_hourly_follow_limit(self):
        self.HOURLY_FOLLOW_LIMIT = self.DAILY_FOLLOW_LIMIT // 24

    def _get_relevant_tweets(self):
        public_tweets = self.api.home_timeline()
        time_bound = datetime.datetime.utcnow() - datetime.timedelta(minutes=self.threshold)
        tweets = filter(lambda t: t.user.id in self.cool_people and
            t.created_at >= time_bound, public_tweets)
        return tweets

    def _get_liked_screen_names(self, screen_name, tweet_id):
        likes_url = self.LIKES_URL_TEMPLATE.format(screen_name, tweet_id)
        self.driver.get(likes_url)
        time.sleep(5)
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')
        res = soup.find('div', {'aria-label': 'Timeline: Liked by', 'class': 'css-1dbjc4n'})
        if res:
            user_screen_names = re.findall('@([\\w\\d\\S]*?)Follow', res.text)
            return user_screen_names
        return []

    def _get_cool_peole_ids(self):
        cool_people_ids = []
        with open(self.RELEVANT_SCREEN_NAMES_FILE) as f:
            screen_name = f.readline().strip()
            while screen_name:
                cool_person = self.api.get_user(screen_name)
                if cool_person:
                    cool_people_ids.append(cool_person.id)
                screen_name = f.readline().strip()
        return cool_people_ids

    def _screen_names_to_ids(self, screen_names):
        ids = []
        for screen_name in screen_names:
            try:
                user = self.api.get_user(id=screen_name)
            except tweepy.TweepError as e:
                print(e)
                print(f'Error from _screen_names_to_ids(): {screen_name} caused error')
            else:
                if user and user.id:
                    ids.append(user.id)
        return ids

USER = config.email
PASS = config.password

bot = TwitterBot(USER, PASS)
bot.login()
hr = 0

while True:
    bot.do_your_thing()
    time.sleep(60 * 60) # 1 hr = 60 sec/min * 60 min/hr
    hr += 1
    print(f'hour {hr}: WAITING')
    bot.unfollow()
    if hr == 23:
        bot.reset_hourly_follow_limit()
