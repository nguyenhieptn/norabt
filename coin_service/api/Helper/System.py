import os
import sys

class System:
    @staticmethod
    def isRunning(command):
        cmd = f"ps -aux | grep  \"{command}\" | grep -v grep"
        result = os.popen(cmd).read()
        return not result == ""

    @staticmethod
    def isComplied():
        return getattr(sys, 'frozen', False)