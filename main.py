import feedparser
import wget
import sqlite3
import json
import pdftotext
import os


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


def parse_rss() -> None:
    """ 
    Get the RSS feed from arXiv.org
    """
    for [category, url] in arxiv_url_dict.items():
        feed = feedparser.parse(url)
        print("parse rss feed url: ", url)
        print(feed)
        
        if feed["bozo"] is False:
            print("fetch rss feed url: ", url, "failed")
        else:
            print("fetch rss feed url: ", url, "successed")

        for entry in feed["entries"]:
            # print(entry)
            p = Paper(entry["title"], entry["link"], category)
            paper_list.append(p)
            

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


def download_arxiv_paper(paper_list) -> None:
    """
    Download the paper from arXiv.org
    """
    download_path = get_download_path()
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
                print(f"Skipped {paper.title}")
        except Exception as e:
            print(e)
        else:
            print(f"Downloaded {paper.title}")
            # pdf2text(paper)
            # break


def pdf2text(paper: Paper) -> str:
    paper_path = get_paper_path(paper)
            
    # Load your PDF
    with open(paper_path, "rb") as f:
        pdf = pdftotext.PDF(f, "secret")

    return ' '.join(pdf)

    
def run_web():
    pass

    
def main():
    # parse_rss()
    # download_arxiv_paper(paper_list)
    run_web()
        

if __name__ == "__main__":
    main()