import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import tldextract
import json
from selenium.common.exceptions import NoSuchElementException
import plotly.express as px
from streamlit_tags import st_tags
from selenium.webdriver.chrome.options import Options
import os
import sqlite3

# Specify User Agent
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3538.102 Safari/537.36 Edge/18.19582"
}

def displayScraperResult():
    st.title(':bar_chart: Analysis Visualizer')
    df = pd.read_csv('AdScraperResult.csv')

    keywords = df['Keyword'].unique().tolist()
    keyword_selection = st.multiselect('Keyword:', keywords, default=keywords)
    if not keyword_selection:
        st.error("Please select at least one keyword to display the dataframe.")
    mask = df['Keyword'].isin(keyword_selection)
    number_of_result = df[mask].shape[0]
    st.markdown(f'*Available rows: {number_of_result}*')
    st.dataframe(df[mask])

    groupedKeywordPercentage_df = generateKeywordAdPercentage(df)
    # remove rows with zero percentage
    groupedKeywordPercentage_df = groupedKeywordPercentage_df[groupedKeywordPercentage_df.Percentage != 0]

    # plot bar chart
    bar_chart = px.bar(
        groupedKeywordPercentage_df,
        x="Keyword",
        y="Percentage",
        text="Percentage",
        template="plotly_white",
        title="Keyword Ads Percentage(%)"
    )
    st.plotly_chart(bar_chart)

    test_df = df.groupby(by="Company", dropna=True)

    companyList = []
    companyCount = []
    for key, item in test_df:
        companyList.append(key)
        companyCount.append(len(test_df.get_group(key)))

    companyAppearance_df = pd.DataFrame({'Company': companyList, 'Appearance': companyCount}, columns=['Appearance'], index=companyList)
    st.bar_chart(companyAppearance_df)

    for keyword in keywords:
        keyword_df = df[df['Keyword'] == keyword]
        if keyword_df['Company'] is not None:
            st.write(keyword)
            new_df = pd.DataFrame({'Company': keyword_df['Company'].tolist(),
                                   'absolute-top': keyword_df['absolute-top'].tolist(),
                                   'top': keyword_df['top'].tolist(),
                                   'bottom': keyword_df['bottom'].tolist()},
                                  columns=["absolute-top", "top", "bottom"],
                                  index=keyword_df['Company'].tolist())
            st.bar_chart(new_df)

# Generate Keyword Ads Appearance Percentage
def generateKeywordAdPercentage(df):
    keywordAdPercentage = []
    for keyword in df['Keyword'].unique().tolist():
        if df[df['Keyword'] == keyword]['Keyword Ads Percentage(%)'].max() is None:
            keywordAdPercentage.append(0)
        else:
            keywordAdPercentage.append(df[df['Keyword'] == keyword]['Keyword Ads Percentage(%)'].max())

    groupedKeywordPercentage_df = pd.DataFrame(list(zip(df['Keyword'].unique().tolist(), keywordAdPercentage)), columns=['Keyword', 'Percentage'])
    groupedKeywordPercentage_df = groupedKeywordPercentage_df.sort_values(by=['Percentage'], ascending=False)
    return groupedKeywordPercentage_df
    
# Create a connection to the SQLite database
conn = sqlite3.connect('ad_scraper.db')
cursor = conn.cursor()

def adScraper(numberOfTimes, listOfKeywords):
    st.subheader('Progress:')
    my_bar = st.progress(0)
    resultDict = {}

    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(os.environ.get("CHROMEDRIVER_PATH"), options=chrome_options)
    driver.get("http://www.python.org")
    print(driver.title)
    timeout_value = 20
    # Create the WebDriver with the specified timeout
    driver = webdriver.Chrome(
        executable_path=os.environ.get("CHROMEDRIVER_PATH"),
        options=chrome_options,
        service_args=["--verbose"]
    )
    total_iterations = numberOfTimes * len(listOfKeywords)
    progress = 0
    for keyword in listOfKeywords:
        resultDict[keyword] = {}
        companyList = []
        numOfTopAds = 0
        numOfBottomAds = 0
        resultDict[keyword] = {}
        absolute_top = 0
        st.write(f"Scraping data for keyword: {keyword}")
