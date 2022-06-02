from re import S
from urllib.request import urlopen
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
from dotenv import load_dotenv
import os
import urllib.request
from pytz import timezone
from datetime import datetime
import json

def exists(path):
    return urllib.request.urlopen(path).getcode() == 200

if __name__ == "__main__":
    load_dotenv()
    AWS_IMAGE_SERVER_URL = os.getenv("AWS_IMAGE_SERVER_URL")
    KST = timezone("Asia/Seoul")
    filenames = ["dessertWines.txt", "fortifiedWines.txt","redWines.txt","roseWines.txt","sparklingWines.txt", "WhiteWines.txt"]
    jsonFilenames = ["dessertWines.json", "fortifiedWines.json","redWines.json","roseWines.json","sparklingWines.json", "WhiteWines.json"]
    browser = webdriver.Chrome('./chromedriver.exe') # Chrome version 100
    count = 0 
    index = 0
    result = []
    for num in range(len(filenames)):
        result.clear()
        count = 0
        print(filenames[num])
        urlFile = open(filenames[num],'r')
        while count < 1000:
            line = urlFile.readline()
            if not line:
                break
            if exists(line):
                browser.get(line)
                time.sleep(3)
                before_height = browser.execute_script("return window.scrollY")
                while True: # infinite scroll
                    browser.find_element(by=By.CSS_SELECTOR, value="body").send_keys(Keys.END)
                    time.sleep(2)
                    after_height = browser.execute_script("return window.scrollY")
                    if after_height == before_height:
                        break 
                    before_height = after_height
                rating = browser.find_element(by=By.CSS_SELECTOR, value='div._19ZcA').text
                #winery = browser.find_element(by=By.CSS_SELECTOR, value='a.winery').text
                wineName = browser.find_element(by=By.CSS_SELECTOR, value='span.vintage').text
                tags = [ele.text for ele in browser.find_elements(by=By.CSS_SELECTOR, value='a._3qc2M.breadCrumbs__link--1TY6b')]
                price = ""
                if len(browser.find_elements(by=By.CSS_SELECTOR, value='span.purchaseAvailabilityPPC__amount--2_4GT')) == 0:
                    if len(browser.find_elements(by=By.CSS_SELECTOR, value='span.purchaseAvailability__currentPrice--3mO4u')) != 0:
                        price = browser.find_element(by=By.CSS_SELECTOR, value='span.purchaseAvailability__currentPrice--3mO4u').text
                else:
                    price = browser.find_element(by=By.CSS_SELECTOR, value='span.purchaseAvailabilityPPC__amount--2_4GT').text
                if price != "":
                    price = float(price.replace("$","").replace(",",""))
                wineImage = browser.find_element(by=By.CSS_SELECTOR, value="picture.bottleShot")
                wineImage = wineImage.find_element(by=By.CSS_SELECTOR, value="source")
                src = wineImage.get_attribute('srcset').split(',')[1].replace(" ","")[0:-2] # scrap 2x image
                src = "https:" + src # append https url
                srcExtension = src.split(".")[-1]
                # download the image
                wineImageName = wineName.replace(" ", "_") +"."+srcExtension
                print(wineImageName)
                print("src =",src)
                if exists(src):
                    urllib.request.urlretrieve(src, "./wines/"+wineImageName)
                else:
                    print(src,"image fetch failed.")
                winery = ""
                grapes = []
                region = []
                wineStyle = []
                abv = 0
                allergens = ""
                bottleClosure = ""
                wineFactsRows =  browser.find_elements(by=By.CSS_SELECTOR, value="td.wineFacts__fact--3BAsi")
                wineFactsHeaders = browser.find_elements(by=By.CSS_SELECTOR, value="span.wineFacts__headerLabel--14doB")
                for i in range(len(wineFactsRows)):
                    texts = wineFactsRows[i].find_elements_by_xpath("./child::*")
                    if wineFactsHeaders[i].text == "Winery":
                        winery = texts[0].text
                    elif wineFactsHeaders[i].text == "Grapes":
                        grapes.extend([grape.text for grape in texts])
                    elif wineFactsHeaders[i].text == "Region":
                        region.extend([region.text for region in texts])
                    elif wineFactsHeaders[i].text == "Wine style":
                        wineStyle.extend([style.text for style in texts])
                    elif wineFactsHeaders[i].text == "Alcohol content":
                        abv = float(texts[0].text.replace("%",""))
                    elif wineFactsHeaders[i].text == "Allergens":
                        allergens = texts[0].text
                    elif wineFactsHeaders[i].text == "Bottle closure":
                        bottleClosure = texts[0].text
                lightness = 0
                smoothness = 0
                sweetness = 0
                softness = 0
                wineTastesHeader = browser.find_elements(by=By.CSS_SELECTOR, value="div.tasteStructure__property--loYWN")
                wineTastesEval = browser.find_elements(by=By.CSS_SELECTOR, value="span.indicatorBar__progress--3aXLX")
                for i in range(0, len(wineTastesHeader), 2):
                    if wineTastesHeader[i].text == "Light":
                        print("lightness caught", i//2)
                        lightness = round(float(wineTastesEval[i//2].get_attribute('style').split("left:")[1].replace("%;","").replace(" ","")) / 100 * (1/0.85) * 5, 1)
                    elif wineTastesHeader[i].text == "Smooth":
                        smoothness = round(float(wineTastesEval[i//2].get_attribute('style').split("left:")[1].replace("%;","").replace(" ","")) / 100 * (1/0.85) * 5, 1)
                    elif wineTastesHeader[i].text == "Dry":
                        sweetness = round(float(wineTastesEval[i//2].get_attribute('style').split("left:")[1].replace("%;","").replace(" ","")) / 100 * (1/0.85) * 5, 1)
                    elif wineTastesHeader[i].text == "Soft":
                        softness = round(float(wineTastesEval[i//2].get_attribute('style').split("left:")[1].replace("%;","").replace(" ","")) / 100 * (1/0.85) * 5, 1)
                winePairings = browser.find_elements(by=By.CSS_SELECTOR, value="a._3qc2M.foodPairing__imageContainer--2CtYR.foodPairing__unlinkable--2wTuA")
                foodPairings = []
                for winePair in winePairings:
                    divs = winePair.find_elements(by=By.CSS_SELECTOR, value="div")
                    for i in range(1, len(divs),2):
                        foodPairings.append(divs[i].text)
                wineJson = {
                    "wineID" : index,
                    "name" : wineName,
                    "tags" : tags,
                    "images" : [AWS_IMAGE_SERVER_URL + "wines/" + wineImageName],
                    "lightness" : lightness,
                    "smoothness": smoothness,
                    "sweetness" : sweetness,
                    "softness" : softness,
                    "abv" : abv,
                    "price" : price,
                    "region" : region,
                    "bottleClosure" : bottleClosure,
                    "grape" : grapes,
                    "winery" : winery,
                    "description" : "",
                    "foodPairings" : foodPairings,
                    "views" : 0,
                    "likes" : 0,
                    "isDeleted": False,
                    "createdAt" : datetime.now().astimezone(KST).strftime("%Y-%m-%d %H:%M"),
                    "lastUpdateAt" : datetime.now().astimezone(KST).strftime("%Y-%m-%d %H:%M")
                }
                print(wineJson)
                result.append(wineJson)
                count+=1
                index+=1
            else:
                print(line, "url fetch failed")
                time.sleep(3)
        urlFile.close()
        print(result)
        with open(jsonFilenames[num], 'w') as f:
            json.dump(result, f, indent=4)
        time.sleep(5)
    print("crawling finished")
            # print(winery, grapes, region, wineStyle, abv, allergens)
            # print(rating, winery, wine, tags,price)
