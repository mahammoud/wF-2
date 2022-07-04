from functools import reduce
import json
import random
import tempfile
import time
from bs4 import BeautifulSoup as bs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as webdriver
import pandas as pa
import os
import datetime
from selenium.webdriver.common.keys import Keys
import pathlib
#create customized web driver in order to add preferences and configure the download destination
class ChromeWithPrefs(webdriver.Chrome):
    def __init__(self, *args, options=None, **kwargs):
        if options:
            self._handle_prefs(options)

        super().__init__(*args, options=options, **kwargs)

        # remove the user_data_dir when quitting
        self.keep_user_data_dir = False

    @staticmethod
    def _handle_prefs(options):
        if prefs := options.experimental_options.get("prefs"):
            # turn a (dotted key, value) into a proper nested dict
            def undot_key(key, value):
                if "." in key:
                    key, rest = key.split(".", 1)
                    value = undot_key(rest, value)
                return {key: value}

            # undot prefs dict keys
            undot_prefs = reduce(
                lambda d1, d2: {**d1, **d2},  # merge dicts
                (undot_key(key, value) for key, value in prefs.items()),
            )

            # create an user_data_dir and add its path to the options
            user_data_dir = os.path.normpath(tempfile.mkdtemp())
            options.add_argument(f"--user-data-dir={user_data_dir}")

            # create the preferences json file in its default directory
            default_dir = os.path.join(user_data_dir, "Default")
            os.mkdir(default_dir)

            prefs_file = os.path.join(default_dir, "Preferences")
            with open(prefs_file, encoding="latin1", mode="w") as f:
                json.dump(undot_prefs, f)

            # pylint: disable=protected-access
            # remove the experimental_options to avoid an error
            del options._experimental_options["prefs"]
#helper function declaration
cwd = pathlib.Path(__file__).parent.resolve()
owd = os.path.join(cwd,"Output")
#create an undetectable driver with all required protections to bypass cloudflare, this process might take 30s
def setup_driver():
    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.default_content_setting_values.notifications" : 2,
    "download.default_directory" : owd}
    prefs["profile.default_content_settings"] = {"images": 2}
    prefs["profile.managed_default_content_settings"] = {"images": 2}
    chrome_options.add_experimental_option("prefs",prefs)
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--test-type")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.binary_location = "C:\Program Files\Google\Chrome Beta\Application\chrome.exe"
    driver = ChromeWithPrefs(browser_executable_path=chromedriverpath,options=chrome_options,use_subprocess=True)
    driver.maximize_window()
    return driver
#helper function to download file from url
def download_file(url, file_path,datarow):
    from requests import get
    reply = get(url, stream=True)
    with open(file_path, 'wb') as file:
        for chunk in reply.iter_content(chunk_size=1024): 
            if chunk:
                file.write(chunk)
        datarow.insert(0,os.path.getctime(file_path))
        #helper function to return a random int between 2 bounds
def random_int(low, high):
    return int(random.random()*(high-low) + low)
#main function, scrapes the video boxes
def scrape_video(video_box,datarows):
    video_link_box = video_box.find_element(By.TAG_NAME,"a")
    video_url= video_link_box.get_attribute('href')
    url = video_url
    title_raw = url.split("/")[4].split('-')
    id = title_raw[-1]
    del title_raw[-1]
    title = ' '.join(title_raw)
    driver.execute_script("window.open('');")
    p = driver.current_window_handle
    #get first child window
    chwd = driver.window_handles
    for w in chwd:
    #switch focus to child window
        if(w!=p):
            driver.switch_to.window(w)
            driver.get(video_url)
            iframe = WebDriverWait(driver,10).until(EC.presence_of_element_located((By.CSS_SELECTOR,".PhotoZoom_iframe__LeuQM")))
            driver.switch_to.frame(iframe)
            WebDriverWait(driver,10).until(EC.presence_of_element_located((By.CSS_SELECTOR,".play.rounded-box.state-playing"))).click()
            driver.switch_to.default_content()
    author_div = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME,"Text_color-greyPlus14A4A4A__VMiOO")))
    author = author_div.text
    tag_list_container = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR,".SpacingGroup_default__vvo8W.SpacingGroup_overflow__aHdxY")))
    tag_list_raw = tag_list_container.find_elements(By.XPATH,".//a") 
    tag_list = []
    for raw_tag in tag_list_raw:
        tag_list.append(raw_tag.text)
    info_button =  WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR,".spacing_margin-right-8__NbSjT.spacing_padding-right-20__Q3ufi.spacing_padding-left-20__GcW24.Button_hideTextMobile__2CewE")))
    driver.implicitly_wait(1)
    info_button.click()
    got_list_details = False
    while not got_list_details:
        try:
            list_of_details = WebDriverWait(driver,2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,".Text_text___5YSC.Text_size-p16__Obkrs.Text_weight-medium__bwK0x")))
            got_list_details = True
        except WebDriverException as e:
            info_button.click()
    dimensions = list_of_details[0].text
    aspect_ratio = list_of_details[1].text
    duration = list_of_details[2].text
    fps = list_of_details[3].text
    if aspect_ratio == "9:16":
        orientation = "vertical"
    else:
        orientation ="horizontal"
    datarow = []
    datarow.append(url)
    datarow.append(title)
    datarow.append(id)
    datarow.append(duration)
    datarow.append(dimensions)
    datarow.append(aspect_ratio)
    datarow.append(fps)
    datarow.append(orientation)
    datarow.append(author)
    datarow.append(tag_list)
    datarows.append(datarow)
    file_path = os.path.join(owd,title + '.mp4')
    download_file("https://www.pexels.com/video/"+ f"{id}/"+"download",file_path, datarow)
    driver.find_element(By.CLASS_NAME,"Modal_close__ToR04").click()
    buttons = WebDriverWait(driver,10).until(EC.presence_of_all_elements_located((By.XPATH,'//*[@id="medium-download-size-selector-toggle-button"]')))
    for button in buttons:
        if button.location['x'] != 0:
            button.click()
    p = driver.current_window_handle
    #get first child window
    chwd = driver.window_handles
    for w in chwd:
    #switch focus to child window
        if(w!=p):
            driver.close()
            driver.switch_to.window(w)

