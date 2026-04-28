import os
import smtplib
import zipfile

from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from email import encoders


class Gather_Screenshots:
    
    subject = "Screenshots from Android Devices *Automated Email-DO NOT REPLY*"
    text = "Attachment should contain screenshots for Android Devices. For queries contact nachiket.wattamwarm@hp.com" 
    recipients = ['daixuefeng@beyondsoft.com','nachiket.wattamwarm@hp.com']

    def list_of_recipients(self):
        return self.recipients

    def zip_screenshots(self,path,zipfile):
        for root,_,files in os.walk(path):
            for file in files:
                zipfile.write(os.path.join(root,file))
    
    def send_message(self,attachment=None):
        # build message contents
        msg = MIMEMultipart()
        msg['Subject'] = str(self.subject)
        msg.attach(MIMEText(self.text))
        zippedAttachments = MIMEBase('application', 'zip')
        zf = open(attachment,'rb')
        zippedAttachments.set_payload(zf.read())
        encoders.encode_base64(zippedAttachments)
        file_name = os.path.basename(attachment)
        zippedAttachments.add_header('Content-Disposition', 'attachment',
               filename=file_name)
        msg.attach(zippedAttachments)
        return str(msg)

if __name__ == "__main__":
    Gather_Screenshots = Gather_Screenshots()
    Gather_Screenshots.zip_screenshots('/work/exec/ss_gather',zipfile.ZipFile('/work/exec/ss_gather/Screenshots.zip','w',zipfile.ZIP_DEFLATED))
    smtp = smtplib.SMTP('localhost', port=25)
    smtp.sendmail(to_addrs=Gather_Screenshots.list_of_recipients(),msg=Gather_Screenshots.send_message(attachment='/work/exec/ss_gather/Screenshots.zip'),from_addr="nachiket.wattamwarm@hp.com")