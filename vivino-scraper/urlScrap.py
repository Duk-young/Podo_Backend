from urllib.request import urlopen
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time


if __name__ == "__main__":

    wineDetailPages = []
    types = ['redWines.txt','whiteWines.txt','sparklingWines.txt','roseWines.txt','dessertWines.txt','fortifiedWines.txt']
    browser = webdriver.Chrome('./chromedriver.exe') # Chrome version 100

    browser.get('https://www.vivino.com/US-CA/en/')
    time.sleep(2)
    browser.find_element(by=By.CSS_SELECTOR, value='a.menuLink__menuLink--xBcq1.wineNavigationMenu__menuLink--UFFsM').click()
    time.sleep(1)
    browser.find_element_by_id('1').click()
    time.sleep(1)
    wineTypes = browser.find_elements(by=By.CSS_SELECTOR, value='div.pill__inner--2uty5')
    wineTypes[0].click() # unselect white wine type
    wineTypes[1].click()
    wineTypes[3].click()
    slider1 = browser.find_element(by=By.CSS_SELECTOR, value='div.rc-slider-handle.rc-slider-handle-1')
    ActionChains(browser).drag_and_drop_by_offset(slider1, -100,0).perform()
    time.sleep(2)
    slider2 = browser.find_element(by=By.CSS_SELECTOR, value='div.rc-slider-handle.rc-slider-handle-2')
    ActionChains(browser).drag_and_drop_by_offset(slider2, 250,0).perform()
    time.sleep(2)
    # browser.find_element_by_css_selector('class.rc-slider-handle,rc-slider-handle-2').send_keys()

    before_height = browser.execute_script("return window.scrollY")
    for i in range(3,6): # select all the wine types
        if i != 3:
            wineTypes[i-1].click()
            time.sleep(2)
            wineTypes[i].click()
            time.sleep(2)
        while True: # infinite scroll
            browser.find_element(by=By.CSS_SELECTOR, value="body").send_keys(Keys.END)
            time.sleep(2)
            after_height = browser.execute_script("return window.scrollY")
            if after_height == before_height:
                break 
            before_height = after_height
        items = browser.find_elements(by=By.CSS_SELECTOR, value='a._3qc2M.wineCard__cardLink--3F_uB')
        for item in items:
            wineDetailPages.append(item.get_attribute('href'))
        print("# of crawled wines:", len(wineDetailPages))
        with open(types[i], 'w') as f:
            f.write('\n'.join(wineDetailPages))
            f.close()
        wineDetailPages.clear()
        browser.find_element(by=By.CSS_SELECTOR, value="body").send_keys(Keys.HOME)
        time.sleep(10)
    #print(wineDetailPages)
