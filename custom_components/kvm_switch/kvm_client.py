import asyncio
import logging
from typing import Callable, Dict

_LOGGER = logging.getLogger(__name__)

class KvmClient:
    def __init__(self, loop: asyncio.AbstractEventLoop, host: str, port: int):
        self.loop = loop
        self.host = host
        self.port = port
        self.reader: asyncio.StreamReader = None
        self.writer: asyncio.StreamWriter = None
        self.connected = False
        self._callbacks: Dict[str, Callable] = {}
        self._monitor_task: asyncio.Task = None

    async def connect(self) -> bool:
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.connected = True
            _LOGGER.info(f"Connected to KVM switch at {self.host}:{self.port}")
            self._start_monitoring()
            return True
        except (ConnectionRefusedError, OSError):
            _LOGGER.error(f"Failed to connect to KVM switch at {self.host}:{self.port}")
            return False

    async def disconnect(self):
        if self.connected:
            self.connected = False
            if self._monitor_task:
                self._monitor_task.cancel()
            self.writer.close()
            await self.writer.wait_closed()
            _LOGGER.info("Disconnected from KVM switch")

    def _start_monitoring(self):
        self._monitor_task = self.loop.create_task(self._monitor_connection())

    async def _monitor_connection(self):
        while self.connected:
            try:
                data = await self.reader.readuntil(b'\n')
                if data:
                    response = data.decode().strip()
                    _LOGGER.debug(f"Received from KVM: {response}")
                    self._handle_response(response)
            except asyncio.IncompleteReadError:
                _LOGGER.warning("Connection closed by KVM switch")
                self.connected = False
                break
            except Exception as e:
                _LOGGER.error(f"Error reading from KVM: {e}")
                await asyncio.sleep(1)

    def _handle_response(self, response: str):
        # 处理设备状态响应 - 移除所有换行符和回车符
        cleaned_response = response.strip()
        
        # 状态格式: s<output_port><device_code> (如s10, s23)
        if cleaned_response.startswith('s') and len(cleaned_response) >= 3:
            output_port = cleaned_response[1]
            device_code = cleaned_response[2:]
            
            # 验证输出口和设备代码
            if output_port.isdigit() and device_code.isdigit():
                if output_port in self._callbacks:
                    self._callbacks[output_port](device_code)
            else:
                _LOGGER.warning(f"Invalid state format: {cleaned_response}")

    def register_callback(self, output_port: str, callback: Callable):
        self._callbacks[output_port] = callback

    async def send_command(self, hex_command: str):
        if not self.connected:
            _LOGGER.error("Not connected to KVM switch")
            return False

        try:
            # 将十六进制字符串转换为字节
            command_bytes = bytes.fromhex(hex_command)
            self.writer.write(command_bytes)
            await self.writer.drain()
            _LOGGER.debug(f"Sent command: {hex_command}")
            return True
        except Exception as e:
            _LOGGER.error(f"Error sending command: {e}")
            return False