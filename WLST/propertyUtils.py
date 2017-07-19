#Script to manipulate properties file.

from java.io import File
from java.io import FileInputStream
from java.util import Properties


#Load properties file in java.util.Properties
def loadProperties(filePath):

 inStream = FileInputStream(filePath)
 propFile = Properties()
 propFile.load(inStream)

 return propFile


#Displays all keys and values of properties file.
def dispayProperties(filePath):

 myPorpFile = loadProperties(filePath)
 keys = myPorpFile.keySet()
 for key in keys:
  print key+': '+myPorpFile.getProperty(key)

 return
