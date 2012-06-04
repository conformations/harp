import json
import smtplib

def account_info(filename):
  '''Loads account information from JSON-format file'''
  with open(filename) as file:
    obj = json.load(file)
    assert 'username' in obj
    assert 'password' in obj
    return obj['username'], obj['password']

def send(username, password, msg):
  server = smtplib.SMTP('smtp.gmail.com', 587)
  server.set_debuglevel(1)
  server.ehlo()
  server.starttls()
  server.login(username, password)
  server.sendmail(msg['From'], msg['To'], msg.as_string())
  server.quit()
