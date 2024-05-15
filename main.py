"""
author: EvanLyu732
"""

from pymongo import MongoClient
import feedparser
import wget
import datetime
import json
import tiktoken
import sys
import pdftotext
import os
import httpx
from openai import OpenAI

paper_list = []

arxiv_url_dict = {
    "Computer Vision": "https://arxiv.org/rss/cs.CV",
    "Computer Sicence": "https://arxiv.org/rss/cs",
    "Artificial Intelligence": "https://arxiv.org/rss/cs.AI",
    "Robotics": "https://arxiv.org/rss/cs.RO",
    "Software Engineering": "https://rss.arxiv.org/rss/cs.SE",
}

class Paper:
    def __init__(self, title, link, category):
        self.title = title
        self.link = link
        self.category = category

    def __repr__(self):
        return f'Paper(title={self.title!r}, category={self.category!r})'


def parse_rss() -> None:
    """ 
    Get the RSS feed from arXiv.org
    """
    for [category, url] in arxiv_url_dict.items():
        feed = feedparser.parse(url)
        print("parse rss feed url: ", url)
        for entry in feed["entries"]:
            # print(entry)
            p = Paper(entry["title"], entry["link"], category)
            # print(f"append p {p}")
            paper_list.append(p)

def get_today_date() -> str:
    """
    Return the date of today in format YYYY-MM-DD
    """
    date = datetime.datetime.today().strftime("%Y-%m-%d")
    return date

def get_download_path() -> str:
    """
    Return the path to downloaded paper 
    """
    download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")
    return download_path

def get_paper_path(paper: Paper) -> str:
    """
    Return the path to actual paper
    """
    paper_path = os.path.join(get_download_path(), (paper.title+".pdf"))
    return paper_path

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens



def download_arxiv_paper(paper_list) -> None:
    """
    Download the paper from arXiv.org
    """
    download_path = get_download_path()
    db_manager = MongoDBMananger()

    for paper in paper_list:
        l = paper.link.replace("abs", "pdf")
        try: 
            # There is a stange v1.pdf suffix by using python wget to download the paper
            n  = wget.filename_from_url(l) + "v1.pdf"
            tmp_paper_path = os.path.join(download_path, n)
            paper_path = get_paper_path(paper)
            if not os.path.exists(paper_path):
                f  = wget.download(l, out=download_path)
                os.rename(tmp_paper_path, paper_path)
            else:
                print(f"Skipped {paper.title} in category {paper.category}")
        except Exception as e:
            print(e)
        else:
            print(f"Download {paper.title} in category {paper.category}")
            text =pdf2text(paper)
            text_token_num = num_tokens_from_string(text, "gpt2")
            print(f"{paper.title} token count {text_token_num}")
            filename = os.path.join(download_path, paper.title)
            with open(filename, "w") as f:
                f.write(text)
                # save to read
                res = db_manager.find_record(paper.title)

                if res is False:
                    print(f"Not found recored in MongoDB for {paper.title}")
                    print(f"Ready to request LLM for {paper.title}")
                    paper_note = request_llm(paper.title, text)
                    db_manager.insert_record(get_today_date(), paper.title, paper.category, paper.link, text_token_num, paper_note, None)
                    print(f"MongoDB insert {paper.title} in category {paper.category}")


def pdf2text(paper: Paper) -> str:
    paper_path = get_paper_path(paper)
            
    # Load your PDF
    with open(paper_path, "rb") as f:
        pdf = pdftotext.PDF(f, "secret")

    return ' '.join(pdf)


def get_prompt_str(paper_title: str, paper_text: str) -> str:
    """
    Get the prompt string from user input
    """
    # customize prompt string in here
    prompt = "You are an extraordinarily talented and gifted research scientist. \
            You are a master of the art of programming, writing, and speaking in English. \
            I would like you to summarize the paper that I have provided in three sections.  \
            The first section should explain what the paper is about. \
            The second section should discuss why this paper proposes a specific method compared to related works. \
            The third section should describe how the paper conducted its experimental work. \
            Here is the title of the paper: "
    full_prompt = prompt + paper_title
    full_prompt = full_prompt + "Here are the full paper text: " 
    full_prompt = prompt + paper_text
    return full_prompt


def request_llm(paper_title: str, paper_text: str) -> str: 
    """
    os get enviroment variable from OPENAI_API_KEY
    """
    api_key = os.environ["OPENAI_API_KEY"] 
    if api_key == "":
        print("No API key found, please set enviroment variable OPENAI_API_KEY")
        sys.exit()

    proxy_url = os.environ.get("OPENAI_PROXY_URL")
    client = OpenAI() if proxy_url is None or proxy_url == "" else OpenAI(http_client=httpx.Client(proxy=proxy_url))

    # Non-streaming:
    print("----- standard request -----")
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "user",
                "content": get_prompt_str(paper_title, paper_text),
            },
        ],
        max_tokens=30000
    )
    print("----- generate response -----")
    print(completion.choices[0].message.content)
    print("----- response finished-----")
    return completion.choices[0].message.content



class MongoDBMananger:
    def __init__(self) -> None:
        try:
            self.client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=1000)
            self.db = self.client["daily_arxiv_db"]
            self.collection = self.db["collection"]
            print("MongoDBMananger check MongoDB server info")
            server_info = self.client.server_info()
            print("Connection to MongoDB server")
        except Exception as e:
            print("MongoDB Connection failed:", e)
            sys.exit(1)

    def insert_record(self, date, title, category, link, token_counts, notes, realated_entity) -> None:
        """
        Every document has below attibutes:
        - date: str
        - title: str
        - category: str
        - link: str
        - token_counts: int
        - notes: str
        - related entity: str
        """
        self.collection.insert_one({
            "date": date,
            "title": title,
            "category": category,
            "link": link,
            "token_counts": token_counts,
            "notes": notes,
            "related_entity": None
        })
        pass

    def update_related_entity(self, title, related_entity_title) -> None:
        pass

    def find_record(self, title) -> bool:
        """
        Find the record in database by date and title. 
        If there is no such record, return False
        """
        cursor = self.collection.find_one({
            "title": title
        })
        if cursor is None:
            print(f"MongoDb No such record: {title}")
            return False
        else:
            print(f"MongoDb found record: {title}")
            return True



    
def main():
    parse_rss()
    download_arxiv_paper(paper_list)
        

if __name__ == "__main__":
    main()