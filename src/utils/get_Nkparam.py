from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import time


# Target URL
url = "https://www.naukri.com/node-dot-js-jobs-in-pune?k=node.js&l=pune&experience=3"


# Configure Chrome options
options = Options()
# options.add_argument("--headless")  # Enable if you want to run without UI

# Enable performance logging to capture network requests
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})


# Initialize WebDriver
driver = webdriver.Chrome(options=options)


def clear_session(driver):
    """
    Clears browser session data to force generation of a fresh nkparam.
    """
    # Clear cookies
    driver.delete_all_cookies()

    # Clear local storage and session storage
    driver.execute_script("window.localStorage.clear();")
    driver.execute_script("window.sessionStorage.clear();")


try:
    while True:
        print("\nStarting new cycle...\n")

        # Load the page
        driver.get(url)

        # Wait for network requests to complete
        time.sleep(5)

        # Capture browser performance logs
        logs = driver.get_log("performance")
        nkparam = None

        # Iterate through logs to find nkparam in request headers
        for entry in logs:
            log = json.loads(entry["message"])["message"]

            if log["method"] == "Network.requestWillBeSent":
                request = log["params"]["request"]
                headers = request.get("headers", {})

                if "nkparam" in headers:
                    nkparam = headers["nkparam"]

                    # Store nkparam in file
                    with open("nkPool.txt", "a", encoding="utf-8") as f:
                        f.write(nkparam + "\n")

                    print("nkparam captured and stored")
                    break

        if not nkparam:
            print("nkparam not found in this cycle")

        # Clear session to force new token generation in next iteration
        clear_session(driver)

        # Small delay to avoid rapid requests
        time.sleep(2)

except KeyboardInterrupt:
    print("Process stopped by user")

finally:
    driver.quit()