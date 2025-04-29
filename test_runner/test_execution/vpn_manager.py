import os
import subprocess
import asyncio
import time
import platform
import tempfile
import shutil

class VPNManager:
    """
    Manages VPN connections for test execution.
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
        self.temp_dir = None
        self.temp_config = None
    
    def __enter__(self):
        """
        Context manager entry.
        
        Returns:
            VPNManager: The VPN manager instance
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit.
        
        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        if self.connected:
            asyncio.run(self.disconnect())
    
    async def connect(self):
        """
        Connect to the VPN.
        
        Returns:
            bool: True if connected successfully, False otherwise
        """
        if self.connected:
            return True
        
        try:
            # Create a temporary directory for the config file
            self.temp_dir = tempfile.mkdtemp()
            self.temp_config = os.path.join(self.temp_dir, 'vpn_config.ovpn')
            
            # Copy the config file to the temporary directory
            shutil.copy(self.config_path, self.temp_config)
            
            # Connect to the VPN
            if platform.system() == 'Windows':
                await self._connect_windows()
            elif platform.system() == 'Linux':
                await self._connect_linux()
            elif platform.system() == 'Darwin':  # macOS
                await self._connect_macos()
            else:
                raise OSError(f"Unsupported operating system: {platform.system()}")
            
            # Wait for connection to establish
            for _ in range(10):
                if self.connected:
                    return True
                await asyncio.sleep(1)
            
            return self.connected
        except Exception as e:
            print(f"VPN connection error: {str(e)}")
            return False
    
    async def disconnect(self):
        """
        Disconnect from the VPN.
        
        Returns:
            bool: True if disconnected successfully, False otherwise
        """
        if not self.connected:
            return True
        
        try:
            if platform.system() == 'Windows':
                await self._disconnect_windows()
            elif platform.system() == 'Linux':
                await self._disconnect_linux()
            elif platform.system() == 'Darwin':  # macOS
                await self._disconnect_macos()
            else:
                raise OSError(f"Unsupported operating system: {platform.system()}")
            
            # Wait for disconnection
            for _ in range(10):
                if not self.connected:
                    return True
                await asyncio.sleep(1)
            
            return not self.connected
        except Exception as e:
            print(f"VPN disconnection error: {str(e)}")
            return False
        finally:
            # Clean up temporary files
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
    
    async def _connect_windows(self):
        """
        Connect to the VPN on Windows.
        """
        # Check if OpenVPN is installed
        try:
            subprocess.run(['openvpn', '--version'], check=True, capture_output=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            raise RuntimeError("OpenVPN is not installed or not in PATH")
        
        # Start OpenVPN process
        self.process = subprocess.Popen(
            ['openvpn', '--config', self.temp_config],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for connection
        await asyncio.sleep(2)
        
        # Check if process is still running
        if self.process.poll() is not None:
            raise RuntimeError("OpenVPN process terminated unexpectedly")
        
        # Set connected flag
        self.connected = True
    
    async def _connect_linux(self):
        """
        Connect to the VPN on Linux.
        """
        # Check if OpenVPN is installed
        try:
            subprocess.run(['openvpn', '--version'], check=True, capture_output=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            raise RuntimeError("OpenVPN is not installed or not in PATH")
        
        # Start OpenVPN process
        self.process = subprocess.Popen(
            ['sudo', 'openvpn', '--config', self.temp_config],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for connection
        await asyncio.sleep(2)
        
        # Check if process is still running
        if self.process.poll() is not None:
            raise RuntimeError("OpenVPN process terminated unexpectedly")
        
        # Set connected flag
        self.connected = True
    
    async def _connect_macos(self):
        """
        Connect to the VPN on macOS.
        """
        # Check if OpenVPN is installed
        try:
            subprocess.run(['openvpn', '--version'], check=True, capture_output=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            raise RuntimeError("OpenVPN is not installed or not in PATH")
        
        # Start OpenVPN process
        self.process = subprocess.Popen(
            ['sudo', 'openvpn', '--config', self.temp_config],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for connection
        await asyncio.sleep(2)
        
        # Check if process is still running
        if self.process.poll() is not None:
            raise RuntimeError("OpenVPN process terminated unexpectedly")
        
        # Set connected flag
        self.connected = True
    
    async def _disconnect_windows(self):
        """
        Disconnect from the VPN on Windows.
        """
        if self.process:
            # Terminate the process
            self.process.terminate()
            
            # Wait for process to terminate
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            
            self.process = None
        
        # Set disconnected flag
        self.connected = False
    
    async def _disconnect_linux(self):
        """
        Disconnect from the VPN on Linux.
        """
        if self.process:
            # Terminate the process
            subprocess.run(['sudo', 'kill', str(self.process.pid)], check=True)
            
            # Wait for process to terminate
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                subprocess.run(['sudo', 'kill', '-9', str(self.process.pid)], check=True)
            
            self.process = None
        
        # Set disconnected flag
        self.connected = False
    
    async def _disconnect_macos(self):
        """
        Disconnect from the VPN on macOS.
        """
        if self.process:
            # Terminate the process
            subprocess.run(['sudo', 'kill', str(self.process.pid)], check=True)
            
            # Wait for process to terminate
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                subprocess.run(['sudo', 'kill', '-9', str(self.process.pid)], check=True)
            
            self.process = None
        
        # Set disconnected flag
        self.connected = False 