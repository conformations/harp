import json
import smtplib

def account_info(filename):
  '''Loads account information from JSON-format file'''
  with open(filename) as file:
    obj = json.load(file)
    assert 'username' in obj
    assert 'password' in obj
    return obj['username'], obj['password']

def email(username, password, sender, recipient, subject, body):
  msg = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n" % (sender, recipient, subject))
  msg += body
  msg += "\r\n"

  server = smtplib.SMTP('smtp.gmail.com', 587)
  server.set_debuglevel(1)
  server.ehlo()
  server.starttls()
  server.login(username, password)
  server.sendmail(sender, recipient, msg)
  server.quit()
