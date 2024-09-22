import requests 
import urllib3
import sqlite3
import pandas as pd
from bs4 import BeautifulSoup 
from datetime import datetime

Database_name = './NewRSG.db'

# 데이터베이스에 데이터를 저장하는 함수
def save_to_db(df, table_name):
    con = sqlite3.connect(Database_name)
    cursor = con.cursor()
    
    if table_name == "NaverNews":
        SQL = "INSERT INTO NaverNews(Subject,Link) VALUES(?, ?);"
    else:
        SQL = "INSERT INTO BoanNews(Subject,Date,Link) VALUES(?, ?, ?);"
    
    for row in df.itertuples():
        cursor.execute(SQL, row[1:])
    
    con.commit()
    con.close()

# 네이버 뉴스 헤드라인 크롤링 함수
def get_headline_Nnews():
    url = "https://news.naver.com/section/101"
    target_class = "sa_text"
    
    response = requests.get(url, verify=False)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    headlines = [
        (element.get_text().strip(), element.find('a')['href']) 
        for element in soup.find_all(class_=target_class) 
        if element.find('a') and 'href' in element.find('a').attrs
    ]
    
    if headlines:
        df = pd.DataFrame(headlines, columns=["Subject", "Link"])
        print(df)
        save_to_db(df, "NaverNews")
    else:
        print("헤드라인 뉴스 제목을 가져올 수 없습니다.")

# 보안 뉴스 헤드라인 크롤링 함수
def get_headline_Snews():
    urllib3.disable_warnings() 
    main_url = 'https://www.boannews.com'
    today = datetime.today().date()
    
    title_list, date_list, link_list = [], [], []
    break_flag = False
    
    for i in range(1, 11):
        news_page_url = f'{main_url}/media/t_list.asp?Page={i}&kind='
        response = requests.get(news_page_url, verify=False)
        soup = BeautifulSoup(response.text, "html.parser")
        news_items = soup.select('#news_area div.news_list')
        
        for news in news_items:
            news_date_text = news.find('span', {'class': 'news_writer'}).text.split("|")[-1].strip()
            news_date = datetime.strptime(news_date_text, "%Y년 %m월 %d일 %H:%M").date()
            
            if today == news_date:
                link = news.select_one('a')['href']
                title = news.select_one('a span').text.strip()
                title_list.append(title)
                date_list.append(news_date_text)
                link_list.append(main_url + link)
            else:
                break_flag = True
                break
                
        if break_flag:
            break
    
    df = pd.DataFrame({"Subject": title_list, "Date": date_list, "Link": link_list})
    if not df.empty:
        print(df)
        save_to_db(df, "BoanNews")
    else:
        print("보안 뉴스 제목을 가져올 수 없습니다.")

# 데이터베이스에서 기존 데이터를 삭제하는 함수
def delete_table_data(table_name):
    con = sqlite3.connect(Database_name)
    cursor = con.cursor()
    cursor.execute(f"DELETE FROM {table_name};")
    con.commit()
    con.close()

def main():
    delete_table_data("NaverNews")
    delete_table_data("BoanNews")
    
    get_headline_Nnews()
    get_headline_Snews()

if __name__ == "__main__":
    main()