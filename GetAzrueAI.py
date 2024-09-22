import os
import openai
import pandas as pd
import time
import sqlite3
import bs4
import urllib3
import json
import re
import smtplib

from urllib3.exceptions import InsecureRequestWarning
from dotenv import load_dotenv, find_dotenv
from pandas import Series, DataFrame

from langchain import hub
from langchain_openai import AzureOpenAI  
from langchain_community.document_loaders import WebBaseLoader
from langchain.prompts import PromptTemplate
from langchain_chroma import Chroma
from langchain.chains import LLMChain

from email.utils import make_msgid
from datetime import datetime
from pathlib import Path
from email import policy
from email.encoders import encode_base64
from email.header import Header
from email.parser import BytesParser
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText


# SSL 경고 무시
urllib3.disable_warnings(InsecureRequestWarning)
os.environ["USER_AGENT"] =  os.getenv("USER_AGENT", "Mozilla/5.0")

Database_name = './NewRSG.db'

load_dotenv(find_dotenv())
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") 
api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = os.getenv("AZURE_API_VERSION")
deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME")
model_name = os.getenv("AZURE_MODEL_NAME")


def AzureOpenAIProcExt(text):

    # Prompt as a string
    prompt = f"""
        Given the following news article, extract the following information in JSON format:

        뉴스_제목: The title of the news article.
        뉴스_요약: 3 points summary of the news article.
        뉴스_키워드: 5 Keywords related to the news article.

        
        Please return the output in the following JSON format:
        {{
            "뉴스_제목": "...",
            "뉴스_요약": "...",
            "뉴스_키워드": "...",
        }}
        News Article:
        {text}
    """

    # Initialize the LLM (Azure OpenAI)
    llm = AzureOpenAI(
        azure_endpoint=endpoint,
        openai_api_key=api_key,
        openai_api_version=api_version,
        temperature=0,  # Adjust as needed
        max_tokens=2000,   # Set to allow more tokens
        deployment_name=deployment_name,
        model_name=model_name
    )

    # Execute the prompt using invoke method
    #print(prompt)

    raw_response = llm.invoke(prompt)

    # Debug: print the raw response

    #print("Raw response:", raw_response)

    # Check if the response is valid and not empty
    if not raw_response:
        print("Error: Received empty response from the model.")
        return None

    try:
        # Assuming the model returns a text that we need to process
        response_lines = raw_response.split("\n")
        
        print(response_lines)
        news_title = re.findall(r"'뉴스_제목': '(.+?)'", raw_response)[0] if re.findall(r"'뉴스_제목': '(.+?)'", raw_response) else ''
        news_summary = re.findall(r"'뉴스_요약': '(.+?)'", raw_response)[0] if re.findall(r"'뉴스_요약': '(.+?)'", raw_response) else ''
        news_keyword = re.findall(r"'뉴스_키워드': '(.+?)'", raw_response)[0] if re.findall(r"'뉴스_키워드': '(.+?)'", raw_response) else ''

        html_output = f"""
        <html>
        <head><title>뉴스 정보</title></head>
        <body>
            <h3>뉴스 제목</h3>
            <p>{news_title}</p>

            <h3>뉴스 요약</h3>
            <p>{news_summary}</p>

            <h3>뉴스 키워드</h3>
            <p>{news_keyword}</p>
        </body>
        </html>
        """
        return html_output
    
    except Exception as e:
        print(f"An error occurred while processing the response: {e}")
        return None

def GetLinkContent(url):

    loader = WebBaseLoader(
        web_paths=[url],
        bs_kwargs=dict(
            parse_only=bs4.SoupStrainer(
                #class_=["dic_area"]
                class_=["newsct_body"]
            )
        ),
        requests_kwargs={"headers": {"User-Agent": os.getenv("USER_AGENT", "Mozilla/5.0")}, "verify": False}  
    )
    docs = loader.load()
    time.sleep(1)
    return docs[0].page_content.strip()

def Send_email(Content):

    server = '172.212.95.146'
    port = 25
    mailfrom = 'quimlee@seulweb.info'
    rcptto = 'b001@seulweb.info'

    message = Content
    msgid = "Message-ID: " + make_msgid()
    smtp = None
    try:

        msg = MIMEMultipart("alternative")
        msg['From'] = mailfrom
        msg['To'] = rcptto
        msg['Subject'] = "NaverFin_AI_LLM"
        #body = MIMEText(message, 'html', _charset='uft-8') 
        body = MIMEText(message,'html',_charset='utf-8')
        msg.add_header('Content-Transfer-Encoding', 'base64')
        msg.attach(body)
        
        #print(msg);
        
        smtp = smtplib.SMTP(server, port)
        smtp.sendmail(mailfrom, rcptto, msg.as_string())
        
    except Exception as e:
        print('Failed to send mail.')
        print(str(e))
    else:
        print('Succeeded to send mail.')
    finally:
        if smtp != None:
            smtp.close()

def main():
      
    con = sqlite3.connect(r"C:/DevP/Hackathon/NewRSG.db")
    df_Sql = pd.read_sql_query("SELECT * FROM NaverNews LIMIT 1", con) 
  
    df_Sql['content'] = df_Sql['Link'].apply(GetLinkContent)
    df_Sql.head()
    text = df_Sql['content'].iloc[0]
    #print(text)
    result = AzureOpenAIProcExt(text)
    Send_email(result)

if __name__ == "__main__":
    main()