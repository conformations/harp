import json
import logging
import os.path
import smtplib

# Logging configuration
logging.basicConfig(filename = 'gmail.log',
                    format = '%(asctime)-15s %(message)s',
                    level = logging.INFO)

logger = logging.getLogger('gmail')

class SendError(Exception):
  def __init__(self, msg):
    self.msg = msg

  def __str__(self):
    return repr(self.msg)


class GMail:
  def __init__(self, conf):
    self.__username, self.__password = self.__account_info(conf)
    logger.info('Loaded configuration info from %s' % conf)


  def __account_info(self, filename):
    '''Loads GMail authentication information from filename. Throws IOError if
    filename could not be found, ValueError if the file's contents could not be
    decoded or lack required information.'''
    if not os.path.exists(filename):
      raise IOError('Configuration file `%s` does not exist' % filename)

    with open(filename) as file:
      try:
        obj = json.load(file)
      except:
        raise ValueError('Configuration file has invalid format, expected JSON')

    required_fields = ('username', 'password')
    for f in required_fields:
      if not f in obj:
        raise ValueError('Configuration file missing required field `%s`' % f)

    return obj['username'], obj['password']


  def send(self, msg):
    try:
      server = smtplib.SMTP(host = 'smtp.gmail.com', port = 587, timeout = 10)
      server.ehlo()
      server.starttls()
      server.login(self.__username, self.__password)
      server.sendmail(msg['From'], msg['To'], msg.as_string())
      server.quit()
    except:
      raise SendError()