scrape_indefinitely = False

keyword = input("Enter the keyword to scrape: ")

got_min = False
while not got_min:
    min_text = input("Enter the minimum amount to scrape: ")
    if min_text == "x":
        scrape_indefinitely = True
        min = None
        got_min = True
    else:
        try:
            min = int(min_text)
            got_min = True
        except Exception as e:
            print("Enter a valid number.")
got_max = False
while not got_max:
    max_text = input("Enter the maximum amount to scrape ")
    try:
        max = int(max_text)
        got_max =True
    except Exception as e:
        print("Enter a valid number.")

if scrape_indefinitely != True:
    n_to_scrape = random_int(min,max)

with open('settings.txt', 'r') as f:
        chromedriverpath = f.readline().replace('\n', '')
        max_threads = f.readline().replace('\n', '')

driver = setup_driver()
datarows = []
root_url = "https://www.pexels.com"
base_url = "https://www.pexels.com/search/videos/"
try:
    driver.get(base_url + keyword)
    video_box_container = driver.find_element(By.CSS_SELECTOR,"div[class='BreakpointGrid_grid__xedYm BreakpointGrid_grid-desktop__lrYdh']")
    video_boxes = video_box_container.find_elements(By.CSS_SELECTOR,".BreakpointGrid_item__erUQQ")
    driver.execute_script('videos = document.querySelectorAll("video"); for(video of videos) {video.pause()}')
    for i in range(n_to_scrape):
        #check if number of video boxes does not satisfy the desired amount of videos
        if i >= len(video_boxes):
            got_video_boxes = False
            while not got_video_boxes:
                try:
                    new_video_boxes = driver.find_element(By.CSS_SELECTOR,".BreakpointGrid_grid__xedYm.BreakpointGrid_grid-desktop__lrYdh").find_elements(By.CSS_SELECTOR,".BreakpointGrid_item__erUQQ") 
                    if not len(new_video_boxes) == len(video_boxes):
                        got_video_boxes = True
                        video_boxes = new_video_boxes
                    else: 
                        driver.execute_script("window.scrollBy(0,250)", "")
                        driver.implicitly_wait(2)
                        WebDriverWait(driver, 3).until_not(EC.presence_of_element_located((By.CLASS_NAME,"Loading_container__7S4ir")))
                except Exception as e:
                    print(e)
            driver.execute_script('videos = document.querySelectorAll("video"); for(video of videos) {video.pause()}')
        video_box = video_boxes[i]
        scrape_video(video_box,datarows)
    driver.close()
    driver.quit()
    for row in datarows:
        row.insert(0,keyword)
    datacolumns = ["search_tag","downloaded_date","url","title","id","duration","dimensions","aspect_ratio","fps","orientation","username","tags" ]
    dt_f = pa.DataFrame(data=datarows,columns=datacolumns)
    dest =owd
    isExist = os.path.exists(dest)
    csvpath = os.path.join(dest,str(int(round(datetime.datetime.timestamp(datetime.datetime.now())))))+'.csv'
    dt_f.to_csv(csvpath,index=False)
except Exception as e:
    print(e)