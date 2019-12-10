import config
import time
import tweepy
import datetime
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

class TwitterBot:

    LOGIN_URL = 'https://twitter.com/'
    threshold = 30 # minutes
    LIKES_URL_TEMPLATE = 'https://twitter.com/{}/status/{}/likes'

    def __init__(self, username, password):
        auth = tweepy.OAuthHandler(config.consumer_key, config.consumer_secret)
        auth.set_access_token(config.access_token, config.access_token_secret)
        # credentials
        self.username = username
        self.password = password
        # tools
        self.driver = webdriver.Chrome()
        self.api = tweepy.API(auth)
        self.unfollow_queue = []
        self.cool_people = self._get_cool_peole_ids()

    def _get_cool_peole_ids(self):
        file_path = 'cool_people_screenames.txt'
        cool_people_ids = []
        with open(file_path) as f:
            screen_name = f.readline().strip()
            while screen_name:
                cool_person = self.api.get_user(screen_name)
                if cool_person:
                    cool_people_ids.append(cool_person.id)
                screen_name = f.readline().strip()
        return cool_people_ids

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
        public_tweets = self.api.home_timeline()
        time_bound = datetime.datetime.utcnow() - datetime.timedelta(minutes=self.threshold)
        tweets = filter(lambda t: t.user.id in self.cool_people and
                                t.created_at >= time_bound, public_tweets)
        for tweet in tweets:
            print(tweet.text)
            tweet_id, screen_name = tweet.id, tweet.user.screen_name
            likes_url = self.LIKES_URL_TEMPLATE.format(screen_name, tweet_id)
            self.driver.get(likes_url)
            time.sleep(5)
            page_source = self.driver.page_source
            liked_by = re.findall('<span[^>]*>(@[^</span>$]+)', page_source)
            print(liked_by)

USER = config.email
PASS = config.password

bot = TwitterBot(USER, PASS)
bot.login()
bot.do_your_thing()
