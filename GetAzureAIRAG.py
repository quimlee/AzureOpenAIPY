import os
import openai
import bs4
import sqlite3
import pandas as pd
import smtplib
import pymsteams

from bs4 import BeautifulSoup 
from langchain import hub
from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import AzureOpenAI, AzureOpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv, find_dotenv


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


def load_environment_variables():
    """Load environment variables from the .env file."""
    load_dotenv(find_dotenv())
    return {
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
        "api_version": os.getenv("AZURE_API_VERSION"),
        "deployment_name": os.getenv("AZURE_DEPLOYMENT_NAME"),
        "model_name": os.getenv("AZURE_MODEL_NAME"),
        "embeddings_model_name": os.getenv("EMBEDDING_MODEL_NAME"),
        "embeddings_model_version": os.getenv("EMBEDDING_MODEL_VERSION"),
    }

def load_documents(url, class_name):
    """Load and parse documents from the web using WebBaseLoader."""
    loader = WebBaseLoader(
        web_paths=(url,),
        bs_kwargs=dict(
            parse_only=bs4.SoupStrainer(
                class_=[class_name]
            )
        ),
    )
    return loader.load()

def create_embeddings(env_vars):
    """Create Azure OpenAI embeddings."""
    return AzureOpenAIEmbeddings(
        model=env_vars['embeddings_model_name'],
        azure_endpoint=env_vars['endpoint'],
        openai_api_key=env_vars['api_key'],
        openai_api_version=env_vars['embeddings_model_version']
    )

def process_documents_and_run_rag_chain(env_vars, docs, question):
    """
    Process the documents, create the vectorstore, initialize the retriever, 
    and run the RAG chain to get the result for the given question.
    """
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)

    # Create embeddings
    embeddings = create_embeddings(env_vars)

    # Create a vectorstore from the document splits and embeddings
    vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)

    # Initialize retriever from vectorstore
    retriever = vectorstore.as_retriever()

    # Initialize LLM
    llm = AzureOpenAI(
        azure_endpoint=env_vars['endpoint'],
        openai_api_key=env_vars['api_key'],
        openai_api_version=env_vars['api_version'],
        deployment_name=env_vars['deployment_name'],
        model_name=env_vars['model_name'],
        temperature=0
    )

    # Build RAG chain
    prompt = hub.pull("rlm/rag-prompt")

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # Run the query and return the result
    result = rag_chain.invoke(question)
    return result

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
        msg['Subject'] = "NaverFin_AI_RAG"
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


def Send_Teans(Content):
    myTeamsMessage = pymsteams.connectorcard("WEBHOOK_URL")
    myTeamsMessage.text(Content)
    myTeamsMessage.send()
  

def main():
    # Load environment variables
    env_vars = load_environment_variables()
    
    con = sqlite3.connect(r"C:/DevP/Hackathon/NewRSG.db")
    nList: list[tuple] = con.execute("SELECT * FROM  NaverNews LIMIT 1 ").fetchall()
    for row in nList:
        url = f"{row[2]}"
    
    docs = load_documents(url, "newsct_body")

    # Define a question for RAG
    question = "Please summarize the article and answer in Korean."

    # Process documents and run the RAG chain
    result = process_documents_and_run_rag_chain(env_vars, docs, question)

    print(result)
    Send_email(result)

if __name__ == "__main__":
    main()