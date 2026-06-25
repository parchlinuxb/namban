import sys
import os
import subprocess
import json
from pathlib import Path

class BaseToolBox:
    def __init__(self):
        self._subprocess_keeper: subprocess.Popen | None = None
        self.daemon_path = Path(__file__).parent / 'daemon.py'

    @property
    def _subprocess(self) -> subprocess.Popen:
        if self._subprocess_keeper:
            return self._subprocess_keeper
        if os.getuid() == 0:
            command = [sys.executable, str(self.daemon_path)]
        else:
            command = ['pkexec', sys.executable, str(self.daemon_path)]
        self._subprocess_keeper = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self._hello()
        return self._subprocess_keeper

    def _hello(self):
        while self._readline() != '$hello':
            pass
        self._write('&hi')


    def _readline(self):
        line = self._subprocess.stdout.readline()
        line = line.decode()
        return line.strip()

    def _write(self, mess:str):
        self._subprocess.stdin.write((mess+'\n').encode())
        self._subprocess.stdin.flush()

    def _write_arguments(self, **kws):
        js = json.dumps(kws)
        self._write(js)
        self._write('&end')

    def _read_result(self):
        message = None
        error = False
        while True:
            line = self._readline()
            if line == '$end':
                break
            if line == '$error':
                message = ''
                error = True
            if line == '$resp':
                message = ''
            elif message is not None:
                message += line + '\n'
        if error:
            return False, message
        if message:
            message = json.loads(message)
        return True, message

    def copy(self, source:str, destination:str) -> bool:
        self._write('&copy')
        self._write_arguments(source=source, dest=destination)
        result, error = self._read_result()
        if error:
            print(error)
        return result

    def remove(self, destination:str) -> bool:
        self._write('&remove')
        self._write_arguments(dest=destination)
        result, error = self._read_result()
        if error:
            print(error)
        return result

    def write(self, file:str, body:str) -> bool:
        self._write('&write')
        self._write_arguments(file=file, body=body)
        result, error = self._read_result()
        if error:
            print(error)
        return result

    def read(self, file:str) -> str:
        self._write('&read')
        self._write_arguments(file=file)
        success, result = self._read_result()
        if success:
            return result.get('body')

    def exists(self, path: str) -> bool:
        self._write('&exists')
        self._write_arguments(path=path)
        success, result = self._read_result()
        if success:
            return result.get('result', False)
        return False
    
    def mkdir(self, path: str) -> bool:
        """Create directory with parents (through privileged daemon)."""
        self._write('&mkdir')
        self._write_arguments(path=path)
        result, error = self._read_result()
        if error:
            print(error)
        return result
    
    def execute(self, command: list) -> bool:
        self._write('&execute')
        self._write_arguments(command=command)
        result, error = self._read_result()
        if error:
            print(error)
        return result
        self._write('&exists')
        self._write_arguments(path=path)
        success, result = self._read_result()
        if success:
            return result.get('result')

    def execute(self, command: list[str]):
        self._write('&execute')
        self._write_arguments(command=command)
        success, _ = self._read_result()
        return success

toolbox = BaseToolBox()