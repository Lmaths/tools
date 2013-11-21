#!/usr/bin/python
# Filename: autopatch.py

### File Information ###
"""
Patch the files automatically based on the autopatch.xsd.

Usage: $shell autopatch.py
         Use the default baidu_patch.xml

       $shell autopatch.py path_to_patch.xml
         To provide a patch.xml, should firstly referenced to
         the XML schema autopatch.xsd
"""

__author__ = 'duanqizhi01@baidu.com (duanqz)'



### import block ###

import commands
import os.path
import shutil
import sys

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET



### Class definition ###

class AutoPatch:
    """
    Entry of the script.
    """

    def __init__(self):
        argLen = len(sys.argv)
        if argLen == 1:
            patchesDir = Config.PATCHES_DIR
            patchXML = Config.DEFAULT_REVISION_XML
        elif argLen == 2:
            patchesDir = Config.PATCHES_DIR
            patchXML = sys.argv[1]
        elif argLen >= 3:
            patchesDir = sys.argv[1]
            patchXML = sys.argv[2]

        AutoPatch.apply(patchesDir, patchXML)

    @staticmethod
    def apply(patchesDir, patchXML):
        Config.PATCHES_DIR = patchesDir
        AutoPatchXML().parse(patchXML)
        pass

# End of class Main

class Config:
    """
    Configuration.
    """
    DEBUG = False

    PROJECT_DIR = os.getcwd() + "/"
    SCRIPT_DIR = sys.path[0] + "/"

    # Default patch.xml to be parsed
    DEFAULT_REVISION_XML = PROJECT_DIR + "baidu_patch.xml"

    # Source and destination directory holding the file to be handled
    SOURCE_DIR = PROJECT_DIR + "baidu/smali/"
    TARGET_DIR = PROJECT_DIR

    # Patches directory
    PATCHES_DIR = PROJECT_DIR + "patches/"

    # Whether to revise OPTION feature, default to be True
    REVISE_OPTION = True

    @staticmethod
    def initConfigFrom(XMLDom):
        """
        Initialize configuration from XML document.
        """

        try:
            config = XMLDom.find('config')
        except AttributeError:
            Log.i("Using default configuration")
            return

        sourceDir = Config.findAttrib(config, 'source_dir')
        if sourceDir != None:
            Config.SOURCE_DIR = sourceDir.text

        targetDir = Config.findAttrib(config, 'target_dir')
        if targetDir != None:
            Config.SOURCE_DIR = targetDir.text

        patchesDir = Config.findAttrib(config, 'patches_dir')
        if patchesDir != None:
            Config.PATCHES_DIR = patchesDir.text

        reviseOption = Config.findAttrib(config, 'revise_option')
        if reviseOption != None:
            Config.REVISE_OPTION = reviseOption.text

    @staticmethod
    def findAttrib(config, attribKey):
        try:
            return config.find(attribKey)
        except AttributeError:
            return None

    @staticmethod
    def toString():
        Log.i("--------------------------------------------")
        Log.i("Source_Dir\t=\t" + Config.SOURCE_DIR)
        Log.i("Target_Dir\t=\t" + Config.TARGET_DIR)
        Log.i("Patches_Dir\t=\t" + Config.PATCHES_DIR)
        Log.i("--------------------------------------------")

# End of class Config


class AutoPatchXML:
    """
    Represent the tree of an input XML.
    """

    def __init__(self):
        pass

    def parse(self, autoPatchXML):
        """
        Parse the XML with the schema defined in autopatch.xsd
        """

        XMLDom = ET.parse(autoPatchXML)
        Config.initConfigFrom(XMLDom)
        #Config.toString()

        for revise in XMLDom.findall('revise'):
            self.handleRevise(revise)

        self.showRejectFilesIfNeeded()

    def handleRevise(self, revise):
        require = revise.attrib['require']
        description = revise.attrib['description']

        if require == "MUST":
            Log.i("\n>>> [M] " + description)
            for target in revise:
                ActionExecutor(target).run()
 
        elif Config.REVISE_OPTION and require == "OPTION":
            Log.i("\n>>> [O] " + description)
            for target in revise:
                ActionExecutor(target).run()

    def showRejectFilesIfNeeded(self):
        rejectFiles = os.listdir(Config.PROJECT_DIR + "out/reject")
        if len(rejectFiles) > 0:
            rejectDir = Config.PROJECT_DIR + "out/reject/"
            Log.i("\nThere are reject files in " +  rejectDir + ", please check it out!")
            Log.i(rejectFiles)
            Log.i("\n")
# End of class Revision


class ActionExecutor:
    """
    Execute action to target.
    """

    ADD = "ADD"
    MERGE = "MERGE"
    REPLACE = "REPLACE"

    def __init__(self, target):
        """
        @args target: the revise target.
        """

        self.action = target.attrib['action']

        # Compose the source and destination file path
        path = target.attrib['path']
        self.mSrc = Config.SOURCE_DIR + path
        self.mDst = Config.TARGET_DIR + path

        self.executeNodes = target.getchildren()

    def run(self):
        if self.action == ActionExecutor.ADD:
            self.add()
        elif self.action == ActionExecutor.REPLACE:
            self.replace()
        elif self.action == ActionExecutor.MERGE:
            self.merge()

    def add(self):
        if not self.checkExists(self.mSrc) :
            return

        Log.i(" ADD  " + self.mDst)
        shutil.copy(self.formatPath(self.mSrc), \
                    self.formatPath(self.mDst))

    def replace(self):
        if not self.checkExists(self.mSrc) or \
           not self.checkExists(self.mDst) :
            return

        Log.i(" REPLACE  " + self.mDst)
        shutil.copy(self.formatPath(self.mSrc), \
                    self.formatPath(self.mDst))

    def merge(self):
        if not self.checkExists(self.mDst) :
            return

        Log.i(" MERGE  " + self.mDst)
        self.executeRoutineIfNeeded()

    def executeRoutineIfNeeded(self):
        # If execute node exists in tree, execute the command
        if len(self.executeNodes) > 0:
            # The first child is element <execute>
            execute = self.executeNodes[0]

            script = execute.attrib['script']
            routine = Config.SCRIPT_DIR + execute.attrib['routine']

            # Compose the command string with parameters
            paramList = [routine, self.mDst]
            for param in execute:
                paramList.append(Config.PATCHES_DIR + param.text)

            # Execute the command
            command = " ".join(paramList)
            RoutineExecutor(script).run(command)


    @staticmethod
    def checkExists(target):
        if os.path.exists(ActionExecutor.formatPath(target)):
            return True

        Log.w("Target not exists. " + target)
        return False

    @staticmethod
    def formatPath(path):
        return path.replace("\\", "")

# End of class Target


class RoutineExecutor:
    """
    RoutineExecutor to execute the command.
    """

    def __init__(self, script):
        self.script = script
        # TODO Create different RoutineExecutor by script. [shell|python] etc.

    def run(self, command):
        result = commands.getstatusoutput(command)
        if result[0] == 0:
            Log.d("Execute Successfully [" + command + "]")
            pass
        else:
            Log.w(result[1])

# End of class RoutineExecutor


class Log:

    @staticmethod
    def d(message):
        if Config.DEBUG:
            print " " + message

    @staticmethod
    def i(message):
        print message

    @staticmethod
    def w(message):
        print "Waring: " + message

    @staticmethod
    def e(message):
        print "Error: " + message

# End of class Log

if __name__ == "__main__":
    AutoPatch()
