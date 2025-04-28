
import os
import subprocess
import asyncio
import platform
import logging

class VPNManager:
    """
    Manages VPN connections for test execution.
    Supports OpenVPN configurations.
    """
    
    def __init__(self, config_path):
        """
        Initialize the VPN manager with a configuration file.
        
        Args:
            config_path (str): Path to the VPN configuration file
        """
        self.config_path = config_path
        self.process = None
        self.connected = False
        self.system = platform.system()
        
    def __enter__(self):
        """Context manager entry point"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point - ensures VPN is disconnected"""
        asyncio.run(self.disconnect())
        
    async def connect(self):
        """
        Connect to the VPN using the provided configuration.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        if not os.path.exists(self.config_path):
            logging.error(f"VPN configuration file not found: {self.config_path}")
            return False
            
        try:
            # Determine the command based on the operating system
            if self.system == "Windows":
                # For Windows, use the OpenVPN GUI or command line
                cmd = ["openvpn", "--config", self.config_path]
            elif self.system == "Linux":
                # For Linux, use the openvpn command
                cmd = ["sudo", "openvpn", "--config", self.config_path, "--daemon"]
            elif self.system == "Darwin":  # macOS
                # For macOS, use the openvpn command
                cmd = ["sudo", "openvpn", "--config", self.config_path, "--daemon"]
            else:
                logging.error(f"Unsupported operating system: {self.system}")
                return False
                
            # Start the VPN process
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for connection to establish (this is a simplified approach)
            await asyncio.sleep(5)
            
            # Check if the process is still running
            if self.process.returncode is None:
                self.connected = True
                logging.info(f"Connected to VPN using {self.config_path}")
                return True
            else:
                stdout, stderr = await self.process.communicate()
                logging.error(f"VPN connection failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logging.error(f"Error connecting to VPN: {str(e)}")
            return False
            
    async def disconnect(self):
        """
        Disconnect from the VPN.
        
        Returns:
            bool: True if disconnection was successful, False otherwise
        """
        if not self.connected:
            return True
            
        try:
            # Terminate the VPN process if it's still running
            if self.process and self.process.returncode is None:
                self.process.terminate()
                await self.process.wait()
                
            # Additional cleanup based on the operating system
            if self.system == "Windows":
                # For Windows, no additional cleanup needed
                pass
            elif self.system in ["Linux", "Darwin"]:
                # For Linux and macOS, kill any remaining openvpn processes
                await asyncio.create_subprocess_shell(
                    "sudo pkill openvpn",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
            self.connected = False
            logging.info("Disconnected from VPN")
            return True
            
        except Exception as e:
            logging.error(f"Error disconnecting from VPN: {str(e)}")
            return False
            
    async def check_connection(self):
        """
        Check if the VPN connection is active.
        
        Returns:
            bool: True if connected, False otherwise
        """
        if not self.connected:
            return False
            
        try:
            # Simple ping test to check connectivity
            if self.system == "Windows":
                cmd = ["ping", "-n", "1", "8.8.8.8"]
            else:
                cmd = ["ping", "-c", "1", "8.8.8.8"]
                
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logging.error(f"Error checking VPN connection: {str(e)}")
            return False