# Initialize 'keys' as an empty list before the loop
        keys = []

        for _ in range(numberOfTimes):
            payload = {'q': keyword, 'gl': 'ca'}
            driver.get("https://www.google.ca/search?" + "&".join([f"{k}={v}" for k, v in payload.items()]))
            time.sleep(3)

            print('----------------Top Ads-------------------')
            topAds = driver.find_elements(By.CSS_SELECTOR, '#tvcap .uEierd')
            if topAds:
                if len(topAds) > 0:
                    numOfTopAds += 1
                absolute_top = 0
                for container in topAds:
                    try:
                        advertisementTitle = container.find_element(By.CSS_SELECTOR, '.CCgQ5.vCa9Yd.QfkTvb.N8QANc.MUxGbd.v0nnCb span').text
                    except NoSuchElementException:
                        advertisementTitle = 'N/A'

                    try:
                        company = container.find_element(By.CSS_SELECTOR, '.v5yQqb .x2VHCd.OSrXXb.ob9lvb').text
                        company = tldextract.extract(company).domain
                    except NoSuchElementException:
                        company = 'N/A'
                        company_domain = 'N/A'

                    if company not in companyList:
                        companyList.append(company)
                        if absolute_top == 0:
                            resultDict[keyword][company] = {'absolute-top': 1, 'top': 0, 'bottom': 0}
                        else:
                            resultDict[keyword][company] = {'absolute-top': 0, 'top': 1, 'bottom': 0}
                    else:
                        if absolute_top == 0:
                            resultDict[keyword][company]['absolute-top'] += 1
                        else:
                            resultDict[keyword][company]['top'] += 1

                    productDescription = container.find_element(By.CSS_SELECTOR, '.MUxGbd.yDYNvb.lyLwlc').text

                progress += 1  # Increment the progress for each iteration
                my_bar.progress(progress / total_iterations)

            time.sleep(3)
            print('------------------------------------------')
            print('----------------Bottom Ads-------------------')
            bottomAds = driver.find_elements(By.CSS_SELECTOR, '#bottomads .uEierd')
            if bottomAds:
                if len(bottomAds) > 0:
                    numOfBottomAds += 1
                for container in bottomAds:
                    try:
                        advertisementTitle = container.find_element(By.CSS_SELECTOR, '.CCgQ5.vCa9Yd.QfkTvb.MUxGbd.v0nnCb span').text
                    except NoSuchElementException:
                        advertisementTitle = 'N/A'

                    try:
                        company = container.find_element(By.CSS_SELECTOR, '.v5yQqb .x2VHCd.OSrXXb.ob9lvb').text
                        company = tldextract.extract(company).domain
                    except NoSuchElementException:
                        company = 'N/A'
                        company_domain = 'N/A'

                    if company not in companyList:
                        companyList.append(company)
                        resultDict[keyword][company] = {'absolute-top': 0, 'top': 0, 'bottom': 1}
                    else:
                        resultDict[keyword][company]['bottom'] += 1

                    productDescription = container.find_element(By.CSS_SELECTOR, '.MUxGbd.yDYNvb.lyLwlc').text

                    keys = list(resultDict[keyword].keys())
                    for name in ['bottom', 'top', 'absolute-top']:
                        keys.sort(key=lambda k: resultDict[keyword][k][name], reverse=True)

        resultDict[keyword]['top performers'] = keys
        resultDict[keyword]['total top ads'] = numOfTopAds
        resultDict[keyword]['total bottom ads'] = numOfBottomAds

    print(json.dumps(resultDict, indent=4))
    driver.quit()

    st.success('Google Ads Scraping completed successfully.')
    return resultDict

