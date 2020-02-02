from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
from flask import abort, Flask, Response, request as fRequest, send_file
from io import BytesIO
from os import getenv
from sys import argv
import re
import requests
import xml.etree.ElementTree as ET
from unrar import rarfile

# Constants
BASE_URL = "http://www.bd25.eu"

DOWNLOAD_URL = f"{BASE_URL}/download.php"
FILES_URL = f"{BASE_URL}/index.php?page=files"
DETAILS_URL = f"{BASE_URL}/index.php?page=NZB-details"
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


def getSession():
    session = requests.Session()
    login(session)
    return session


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
    password = pwSearch[0].replace("|1", "")
    if password == "nopw":
        return
    return password


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

                sizeTd = result.find(string=re.compile("\d+.\d+ GB"))
                if not sizeTd:
                    continue
                size = str(int(float(sizeTd.replace(" GB", "")) * 1024 * 1024 * 1024))
                date = datetime.strptime(dateTd, "%d/%m/%Y")
                pubDate = date.strftime("%a, %d %b %Y %H:%M:%S")
                idMatch = re.search("id=(\d+)", detailsHref["href"])
                resultId = idMatch[1]
                resultCategory = categoryHref.contents[0]
                resultTitle = detailsHref.contents[0]
                finalResults.append(
                    {
                        "id": resultId,
                        "category": resultCategory,
                        "title": f"{resultTitle}.{resultCategory}",
                        "pubDate": pubDate,
                        "size": size,
                        "detailsURL": f"{fRequest.base_url}/details?id={resultId}",
                        "downloadURL": f"{fRequest.base_url}?t=getNzb&id={resultId}",
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
        return "Movies > 4k"
    return "Movies > BluRay"


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

        itemGuid = ET.SubElement(item, "guid")
        itemGuid.text = result["downloadURL"]

        itemComments = ET.SubElement(item, "comments")
        itemComments.text = result["detailsURL"]

        itemPubDate = ET.SubElement(item, "pubDate")
        itemPubDate.text = result["pubDate"]

        itemCategory = ET.SubElement(item, "category")
        itemCategory.text = categoryToNewzNab(result["category"])

        itemDescription = ET.SubElement(item, "description")
        itemDescription.text = result["title"].replace(" ", ".")

        itemEnclosure = ET.SubElement(item, "enclosure")
        itemEnclosure.set("url", result["detailsURL"])
        itemEnclosure.set("length", result["size"])
        itemEnclosure.set("type", "application/x-rar-compressed")

        itemLink = ET.SubElement(item, "link")
        itemLink.text = result["downloadURL"]

        nnMainCategory = ET.SubElement(item, "newznab:attr")
        nnMainCategory.set("name", "category")
        nnMainCategory.set("value", "2000")

        nnCategory = ET.SubElement(item, "newznab:attr")
        nnCategory.set("name", "category")
        nnCategory.set("value", categoryToNewzNabId(result["category"]))

        nnSize = ET.SubElement(item, "newznab:attr")
        nnSize.set("name", "size")
        nnSize.set("value", result["size"])

        nnGrabs = ET.SubElement(item, "newznab:attr")
        nnGrabs.set("name", "grabs")
        nnGrabs.set("value", "100")

        nnGuid = ET.SubElement(item, "newznab:attr")
        nnGuid.set("name", "guid")
        nnGuid.set("value", result["id"])

        nnInfo = ET.SubElement(item, "newznab:attr")
        nnInfo.set("name", "info")
        nnInfo.set("value", result["detailsURL"])

        nnComments = ET.SubElement(item, "newznab:attr")
        nnComments.set("name", "comments")
        nnComments.set("value", "0")

        nnComments = ET.SubElement(item, "newznab:attr")
        nnComments.set("name", "password")
        nnComments.set("value", "1")

    return rss


def buildCapsXML():
    caps = ET.Element("caps")
    caps.set("version", "2.0")
    caps.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    caps.set("xmlns:newznab", "http://www.newznab.com/DTD/2010/feeds/attributes/")

    server = ET.SubElement(caps, "server")
    server.set("version", "1.0")
    server.set("title", "BD25.eu Scraper")

    searching = ET.SubElement(caps, "searching")
    search = ET.SubElement(searching, "search")
    search.set("available", "yes")
    search.set("supportedParams", "q")

    tvSearch = ET.SubElement(searching, "tv-search")
    tvSearch.set("available", "yes")
    tvSearch.set("supportedParams", "q")

    movieSearch = ET.SubElement(searching, "movie-search")
    movieSearch.set("available", "yes")
    movieSearch.set("supportedParams", "q")

    categories = ET.SubElement(caps, "categories")

    moviesCategory = ET.SubElement(categories, "category")
    moviesCategory.set("id", "2000")
    moviesCategory.set("name", "Movies")

    UHDSubcategory = ET.SubElement(moviesCategory, "subcat")
    UHDSubcategory.set("id", "2045")
    UHDSubcategory.set("name", "4k")

    BRSubcategory = ET.SubElement(moviesCategory, "subcat")
    BRSubcategory.set("id", "2050")
    BRSubcategory.set("name", "BluRay")

    tvCategory = ET.SubElement(categories, "category")
    tvCategory.set("id", "2000")
    tvCategory.set("name", "TV")

    HDTVSubcategory = ET.SubElement(tvCategory, "subcat")
    HDTVSubcategory.set("id", "5040")
    HDTVSubcategory.set("name", "HD")

    UHDTVSubcategory = ET.SubElement(tvCategory, "subcat")
    UHDTVSubcategory.set("id", "5045")
    UHDTVSubcategory.set("name", "4K")

    return caps


def getXMLResponse(xml):
    return Response(
        ET.tostring(xml, encoding="utf8", method="xml"), mimetype="text/xml"
    )


#####################################################################################
# ROUTES
#####################################################################################


@app.route("/api")
def api():
    reqType = fRequest.args.get("t")
    if reqType == "caps":
        return getXMLResponse(buildCapsXML())
    if reqType == "search" or reqType == "movie":
        searchTerm = fRequest.args.get("q")
        session = requests.Session()
        login(session)
        allResults = getAllResults(session, searchTerm)
        return getXMLResponse(buildRSSXML(allResults))
    if reqType == "getNzb":
        nzbId = fRequest.args.get("id")
        return Response(f"{fRequest.base_url}/download?id={nzbId}", 200)
    return abort(404)


@app.route("/api/download")
def download():
    nzbId = fRequest.args.get("id")
    session = getSession()
    rarFile = f"/tmp/{nzbId}-{datetime.utcnow()}.rar"
    res = session.get(f"{DOWNLOAD_URL}?id={nzbId}")
    with open(rarFile, "wb") as f:
        for chunk in res.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    rar = rarfile.RarFile(rarFile)
    file = next(x for x in rar.infolist() if x.filename.endswith("nzb"))
    rar.extract(file, path="/tmp")
    finalFilename = file.filename
    if not re.search("{{.+}}", finalFilename):
        password = getPagePassword(session, nzbId)
        if password:
            finalFilename = (
                f"{finalFilename.replace('.nzb', '')}{'{{'}{password}{'}}'}.nzb"
            )
    return send_file(
        f"/tmp/{file.filename}", attachment_filename=finalFilename, as_attachment=True,
    )


@app.route("/api/details")
def details():
    nzbId = fRequest.args.get("id")
    session = getSession()
    res = session.get(f"{DETAILS_URL}&id={nzbId}")
    return Response(res.content, res.status_code)

