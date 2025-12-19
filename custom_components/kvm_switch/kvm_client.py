import asyncio
import logging
import re
from typing import Callable, Dict, Optional, Set

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
        self._read_lock = asyncio.Lock()  # 用于同步读取操作
        self._status_queue = asyncio.Queue()  # 用于状态获取的响应队列
        self._waiting_for_status = False  # 标记是否正在等待状态响应
        
        # 状态获取命令映射
        self._status_commands = {
            1: {"decrease": b'cir 1d\r\n', "increase": b'cir 1e\r\n'},
            2: {"decrease": b'cir 05\r\n', "increase": b'cir 06\r\n'},
            3: {"decrease": b'cir 0d\r\n', "increase": b'cir 0e\r\n'},
            4: {"decrease": b'cir 15\r\n', "increase": b'cir 16\r\n'}
        }

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
                    
                    # 如果正在等待状态响应，将响应放入队列
                    if self._waiting_for_status:
                        await self._status_queue.put(response)
                    else:
                        # 否则正常处理响应
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
            
    async def get_current_status(self, output_port: int) -> int:
        """
        获取指定输出端口的当前输入源
        
        Args:
            output_port: 输出端口号 (1-4)
            
        Returns:
            当前输入源编号 (1-4), 如果获取失败返回None
        """
        if not self.connected:
            _LOGGER.error("Not connected to KVM switch")
            return None
            
        if output_port not in self._status_commands:
            _LOGGER.error(f"Invalid output port: {output_port}")
            return None
            
        commands = self._status_commands[output_port]
        current_input = None
        
        # 使用锁确保同一时间只有一个状态获取操作
        async with self._read_lock:
            try:
                self._waiting_for_status = True
                
                # 清空状态队列
                while not self._status_queue.empty():
                    try:
                        await self._status_queue.get()
                    except:
                        break
                        
                # 发送输入减1命令
                self.writer.write(commands["decrease"])
                await self.writer.drain()
                _LOGGER.debug(f"Sent status check command for Output {output_port}: {commands['decrease'].decode().strip()}")
                await asyncio.sleep(0.2)
                
                # 接收响应 - 从队列中获取
                response_str = ""
                start_time = asyncio.get_event_loop().time()
                while asyncio.get_event_loop().time() - start_time < 2:
                    try:
                        # 从队列中获取响应，超时0.5秒
                        response_line = await asyncio.wait_for(self._status_queue.get(), timeout=0.5)
                        response_str += response_line + "\n"
                    except asyncio.TimeoutError:
                        break
                        
                _LOGGER.debug(f"Response for Output {output_port}: {repr(response_str)}")
                
                # 解析响应
                status_lines = re.findall(r's\d+', response_str)
                
                for line in status_lines:
                    if len(line) >= 3:
                        status_port = int(line[1])
                        if status_port == output_port:
                            input_code = int(line[2])
                            current_input = input_code + 1
                            _LOGGER.debug(f"Parsed status: Output {status_port} -> Input {current_input}")
                
                # 发送输入加1命令恢复原始状态
                self.writer.write(commands["increase"])
                await self.writer.drain()
                _LOGGER.debug(f"Sent restore command for Output {output_port}: {commands['increase'].decode().strip()}")
                await asyncio.sleep(0.2)
                
                # 清空恢复命令的响应
                await asyncio.sleep(0.1)
                while not self._status_queue.empty():
                    try:
                        await self._status_queue.get()
                    except:
                        break
                        
            except Exception as e:
                _LOGGER.error(f"Error getting status for Output {output_port}: {e}")
                return None
            finally:
                self._waiting_for_status = False
            
        return current_input