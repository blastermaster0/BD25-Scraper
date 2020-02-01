import xml.etree.ElementTree as ET
import requests
import re
from sys import argv
from os import getenv
from io import BytesIO
from flask import Flask, Response, request as fRequest, stream_with_context
from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup
from gevent.pywsgi import WSGIServer

# Constants
BASE_URL = "http://www.bd25.eu"

DOWNLOAD_URL = f"{BASE_URL}/download.php"
FILES_URL = f"{BASE_URL}/index.php?page=files"
LOGIN_URL = f"{BASE_URL}/index.php?page=login"
PASSWORD_URL = f"{BASE_URL}/getpass.php"

# Flask App
app = Flask(__name__)

# Secrets
load_dotenv()
uid = getenv("USERNAME")
pwd = getenv("PASSWORD")


def login(session):
    data = {"uid": uid, "pwd": pwd}
    session.post(LOGIN_URL, data=data)


def getSearchResultsByPage(session, searchTerm, page):
    res = session.get(f"{FILES_URL}&search={searchTerm}&pages={page}")
    return BeautifulSoup(res.text, features="lxml")


def checkHasNextPage(soup):
    paginationForm = soup.find("form", attrs={"name": "change_page1pages"})
    if paginationForm is not None:
        nextButton = soup.find(string=re.compile("»"))
        return nextButton is not None
    return False


def getPagePassword(session, pageId):
    data = {"infohash": pageId, "rndval": datetime.utcnow(), "thanks": 1}
    res = session.post(PASSWORD_URL, data=data)
    pwSearch = re.search("(?:[^ ]+|1)$", res.text)
    return pwSearch[0].replace("|1", "")


def parseSearchResults(session, soup):
    results = soup.select("table.lista > tr")
    if results:
        finalResults = list()
        for result in results:
            try:
                categoryHref = result.find(href=re.compile("category=[0-9]+"))
                if not categoryHref:
                    continue

                detailsHref = result.find(href=re.compile("NZB-details"))
                if not detailsHref:
                    continue

                dateTd = result.find(string=re.compile("\d+/\d+/\d+"))
                if not dateTd:
                    continue
                date = datetime.strptime(dateTd, "%d/%m/%Y")
                pubDate = date.strftime("%a, %d %b %Y %H:%M:%S")
                idMatch = re.search("id=(\d+)", detailsHref["href"])
                resultId = idMatch[1]
                resultCategory = categoryHref.contents[0]
                resultTitle = detailsHref.contents[0]
                resultPassword = getPagePassword(session, resultId)
                finalResults.append(
                    {
                        "id": resultId,
                        "category": resultCategory,
                        "title": resultTitle,
                        "pubDate": pubDate,
                        "password": resultPassword,
                        "downloadURL": f"{fRequest.base_url}download?id={resultId}",
                    }
                )
            except err:
                print(err)
                pass
        return finalResults


def getAllResults(session, searchTerm):
    allResults = list()
    notLastPage = True
    pageNum = 0
    while notLastPage:
        pageNum += 1
        print(f"Getting results (Page {pageNum})...")
        soup = getSearchResultsByPage(session, searchTerm, pageNum)
        allResults.extend(parseSearchResults(session, soup))
        notLastPage = checkHasNextPage(soup)
    return allResults


def categoryToNewzNab(category):
    if re.search("UHD", category):
        return "4k"
    return "BluRay"


def categoryToNewzNabId(category):
    if re.search("UHD", category):
        return "2045"
    return "2050"


def buildRSSXML(results):
    rss = ET.Element("rss")
    rss.set("version", "2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    rss.set("xmlns:newznab", "http://www.newznab.com/DTD/2010/feeds/attributes/")
    channel = ET.SubElement(rss, "channel")
    title = ET.SubElement(channel, "title")
    title.text = "BD25.eu"
    for result in results:
        item = ET.SubElement(channel, "item")
        itemTitle = ET.SubElement(item, "title")
        itemTitle.text = result["title"].replace(" ", ".")
        itemPubDate = ET.SubElement(item, "pubDate")
        itemPubDate.text = result["pubDate"]
        itemCategory = ET.SubElement(item, "category")
        itemCategory.text = categoryToNewzNab(result["category"])
        itemLink = ET.SubElement(item, "link")
        itemLink.text = result["downloadURL"]
        itemGuid = ET.SubElement(item, "guid")
        itemGuid.text = result["downloadURL"]
        nnCategory = ET.SubElement(item, "newznab:attr")
        nnCategory.set("name", "category")
        nnCategory.set("value", categoryToNewzNabId(result["category"]))
        nnPwd = ET.SubElement(item, "newznab:attr")
        nnPwd.set("name", "password")
        nnPwd.set("value", result["password"])
    return rss


@app.route("/")
def main():
    searchTerm = fRequest.args.get("q")
    session = requests.Session()
    login(session)
    allResults = getAllResults(session, searchTerm)
    xml = buildRSSXML(allResults)
    return Response(
        ET.tostring(xml, encoding="utf8", method="xml"), mimetype="text/xml"
    )


@app.route("/download")
def download():
    nzbId = fRequest.args.get("id")
    session = requests.Session()
    login(session)
    res = session.get(f"{DOWNLOAD_URL}?id={nzbId}", stream=True)
    return Response(
        stream_with_context(res.iter_content()),
        content_type=res.headers["content-type"],
        headers={"Content-Disposition": res.headers["Content-Disposition"]},
    )


if __name__ == "__main__":
    http_server = WSGIServer(("", 5000), app)
    http_server.serve_forever()
