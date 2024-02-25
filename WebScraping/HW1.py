from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib.parse import urlparse
import time
import csv, json
from time import sleep
import requests
from random import randint
from html.parser import HTMLParser
USER_AGENT = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100Safari/537.36'}
SEARCHING_URL = 'http://www.bing.com/search?q='
QUERY_PATH = "https://bytes.usc.edu/cs572/s24-s-e-a-r-c-hhh/hw/HW1/100QueriesSet1.txt"
GOOGLE_RESPONSE_FILE = 'https://bytes.usc.edu/cs572/s24-s-e-a-r-c-hhh/hw/HW1/Google_Result1.json'

def cleanURLS(url):
        # Parse the URL
        parsed_url = urlparse(url)
        # Remove 'www' from the netloc
        netloc = parsed_url.netloc.replace('www.', '')
        # Remove ending slash from path
        path = parsed_url.path.rstrip('/')
        # Reconstruct the cleaned URL
        simplified_url = f"{netloc}{path}"
        return simplified_url
        
class SearchEngine:
    @staticmethod
    def search(query, sleep=True):
        if sleep: # Prevents loading too many pages too soon
            time.sleep(randint(7, 15))
        temp_url = '+'.join(query.split()) #for adding + between words for the query
        url = SEARCHING_URL + temp_url + '&count=30'
        try:
            soup = BeautifulSoup(requests.get(url, headers=USER_AGENT).text,"html.parser")
            new_results, parsedNewResults = SearchEngine.scrape_search_result(soup)
            return new_results, parsedNewResults
        except ConnectionError as ce:
            print(f"Connection error: {ce}")
            time.sleep(5)  # Add a delay before retrying
        
    
    @staticmethod
    def scrape_search_result(soup):
        raw_results = soup.find_all("li", {"class" : "b_algo"})
        results = []
        parsedResults = []
        for result in raw_results:
            link = result.find('a').get('href')
            if link:
                parsedLink = cleanURLS(link)
                if parsedLink not in results:
                    results.append(link)
                    parsedResults.append(parsedLink)
                    if len(results)==10:
                        break
        return results, parsedResults
    
def getGoogleResponse():
    googleResponse = requests.get(GOOGLE_RESPONSE_FILE)
    if googleResponse.status_code == 200:
        googleResponseJSON = googleResponse.json()
        for key, googleValue in googleResponseJSON.items():
            parsedUrls = []
            for url in googleValue:
                parsedUrls.append(cleanURLS(url))
            googleResponseJSON[key] = parsedUrls
        return googleResponseJSON
    else:
        return None

def readQueries():
    queryFile = requests.get(QUERY_PATH)
    if queryFile.status_code == 200:
        queries = queryFile.text.split("\n")
        queries = [query for query in queries if len(query) > 0]
    for index, q in enumerate(queries):
        queries[index] = q.strip()
    return queries

def constructBingResponse(queries):
    bingResponse = {}
    parsedBingResponse = {}
    for query in tqdm(queries):
        bingResults, parsedBingResults = SearchEngine.search(query)
        bingResponse[query] = bingResults
        parsedBingResponse[query] = parsedBingResults
        # print("\nQUERY:", query)
        # print("\nResults:", bingResults)
    return bingResponse, parsedBingResponse

def calculateOverlap(bingResponse, googleResponse):
    overlapValue = 0
    matchingCount=0
    # print("\nbingResponse", bingResponse)
    # print("\ngoogleResponse", googleResponse)
    for res in bingResponse:
        if res in googleResponse:
            matchingCount+=1

    overlapValue = (matchingCount/len(googleResponse))*100
    return matchingCount, overlapValue

def calculatePearson(bingResponse, googleResponse):
    correlationValue = 0
    rankDiffSum = 0
    n = 0
    for index, link in enumerate(bingResponse):
        if link in googleResponse:
            googlerank = googleResponse.index(link)
            rankDiffSum = rankDiffSum + ((googlerank - index)**2)
            n+=1
    
    if n==0:
        return 0
    elif n==1:
        if rankDiffSum == 0:
            return 1
        else:
            return 0
    else:
        correlationValue = 1 - ((6*rankDiffSum)/((n**2 - 1)*n))
        return correlationValue
    
#readQueries
queries = readQueries()
bingResponseJSON, parsedBingResponseJSON = constructBingResponse(queries)
googleResponseJSON = getGoogleResponse()

with open('hw1.json', 'w') as json_file:
    json.dump(bingResponseJSON, json_file, indent=4)

# with open("hw1.json", 'r') as json_file:
#     bingResponseJSON = json.load(json_file)

output_filename = 'hw1.csv'
with open(output_filename, 'w', newline='') as csvfile:
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(['Queries', 'Number of Overlapping Results', 'Percent Overlap', 'Spearman Coefficient'])
    i=0
    avgmatchingCount, avgoverlapValue, avgcorrelationValue = 0,0,0

    for key, bingValue in parsedBingResponseJSON.items():
        matchingCount, overlapValue = calculateOverlap(bingValue, googleResponseJSON[key])
        correlationValue = calculatePearson(bingValue, googleResponseJSON[key])
        # print(key, matchingCount, overlapValue, correlationValue)
        i+=1
        avgmatchingCount+=matchingCount
        avgoverlapValue+=overlapValue
        avgcorrelationValue+=correlationValue
        csv_writer.writerow(['Query '+str(i), matchingCount, overlapValue, correlationValue])

    csv_writer.writerow(['Averages', avgmatchingCount/i, avgoverlapValue/i, avgcorrelationValue/i])
    