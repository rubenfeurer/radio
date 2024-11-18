from unittest.mock import MagicMock
import subprocess
import time
from typing import List, Dict, Tuple, Any
import re
import logging

class WiFiManager:
    @staticmethod
    def scan_networks() -> List[Dict[str, Any]]:
        try:
            # Get current connection first
            current = WiFiManager.get_current_connection()
            current_ssid = current.get('ssid', '')

            # Force a rescan
            subprocess.run(
                ['sudo', 'iwlist', 'wlan0', 'scan'],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Get scan results with more detailed output
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,BARS', 'device', 'wifi', 'list', '--rescan', 'yes'],
                capture_output=True,
                text=True,
                check=True
            )

            networks = []
            seen_ssids = set()

            for line in result.stdout.strip().split('\n'):
                try:
                    if not line:
                        continue
                        
                    parts = line.split(':')
                    if len(parts) < 3:
                        continue
                        
                    ssid = parts[0].strip()
                    signal = parts[1]
                    security = parts[2] if len(parts) > 2 else ''
                    
                    # Enhanced validation for SSID
                    if not ssid or ssid.isspace() or '\x00' in ssid or len(ssid) < 1:
                        logging.debug(f"Skipping invalid SSID: {repr(ssid)}")
                        continue
                        
                    if ssid in seen_ssids:
                        logging.debug(f"Skipping duplicate SSID: {ssid}")
                        continue
                        
                    seen_ssids.add(ssid)
                    networks.append({
                        'ssid': ssid,
                        'signal': signal,
                        'security': security,
                        'active': ssid == current_ssid
                    })
                except Exception as e:
                    logging.warning(f"Error parsing network entry {line}: {str(e)}")
                    continue

            return sorted(networks, key=lambda x: int(x.get('signal', '0')), reverse=True)

        except subprocess.CalledProcessError as e:
            logging.error(f"Error running nmcli: {e.stderr}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in scan_networks: {str(e)}")
            return []

    @staticmethod
    def get_saved_connections() -> List[str]:
        try:
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show'],
                capture_output=True,
                text=True,
                check=True
            )
            saved = []
            for line in result.stdout.strip().split('\n'):
                if ':802-11-wireless' in line:  # Only get WiFi connections
                    saved.append(line.split(':')[0])
            return saved
        except Exception as e:
            print(f"Error getting saved connections: {str(e)}")
            return []

    @staticmethod
    def connect_to_network(ssid: str, password: str) -> dict:
        """Connect to a WiFi network."""
        try:
            result = subprocess.run(
                ['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return {'success': True, 'message': 'Successfully connected'}
            
            error_msg = result.stderr.lower()
            if 'password' in error_msg:
                return {'success': False, 'error': 'Incorrect password'}
            elif 'timeout' in error_msg:
                return {'success': False, 'error': 'Connection timed out'}
            elif 'device not found' in error_msg:
                return {'success': False, 'error': 'Network device not found'}
            else:
                return {'success': False, 'error': 'Failed to connect to network'}
            
        except Exception as e:
            logging.error(f"Error connecting to network: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def forget_network(ssid: str) -> Tuple[bool, str]:
        try:
            cmd = ['nmcli', 'connection', 'delete', ssid]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, "Network forgotten"
            return False, result.stderr
            
        except subprocess.SubprocessError as e:
            return False, str(e)

    @staticmethod
    def get_current_connection() -> dict:
        """Get current WiFi connection details"""
        try:
            # Run iwconfig to get current connection info
            result = subprocess.run(['iwconfig', 'wlan0'], capture_output=True, text=True)
            output = result.stdout

            if 'ESSID:' in output:
                # Extract SSID
                ssid = output.split('ESSID:')[1].split('"')[1]
                
                # Extract signal strength
                quality = 0
                if 'Quality=' in output:
                    quality_str = output.split('Quality=')[1].split(' ')[0]
                    try:
                        current, max_val = map(int, quality_str.split('/'))
                        quality = int((current / max_val) * 100)
                    except:
                        quality = 0

                if ssid:  # Only return if actually connected
                    return {
                        'ssid': ssid,
                        'signal': quality,
                        'connected': True
                    }
        except Exception as e:
            logging.error(f"Error getting current connection: {e}")
        
        return None

    @staticmethod
    def disconnect() -> Dict[str, Any]:
        """Disconnect from current WiFi network"""
        try:
            # Get current connection to check if we're actually connected
            current = WiFiManager.get_current_connection()
            if not current:
                return {'success': False, 'error': 'Not connected to any network'}

            # Run nmcli to disconnect
            result = subprocess.run(
                ['sudo', 'nmcli', 'device', 'disconnect', 'wlan0'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': result.stderr.strip() or 'Failed to disconnect'
                }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Disconnect operation timed out'}
        except Exception as e:
            logging.error(f"Error disconnecting from network: {str(e)}")
            return {'success': False, 'error': str(e)}