import json
import os
import praw
import requests
import io
import re
import PyPDF2
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import uuid
from dotenv import load_dotenv

load_dotenv()

reddit = praw.Reddit(
  client_id=os.getenv("CLIENT_ID"),
  client_secret=os.getenv("CLIENT_SECRET"),
  user_agent=os.getenv("USER_AGENT"),
  username=os.getenv("REDDIT_USERNAME"),
  password=os.getenv("REDDIT_PASSWORD")
)

import pdb

def get_author(o):
  author = o.author
  if author is None:
    return '<no author>'
  if type(author.name) is tuple:
    (name,) = author.name
    return name
  return author.name

def enumerate_comments(comment_forest):
  if getattr(comment_forest, 'comments', None):
    return enumerate_comments(comment_forest.comments())
  comments = comment_forest
  out = [];
  for comment in comments:
    if getattr(comment, 'comments', None):
      out = out + enumerate_comments(comment.comments());
    else:
      out.append({ 'author': get_author(comment), 'replies': enumerate_comments(comment.replies), 'body': comment.body })
  return out

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

def extract_pdf_text(pdf):
  pdf2 = PyPDF2.PdfFileReader(io.StringIO(response.content))
  output = ''
  for i in range(0, pdf2.getNumPages()):
    page = pdf2.getPage(i)
    output += page.extractText()
  return output

def get_external(url):
  try:
    response = requests.get(url, headers=headers)
    if re.search(r"\.pdf$", urlparse(url).path):
      return extract_pdf_text(response.content)   
    return BeautifulSoup(response.content, features='html.parser').get_text(separator=' ')
  except Exception as err:
    return ''

def format_comment(comment):
    comment_uuid = str(uuid.uuid1())
    output = 'AUTHOR: ' + comment['author'] + '\n' + 'UUID: ' + comment_uuid + '\n' 'TEXT: ' + comment['body'] + '\n'
    if len(comment['replies']) > 0:
      output += '(BEGIN REPLIES TO COMMENT ' + comment_uuid + ')' + '\n'
      for reply in comment['replies']:
        output += format_comment(reply) + '\n'
        output += '(END REPLIES TO COMMENT ' + comment_uuid + ')' + '\n'
    return output
def format_subreddit(o):
  output = 'TITLE: ' + o['title'] + '\n' + 'NAME: ' + o['name'] + '\n' + 'AUTHOR: ' + o['author'] + '\n' + 'TEXT: ' + o['selftext'] + '\n' + 'MORE INFORMATION: ' + o['externaltext'] + '\n' + 'URL: ' + o['url'] + '\n' + '(COMMENTS BELOW THIS LINE)\n'
  for comment in o['comments']:
    output = output + format_comment(comment) + '\n'
  return output

     
import sys

class ThreadGetter:
  def __init__(self, url):
    self.url = url
    self.reddit = reddit
  def subreddit(self, *kwargs):
    url = self.url
    _reddit = self.reddit
    def get(*args, **kwkargs):
      return [ _reddit.submission(url) ];
    class Getter:
        def __getattr__(self, key):
            return get
    return Getter()

def get_subreddit(subreddit, length=10000, type_of_search='new'):
  length = int(length)
  count = 0
  for thread in getattr(reddit.subreddit(subreddit), type_of_search)(limit=length):
    count += 1
    out = {}
    out['author'] = get_author(thread)
    out['comments'] = [] #enumerate_comments(thread.comments)
    out['selftext'] = thread.selftext 
    out['externaltext'] = urlparse(thread.url).netloc.find('reddit') == -1 and get_external(thread.url) or ''
    out['url'] = thread.url
    out['name'] = thread.name
    out['title'] = thread.title
    formatted = format_subreddit(out)
    print(json.dumps({ 'text': formatted, 'metadata': 'a thread of discussion with multi-level comments related to ' + subreddit }));

if __name__ == '__main__':
    subreddit, = sys.argv[1:2] or ['privacy']
    if subreddit == 'submission':
      reddit = ThreadGetter(sys.argv[2])
      get_subreddit('only-thread', 1, 'new');
    else:
      length, = sys.argv[2:3] or [100]
      type_of_search, = sys.argv[3:4] or ['new']
      get_subreddit(subreddit, length, type_of_search)
