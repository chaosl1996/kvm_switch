import asyncio
import logging
from typing import Callable, Dict, Optional

_LOGGER = logging.getLogger(__name__)

class KvmClient:
                """KVM Switch Client - Simple and reliable implementation"""

                def __init__(self, loop: asyncio.AbstractEventLoop, host: str, port: int):
                                """Initialize KVM client"""
                                self.loop = loop
                                self.host = host
                                self.port = port
                                self.reader: Optional[asyncio.StreamReader] = None
                                self.writer: Optional[asyncio.StreamWriter] = None
                                self.connected = False
                                self._status_cache: Dict[int, int] = {}  # {output_port: input_source}
                                self._callbacks: Dict[str, Callable] = {}  # {output_port: callback}
                                self._monitor_task: Optional[asyncio.Task] = None

                async def connect(self) -> bool:
                                """Connect to KVM switch and start monitoring"""
                                try:
                                                _LOGGER.info(f"🔌 Connecting to KVM at {self.host}:{self.port}")
                                                self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
                                                self.connected = True
                                                _LOGGER.info("✅ Connected to KVM")

                                                # Start response monitoring
                                                self._start_monitoring()
                                                return True
                                except Exception as e:
                                                _LOGGER.error(f"❌ Failed to connect to KVM: {e}")
                                                self.connected = False
                                                return False

                async def disconnect(self):
                                """Disconnect from KVM switch"""
                                if self.connected:
                                                _LOGGER.info("🔌 Disconnecting from KVM")
                                                self.connected = False

                                                # Stop monitoring
                                                if self._monitor_task:
                                                                self._monitor_task.cancel()
                                                                self._monitor_task = None

                                                # Close connection
                                                if self.writer:
                                                                self.writer.close()
                                                                await self.writer.wait_closed()

                                                self.reader = None
                                                self.writer = None
                                                self._status_cache.clear()
                                                _LOGGER.info("✅ Disconnected from KVM")

                def _start_monitoring(self):
                                """Start response monitoring task"""
                                if self._monitor_task is None or self._monitor_task.done():
                                                self._monitor_task = self.loop.create_task(self._monitor_responses())

                async def _monitor_responses(self):
                                """Monitor KVM responses"""
                                _LOGGER.info("🔍 Starting KVM response monitoring")

                                while self.connected and self.reader:
                                                try:
                                                                data = await self.reader.readuntil(b'\n')
                                                                if data:
                                                                                response = data.decode().strip()
                                                                                # Only log responses that contain status information
                                                                                if response.startswith('s') or 'to' in response or 'bypass' in response.lower() or 'rx' in response.lower() or 'tx' in response.lower():
                                                                                                _LOGGER.info(f"📥 Received KVM response: '{response}'")
                                                                                await self._handle_response(response)
                                                except asyncio.IncompleteReadError:
                                                                _LOGGER.warning("⚠️  Connection closed by KVM")
                                                                await self.disconnect()
                                                                break
                                                except asyncio.TimeoutError:
                                                                # Skip timeout debug logs
                                                                pass
                                                except Exception as e:
                                                                _LOGGER.error(f"❌ Error reading from KVM: {e}")
                                                                await asyncio.sleep(1)

                                _LOGGER.info("🔴 KVM response monitoring stopped")

                async def _handle_response(self, response: str):
                                """Handle KVM responses with flexible parsing - extract any useful status information"""
                                # Only log status processing for responses that might contain status information
                                if response.startswith('s') or 'to' in response or 'bypass' in response.lower() or 'rx' in response.lower() or 'tx' in response.lower():
                                                _LOGGER.info(f"📥 Processing KVM response: '{response}'")

                                # Handle status responses - support multiple formats
                                if response.strip():
                                                try:
                                                                # Parse any response for potential status information
                                                                response_lower = response.lower()

                                                                # Case 1: Look for direct mappings like "Rx11 to Tx4" or "Rx12 to Tx5"
                                                                if "to" in response and ("rx" in response_lower or "tx" in response_lower):
                                                                                # Extract Rx and Tx numbers
                                                                                rx_match = None
                                                                                tx_match = None

                                                                                # Split into parts and look for Rx/Tx patterns
                                                                                parts = response.split()
                                                                                for part in parts:
                                                                                                if part.startswith("Rx") or part.startswith("rx"):
                                                                                                                rx_num = part[2:]
                                                                                                                if rx_num.isdigit():
                                                                                                                                rx_match = int(rx_num)
                                                                                                elif part.startswith("Tx") or part.startswith("tx"):
                                                                                                                tx_num = part[2:]
                                                                                                                if tx_num.isdigit():
                                                                                                                                tx_match = int(tx_num)

                                                                                if rx_match and tx_match:
                                                                                                # Map Rx/Tx numbers to output/input ports
                                                                                                # Rx11 -> Input 1, Rx12 -> Input 2, etc.
                                                                                                mapped_input = (rx_match - 11) + 1
                                                                                                # Tx4 -> Output 1, Tx5 -> Output 2, etc.
                                                                                                output_port = (tx_match - 4) + 1

                                                                                                # Validate extracted values
                                                                                                if 1 <= output_port <= 4 and 1 <= mapped_input <= 4:
                                                                                                                old_status = self._status_cache.get(output_port)
                                                                                                                self._status_cache[output_port] = mapped_input

                                                                                                                _LOGGER.info(f"📊 Status updated from Rx/Tx: Output {output_port} -> IN{mapped_input} (was IN{old_status if old_status else '?':<2})")

                                                                                                                # Notify callback if registered
                                                                                                                port_str = str(output_port)
                                                                                                                if port_str in self._callbacks:
                                                                                                                                device_code = mapped_input - 1
                                                                                                                                self._callbacks[port_str](str(device_code))
                                                                                                                return

                                                                # Case 2: Look for bypass information like "Bypass is 1 from In11(Legacy1) to Out[1/4]"
                                                                elif "bypass" in response_lower and "from" in response_lower and "to" in response_lower:
                                                                                # Extract input source from "In11" or "Rx11"
                                                                                input_source = None
                                                                                output_port = None

                                                                                # Look for In11 format
                                                                                if "in" in response_lower:
                                                                                                in_start = response_lower.find("in")
                                                                                                if in_start != -1:
                                                                                                                in_part = response[in_start:in_start+4]  # Get "In11"
                                                                                                                if in_part.startswith("In"):
                                                                                                                                in_num = in_part[2:]
                                                                                                                                if in_num.isdigit():
                                                                                                                                                input_source = int(in_num)

                                                                                # Look for Out[1/4] format
                                                                                if "out[" in response_lower:
                                                                                                out_start = response_lower.find("out[")
                                                                                                if out_start != -1:
                                                                                                                out_end = response_lower.find("]", out_start)
                                                                                                                if out_end != -1:
                                                                                                                                out_part = response[out_start+4:out_end]  # Get "1/4"
                                                                                                                                out_num = out_part.split("/")[0]
                                                                                                                                if out_num.isdigit():
                                                                                                                                                output_port = int(out_num)

                                                                                # Look for Tx4 format as backup
                                                                                if output_port is None and "tx" in response_lower:
                                                                                                for part in response.split():
                                                                                                                if part.startswith("Tx") or part.startswith("tx"):
                                                                                                                                tx_num = part[2:]
                                                                                                                                if tx_num.isdigit():
                                                                                                                                                output_port = (int(tx_num) - 4) + 1
                                                                                                                                                break

                                                                                if input_source and output_port:
                                                                                                mapped_input = (input_source - 11) + 1
                                                                                                if 1 <= output_port <= 4 and 1 <= mapped_input <= 4:
                                                                                                                old_status = self._status_cache.get(output_port)
                                                                                                                self._status_cache[output_port] = mapped_input

                                                                                                                _LOGGER.info(f"📊 Status updated from Bypass: Output {output_port} -> IN{mapped_input} (was IN{old_status if old_status else '?':<2})")

                                                                                                                # Notify callback if registered
                                                                                                                port_str = str(output_port)
                                                                                                                if port_str in self._callbacks:
                                                                                                                                device_code = mapped_input - 1
                                                                                                                                self._callbacks[port_str](str(device_code))
                                                                                                                return

                                                                # Case 3: Look for HDMI bypass port information like "** HDMI HDCP bypass port 6"
                                                                elif "bypass port" in response_lower:
                                                                                # Extract bypass port number
                                                                                bypass_port = None
                                                                                parts = response.split()
                                                                                for i, part in enumerate(parts):
                                                                                                if part == "port" and i + 1 < len(parts):
                                                                                                                port_num = parts[i+1]
                                                                                                                if port_num.isdigit():
                                                                                                                                bypass_port = int(port_num)
                                                                                                                                break

                                                                                if bypass_port:
                                                                                                # Map bypass port to output port (port 6 -> Output 1, port 7 -> Output 2, etc.)
                                                                                                output_port = (bypass_port - 6) + 1
                                                                                                # This might indicate the current active port
                                                                                                if 1 <= output_port <= 4:
                                                                                                                _LOGGER.info(f"🔍 Detected bypass port {bypass_port} -> Output {output_port}")
                                                                                                                # We can use this to infer current output port

                                                                # Case 4: Handle traditional status formats if they appear
                                                                elif response.startswith('s'):
                                                                                # Legacy format: "s10" (s[port][device_code])
                                                                                if len(response) >= 3:
                                                                                                output_port = int(response[1])
                                                                                                device_code = int(response[2:])
                                                                                                mapped_input = device_code + 1

                                                                                                if 1 <= output_port <= 4 and 1 <= mapped_input <= 4:
                                                                                                                old_status = self._status_cache.get(output_port)
                                                                                                                self._status_cache[output_port] = mapped_input

                                                                                                                _LOGGER.info(f"📊 Status updated from legacy format: Output {output_port} -> IN{mapped_input} (was IN{old_status if old_status else '?':<2})")

                                                                                                                # Notify callback if registered
                                                                                                                port_str = str(output_port)
                                                                                                                if port_str in self._callbacks:
                                                                                                                                device_code = mapped_input - 1
                                                                                                                                self._callbacks[port_str](str(device_code))
                                                                                                                return

                                                                # Case 5: Look for any digit patterns that might indicate port status
                                                                else:
                                                                                # Look for patterns like "1 from" or "2 to" that might indicate port numbers
                                                                                digits = [int(c) for c in response if c.isdigit()]
                                                                                if len(digits) >= 2:
                                                                                                # Check for patterns like 11,12,13,14 (Input sources) followed by 4,5,6,7 (Output targets)
                                                                                                input_candidates = [d for d in digits if 11 <= d <= 14]
                                                                                                output_candidates = [d for d in digits if 4 <= d <= 7]

                                                                                                if input_candidates and output_candidates:
                                                                                                                input_source = input_candidates[0]
                                                                                                                output_target = output_candidates[0]

                                                                                                                mapped_input = (input_source - 11) + 1
                                                                                                                output_port = (output_target - 4) + 1

                                                                                                                if 1 <= output_port <= 4 and 1 <= mapped_input <= 4:
                                                                                                                                old_status = self._status_cache.get(output_port)
                                                                                                                                self._status_cache[output_port] = mapped_input

                                                                                                                                _LOGGER.info(f"📊 Status inferred from digits: Output {output_port} -> IN{mapped_input} (was IN{old_status if old_status else '?':<2})")

                                                                                                                                # Notify callback if registered
                                                                                                                                port_str = str(output_port)
                                                                                                                                if port_str in self._callbacks:
                                                                                                                                                device_code = mapped_input - 1
                                                                                                                                                self._callbacks[port_str](str(device_code))
                                                                                                                                return
                                                except Exception as e:
                                                                _LOGGER.error(f"❌ Error processing response: {e}")

                def register_callback(self, output_port: str, callback: Callable):
                                """Register status update callback"""
                                self._callbacks[output_port] = callback
                                _LOGGER.info(f"📝 Registered callback for Output {output_port}")

                async def _send_command(self, command: bytes) -> bool:
                                """Send command to KVM"""
                                if not self.connected or not self.writer:
                                                _LOGGER.error("❌ Not connected to KVM")
                                                return False

                                try:
                                                self.writer.write(command)
                                                await self.writer.drain()
                                                # Only log commands sent during status detection or explicit user actions
                                                if b'cir' in command:
                                                                _LOGGER.info(f"📤 Sent command: {command.decode().strip()}")
                                                return True
                                except Exception as e:
                                                _LOGGER.error(f"❌ Error sending command: {e}")
                                                await self.disconnect()
                                                return False

                async def get_current_status(self, output_port: int) -> Optional[int]:
                                """Get current status for output port using safe status detection"""
                                _LOGGER.info(f"🔍 Getting status for Output {output_port}")

                                # Return cached status if available
                                if output_port in self._status_cache:
                                                cached_status = self._status_cache[output_port]
                                                _LOGGER.info(f"📋 Using cached status for Output {output_port}: IN{cached_status}")
                                                return cached_status

                                # Clear any existing status for this port before detection
                                if output_port in self._status_cache:
                                                del self._status_cache[output_port]

                                # Safe status detection: use commands that trigger status updates
                                # For most ports, use decrease/increase pattern to return to original state
                                # For Output 4, use the new strategy: increase once, get status, then directly restore using set_input_source
                                try:
                                                # If no cached status, use the safe status detection
                                                _LOGGER.info(f"🔄 Using safe status detection for Output {output_port}")

                                                # Clear any existing status for this port before detection
                                                if output_port in self._status_cache:
                                                                del self._status_cache[output_port]

                                                # Special handling for Output 4: new strategy
                                                if output_port == 4:
                                                                _LOGGER.info(f"🔄 Using special status detection for Output 4")

                                                                # Step 1: Send one increase command
                                                                increase_cmd = b'cir 16\r\n'
                                                                _LOGGER.info(f"📤 Step 1: Sending increase command for Output 4")
                                                                await self._send_command(increase_cmd)
                                                                await asyncio.sleep(0.5)  # Wait for response

                                                                # Step 2: Get the status after increase
                                                                _LOGGER.info(f"⏰ Step 2: Waiting for status after increase...")

                                                                # Check status cache for the increased status
                                                                increased_status = None
                                                                for attempt in range(5):
                                                                                await asyncio.sleep(0.5)
                                                                                if output_port in self._status_cache:
                                                                                                increased_status = self._status_cache[output_port]
                                                                                                _LOGGER.info(f"✅ Step 2: Status after increase: IN{increased_status}")
                                                                                                break
                                                                                _LOGGER.debug(f"⏰ Waiting for increased status... (Attempt {attempt + 1}/5)")

                                                                if increased_status is not None:
                                                                                # Step 3: Calculate original state based on increased status
                                                                                # Mapping: increased_status -> original_state
                                                                                # If increased_status is IN1 → original was IN4
                                                                                # If increased_status is IN2 → original was IN1
                                                                                # If increased_status is IN3 → original was IN2
                                                                                # If increased_status is IN4 → original was IN3
                                                                                original_state = increased_status - 1 if increased_status > 1 else 4
                                                                                _LOGGER.info(f"📊 Step 3: Original state inferred: IN{original_state}")

                                                                                # Step 4: Directly restore original state using set_input_source
                                                                                _LOGGER.info(f"📤 Step 4: Restoring original state IN{original_state} using set_input_source")
                                                                                success = await self.set_input_source(output_port, original_state)
                                                                                if success:
                                                                                                _LOGGER.info(f"✅ Step 4: Successfully restored Output 4 to IN{original_state}")
                                                                                else:
                                                                                                _LOGGER.warning(f"⚠️  Step 4: Failed to restore Output 4 to IN{original_state}")

                                                                                # Step 5: Return the inferred original state
                                                                                _LOGGER.info(f"✅ Step 5: Status detected and restored: Output {output_port} -> IN{original_state}")

                                                                                # Update cache with original state
                                                                                self._status_cache[output_port] = original_state
                                                                                return original_state
                                                else:
                                                                # Original strategy for other ports
                                                                safe_commands = {
                                                                                1: [b'cir 1d\r\n', b'cir 1e\r\n'],  # Output 1: decrease, increase
                                                                                2: [b'cir 05\r\n', b'cir 06\r\n'],  # Output 2: decrease, increase
                                                                                3: [b'cir 0d\r\n', b'cir 0e\r\n'],  # Output 3: decrease, increase
                                                                }

                                                                if output_port not in safe_commands:
                                                                                _LOGGER.error(f"❌ Invalid output port: {output_port}")
                                                                                return None

                                                                commands = safe_commands[output_port]

                                                                # Send commands in sequence to trigger status updates
                                                                for i, cmd in enumerate(commands, 1):
                                                                                _LOGGER.info(f"📤 Sending command {i}/{len(commands)} for Output {output_port}")
                                                                                await self._send_command(cmd)
                                                                                await asyncio.sleep(0.5)  # Wait for response

                                                # Wait for status updates to come in after all commands are sent
                                                _LOGGER.info(f"⏰ Waiting for KVM status updates...")

                                                # Check status cache every second for updates
                                                for attempt in range(10):  # Wait longer for status updates
                                                                await asyncio.sleep(1.0)
                                                                if output_port in self._status_cache:
                                                                                detected_status = self._status_cache[output_port]
                                                                                _LOGGER.info(f"✅ Status detected for Output {output_port}: IN{detected_status}")
                                                                                return detected_status
                                                                _LOGGER.debug(f"⏰ Waiting for status update... (Attempt {attempt + 1}/10)")

                                except Exception as e:
                                                _LOGGER.error(f"❌ Error during status detection: {e}", exc_info=True)

                                # If all methods fail, try direct query for the specific port
                                _LOGGER.warning(f"⚠️  Safe status detection failed for Output {output_port}, trying direct query")

                                try:
                                                # Direct query commands for each port
                                                direct_query_commands = {
                                                                1: b'cir 00\r\n',  # Output 1 query
                                                                2: b'cir 08\r\n',  # Output 2 query
                                                                3: b'cir 10\r\n',  # Output 3 query
                                                                4: b'cir 18\r\n',  # Output 4 query
                                                }

                                                if output_port in direct_query_commands:
                                                                query_cmd = direct_query_commands[output_port]
                                                                _LOGGER.info(f"📤 Sending direct query command for Output {output_port}")
                                                                await self._send_command(query_cmd)
                                                                await asyncio.sleep(1.0)  # Wait for response

                                                                # Check status cache again
                                                                if output_port in self._status_cache:
                                                                                detected_status = self._status_cache[output_port]
                                                                                _LOGGER.info(f"✅ Status detected via direct query: Output {output_port} -> IN{detected_status}")
                                                                                return detected_status
                                except Exception as e:
                                                _LOGGER.error(f"❌ Error during direct query: {e}", exc_info=True)

                                # If all methods fail, use a reasonable default but log it clearly
                                _LOGGER.warning(f"⚠️  All status detection methods failed for Output {output_port}, using default IN1")
                                default_status = 1  # Default to IN1
                                self._status_cache[output_port] = default_status
                                return default_status

                async def set_input_source(self, output_port: int, input_source: int) -> bool:
                                """Set input source for output port"""
                                _LOGGER.info(f"🎯 Setting Output {output_port} → IN{input_source}")

                                # Validate parameters
                                if not 1 <= output_port <= 4 or not 1 <= input_source <= 4:
                                                _LOGGER.error(f"❌ Invalid parameters: Output {output_port}, Input {input_source}")
                                                return False

                                # Get command for this output/input combination
                                command_key = f"OUT{output_port}_IN{input_source}"
                                commands = {
                                                "OUT1_IN1": b'cir 00\r\n',
                                                "OUT1_IN2": b'cir 01\r\n',
                                                "OUT1_IN3": b'cir 02\r\n',
                                                "OUT1_IN4": b'cir 03\r\n',
                                                "OUT2_IN1": b'cir 08\r\n',
                                                "OUT2_IN2": b'cir 09\r\n',
                                                "OUT2_IN3": b'cir 0a\r\n',
                                                "OUT2_IN4": b'cir 0b\r\n',
                                                "OUT3_IN1": b'cir 10\r\n',
                                                "OUT3_IN2": b'cir 11\r\n',
                                                "OUT3_IN3": b'cir 12\r\n',
                                                "OUT3_IN4": b'cir 13\r\n',
                                                "OUT4_IN1": b'cir 18\r\n',
                                                "OUT4_IN2": b'cir 19\r\n',
                                                "OUT4_IN3": b'cir 1a\r\n',
                                                "OUT4_IN4": b'cir 1b\r\n',
                                }

                                if command_key not in commands:
                                                _LOGGER.error(f"❌ Command not found: {command_key}")
                                                return False

                                # Send command
                                if not await self._send_command(commands[command_key]):
                                                return False

                                # Update cache immediately
                                self._status_cache[output_port] = input_source
                                await asyncio.sleep(0.3)

                                _LOGGER.info(f"✅ Successfully set Output {output_port} → IN{input_source}")
                                return True

