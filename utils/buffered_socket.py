import socket
import time
import struct
from utils.mcollections import FifoBuffer


class BufferedSocket:
    buffer_len = 2048

    def __init__(self, sock: socket.socket):
        self.__socket = sock
        self.__timeout = 0
        self.buffer = FifoBuffer(self.buffer_len)

    def settimeout(self, seconds: float):
        self.__timeout = seconds
        self.__socket.settimeout(seconds)

    def gettimeout(self):
        return self.__timeout

    def read(self, size: int):
        if self.buffer:
            return self.buffer.pop(size)
        else:
            return self.__socket.recv(size)

    @property
    def __max_read(self):
        return max(len(self.buffer), 1024)

    def read_line(self, limit: int):
        line = self.buffer.pop_line()
        if line and line[-1] == ord('\n'):
            del line[-2:]
            return line
        start = time.perf_counter()
        remaining = limit - len(line)
        while True:
            received = self.__socket.recv(min(self.__max_read, remaining))
            remaining -= len(received)
            index = received.find(b'\n')
            if index != -1:
                line.extend(received[:index])
                if line[-1] == ord('\r'):
                    line.pop()
                self.buffer.push(received[index+1:])
                self.__socket.settimeout(self.__timeout)
                return line
            self.buffer.push(received)
            if remaining <= 0:
                raise ValueError("Line not found within limit")
            elapsed = time.perf_counter() - start
            if elapsed > self.__timeout:
                raise TimeoutError()
            else:
                self.__socket.settimeout(self.__timeout - elapsed)

    def send(self, data):
        self.__socket.send(data)

    def fileno(self):
        return self.__socket.fileno()

    def close(self):
        self.__socket.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__socket.__exit__(exc_type, exc_val, exc_tb)
        self.close()