def jsonToDatabase(resultDict, listOfKeywords, numberOfTimes):
    for keyword in listOfKeywords:
        if (resultDict[keyword]["top performers"] != []):
            for company in resultDict[keyword]["top performers"]:
                if keyword in resultDict and company in resultDict[keyword]:
                    topPercentage = 0
                    bottomPercentage = 0
                    if resultDict[keyword]["total top ads"] != 0:
                        topPercentage = round((resultDict[keyword][company]["top"] + resultDict[keyword][company]["absolute-top"]) / resultDict[keyword]["total top ads"] * 100, 1)
                    if resultDict[keyword]["total bottom ads"] != 0:
                        bottomPercentage = round(resultDict[keyword][company]["bottom"] / resultDict[keyword]["total bottom ads"] * 100, 1)

                    # Insert data into the database
                    cursor.execute(
                        "INSERT INTO scraped_data (keyword, company, absolute_top, top, bottom, top_percentage, bottom_percentage, keyword_percentage) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (keyword, company, resultDict[keyword][company]["absolute-top"], resultDict[keyword][company]["top"], resultDict[keyword][company]["bottom"], topPercentage, bottomPercentage, round((resultDict[keyword]["total top ads"] + resultDict[keyword]["total bottom ads"]) / (numberOfTimes * 2) * 100, 1))
                    )

    # Commit changes and close the connection
    conn.commit()
                    resultList.append([
                        keyword,
                        company,
                        resultDict[keyword][company]["absolute-top"],
                        resultDict[keyword][company]["top"],
                        resultDict[keyword][company]["bottom"],
                        topPercentage,
                        bottomPercentage,
                        round((resultDict[keyword]["total top ads"] + resultDict[keyword]["total bottom ads"]) / (numberOfTimes * 2) * 100, 1),
                    ])
                else:
                    print(f"KeyError: Keyword '{keyword}' or Company '{company}' not found in resultDict.")
        else:
            resultList.append([keyword, None, 0, 0, 0, 0, 0, 0])

    df = pd.DataFrame(resultList, columns=["Keyword", "Company", "absolute-top", "top", "bottom", "top(%)", "bottom(%)", "Keyword Ads Percentage(%)"])
    return df

resultDict = adScraper(numberOfTimes, chosen_keywords)
jsonToDatabase(resultDict, chosen_keywords, numberOfTimes)
# Close the database connection
conn.close()


# Read the custom CSS file
st.markdown(
    """
    <style>
    body {
        background-color: black;
        color: white;
    }
    .header-image {
        max-width: 200px;
        margin-bottom: 20px;
    }
    .section-title {
        font-size: 24px;
        margin-bottom: 15px;
    }
    .section-subtitle {
        font-size: 18px;
        margin-bottom: 10px;
    }
    .app-footer {
        margin-top: 30px;
        text-align: center;
    }
    .dataframe {
        border: 1px solid white;
        border-collapse: collapse;
        margin-bottom: 20px;
    }
    .dataframe th {
        background-color: #555;
        padding: 8px;
        text-align: center;
    }
    .dataframe td {
        padding: 8px;
        text-align: left;
    }
    .keyword-visualizations {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
    }
    .keyword-visualization {
        width: 48%;
        margin-bottom: 20px;
    }
    .chart-title {
        font-size: 18px;
        margin-bottom: 10px;
    }
    .sidebar-widget {
        margin-bottom: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Add header image and titles
st.title(":male-detective: Google Ads Keyword Dashboard")

numberOfTimes = st.slider('How many times do you want this keyword scraping to be run?', 1, 100, 10)
listOfKeywords = ["nft", "crypto", "etf"]

col1, col2 = st.columns(2)

with col1:
    chosen_keywords = st_tags(
                label='Add Keywords here!',
                text='Press enter to add more',
                value=listOfKeywords,
                suggestions=['blockchain', 'web 3.0', 'insurance', 'loans'],
                maxtags=10,
                key="aljnf"
            )
with col2:
    st.caption('Current List of Keywords')
    st.write((chosen_keywords))

submitted = st.button("Submit")

if submitted:
    st.write('Google Ads Scraping for the following keywords:', str(chosen_keywords), ' for ', numberOfTimes, ' times.')

    resultDict = adScraper(numberOfTimes, chosen_keywords)
    rawOutput = jsonToDataFrame(resultDict, chosen_keywords, numberOfTimes)
    rawOutput.to_csv('AdScraperResult.csv', index=False)


    # Hide the input section when the "Submit" button is clicked
    st.empty()
    displayScraperResult()

# Footer and credits
st.markdown(
    """
    <div class="app-footer">
        Made with <3 by Kartik Chopra(https://kartik.vibin.in)
    </div>
    """,
    unsafe_allow_html=True
)
