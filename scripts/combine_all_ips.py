import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as exp
from selenium.webdriver.support.ui import WebDriverWait

def whitelist_ips(url, username, password, ips):
    
    # Set up Chrome options
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")    
    # specify the path to chromedriver.exe
    chrome_driver_path = "/home/zhoub/Desktop/whitelist/chromedriver-linux64-124/chromedriver"
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        driverWait = WebDriverWait(driver, 20).until(exp.presence_of_element_located((By.XPATH, "/html/body/div/form/div[1]/input")))

        userName = driver.find_element(by=By.XPATH, value="/html/body/div/form/div[1]/input")
        password_elem = driver.find_element(by=By.XPATH, value="/html/body/div/form/div[2]/input")

        userName.send_keys(username)
        password_elem.send_keys(password)

        driver.find_element(by=By.XPATH, value='/html/body/div/form/button').click()

        driverWait = WebDriverWait(driver, 20).until(exp.presence_of_element_located((By.ID, "ipaddress")))

        print("Entering IP address one by one")
        for ip in ips:
            ipadd = driver.find_element(by=By.ID, value="ipaddress")
            submit = driver.find_element(by=By.ID, value="submit")

            ipadd.clear()
            ipadd.send_keys(ip)
            submit.click()

            print(ip, "is added")
            time.sleep(2)
    except:
        pass
    finally:
        print("All IPs in the list have been whitelisted")
        driver.quit()

# For HP Smart project on QAMA automation testing team
whitelist_ips("https://devsecgrp.cso-hp.com/devsecgrp", "belinda.zhou@hp.com", "N/A", ["192.56.42.1", "192.56.42.2", "192.56.42.3", "192.56.42.4", "192.56.42.5", "98.176.241.32", "98.153.103.66", "192.56.99.3", "15.1.225.77", "136.226.66.251"])

# For HPX project on QAMA automation testing team
whitelist_ips("https://ip-whitelist.hponecloud.com/devsecgrp", "belinda.zhou@hp.com", "N/A", ["192.56.42.1", "192.56.42.2", "192.56.42.3", "192.56.42.4", "192.56.42.5", "98.176.241.32", "98.153.103.66", "192.56.99.3", "15.1.225.77", "136.226.66.251"])

# For MobileFax server on HP Smart project
whitelist_ips("https://devsecgrp.cso-hp.com/devsecgrp", "belinda.zhou@hp.com", "N/A", ["3.239.80.191", "3.219.170.59", "54.91.56.196", "3.86.3.2", "35.175.125.198", "54.198.43.114", "3.228.10.32", "50.19.51.132", "136.226.66.251"])

# For MobileFax server on HPX project
whitelist_ips("https://ip-whitelist.hponecloud.com/devsecgrp", "belinda.zhou@hp.com", "N/A", ["3.239.80.191", "3.219.170.59", "54.91.56.196", "3.86.3.2", "35.175.125.198", "54.198.43.114", "3.228.10.32", "50.19.51.132", "136.226.66.251"])

# For HP Smart project on iOS developer team
whitelist_ips("https://devsecgrp.cso-hp.com/devsecgrp", "belinda.zhou@hp.com", "N/A", ["83.142.235.16", "193.33.38.56", "193.33.39.56", "37.201.6.78", "62.80.169.226", "82.193.100.201", "92.244.126.223", "31.43.99.104", "178.150.254.95", "78.27.173.15", "78.27.134.138", "194.31.236.110", "46.219.235.252", "82.193.114.191", "37.57.219.202", "176.37.43.189", "178.54.63.20", "176.37.164.87", "176.37.204.54", "178.158.227.45", "66.183.228.79", "89.64.35.86", "46.219.211.219", "176.36.106.134", "23.241.224.127"])

# For HPX project on iOS developer team
whitelist_ips("https://ip-whitelist.hponecloud.com/devsecgrp", "belinda.zhou@hp.com", "N/A", ["83.142.235.16", "193.33.38.56", "193.33.39.56", "37.201.6.78", "62.80.169.226", "82.193.100.201", "92.244.126.223", "31.43.99.104", "178.150.254.95", "78.27.173.15", "78.27.134.138", "194.31.236.110", "46.219.235.252", "82.193.114.191", "37.57.219.202", "176.37.43.189", "178.54.63.20", "176.37.164.87", "176.37.204.54", "178.158.227.45", "66.183.228.79", "89.64.35.86", "46.219.211.219", "176.36.106.134", "23.241.224.127"])


