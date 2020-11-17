import os
import sys
import ast
import time
import smtplib
import email
import traceback
import argparse
import fnmatch
import logging
import papermill as pm
import shutil
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, g, current_app
from config import Config
from util.logging import setup_logging

setup_logging(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))  # important to do this first

# Notebook Scheduler
# ---------------------------------------
# This script helps with the automated processing of Jupyter Notebooks via
# papermill (https://github.com/nteract/papermill/)

snapshotDir = 'snapshots'

def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)
    # db.init_app(app)
    app.app_context().push()
    current_app.logger.debug('created the Flask App and pushed the App Context')

    return app
    

def findfiles(directory, pattern):
    # Lists all files in the specified directory that match the specified pattern
    for filename in os.listdir(directory):
        if fnmatch.fnmatch(filename.lower(), pattern):
            yield os.path.join(directory, filename)


def send_email(subject, filename, emailtype, errormessage):
    message = MIMEMultipart()
    message["Subject"] = subject
    sender_email = os.getenv('SENDER_EMAIL', '')

    if emailtype == "ERROR":
        recipients = os.getenv('ERROR_EMAIL_RECIPIENTS', '')
        message.attach(MIMEText("ERROR!!! \n" + errormessage, "plain"))
    else:        
        if (subject.split()[0] == 'Incorporation'): 
            recipients = os.getenv('INCORPORATION_FILINGS_DAILY_REPORT_RECIPIENTS', '')
        if (subject.split()[0] == 'COOP'): 
            recipients = os.getenv('COOP_FILINGS_MONTHLY_REPORT_RECIPIENTS', '')
        if (subject.split()[0] == 'Cooperative'): 
            recipients = os.getenv('COOPERATIVE_MONTHLY_REPORT_RECIPIENTS', '')
        # Add body to email
        message.attach(MIMEText("Please see attached.", "plain"))

        # Open file in binary mode
        with open(filename, "rb") as attachment:
            # Add file as application/octet-stream
            # Email client can usually download this automatically as attachment
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        # Encode file in ASCII characters to send by email
        encoders.encode_base64(part)

        # Add header as key/value pair to attachment part
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {filename}",
        )

        # Add attachment to message and convert message to string
        message.attach(part)

    server = smtplib.SMTP(os.getenv('EMAIL_SMTP', ''))
    email_list = []
    email_list = recipients.strip('][').split(', ')
    logging.info('Email recipients list is: {}'.format(email_list))
    server.sendmail(sender_email, email_list, message.as_string())
    logging.info('Email with subject \'' + subject + '\' has been sent successfully!')
    server.quit()


def processnotebooks(notebookdirectory):
    status = False
    now = datetime.now()
    date = datetime.strftime(datetime.now() - timedelta(1), '%Y-%m-%d')
    ext = ''
    if not os.getenv('ENVIRONMENT', '') == 'prod':
        ext = ' on ' + os.getenv('ENVIRONMENT', '')

    try:
        retry_times = int(os.getenv('RETRY_TIMES', '1'))
        retry_interval = int(os.getenv('RETRY_INTERVAL', '60'))
        if notebookdirectory == 'monthly':            
            days = ast.literal_eval(os.getenv('MONTH_REPORT_DATES', ''))  
    except Exception:
        logging.exception("Error processing notebook for {}.".format(notebookdirectory))
        # we failed all the attempts
        subject = "Jupyter Notebook Error Notification from LEAR for processing '" + notebookdirectory + "' on " + date + ext
        filename = ''
        send_email(subject, filename, "ERROR", traceback.format_exc())
        return status

    # For monthly tasks, we only run on the specified days
    # (or for others if no days are specified)
    if ( notebookdirectory == 'daily' or (notebookdirectory == 'monthly' and now.day in days)): 

        logging.info('Processing: ' + notebookdirectory)
        
        num_files = len(os.listdir(notebookdirectory))
        file_processed = 0
        last_month = datetime.now() - relativedelta(months=1)   

        # Each time a notebook is processed a snapshot is saved to a snapshot sub-directory
        # This checks the sub-directory exists and creates it if not
        snapshotdir = os.path.join(notebookdirectory, snapshotDir)
        if not os.path.isdir(snapshotdir):
            os.mkdir(snapshotdir)        

        for file in findfiles(notebookdirectory, '*.ipynb'): 
            file_processed += 1               
            for attempt in range(retry_times):
                try:
                    nb = os.path.basename(file)

                    pm.execute_notebook(
                        file,
                        os.path.join(snapshotdir, nb),
                        parameters=None
                    )

                    file_processing = nb.split('.ipynb')[0]

                    if ( file_processing == 'incorpfilings' ):    
                        subject = "Incorporation Filings Daily Stats " + date + ext
                        filename = 'incorporation_filings_daily_stats_' + date + '.csv'                    
                    elif ( file_processing == 'coopfilings' ):   
                        subject = "COOP Filings Monthly Stats for " + format(last_month, '%B %Y') + ext
                        filename = 'coop_filings_monthly_stats_for_' + format(last_month, '%B_%Y') + '.csv'
                    elif ( file_processing == 'cooperative' ):     
                        subject = "Cooperative Monthly Stats for " + format(last_month, '%B %Y') + ext
                        filename = 'cooperative_monthly_stats_for_' + format(last_month, '%B_%Y') + '.csv'    
                    
                    # send email to receivers and remove files/directories which we don't want to keep
                    send_email(subject, filename, "", "")
                    os.remove(filename)
                    
                    status = True                
                    break
                except Exception:
                    if attempt + 1 == retry_times:
                        # If any errors occur with the notebook processing they will be logged to the log file
                        logging.exception(
                            "Error processing notebook {0} at {1}/{2} try.".format(notebookdirectory, attempt + 1,
                                                                                retry_times))
                        # we failed all the attempts                    
                        subject = "Jupyter Notebook Error Notification from LEAR for processing '" \
                                + notebookdirectory + "' on " + date + ext
                        filename = ''
                        send_email(subject, filename, "ERROR", traceback.format_exc())
                    else:
                        # If any errors occur with the notebook processing they will be logged to the log file
                        logging.exception("Error processing notebook {0} at {1}/{2} try. "
                                        "Sleeping for {3} secs before next try".format(notebookdirectory, attempt + 1,
                                                                                        retry_times, retry_interval))
                        time.sleep(retry_interval)
                        continue
            if not status and num_files==file_processed:
                break

        shutil.rmtree(snapshotdir, ignore_errors=True)    
        return status


if __name__ == '__main__':
    start_time = datetime.utcnow()    

    # Check if the subfolders for notebooks exist, and create them if they don't    
    for directory in ['daily', 'monthly']:    
        if not os.path.isdir(directory):
            os.mkdir(directory)
        
        processnotebooks(directory)      
    
    end_time = datetime.utcnow()
    logging.info("job - jupyter notebook report completed in: {}".format(end_time - start_time))
    exit(0)
