import streamlit as st
import smtplib
import ssl
from email.message import EmailMessage
import imaplib
import email
from langchain.llms import OpenAI
from langchain import PromptTemplate
from langchain.chains import LLMChain
from langchain.chains import SequentialChain
from langchain.chat_models import ChatOpenAI
from langchain import PromptTemplate,  LLMChain
import os
import requests
import json

# To access the .env file and extract the password from it
def main():
    st.title("User Information Form")
    slack_api_url = "https://slack.com/api/chat.postMessage"
    username = st.text_input("Enter your email:")
    app_password = st.text_input("Enter a key:", type="password")
    slack_token=st.text_input("Enter slack token:", type="password")
    slack_destination = st.text_input("Channel or user name:")
    openai_api = st.text_input("Enter your OpenAI API key: ", type="password")  # Hide the input as a password field
    # Submit button
    if st.button("Submit"):
        # https://www.systoolsgroup.com/imap/
        gmail_host= 'smtp.gmail.com'
        #set connection
        mail = imaplib.IMAP4_SSL(gmail_host)
        print('pass')
        # to login to your email account with your username and password
        mail.login(username, app_password)
        # we select the inbox mailbox
        mail.select("INBOX")
        llm = ChatOpenAI(openai_api_key=openai_api)
        def newsletters_resume(body):
                text=body[:4097]
                template = """
                        Write a concise summary of the following newsletter, without mentioning that it's a summary.
                        Return your response in paragraph.
                        ```{text}```
                        paragraph:
                        """

                prompt = PromptTemplate(template=template, input_variables=["text"])

                llm_chain = LLMChain(prompt=prompt, llm=llm)

                return llm_chain.run(text)
        # Read comning emails (coming TO your email adress), and that you didn't read previously:
        #_, selected_mails = mail.search(None, '(UNSEEN)', '(TO \"'+username+'\")')
        _, selected_mails = mail.search(None,None,  '(TO "' + username + '")', 'SUBJECT "newsletter*"')

        for num in selected_mails[0].split():
                
                # data at this point is byte data, we have to work on it to get the actual content we want
                _, data = mail.fetch(num , '(RFC822)')
                _, bytes_data = data[0]
                email_message = email.message_from_bytes(bytes_data)
                # email_message has the content we want from our emails

                #access data
                Subject = email_message["subject"]
                To = email_message["to"]
                From = email_message["from"]
                
                # all of these data are strings !!
                # but the message, is represented by a tree object
                # the walk message will take you to each part of it
                for part in email_message.walk():
                # if the message content is either plain text or html content (parts that we are interested in)
                   if part.get_content_type()=="text/plain" or part.get_content_type()=="text/html":
                        # then take the content as a string
                        message = part.get_payload(decode=True)
                        body = message.decode()

                        # Now I have all I need. I will transform the message
                        email_sender = username
                        email_subject = Subject
                        email_body = newsletters_resume(body)

                        # construct our email
                        em = EmailMessage()
                        em['From'] = From
                        em['To'] = email_sender
                        em['Subject'] = str(email_subject).replace("\n", "").replace("\r", "")
                        em.set_content(email_body)
                        payload = {
                        "channel": slack_destination,
                        "text": em.as_string()
                        }
                        # Headers with the Authorization token
                        headers = {
                        "Authorization": f"Bearer {slack_token}",
                        "Content-Type": "application/json"
                        }

                        # Send the message using the Slack API
                        response = requests.post(slack_api_url, headers=headers, data=json.dumps(payload))

                        # Check the response
                        if response.status_code == 200:
                           st.text(f"Message from {From} sent to slack channel successfully!")
                          
                        else:
                                st.text(f"Failed to send message. Status code: {response.status_code}")
                                st.text(f"Response: {response.text}")
                st.text("Finish")
      

if __name__ == '__main__':
    main()
